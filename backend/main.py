"""AcademicOS FastAPI backend — bridges SQLite databases to the Next.js frontend.

Every value returned by this API comes from a real database query.
No hardcoded data. Empty databases produce empty (honest) responses.

Run from project root:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from collections import deque

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from config.settings import (
    ALLOWED_ORIGINS,
    API_KEY,
    DB_ATTEMPTS,
    DB_EXAMINER,
    DB_MARKSCHEME,
    DB_PROGRESS,
    DB_QUESTION_BANK,
    RATE_LIMIT,
    RATE_LIMIT_WINDOW,
)
from db.models import get_db

logger = logging.getLogger(__name__)

app = FastAPI(title="AcademicOS API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*", "X-API-Key", "Authorization"],
)

if not API_KEY:
    logger.warning(
        "API_KEY is not set — the API is unauthenticated. Set API_KEY in the "
        "environment before exposing this service beyond localhost."
    )

# Routes reachable without an API key (health check / monitoring only).
_PUBLIC_PATHS = {"/api/health", "/", "/docs", "/openapi.json", "/redoc"}

# Simple in-process sliding-window rate limiter keyed by client IP.
_rate_buckets: dict[str, deque[float]] = {}


def _client_key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path

    # 1. Rate limiting (per client IP, sliding window).
    if path.startswith("/api/"):
        key = _client_key(request)
        now = time.monotonic()
        bucket = _rate_buckets.setdefault(key, deque())
        cutoff = now - RATE_LIMIT_WINDOW
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Slow down and retry shortly."},
                status_code=429,
            )
        bucket.append(now)

    # 2. API-key authentication (when configured), except for public paths.
    if API_KEY and path.startswith("/api/") and path not in _PUBLIC_PATHS:
        supplied = request.headers.get("x-api-key", "")
        if not supplied:
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                supplied = auth[7:].strip()
        if supplied != API_KEY:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    response = await call_next(request)

    # 3. Security response headers (defense in depth; HSTS only over HTTPS).
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
    )
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
    return response

# Spaced-repetition interval ceiling (days). Prevents date overflow on long
# streaks of strong reviews (see _update_mastery).
MAX_INTERVAL_DAYS = 365.0

# Map DB subject strings to frontend IDs
SUBJECT_ID: dict[str, str] = {
    "Physics": "physics",
    "Mathematics": "maths",
    "Further Mathematics": "fmaths",
    "Chemistry": "chemistry",
    "Computer Science": "cs",
}


def _log_db_error(db_path: Path, exc: sqlite3.Error) -> None:
    """Surface genuine failures loudly so schema drift / corruption / lock
    contention is not mistaken for 'no data yet' (the empty-list fallback keeps
    the UI alive, but operational errors must be observable)."""
    if isinstance(exc, sqlite3.OperationalError):
        logger.error("DB operational error on %s: %s", db_path.name, exc)
    else:
        logger.warning("Query failed on %s: %s", db_path.name, exc)


def _query(db_path: Path, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Read query returning list of dicts. Empty list if the DB/table is missing."""
    try:
        with get_db(db_path) as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error as exc:
        _log_db_error(db_path, exc)
        return []


def _scalar(db_path: Path, sql: str, params: tuple = (), default: Any = 0) -> Any:
    try:
        with get_db(db_path) as conn:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row and row[0] is not None else default
    except sqlite3.Error as exc:
        _log_db_error(db_path, exc)
        return default


def _utc_today() -> date:
    """Single source of 'today' — UTC, matching stored timestamps and SQLite
    DATE('now'). Avoids off-by-one between local server time and UTC rows."""
    return datetime.now(timezone.utc).date()


_DIFFICULTY_LABELS = ["", "Recall", "Standard", "Multi-step", "Advanced", "Trap"]


def _difficulty_label(value: Any) -> str:
    """Map a difficulty code to its label, tolerating NULL/out-of-range values."""
    if isinstance(value, int) and 0 <= value < len(_DIFFICULTY_LABELS):
        return _DIFFICULTY_LABELS[value]
    return ""


def _grade_from_mastery(mastery: float) -> str:
    if mastery >= 0.85:
        return "A*"
    if mastery >= 0.70:
        return "A"
    if mastery >= 0.55:
        return "B"
    if mastery >= 0.40:
        return "C"
    return "U"


def _projected_mastery(mastery: float, reviewed_fraction: float) -> float:
    """Project mastery forward based on review activity, not a blanket bump.

    The improvement buffer is earned by how much of the subject has actually
    been reviewed: nothing reviewed → projection equals current mastery
    (honest), fully reviewed → up to +0.10 of the remaining headroom-capped
    gain. Replaces the previous flat, data-independent +0.10.
    """
    reviewed_fraction = max(0.0, min(1.0, reviewed_fraction))
    headroom = max(0.0, 1.0 - mastery)
    buffer = min(0.10, headroom * 0.4) * reviewed_fraction
    return min(1.0, mastery + buffer)


def _exam_grade(pct: float) -> str:
    """Grade from an exam percentage using Edexcel IAL-style boundaries.

    Single source of truth for paper grades — mirrors the frontend
    `gradeFromPct` (lib/data.ts) so the same paper shows the same grade
    everywhere. Distinct from `_grade_from_mastery`, which bands 0–1 mastery.
    """
    if pct >= 90:
        return "A*"
    if pct >= 80:
        return "A"
    if pct >= 70:
        return "B"
    if pct >= 60:
        return "C"
    if pct >= 50:
        return "D"
    return "E"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def get_health() -> dict:
    questions = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM questions")
    papers = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM papers")
    ms_points = _scalar(DB_MARKSCHEME, "SELECT COUNT(*) FROM markscheme_entries")
    observations = _scalar(DB_EXAMINER, "SELECT COUNT(*) FROM observations")
    topics = _scalar(DB_PROGRESS, "SELECT COUNT(*) FROM spaced_repetition_items")
    due_today = _scalar(
        DB_PROGRESS,
        "SELECT COUNT(*) FROM spaced_repetition_items WHERE due_date <= DATE('now')",
    )
    attempts = _scalar(DB_ATTEMPTS, "SELECT COUNT(*) FROM attempts")
    sessions = _scalar(DB_ATTEMPTS, "SELECT COUNT(*) FROM sessions")

    return {
        "status": "ok",
        "databases": {
            "question_bank": {"questions": questions, "papers": papers},
            "markscheme": {"points": ms_points},
            "examiner_reports": {"observations": observations},
            "progress": {"topics": topics, "due_today": due_today},
            "attempts": {"total": attempts, "sessions": sessions},
        },
        "briefing_ready": questions > 0 and topics > 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------

@app.get("/api/papers")
def get_papers(
    subject: str | None = None,
    limit: int = Query(default=500, ge=1, le=500),
) -> list[dict]:
    where = "WHERE p.paper_type = 'question_paper'"
    params: list[Any] = []
    if subject:
        subj_name = next((k for k, v in SUBJECT_ID.items() if v == subject), subject)
        where += " AND p.subject = ?"
        params.append(subj_name)

    rows = _query(
        DB_QUESTION_BANK,
        f"""
        SELECT p.id, p.paper_code, p.subject, p.module_code, p.session, p.year,
               COUNT(q.id) AS question_count,
               COALESCE(SUM(q.marks), 0) AS total_marks
        FROM papers p
        LEFT JOIN questions q ON q.paper_id = p.id
        {where}
        GROUP BY p.id
        ORDER BY p.subject ASC, p.year DESC, p.session ASC
        LIMIT ?
        """,
        tuple(params) + (limit,),
    )

    # Latest completed session per paper (real scores only)
    session_rows = _query(
        DB_ATTEMPTS,
        """
        SELECT s.paper_id, s.id AS session_id, s.started_at, s.total_time_seconds,
               s.target_time_seconds,
               (SELECT COALESCE(SUM(a.marks_awarded), 0) FROM attempts a WHERE a.session_id = s.id) AS awarded,
               (SELECT COALESCE(SUM(a.marks_available), 0) FROM attempts a WHERE a.session_id = s.id) AS available
        FROM sessions s
        WHERE s.ended_at IS NOT NULL
        ORDER BY s.started_at DESC
        """,
    )
    latest_by_paper: dict[int, dict] = {}
    for s in session_rows:
        latest_by_paper.setdefault(s["paper_id"], s)

    today = _utc_today()
    result = []
    for r in rows:
        raw = r["paper_code"] or ""
        code = raw.split("_")[0] if "_" in raw else raw[:14]
        sess = latest_by_paper.get(r["id"])
        days_ago = None
        if sess and sess["started_at"]:
            try:
                started = datetime.fromisoformat(sess["started_at"]).date()
                days_ago = (today - started).days
            except ValueError:
                days_ago = None
        result.append({
            "id": str(r["id"]),
            "code": code,
            "full_code": raw,
            "subject": SUBJECT_ID.get(r["subject"] or "", (r["subject"] or "").lower()),
            "unit": r["module_code"] or "",
            "session": r["session"] or str(r["year"]),
            "year": r["year"],
            "question_count": r["question_count"] or 0,
            "total_marks": r["total_marks"] or 0,
            "score": sess["awarded"] if sess and sess["available"] else None,
            "max": sess["available"] if sess and sess["available"] else None,
            "time": round(sess["total_time_seconds"] / 60) if sess and sess["total_time_seconds"] else None,
            "target": round(sess["target_time_seconds"] / 60) if sess and sess["target_time_seconds"] else None,
            "days_ago": days_ago,
        })

    return result


@app.get("/api/papers/{paper_id}/questions")
def get_paper_questions(paper_id: int) -> dict:
    paper_rows = _query(
        DB_QUESTION_BANK,
        "SELECT id, paper_code, subject, module_code, session, year FROM papers WHERE id = ?",
        (paper_id,),
    )
    if not paper_rows:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
    paper = paper_rows[0]

    questions = _query(
        DB_QUESTION_BANK,
        """
        SELECT q.id, q.question_number, q.raw_text AS question_text, q.marks,
               q.difficulty, q.has_diagram, q.command_word,
               (SELECT qt.topic FROM question_topics qt
                WHERE qt.question_id = q.id AND qt.is_primary = 1 LIMIT 1) AS topic,
               (SELECT qt.subtopic FROM question_topics qt
                WHERE qt.question_id = q.id AND qt.is_primary = 1 LIMIT 1) AS subtopic
        FROM questions q
        WHERE q.paper_id = ?
        ORDER BY CAST(q.question_number AS INTEGER) ASC, q.question_number ASC
        """,
        (paper_id,),
    )

    q_ids = [q["id"] for q in questions]
    ms_by_question: dict[int, list[dict]] = {}
    if q_ids:
        placeholders = ",".join("?" * len(q_ids))
        ms_rows = _query(
            DB_MARKSCHEME,
            f"""
            SELECT question_id, mark_type, marks_value, description, sequence, conditionality
            FROM markscheme_entries
            WHERE question_id IN ({placeholders})
            ORDER BY question_id, sequence
            """,
            tuple(q_ids),
        )
        for m in ms_rows:
            ms_by_question.setdefault(m["question_id"], []).append({
                "code": f"{m['mark_type']}{m['marks_value']}",
                "mark_type": m["mark_type"],
                "marks_value": m["marks_value"],
                "text": m["description"],
                "sequence": m["sequence"],
                "conditionality": m["conditionality"],
            })

    for q in questions:
        q["id"] = str(q["id"])
        q["markscheme"] = ms_by_question.get(int(q["id"]), [])

    return {
        "paper": {
            "id": str(paper["id"]),
            "code": (paper["paper_code"] or "").split("_")[0],
            "full_code": paper["paper_code"],
            "subject": SUBJECT_ID.get(paper["subject"] or "", ""),
            "unit": paper["module_code"],
            "session": paper["session"],
            "year": paper["year"],
            "total_marks": sum(q["marks"] or 0 for q in questions),
        },
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# Single question — full intelligence package
# ---------------------------------------------------------------------------

@app.get("/api/questions/{question_id}")
def get_question(question_id: int) -> dict:
    rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT q.id, q.question_number, q.raw_text AS question_text, q.marks,
               q.difficulty, q.has_diagram, q.command_word, q.paper_id,
               p.paper_code, p.subject, p.module_code, p.session, p.year
        FROM questions q
        JOIN papers p ON p.id = q.paper_id
        WHERE q.id = ?
        """,
        (question_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    q = rows[0]

    topics = _query(
        DB_QUESTION_BANK,
        "SELECT topic, subtopic, is_primary FROM question_topics WHERE question_id = ?",
        (question_id,),
    )
    primary_topic = next(
        (t["topic"] for t in topics if t["is_primary"]),
        topics[0]["topic"] if topics else None,
    )

    markscheme = _query(
        DB_MARKSCHEME,
        """
        SELECT mark_type, marks_value, description, sequence, conditionality
        FROM markscheme_entries
        WHERE question_id = ?
        ORDER BY sequence
        """,
        (question_id,),
    )

    # Observations recorded against this exact question
    observations = _query(
        DB_EXAMINER,
        """
        SELECT description, observation_type, emphasis_level
        FROM observations
        WHERE question_id = ?
        ORDER BY emphasis_level DESC
        LIMIT 5
        """,
        (question_id,),
    )

    # Misconceptions for the question's topic
    misconceptions = []
    if primary_topic and primary_topic != "Unknown":
        misconceptions = _query(
            DB_EXAMINER,
            """
            SELECT description, topic, frequency
            FROM misconceptions
            WHERE is_active = 1 AND (topic LIKE '%' || ? || '%' OR ? LIKE '%' || topic || '%')
            ORDER BY frequency DESC
            LIMIT 3
            """,
            (primary_topic, primary_topic),
        )

    # Similar questions: same topic, spread of difficulties, not this one
    similar = []
    if primary_topic and primary_topic != "Unknown":
        similar = _query(
            DB_QUESTION_BANK,
            """
            SELECT q2.id, q2.question_number, q2.marks, q2.difficulty,
                   p2.paper_code, p2.session, p2.year, qt2.topic
            FROM question_topics qt2
            JOIN questions q2 ON q2.id = qt2.question_id
            JOIN papers p2 ON p2.id = q2.paper_id
            WHERE qt2.topic = ? AND q2.id != ?
              AND q2.raw_text IS NOT NULL AND LENGTH(TRIM(q2.raw_text)) > 40
            GROUP BY q2.id
            ORDER BY ABS(q2.difficulty - ?) ASC, RANDOM()
            LIMIT 3
            """,
            (primary_topic, question_id, q["difficulty"]),
        )

    previous_attempts = _query(
        DB_ATTEMPTS,
        """
        SELECT a.id, a.marks_awarded, a.marks_available, a.confidence,
               a.time_seconds, a.notes, a.created_at,
               GROUP_CONCAT(am.mistake_type) AS mistakes
        FROM attempts a
        LEFT JOIN attempt_mistakes am ON am.attempt_id = a.id
        WHERE a.question_id = ?
        GROUP BY a.id
        ORDER BY a.created_at DESC
        """,
        (question_id,),
    )

    return {
        "id": str(q["id"]),
        "question_number": q["question_number"],
        "question_text": q["question_text"],
        "marks": q["marks"],
        "difficulty": q["difficulty"],
        "has_diagram": q["has_diagram"],
        "command_word": q["command_word"],
        "paper": {
            "id": str(q["paper_id"]),
            "code": (q["paper_code"] or "").split("_")[0],
            "subject": SUBJECT_ID.get(q["subject"] or "", ""),
            "unit": q["module_code"],
            "session": q["session"],
            "year": q["year"],
        },
        "topic": primary_topic,
        "topics": topics,
        "markscheme": [
            {
                "code": f"{m['mark_type']}{m['marks_value']}",
                "mark_type": m["mark_type"],
                "marks_value": m["marks_value"],
                "text": m["description"],
                "conditionality": m["conditionality"],
            }
            for m in markscheme
        ],
        "examiner_observations": observations,
        "misconceptions": misconceptions,
        "similar_questions": [
            {
                "id": str(s["id"]),
                "label": (
                    f"Q{s['question_number']} · {(s['paper_code'] or '').split('_')[0]} "
                    f"{s['session']} · {s['marks']} marks · {s['topic']}"
                ),
            }
            for s in similar
        ],
        "previous_attempts": [
            {**a, "mistakes": (a["mistakes"] or "").split(",") if a["mistakes"] else []}
            for a in previous_attempts
        ],
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def _todays_priorities() -> list[dict]:
    rows = _query(
        DB_PROGRESS,
        """
        SELECT topic, subtopic, unit, subject, due_date, mastery,
               CAST(JULIANDAY('now') - JULIANDAY(due_date) AS INTEGER) AS days_overdue
        FROM spaced_repetition_items
        WHERE due_date <= DATE('now')
        ORDER BY mastery ASC, due_date ASC
        LIMIT 5
        """,
    )
    if not rows:
        return []

    for r in rows:
        # Most common mistake on questions matching this topic, from real attempts
        qid_rows = _query(
            DB_QUESTION_BANK,
            """
            SELECT question_id FROM question_topics
            WHERE topic LIKE '%' || ? || '%' OR ? LIKE '%' || topic || '%'
            """,
            (r["topic"], r["topic"]),
        )
        primary_mistake = None
        if qid_rows:
            qids = tuple(q["question_id"] for q in qid_rows)
            placeholders = ",".join("?" * len(qids))
            mistakes = _query(
                DB_ATTEMPTS,
                f"""
                SELECT am.mistake_type, COUNT(*) AS freq
                FROM attempt_mistakes am
                JOIN attempts a ON a.id = am.attempt_id
                WHERE a.question_id IN ({placeholders})
                GROUP BY am.mistake_type ORDER BY freq DESC LIMIT 1
                """,
                qids,
            )
            primary_mistake = mistakes[0]["mistake_type"] if mistakes else None
        r["primary_mistake"] = primary_mistake
        r["subject_id"] = SUBJECT_ID.get(r["subject"] or "", "")
    return rows


def _recent_papers(limit: int = 5) -> list[dict]:
    sessions = _query(
        DB_ATTEMPTS,
        """
        SELECT s.id, s.paper_id, s.started_at, s.ended_at,
               s.total_time_seconds, s.target_time_seconds,
               (SELECT COALESCE(SUM(a.marks_awarded), 0) FROM attempts a WHERE a.session_id = s.id) AS awarded,
               (SELECT COALESCE(SUM(a.marks_available), 0) FROM attempts a WHERE a.session_id = s.id) AS available
        FROM sessions s
        ORDER BY s.started_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    if not sessions:
        return []

    paper_ids = tuple({s["paper_id"] for s in sessions})
    placeholders = ",".join("?" * len(paper_ids))
    papers = {
        p["id"]: p
        for p in _query(
            DB_QUESTION_BANK,
            f"SELECT id, paper_code, subject, module_code, session, year FROM papers WHERE id IN ({placeholders})",
            paper_ids,
        )
    }

    result = []
    for s in sessions:
        p = papers.get(s["paper_id"], {})
        pct = (s["awarded"] / s["available"] * 100) if s["available"] else None
        result.append({
            "session_id": s["id"],
            "paper_id": str(s["paper_id"]),
            "code": (p.get("paper_code") or "").split("_")[0],
            "subject": SUBJECT_ID.get(p.get("subject") or "", ""),
            "unit": p.get("module_code") or "",
            "session": p.get("session") or "",
            "score": s["awarded"] if s["available"] else None,
            "max": s["available"] if s["available"] else None,
            "pct": round(pct) if pct is not None else None,
            "grade": _exam_grade(pct) if pct is not None else None,
            "time_seconds": s["total_time_seconds"],
            "target_seconds": s["target_time_seconds"],
            "started_at": s["started_at"],
            "completed": s["ended_at"] is not None,
        })
    return result


def _subject_mastery() -> list[dict]:
    rows = _query(
        DB_PROGRESS,
        """
        SELECT subject, AVG(mastery) AS avg_mastery, COUNT(*) AS topic_count,
               SUM(CASE WHEN last_reviewed IS NOT NULL THEN 1 ELSE 0 END) AS reviewed_count
        FROM spaced_repetition_items
        GROUP BY subject
        ORDER BY subject
        """,
    )
    unit_rows = _query(
        DB_PROGRESS,
        """
        SELECT subject, unit, AVG(mastery) AS mastery, COUNT(*) AS topics,
               SUM(CASE WHEN mastery < 0.4 AND last_reviewed IS NOT NULL THEN 1 ELSE 0 END) AS weak_topics
        FROM spaced_repetition_items
        GROUP BY subject, unit
        ORDER BY subject, unit
        """,
    )
    # Question counts per module from the question bank (module codes may differ
    # in spacing: progress "Unit1" vs papers "Unit 1" — match with spaces stripped)
    qcount_rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT p.subject, p.module_code, COUNT(q.id) AS n
        FROM papers p JOIN questions q ON q.paper_id = p.id
        GROUP BY p.subject, p.module_code
        """,
    )
    qcounts = {
        (r["subject"], (r["module_code"] or "").replace(" ", "")): r["n"]
        for r in qcount_rows
    }

    # Per-topic detail for unit drill-down
    topic_rows = _query(
        DB_PROGRESS,
        """
        SELECT subject, unit, topic, mastery, last_reviewed
        FROM spaced_repetition_items
        ORDER BY subject, unit, topic
        """,
    )
    topics_by_unit: dict[tuple, list[dict]] = {}
    for t in topic_rows:
        topics_by_unit.setdefault((t["subject"], t["unit"]), []).append({
            "name": t["topic"],
            "mastery": round((t["mastery"] or 0.0) * 100),
            "reviewed": t["last_reviewed"] is not None,
        })

    units_by_subject: dict[str, list[dict]] = {}
    for u in unit_rows:
        units_by_subject.setdefault(u["subject"], []).append({
            "code": u["unit"],
            "mastery": round((u["mastery"] or 0.0) * 100),
            "topic_count": u["topics"],
            "weak_topics": u["weak_topics"] or 0,
            "questions": qcounts.get((u["subject"], (u["unit"] or "").replace(" ", "")), 0),
            "topics": topics_by_unit.get((u["subject"], u["unit"]), []),
        })

    result = []
    for r in rows:
        mastery = r["avg_mastery"] or 0.0
        reviewed_fraction = (r["reviewed_count"] or 0) / (r["topic_count"] or 1)
        result.append({
            "subject": r["subject"],
            "subject_id": SUBJECT_ID.get(r["subject"] or "", ""),
            "mastery_pct": round(mastery * 100, 1),
            "topic_count": r["topic_count"],
            "reviewed_count": r["reviewed_count"],
            "current_grade": _grade_from_mastery(mastery),
            "predicted_grade": _grade_from_mastery(_projected_mastery(mastery, reviewed_fraction)),
            "units": units_by_subject.get(r["subject"], []),
        })
    return result


def _predicted_grades() -> list[dict]:
    mastery_rows = _query(
        DB_PROGRESS,
        """
        SELECT subject, AVG(mastery) AS m,
               CAST(SUM(CASE WHEN last_reviewed IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)
                   / COUNT(*) AS reviewed_fraction
        FROM spaced_repetition_items GROUP BY subject
        """,
    )
    # Attempt counts per subject (confidence basis) — real attempts joined to topics
    attempts_by_subject: dict[str, int] = {}
    attempt_qids = _query(DB_ATTEMPTS, "SELECT question_id FROM attempts")
    if attempt_qids:
        qids = tuple({a["question_id"] for a in attempt_qids})
        placeholders = ",".join("?" * len(qids))
        for r in _query(
            DB_QUESTION_BANK,
            f"""
            SELECT p.subject, COUNT(*) AS n
            FROM questions q JOIN papers p ON p.id = q.paper_id
            WHERE q.id IN ({placeholders})
            GROUP BY p.subject
            """,
            qids,
        ):
            attempts_by_subject[r["subject"]] = r["n"]

    result = []
    for r in mastery_rows:
        mastery = r["m"] or 0.0
        n_attempts = attempts_by_subject.get(r["subject"], 0)
        confidence = "high" if n_attempts >= 50 else "medium" if n_attempts >= 15 else "low"
        result.append({
            "subject": r["subject"],
            "subject_id": SUBJECT_ID.get(r["subject"] or "", ""),
            "current": _grade_from_mastery(mastery),
            "predicted": _grade_from_mastery(
                _projected_mastery(mastery, r["reviewed_fraction"] or 0.0)
            ),
            "confidence": confidence,
            "attempt_count": n_attempts,
        })
    return result


def _examiner_traps(limit: int = 5) -> list[dict]:
    # Weak topics (mastery < 0.6) from progress.db
    weak = _query(
        DB_PROGRESS,
        "SELECT topic, subject FROM spaced_repetition_items WHERE mastery < 0.6",
    )
    traps = _query(
        DB_EXAMINER,
        """
        SELECT description, topic, subject, module_code, frequency
        FROM misconceptions
        WHERE is_active = 1
        ORDER BY frequency DESC
        LIMIT 50
        """,
    )
    def _shape(rows: list[dict]) -> list[dict]:
        return [
            {
                "text": t["description"],
                "topic": t["topic"] or t["module_code"] or "",
                "subject": t["subject"] or "",
                "freq": t["frequency"] or 1,
            }
            for t in rows
        ]

    if not weak:
        # Always emit the contract shape {text, topic, subject, freq}.
        return _shape(traps[:limit])

    weak_topics = {(w["topic"] or "").lower() for w in weak}
    prioritised = sorted(
        traps,
        key=lambda t: (
            0 if any(
                wt and t["topic"] and (wt in t["topic"].lower() or t["topic"].lower() in wt)
                for wt in weak_topics
            ) else 1,
            -(t["frequency"] or 0),
        ),
    )
    return _shape(prioritised[:limit])


def _question_of_day() -> dict | None:
    from briefing.generator import select_question_of_the_day

    qod = select_question_of_the_day()
    if not qod:
        return None

    markscheme = _query(
        DB_MARKSCHEME,
        """
        SELECT mark_type, marks_value, description
        FROM markscheme_entries WHERE question_id = ? ORDER BY sequence
        """,
        (qod["id"],),
    )
    return {
        "id": str(qod["id"]),
        "topic": qod.get("priority_topic") or qod.get("module_code") or "",
        "unit": qod.get("module_code") or "",
        "subject": SUBJECT_ID.get(qod.get("subject") or "", ""),
        "marks": qod["marks"],
        "difficulty": _difficulty_label(qod["difficulty"]),
        "text": (qod["raw_text"] or "").strip()[:400],
        "markscheme": [
            {"code": f"{m['mark_type']}{m['marks_value']}", "text": m["description"]}
            for m in markscheme
        ],
    }


def _streak() -> int:
    # Count days with genuine study activity: completed sessions only, so merely
    # opening a paper in the Timer (which creates a session) does not inflate it.
    days = _query(
        DB_ATTEMPTS,
        """
        SELECT DISTINCT DATE(started_at) AS day
        FROM sessions
        WHERE ended_at IS NOT NULL
          AND started_at >= DATE('now', '-60 days')
        ORDER BY day DESC
        """,
    )
    day_set = {d["day"] for d in days}
    streak = 0
    cursor = _utc_today()
    while cursor.isoformat() in day_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _paper_totals() -> dict:
    """True completed-paper count and overall average, over ALL marked sessions
    (not the 5-row `recent_papers` slice). Keeps Home and Analytics consistent."""
    rows = _query(
        DB_ATTEMPTS,
        """
        SELECT
            (SELECT COALESCE(SUM(a.marks_awarded), 0) FROM attempts a WHERE a.session_id = s.id) AS awarded,
            (SELECT COALESCE(SUM(a.marks_available), 0) FROM attempts a WHERE a.session_id = s.id) AS available
        FROM sessions s
        WHERE s.ended_at IS NOT NULL
        """,
    )
    pcts = [r["awarded"] / r["available"] * 100 for r in rows if (r["available"] or 0) > 0]
    return {
        "completed_papers": len(pcts),
        "average_score": round(sum(pcts) / len(pcts)) if pcts else None,
    }


@app.get("/api/dashboard")
def get_dashboard() -> dict:
    return {
        "todays_priorities": _todays_priorities(),
        "recent_papers": _recent_papers(),
        "paper_totals": _paper_totals(),
        "subject_mastery": _subject_mastery(),
        "predicted_grades": _predicted_grades(),
        "examiner_traps": _examiner_traps(),
        "question_of_day": _question_of_day(),
        "streak": _streak(),
        # No universities table exists; an empty list is honest.
        "university_readiness": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    paper_id: int
    started_at: str = ""
    official_time_seconds: int = Field(default=0, ge=0)
    target_time_seconds: int = Field(default=0, ge=0)


@app.post("/api/sessions")
def create_session(body: SessionCreate) -> dict:
    exists = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM papers WHERE id = ?", (body.paper_id,))
    if not exists:
        raise HTTPException(status_code=404, detail=f"Paper {body.paper_id} not found")

    started = body.started_at or datetime.now(timezone.utc).isoformat()
    with get_db(DB_ATTEMPTS) as conn:
        cur = conn.execute(
            """
            INSERT INTO sessions (paper_id, started_at, official_time_seconds, target_time_seconds)
            VALUES (?, ?, ?, ?)
            """,
            (body.paper_id, started, body.official_time_seconds, body.target_time_seconds),
        )
        return {"session_id": cur.lastrowid}


class QuestionTimeLog(BaseModel):
    time_seconds: int = Field(ge=0)
    status: str = Field(pattern="^(complete|skipped)$")


@app.patch("/api/sessions/{session_id}/questions/{question_id}")
def log_question_time(session_id: int, question_id: int, body: QuestionTimeLog) -> dict:
    with get_db(DB_ATTEMPTS) as conn:
        sess = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not sess:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        conn.execute(
            """
            INSERT OR REPLACE INTO question_times (session_id, question_id, time_seconds, status)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, question_id, body.time_seconds, body.status),
        )
    return {"logged": True}


class SessionComplete(BaseModel):
    ended_at: str = ""
    total_time_seconds: int = Field(default=0, ge=0)


@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: int, body: SessionComplete) -> dict:
    ended = body.ended_at or datetime.now(timezone.utc).isoformat()
    with get_db(DB_ATTEMPTS) as conn:
        cur = conn.execute(
            "UPDATE sessions SET ended_at = ?, total_time_seconds = ? WHERE id = ?",
            (ended, body.total_time_seconds, session_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"completed": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------

class AttemptCreate(BaseModel):
    session_id: int | None = None
    question_id: int
    marks_awarded: int = Field(ge=0)
    marks_available: int = Field(gt=0)
    mistake_types: list[str] = []
    confidence: int = Field(ge=1, le=5)
    time_seconds: int = Field(default=0, ge=0)
    notes: str = ""
    answer_image_path: str | None = None

    @field_validator("answer_image_path")
    @classmethod
    def _safe_image_path(cls, v: str | None) -> str | None:
        """Reject absolute paths and traversal — store only a safe relative name.

        The client never supplies real filesystem paths; only a bare filename
        within the server-managed answers directory is permitted (defence
        against stored path-traversal if this value is ever served as a file).
        """
        if v is None or v == "":
            return v
        candidate = PurePosixPath(v)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in v:
            raise ValueError("answer_image_path must be a relative filename without traversal")
        return v


def _update_mastery(question_id: int, score_pct: float) -> tuple[float | None, str | None]:
    """Apply the spaced-repetition update to every SR item matching the
    question's primary topic. Returns (new_mastery, next_review_date)."""
    topic_rows = _query(
        DB_QUESTION_BANK,
        "SELECT topic FROM question_topics WHERE question_id = ? AND is_primary = 1 LIMIT 1",
        (question_id,),
    )
    if not topic_rows or topic_rows[0]["topic"] in (None, "", "Unknown"):
        return None, None
    topic = topic_rows[0]["topic"]

    with get_db(DB_PROGRESS) as conn:
        items = conn.execute(
            """
            SELECT id, mastery, ease_factor, interval_days
            FROM spaced_repetition_items
            WHERE topic LIKE '%' || ? || '%' OR ? LIKE '%' || topic || '%'
            """,
            (topic, topic),
        ).fetchall()
        if not items:
            logger.warning(
                "No spaced_repetition_items matched topic %r; mastery not updated. "
                "Was progress.db seeded (db/seed_syllabus.py)?",
                topic,
            )
            return None, None

        new_mastery = None
        next_review = None
        for item in items:
            mastery = (item["mastery"] * 0.7) + (score_pct * 0.3)
            ease = item["ease_factor"]
            interval = item["interval_days"]
            if score_pct >= 0.8:
                interval = interval * ease
                ease = min(3.0, ease + 0.1)
            elif score_pct >= 0.6:
                pass  # interval unchanged
            else:
                interval = max(1.0, interval * 0.5)
                ease = max(1.3, ease - 0.2)
            # Clamp the interval so a long streak of strong reviews can never
            # overflow the date arithmetic below (max ~1 year between reviews).
            interval = min(interval, MAX_INTERVAL_DAYS)
            due = (_utc_today() + timedelta(days=round(interval))).isoformat()
            conn.execute(
                """
                UPDATE spaced_repetition_items
                SET mastery = ?, ease_factor = ?, interval_days = ?,
                    due_date = ?, last_reviewed = DATE('now')
                WHERE id = ?
                """,
                (mastery, ease, interval, due, item["id"]),
            )
            if new_mastery is None:
                new_mastery, next_review = mastery, due
        return new_mastery, next_review


@app.post("/api/attempts")
def create_attempt(body: AttemptCreate) -> dict:
    q = _query(
        DB_QUESTION_BANK,
        "SELECT id, marks, paper_id FROM questions WHERE id = ?",
        (body.question_id,),
    )
    if not q:
        raise HTTPException(status_code=404, detail=f"Question {body.question_id} not found")
    if body.marks_awarded > body.marks_available:
        raise HTTPException(status_code=422, detail="marks_awarded cannot exceed marks_available")

    session_paper_id: int | None = None
    if body.session_id is not None:
        sess_rows = _query(
            DB_ATTEMPTS, "SELECT paper_id FROM sessions WHERE id = ?", (body.session_id,)
        )
        if not sess_rows:
            raise HTTPException(status_code=404, detail=f"Session {body.session_id} not found")
        session_paper_id = sess_rows[0]["paper_id"]
        # Reject attempts whose question does not belong to the session's paper.
        if session_paper_id is not None and q[0]["paper_id"] != session_paper_id:
            raise HTTPException(
                status_code=422,
                detail="Question does not belong to the session's paper",
            )

    # If no explicit time was supplied, reuse the time recorded by the Timer for
    # this (session, question) so attempts carry real per-question durations.
    time_seconds = body.time_seconds
    if time_seconds == 0 and body.session_id is not None:
        logged = _scalar(
            DB_ATTEMPTS,
            "SELECT time_seconds FROM question_times WHERE session_id = ? AND question_id = ?",
            (body.session_id, body.question_id),
            default=0,
        )
        time_seconds = logged or 0

    now = datetime.now(timezone.utc).isoformat()
    with get_db(DB_ATTEMPTS) as conn:
        # Re-marking a question within a session replaces the prior attempt
        # rather than inserting a duplicate (one attempt per session/question).
        if body.session_id is not None:
            stale = conn.execute(
                "SELECT id FROM attempts WHERE session_id = ? AND question_id = ?",
                (body.session_id, body.question_id),
            ).fetchall()
            for row in stale:
                conn.execute("DELETE FROM attempt_mistakes WHERE attempt_id = ?", (row["id"],))
                conn.execute("DELETE FROM attempts WHERE id = ?", (row["id"],))

        cur = conn.execute(
            """
            INSERT INTO attempts (session_id, question_id, marks_awarded, marks_available,
                                  confidence, time_seconds, notes, answer_image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.session_id, body.question_id, body.marks_awarded, body.marks_available,
                body.confidence, time_seconds, body.notes, body.answer_image_path, now,
            ),
        )
        attempt_id = cur.lastrowid
        for mistake in set(body.mistake_types):
            if mistake.strip():
                conn.execute(
                    "INSERT OR IGNORE INTO attempt_mistakes (attempt_id, mistake_type) VALUES (?, ?)",
                    (attempt_id, mistake.strip()),
                )

    score_pct = body.marks_awarded / body.marks_available
    new_mastery, next_review = _update_mastery(body.question_id, score_pct)

    return {
        "attempt_id": attempt_id,
        "new_mastery": round(new_mastery, 4) if new_mastery is not None else None,
        "next_review": next_review,
        "marks_awarded": body.marks_awarded,
    }


# ---------------------------------------------------------------------------
# Weaknesses
# ---------------------------------------------------------------------------

@app.get("/api/weaknesses")
def get_weaknesses() -> dict:
    attempts = _query(
        DB_ATTEMPTS,
        """
        SELECT question_id,
               SUM(marks_awarded) AS awarded,
               SUM(marks_available) AS available,
               COUNT(*) AS n
        FROM attempts
        GROUP BY question_id
        """,
    )
    if not attempts:
        return {
            "weaknesses": [],
            "confidence_traps": [],
            "message": "Complete some papers first to see your weakness analysis",
        }

    # Confidence traps: rated 4-5 confident but scored ≤ 50%
    trap_rows = _query(
        DB_ATTEMPTS,
        """
        SELECT question_id, confidence, marks_awarded, marks_available, created_at
        FROM attempts
        WHERE confidence >= 4 AND marks_available > 0
          AND CAST(marks_awarded AS FLOAT) / marks_available <= 0.5
        ORDER BY created_at DESC
        LIMIT 6
        """,
    )
    confidence_traps = []
    for t in trap_rows:
        topic_row = _query(
            DB_QUESTION_BANK,
            "SELECT topic FROM question_topics WHERE question_id = ? AND is_primary = 1 LIMIT 1",
            (t["question_id"],),
        )
        topic = topic_row[0]["topic"] if topic_row else ""
        pct = round(t["marks_awarded"] / t["marks_available"] * 100)
        confidence_traps.append({
            "text": (
                f"Scored {t['marks_awarded']}/{t['marks_available']} on {topic or 'a question'} "
                f"but rated confidence {t['confidence']}"
            ),
            "topic": topic,
            "conf": t["confidence"],
            "score": pct,
        })

    qids = tuple(a["question_id"] for a in attempts)
    placeholders = ",".join("?" * len(qids))
    topic_rows = _query(
        DB_QUESTION_BANK,
        f"""
        SELECT qt.question_id, qt.topic, qt.subtopic, qt.subject, qt.module_code AS unit
        FROM question_topics qt
        WHERE qt.question_id IN ({placeholders}) AND qt.is_primary = 1
        """,
        qids,
    )
    topic_by_qid = {t["question_id"]: t for t in topic_rows}

    # Aggregate per (topic, subtopic)
    agg: dict[tuple, dict] = {}
    for a in attempts:
        t = topic_by_qid.get(a["question_id"])
        if not t or t["topic"] in (None, "", "Unknown"):
            continue
        key = (t["topic"], t["subtopic"])
        entry = agg.setdefault(key, {
            "topic": t["topic"],
            "subtopic": t["subtopic"] or "",
            "subject": SUBJECT_ID.get(t["subject"] or "", ""),
            "unit": t["unit"] or "",
            "attempts": 0, "awarded": 0, "available": 0,
            "question_ids": [],
        })
        entry["attempts"] += a["n"]
        entry["awarded"] += a["awarded"]
        entry["available"] += a["available"]
        entry["question_ids"].append(a["question_id"])

    weaknesses = []
    for entry in agg.values():
        if entry["attempts"] < 2 or not entry["available"]:
            continue
        q_placeholders = ",".join("?" * len(entry["question_ids"]))
        mistakes = _query(
            DB_ATTEMPTS,
            f"""
            SELECT am.mistake_type, COUNT(*) AS freq
            FROM attempt_mistakes am
            JOIN attempts a ON a.id = am.attempt_id
            WHERE a.question_id IN ({q_placeholders})
            GROUP BY am.mistake_type
            ORDER BY freq DESC
            LIMIT 2
            """,
            tuple(entry["question_ids"]),
        )
        weaknesses.append({
            "topic": entry["topic"],
            "subtopic": entry["subtopic"],
            "subject": entry["subject"],
            "unit": entry["unit"],
            "attempts": entry["attempts"],
            "avg": round(entry["awarded"] / entry["available"] * 100),
            "lost": entry["available"] - entry["awarded"],
            "primary": mistakes[0]["mistake_type"] if mistakes else "",
            "secondary": mistakes[1]["mistake_type"] if len(mistakes) > 1 else "",
            "breakdown": [{"tag": m["mistake_type"], "n": m["freq"]} for m in mistakes],
        })

    weaknesses.sort(key=lambda w: -w["lost"])
    return {"weaknesses": weaknesses, "confidence_traps": confidence_traps, "message": None}


# ---------------------------------------------------------------------------
# Status / coverage (Settings + Analytics screens)
# ---------------------------------------------------------------------------

@app.get("/api/status")
def get_status() -> dict:
    qb_papers = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM papers")
    qb_qcount = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM questions")
    er_reports = _scalar(DB_EXAMINER, "SELECT COUNT(*) FROM reports")
    er_misc = _scalar(DB_EXAMINER, "SELECT COUNT(*) FROM misconceptions WHERE is_active=1")
    ms_count = _scalar(DB_MARKSCHEME, "SELECT COUNT(*) FROM markscheme_entries")
    sr_items = _scalar(DB_PROGRESS, "SELECT COUNT(*) FROM spaced_repetition_items")
    att_count = _scalar(DB_ATTEMPTS, "SELECT COUNT(*) FROM attempts")
    sess_count = _scalar(DB_ATTEMPTS, "SELECT COUNT(*) FROM sessions")

    return {
        "databases": [
            {"name": "question_bank.db", "label": f"{qb_papers:,} papers · {qb_qcount:,} questions", "ok": qb_papers > 0},
            {"name": "markscheme.db", "label": f"{ms_count:,} mark points", "ok": ms_count > 0},
            {"name": "examiner_reports.db", "label": f"{er_reports} reports · {er_misc} misconceptions", "ok": er_reports > 0},
            {"name": "progress.db", "label": f"{sr_items} review items", "ok": sr_items > 0},
            {"name": "attempts.db", "label": f"{sess_count} sessions · {att_count} attempts", "ok": True},
        ]
    }


@app.get("/api/coverage")
def get_coverage() -> list[dict]:
    paper_rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT p.subject,
               COUNT(DISTINCT p.id) AS papers,
               COUNT(q.id) AS questions
        FROM papers p
        LEFT JOIN questions q ON q.paper_id = p.id
        WHERE p.paper_type = 'question_paper'
        GROUP BY p.subject
        ORDER BY COUNT(q.id) DESC
        """,
    )

    # Real attempted counts per subject from attempts.db
    attempted_map: dict[str, int] = {}
    attempt_qids = _query(DB_ATTEMPTS, "SELECT DISTINCT question_id FROM attempts")
    if attempt_qids:
        qids = tuple(a["question_id"] for a in attempt_qids)
        placeholders = ",".join("?" * len(qids))
        for r in _query(
            DB_QUESTION_BANK,
            f"""
            SELECT p.subject, COUNT(DISTINCT q.id) AS n
            FROM questions q JOIN papers p ON p.id = q.paper_id
            WHERE q.id IN ({placeholders})
            GROUP BY p.subject
            """,
            qids,
        ):
            attempted_map[r["subject"]] = r["n"]

    result = []
    for r in paper_rows:
        subj = r["subject"] or ""
        total_q = r["questions"] or 0
        attempted = attempted_map.get(subj, 0)
        result.append({
            "subject": subj,
            "subject_id": SUBJECT_ID.get(subj, subj.lower()),
            "papers": r["papers"] or 0,
            "total_questions": total_q,
            "attempted": attempted,
            "pct": round(attempted / total_q * 100) if total_q else 0,
        })
    return result


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------

@app.get("/api/briefing")
def get_briefing() -> dict:
    from briefing.generator import generate_daily_briefing

    b = generate_daily_briefing()
    return {
        "date": b.date,
        "academic": b.section1_academic,
        "curriculum": b.section2_curriculum,
        "revision": b.section3_revision,
        "status": b.section4_status,
    }


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@app.get("/api/analytics")
def get_analytics() -> dict:
    # Score trend from real completed sessions
    sessions = _query(
        DB_ATTEMPTS,
        """
        SELECT s.id, s.started_at,
               (SELECT COALESCE(SUM(a.marks_awarded), 0) FROM attempts a WHERE a.session_id = s.id) AS awarded,
               (SELECT COALESCE(SUM(a.marks_available), 0) FROM attempts a WHERE a.session_id = s.id) AS available
        FROM sessions s
        WHERE s.ended_at IS NOT NULL
        ORDER BY s.started_at ASC
        LIMIT 30
        """,
    )
    trend = [
        round(s["awarded"] / s["available"] * 100)
        for s in sessions
        if (s["available"] or 0) > 0
    ]

    # Confidence calibration from real attempts
    calibration = _query(
        DB_ATTEMPTS,
        """
        SELECT confidence AS conf,
               ROUND(AVG(CAST(marks_awarded AS FLOAT) / marks_available * 100)) AS score
        FROM attempts
        WHERE confidence IS NOT NULL AND marks_available > 0
        GROUP BY confidence
        ORDER BY confidence
        """,
    )

    return {
        "score_trend": trend,
        "sessions": len(sessions),
        "calibration": calibration,
    }
