"""AcademicOS FastAPI backend — bridges SQLite databases to the Next.js frontend.

Run from project root:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="AcademicOS API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

# Map DB subject strings to frontend IDs
SUBJECT_ID: dict[str, str] = {
    "Physics": "physics",
    "Mathematics": "maths",
    "Further Mathematics": "fmaths",
    "Chemistry": "chemistry",
    "Computer Science": "cs",
}


def _query(db_path: Path, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Run a query, returning empty list on any error (uninitialised DB, missing table, etc.)."""
    try:
        from db.models import get_db
        with get_db(db_path) as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception as exc:
        logger.debug("DB query skipped (%s): %s", db_path.name, exc)
        return []


def _scalar(db_path: Path, sql: str, params: tuple = (), default: Any = 0) -> Any:
    try:
        from db.models import get_db
        with get_db(db_path) as conn:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else default
    except Exception as exc:
        logger.debug("DB scalar skipped (%s): %s", db_path.name, exc)
        return default


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------

@app.get("/api/status")
def get_status() -> dict:
    from config.settings import DB_QUESTION_BANK, DB_EXAMINER, DB_MARKSCHEME, DB_ANALYTICS

    qb_papers  = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM papers")
    qb_qcount  = _scalar(DB_QUESTION_BANK, "SELECT COUNT(*) FROM questions")
    er_reports = _scalar(DB_EXAMINER, "SELECT COUNT(*) FROM reports")
    er_misc    = _scalar(DB_EXAMINER, "SELECT COUNT(*) FROM misconceptions WHERE is_active=1")
    ms_count   = _scalar(DB_MARKSCHEME, "SELECT COUNT(DISTINCT question_id) FROM markscheme_entries", default=0)
    pr_sessions = _scalar(DB_ANALYTICS, "SELECT COUNT(*) FROM revision_sessions")

    return {
        "databases": [
            {
                "name": "question_bank.db",
                "label": f"{qb_papers:,} papers · {qb_qcount:,} questions",
                "ok": qb_papers > 0,
            },
            {
                "name": "examiner_reports.db",
                "label": f"{er_reports} reports · {er_misc} misconceptions",
                "ok": True,
            },
            {
                "name": "markscheme.db",
                "label": f"{ms_count:,} questions marked up",
                "ok": ms_count > 0,
            },
            {
                "name": "progress.db",
                "label": f"{pr_sessions} sessions",
                "ok": True,
            },
        ]
    }


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------

@app.get("/api/papers")
def get_papers(subject: str | None = None, limit: int = 200) -> list[dict]:
    from config.settings import DB_QUESTION_BANK

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
               COUNT(q.id) AS question_count
        FROM papers p
        LEFT JOIN questions q ON q.paper_id = p.id
        {where}
        GROUP BY p.id
        ORDER BY p.year DESC, p.subject
        LIMIT ?
        """,
        tuple(params) + (limit,),
    )

    result = []
    for r in rows:
        raw = r["paper_code"] or ""
        # Extract human-readable code (first segment for standard IAL codes)
        code = raw.split("_")[0] if "_" in raw else raw[:14]
        result.append({
            "id": str(r["id"]),
            "code": code,
            "full_code": raw,
            "subject": SUBJECT_ID.get(r["subject"] or "", (r["subject"] or "").lower()),
            "unit": r["module_code"] or "",
            "session": r["session"] or str(r["year"]),
            "year": r["year"],
            "question_count": r["question_count"] or 0,
            # Score fields are null until analytics.db has session data
            "score": None,
            "max": None,
            "time": None,
            "target": None,
            "days_ago": None,
        })

    return result


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

@app.get("/api/coverage")
def get_coverage() -> list[dict]:
    from config.settings import DB_QUESTION_BANK, DB_ANALYTICS

    paper_rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT p.subject,
               COUNT(DISTINCT p.id)  AS papers,
               COUNT(q.id)           AS questions
        FROM papers p
        LEFT JOIN questions q ON q.paper_id = p.id
        WHERE p.paper_type = 'question_paper'
        GROUP BY p.subject
        ORDER BY COUNT(q.id) DESC
        """,
    )

    session_rows = _query(
        DB_ANALYTICS,
        "SELECT subject, SUM(questions_attempted) AS attempted FROM revision_sessions GROUP BY subject",
    )
    attempted_map = {r["subject"]: (r["attempted"] or 0) for r in session_rows}

    result = []
    for r in paper_rows:
        subj = r["subject"] or ""
        total_q = r["questions"] or 0
        attempted = attempted_map.get(subj, 0)
        pct = round(attempted / total_q * 100) if total_q > 0 and attempted > 0 else 0
        result.append({
            "subject": subj,
            "subject_id": SUBJECT_ID.get(subj, subj.lower()),
            "papers": r["papers"] or 0,
            "total_questions": total_q,
            "attempted": attempted,
            "pct": pct,
        })

    return result


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def get_dashboard() -> dict:
    from config.settings import DB_QUESTION_BANK, DB_ANALYTICS, DB_EXAMINER, DB_PROGRESS

    # Aggregate metrics from analytics
    stats_rows = _query(
        DB_ANALYTICS,
        """
        SELECT
            SUM(questions_attempted)                              AS total_q,
            AVG(marks_awarded * 100.0 / NULLIF(marks_available, 0)) AS avg_score,
            COUNT(*)                                             AS sessions
        FROM revision_sessions
        """,
    )
    stats = stats_rows[0] if stats_rows else {}

    # Due reviews from progress
    due_rows = _query(
        DB_PROGRESS,
        """
        SELECT sc.next_review, sc.confidence, sp.spec_ref, sp.description
        FROM syllabus_completion sc
        JOIN specification_points sp ON sp.id = sc.spec_point_id
        WHERE sc.next_review <= date('now') AND sc.status NOT IN ('not_started')
        ORDER BY sc.next_review ASC, sc.confidence ASC
        LIMIT 5
        """,
    )

    # Top examiner traps
    trap_rows = _query(
        DB_EXAMINER,
        """
        SELECT subject, module_code, topic, description, frequency
        FROM misconceptions
        WHERE is_active = 1
        ORDER BY frequency DESC
        LIMIT 6
        """,
    )

    # Question of the day: the most substantive real question available.
    # Marks/difficulty were not reliably captured by the extraction pipeline,
    # so we rank by a command word being present + text length rather than
    # fabricating a difficulty rating.
    qod_rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT q.id, q.raw_text, q.marks, q.difficulty, q.command_word,
               p.subject, p.module_code
        FROM questions q
        JOIN papers p ON q.paper_id = p.id
        WHERE q.raw_text IS NOT NULL
          AND LENGTH(TRIM(q.raw_text)) BETWEEN 120 AND 900
          AND q.command_word IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1
        """,
    )
    if not qod_rows:
        qod_rows = _query(
            DB_QUESTION_BANK,
            """
            SELECT q.id, q.raw_text, q.marks, q.difficulty, q.command_word,
                   p.subject, p.module_code
            FROM questions q JOIN papers p ON q.paper_id = p.id
            WHERE q.raw_text IS NOT NULL AND LENGTH(TRIM(q.raw_text)) > 120
            ORDER BY LENGTH(q.raw_text) DESC
            LIMIT 1
            """,
        )

    qod = None
    if qod_rows:
        r = qod_rows[0]
        diff = r["difficulty"] or 2
        qod = {
            "id": str(r["id"]),
            "topic": (r["command_word"] or "").title() or r["module_code"] or r["subject"] or "Practice",
            "unit": r["module_code"] or r["subject"] or "",
            "marks": r["marks"] or 0,
            "difficulty": "Hard" if diff >= 4 else "Medium" if diff >= 3 else "Standard",
            "text": (r["raw_text"] or "").strip()[:320],
        }

    return {
        "metrics": {
            "total_questions_attempted": int(stats.get("total_q") or 0),
            "avg_score": round(float(stats.get("avg_score") or 0), 1),
            "sessions": int(stats.get("sessions") or 0),
        },
        "due_reviews": [
            {
                "topic": r.get("description") or r.get("spec_ref") or "Review",
                "subject": "general",
                "status": f"Due {r['next_review']}",
                "overdue": True,
            }
            for r in due_rows
        ],
        "examiner_traps": [
            {
                "topic": r.get("module_code") or r.get("subject") or "",
                "text": r.get("description") or "",
                "years": [],
                "freq": int(r.get("frequency") or 1),
            }
            for r in trap_rows
        ],
        "question_of_day": qod,
    }


# ---------------------------------------------------------------------------
# Weaknesses
# ---------------------------------------------------------------------------

@app.get("/api/weaknesses")
def get_weaknesses() -> list[dict]:
    """Real module-level weaknesses computed from marked session_questions.

    session_questions (analytics.db) holds marks per question; questions/papers
    (question_bank.db) hold the module each question belongs to. Cross-DB join is
    done in Python: aggregate marks by module, rank by marks lost, attach the top
    examiner misconceptions for that module.
    """
    from config.settings import DB_ANALYTICS, DB_QUESTION_BANK, DB_EXAMINER

    marked = _query(
        DB_ANALYTICS,
        """
        SELECT question_id,
               COALESCE(marks_awarded, 0) AS awarded,
               marks_available AS available
        FROM session_questions
        WHERE marks_awarded IS NOT NULL
        """,
    )
    if not marked:
        return []

    # Map question_id -> (subject, module_code)
    qids = [m["question_id"] for m in marked]
    placeholders = ",".join("?" * len(qids))
    qmap_rows = _query(
        DB_QUESTION_BANK,
        f"""
        SELECT q.id, p.subject, p.module_code
        FROM questions q JOIN papers p ON q.paper_id = p.id
        WHERE q.id IN ({placeholders})
        """,
        tuple(qids),
    )
    qmap = {r["id"]: (r["subject"], r["module_code"]) for r in qmap_rows}

    # Aggregate by (subject, module)
    agg: dict[tuple, dict] = {}
    for m in marked:
        key = qmap.get(m["question_id"])
        if not key or key[0] is None:
            continue
        a = agg.setdefault(key, {"awarded": 0, "available": 0, "attempts": 0})
        a["awarded"] += m["awarded"] or 0
        a["available"] += m["available"] or 0
        a["attempts"] += 1

    result = []
    for (subject, module_code), a in agg.items():
        avail = a["available"] or 1
        avg = round(a["awarded"] / avail * 100)
        lost = a["available"] - a["awarded"]

        misc = _query(
            DB_EXAMINER,
            """
            SELECT description FROM misconceptions
            WHERE subject = ? AND module_code = ?
            ORDER BY frequency DESC LIMIT 2
            """,
            (subject, module_code),
        )
        primary   = misc[0]["description"] if misc else "No examiner data for this module yet"
        secondary = misc[1]["description"] if len(misc) > 1 else ""

        result.append({
            "subject":  SUBJECT_ID.get(subject or "", (subject or "").lower()),
            "unit":     module_code or "",
            "topic":    module_code or "",
            "subtopic": "",
            "attempts": a["attempts"],
            "avg":      avg,
            "lost":     lost,
            "primary":  primary,
            "secondary": secondary,
            "trap":     bool(misc),
            "trend":    "flat",
            "breakdown": [],
        })

    result.sort(key=lambda r: (-r["lost"], r["avg"]))
    return result


# ---------------------------------------------------------------------------
# Subject detail
# ---------------------------------------------------------------------------

@app.get("/api/subjects/{subject}")
def get_subject(subject: str) -> dict:
    """Real per-subject view: module mastery (progress.db), question counts
    (question_bank.db), and recent attempted papers (analytics.db)."""
    from config.settings import DB_PROGRESS, DB_QUESTION_BANK, DB_ANALYTICS

    subj_name = next((k for k, v in SUBJECT_ID.items() if v == subject), subject)

    # Per-module mastery from progress.db
    mastery_rows = _query(
        DB_PROGRESS,
        """
        SELECT m.code, m.name,
               COUNT(sp.id) AS total,
               SUM(CASE WHEN sc.status IN ('reviewed','mastered') THEN 1 ELSE 0 END) AS covered,
               AVG(sc.confidence) AS avg_conf
        FROM modules m
        JOIN subjects s ON m.subject_id = s.id
        JOIN topics t ON t.module_id = m.id
        JOIN subtopics st ON st.topic_id = t.id
        JOIN specification_points sp ON sp.subtopic_id = st.id
        LEFT JOIN syllabus_completion sc ON sc.spec_point_id = sp.id
        WHERE s.name = ?
        GROUP BY m.code
        ORDER BY m.sequence, m.code
        """,
        (subj_name,),
    )

    # Question counts per module from question_bank.db
    qcount_rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT module_code, COUNT(q.id) AS questions, COUNT(DISTINCT p.id) AS papers
        FROM papers p LEFT JOIN questions q ON q.paper_id = p.id
        WHERE p.subject = ? AND p.paper_type = 'question_paper'
        GROUP BY module_code
        """,
        (subj_name,),
    )
    qmap = {(r["module_code"] or "").replace(" ", ""): r for r in qcount_rows}

    units = []
    for r in mastery_rows:
        total = r["total"] or 0
        mastery = round((r["covered"] or 0) / total * 100) if total > 0 else 0
        qinfo = qmap.get((r["code"] or "").replace(" ", ""), {})
        units.append({
            "code": r["code"],
            "name": r["name"],
            "mastery": mastery,
            "spec_points": total,
            "questions": qinfo.get("questions", 0),
            "papers": qinfo.get("papers", 0),
            "confidence": round(float(r["avg_conf"] or 0), 1),
        })

    # Recent attempted papers from analytics.db
    attempts = _query(
        DB_ANALYTICS,
        """
        SELECT rs.id, rs.module_code, rs.started_at, rs.marks_awarded,
               rs.marks_available, rs.duration_seconds, rs.paper_id
        FROM revision_sessions rs
        WHERE rs.subject = ? AND rs.ended_at IS NOT NULL
        ORDER BY rs.started_at DESC LIMIT 10
        """,
        (subj_name,),
    )

    totals = {
        "papers": sum(u["papers"] for u in units),
        "questions": sum(u["questions"] for u in units),
        "sessions": len(attempts),
    }

    return {
        "subject": subject,
        "name": subj_name,
        "units": units,
        "recent_attempts": [
            {
                "id": str(a["id"]),
                "unit": a["module_code"] or "",
                "started_at": a["started_at"],
                "score": a["marks_awarded"],
                "max": a["marks_available"],
                "pct": round((a["marks_awarded"] or 0) / a["marks_available"] * 100)
                       if (a["marks_available"] or 0) > 0 else 0,
                "minutes": round((a["duration_seconds"] or 0) / 60),
            }
            for a in attempts
        ],
        "totals": totals,
    }


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------

@app.get("/api/briefing")
def get_briefing() -> dict:
    try:
        from briefing.generator import generate_daily_briefing
        b = generate_daily_briefing()
        return {
            "date": b.date,
            "academic":   b.section1_academic,
            "curriculum": b.section2_curriculum,
            "revision":   b.section3_revision,
            "status":     b.section4_status,
        }
    except Exception as exc:
        logger.error("Briefing generation error: %s", exc)
        return {"date": "", "academic": "", "curriculum": "", "revision": "", "status": ""}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@app.get("/api/analytics")
def get_analytics() -> dict:
    from config.settings import DB_ANALYTICS

    sessions = _query(
        DB_ANALYTICS,
        """
        SELECT marks_awarded, marks_available, started_at
        FROM revision_sessions
        WHERE marks_available > 0
        ORDER BY started_at ASC
        LIMIT 30
        """,
    )

    trend = [
        round(s["marks_awarded"] / s["marks_available"] * 100)
        for s in sessions
        if (s["marks_available"] or 0) > 0
    ]

    return {"score_trend": trend, "sessions": len(sessions)}


# ---------------------------------------------------------------------------
# Paper questions
# ---------------------------------------------------------------------------

@app.get("/api/papers/{paper_id}/questions")
def get_paper_questions(paper_id: int) -> list[dict]:
    from config.settings import DB_QUESTION_BANK

    rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT id, question_number, marks, command_word, difficulty,
               raw_text, latex_text, has_diagram
        FROM questions
        WHERE paper_id = ?
        ORDER BY CAST(question_number AS INTEGER), question_number
        """,
        (paper_id,),
    )
    return [
        {
            "id": str(r["id"]),
            "n": r["question_number"] or str(i + 1),
            "marks": r["marks"] or 1,
            "text": (r["raw_text"] or "").strip(),
            "latex": r["latex_text"] or "",
            "difficulty": r["difficulty"] or 2,
            "has_diagram": bool(r["has_diagram"]),
        }
        for i, r in enumerate(rows)
    ]


@app.get("/api/questions/{question_id}")
def get_question(question_id: int) -> dict:
    from config.settings import DB_QUESTION_BANK, DB_MARKSCHEME, DB_EXAMINER

    q_rows = _query(DB_QUESTION_BANK, "SELECT * FROM questions WHERE id = ?", (question_id,))
    if not q_rows:
        raise HTTPException(status_code=404, detail="Question not found")
    q = q_rows[0]

    p_rows = _query(DB_QUESTION_BANK, "SELECT * FROM papers WHERE id = ?", (q["paper_id"],))
    paper = p_rows[0] if p_rows else {}

    scheme = _query(
        DB_MARKSCHEME,
        "SELECT mark_type, description, marks_value FROM markscheme_entries WHERE question_id = ? ORDER BY sequence",
        (question_id,),
    )

    paper_code = paper.get("paper_code") or ""
    obs = _query(
        DB_EXAMINER,
        "SELECT observation_text FROM observations WHERE paper_code = ? LIMIT 3",
        (paper_code,),
    )

    return {
        "id": str(question_id),
        "n": q["question_number"] or "1",
        "marks": q["marks"] or 1,
        "text": (q["raw_text"] or "").strip(),
        "latex": q["latex_text"] or "",
        "difficulty": q["difficulty"] or 2,
        "has_diagram": bool(q["has_diagram"]),
        "paper_code": paper_code,
        "session": paper.get("session") or str(paper.get("year") or ""),
        "subject": paper.get("subject") or "",
        "module_code": paper.get("module_code") or "",
        "markscheme": [
            {
                "code": f"{r['mark_type'] or 'M'}{r['marks_value'] or 1}",
                "text": r["description"] or "",
            }
            for r in scheme
        ],
        "examiner": obs[0]["observation_text"] if obs else None,
    }


# ---------------------------------------------------------------------------
# Sessions (timer flow)
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    paper_id: str
    target_seconds: int = 3600


class QuestionUpdate(BaseModel):
    time_seconds: int | None = None
    status: str = "complete"
    awarded: int | None = None
    tags: list[str] = []
    confidence: int = 3
    note: str = ""


@app.post("/api/sessions")
def create_session(body: SessionCreate) -> dict:
    from config.settings import DB_ANALYTICS, DB_QUESTION_BANK
    from db.models import get_db

    p_rows = _query(
        DB_QUESTION_BANK,
        "SELECT subject, module_code FROM papers WHERE id = ?",
        (int(body.paper_id),),
    )
    paper = p_rows[0] if p_rows else {"subject": "Unknown", "module_code": None}

    with get_db(DB_ANALYTICS) as conn:
        cursor = conn.execute(
            """
            INSERT INTO revision_sessions
                (started_at, subject, module_code, session_type, paper_id, target_seconds)
            VALUES (?, ?, ?, 'mock_exam', ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                paper["subject"],
                paper.get("module_code"),
                int(body.paper_id),
                body.target_seconds,
            ),
        )
        conn.commit()
        return {"id": str(cursor.lastrowid)}


@app.patch("/api/sessions/{session_id}/questions/{question_id}")
def update_session_question(session_id: int, question_id: int, body: QuestionUpdate) -> dict:
    from config.settings import DB_ANALYTICS, DB_QUESTION_BANK
    from db.models import get_db

    marks_row = _query(
        DB_QUESTION_BANK,
        "SELECT marks FROM questions WHERE id = ?",
        (question_id,),
    )
    marks_available = (marks_row[0]["marks"] if marks_row else 1) or 1

    outcome = "skipped"
    if body.awarded is not None:
        if body.awarded == marks_available:
            outcome = "correct"
        elif body.awarded == 0:
            outcome = "incorrect"
        else:
            outcome = "partial"

    with get_db(DB_ANALYTICS) as conn:
        conn.execute(
            """
            INSERT INTO session_questions
                (session_id, question_id, marks_available, time_seconds, outcome, marks_awarded)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, question_id) DO UPDATE SET
                time_seconds = CASE WHEN excluded.time_seconds IS NOT NULL
                    THEN excluded.time_seconds ELSE session_questions.time_seconds END,
                marks_awarded = CASE WHEN excluded.marks_awarded IS NOT NULL
                    THEN excluded.marks_awarded ELSE session_questions.marks_awarded END,
                outcome = CASE WHEN excluded.marks_awarded IS NOT NULL
                    THEN excluded.outcome ELSE session_questions.outcome END
            """,
            (session_id, question_id, marks_available, body.time_seconds, outcome, body.awarded),
        )
        if body.awarded is not None:
            conn.execute(
                """
                UPDATE revision_sessions SET
                    questions_attempted = (
                        SELECT COUNT(*) FROM session_questions
                        WHERE session_id = ? AND marks_awarded IS NOT NULL),
                    questions_correct = (
                        SELECT COUNT(*) FROM session_questions
                        WHERE session_id = ? AND outcome = 'correct'),
                    questions_partial = (
                        SELECT COUNT(*) FROM session_questions
                        WHERE session_id = ? AND outcome = 'partial')
                WHERE id = ?
                """,
                (session_id, session_id, session_id, session_id),
            )
        conn.commit()

    score_pct = (
        round(body.awarded / marks_available * 100)
        if body.awarded is not None and marks_available > 0
        else None
    )
    return {"ok": True, "outcome": outcome, "score_pct": score_pct}


def _update_mastery(subject: str | None, module_code: str | None, score_pct: float) -> int:
    """Update syllabus_completion mastery for every spec point under a module.

    Applies the context.md spaced-repetition policy based on the session score:
      >=80% → reviewed, confidence 5, +14d interval
      60-79% → in_progress, confidence 3, +7d interval
      <60%  → in_progress, confidence 2, +2d interval (flag for review)

    Scoped by subject AND module code — module codes like "Unit4" exist under
    multiple subjects (Physics, Chemistry), so subject scoping is required to
    avoid cross-subject contamination. Returns the number of spec points updated.
    No per-question spec linkage exists, so the result is applied across the module.
    """
    if not module_code or not subject:
        return 0
    from datetime import date, timedelta
    from config.settings import DB_PROGRESS
    from db.models import get_db

    norm = module_code.replace(" ", "")  # "Unit 4" -> "Unit4"

    if score_pct >= 80:
        status, confidence, interval = "reviewed", 5, 14
    elif score_pct >= 60:
        status, confidence, interval = "in_progress", 3, 7
    else:
        status, confidence, interval = "in_progress", 2, 2

    today = date.today()
    next_review = (today + timedelta(days=interval)).isoformat()
    today_iso = today.isoformat()

    try:
        with get_db(DB_PROGRESS) as conn:
            spec_ids = [
                r[0] for r in conn.execute(
                    """
                    SELECT sp.id
                    FROM specification_points sp
                    JOIN subtopics st ON sp.subtopic_id = st.id
                    JOIN topics t ON st.topic_id = t.id
                    JOIN modules m ON t.module_id = m.id
                    JOIN subjects s ON m.subject_id = s.id
                    WHERE m.code = ? AND s.name = ?
                    """,
                    (norm, subject),
                ).fetchall()
            ]
            for sid in spec_ids:
                conn.execute(
                    """
                    INSERT INTO syllabus_completion
                        (spec_point_id, status, confidence, first_taught,
                         last_reviewed, next_review, review_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(spec_point_id) DO UPDATE SET
                        status = excluded.status,
                        confidence = excluded.confidence,
                        last_reviewed = excluded.last_reviewed,
                        next_review = excluded.next_review,
                        review_count = syllabus_completion.review_count + 1
                    """,
                    (sid, status, confidence, today_iso, today_iso, next_review),
                )
            conn.commit()
            return len(spec_ids)
    except Exception as exc:
        logger.error("Mastery update failed for module %s: %s", module_code, exc)
        return 0


@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: int) -> dict:
    from config.settings import DB_ANALYTICS
    from db.models import get_db

    with get_db(DB_ANALYTICS) as conn:
        # Aggregate the session result and persist totals
        agg = conn.execute(
            """
            SELECT COALESCE(SUM(marks_awarded), 0)   AS awarded,
                   COALESCE(SUM(marks_available), 0)  AS available,
                   COALESCE(SUM(time_seconds), 0)     AS total_time
            FROM session_questions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        awarded, available, total_time = agg["awarded"], agg["available"], agg["total_time"]
        score_pct = round(awarded / available * 100) if available > 0 else 0

        sess = conn.execute(
            "SELECT subject, module_code FROM revision_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        subject = sess["subject"] if sess else None
        module_code = sess["module_code"] if sess else None

        conn.execute(
            """
            UPDATE revision_sessions
            SET ended_at = ?, marks_awarded = ?, marks_available = ?, duration_seconds = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), awarded, available, total_time, session_id),
        )
        conn.commit()

    spec_updated = _update_mastery(subject, module_code, score_pct)

    return {
        "ok": True,
        "score_pct": score_pct,
        "marks_awarded": awarded,
        "marks_available": available,
        "spec_points_updated": spec_updated,
    }


# ---------------------------------------------------------------------------
# Attempts (marking flow)
# ---------------------------------------------------------------------------

class AttemptCreate(BaseModel):
    session_id: str | None = None
    question_id: str
    awarded: int
    max_marks: int
    confidence: int = 3
    tags: list[str] = []
    time_seconds: int = 0
    note: str = ""


@app.post("/api/attempts")
def create_attempt(body: AttemptCreate) -> dict:
    """Convenience endpoint — delegates to the session question upsert logic.
    Requires session_id when the question came from a timed session.
    """
    from config.settings import DB_ANALYTICS, DB_QUESTION_BANK
    from db.models import get_db

    marks_available = body.max_marks or 1
    outcome = "correct" if body.awarded == marks_available else (
        "incorrect" if body.awarded == 0 else "partial"
    )

    if not body.session_id:
        return {"ok": True, "outcome": outcome,
                "score_pct": round(body.awarded / marks_available * 100)}

    session_id = int(body.session_id)

    with get_db(DB_ANALYTICS) as conn:
        conn.execute(
            """
            INSERT INTO session_questions
                (session_id, question_id, marks_awarded, marks_available, time_seconds, outcome)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, question_id) DO UPDATE SET
                marks_awarded = excluded.marks_awarded,
                outcome = excluded.outcome,
                time_seconds = CASE WHEN session_questions.time_seconds > 0
                    THEN session_questions.time_seconds ELSE excluded.time_seconds END
            """,
            (session_id, int(body.question_id), body.awarded,
             marks_available, body.time_seconds, outcome),
        )
        conn.execute(
            """
            UPDATE revision_sessions SET
                questions_attempted = (
                    SELECT COUNT(*) FROM session_questions
                    WHERE session_id = ? AND marks_awarded IS NOT NULL),
                questions_correct = (
                    SELECT COUNT(*) FROM session_questions
                    WHERE session_id = ? AND outcome = 'correct'),
                questions_partial = (
                    SELECT COUNT(*) FROM session_questions
                    WHERE session_id = ? AND outcome = 'partial')
            WHERE id = ?
            """,
            (session_id, session_id, session_id, session_id),
        )
        conn.commit()

    return {
        "ok": True,
        "outcome": outcome,
        "score_pct": round(body.awarded / marks_available * 100),
    }


# ---------------------------------------------------------------------------
# Session summary
# ---------------------------------------------------------------------------

@app.get("/api/sessions/{session_id}/summary")
def get_session_summary(session_id: int) -> dict:
    from config.settings import DB_ANALYTICS, DB_QUESTION_BANK
    from db.models import get_db

    session_rows = _query(
        DB_ANALYTICS,
        "SELECT * FROM revision_sessions WHERE id = ?",
        (session_id,),
    )
    if not session_rows:
        raise HTTPException(status_code=404, detail="Session not found")
    sess = session_rows[0]

    qs = _query(
        DB_ANALYTICS,
        """
        SELECT sq.question_id, sq.marks_awarded, sq.marks_available, sq.outcome, sq.time_seconds
        FROM session_questions sq WHERE sq.session_id = ?
        """,
        (session_id,),
    )

    total_awarded = sum(q["marks_awarded"] or 0 for q in qs)
    total_available = sum(q["marks_available"] or 0 for q in qs)
    total_time = sum(q["time_seconds"] or 0 for q in qs)

    return {
        "session_id": session_id,
        "paper_id": sess.get("paper_id"),
        "subject": sess.get("subject"),
        "started_at": sess.get("started_at"),
        "ended_at": sess.get("ended_at"),
        "total_awarded": total_awarded,
        "total_available": total_available,
        "score_pct": round(total_awarded / total_available * 100) if total_available > 0 else 0,
        "total_time_seconds": total_time,
        "questions": len(qs),
    }
