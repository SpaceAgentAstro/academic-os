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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    ms_count   = _scalar(DB_MARKSCHEME, "SELECT COUNT(*) FROM markschemes", default=0)
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
                "label": f"{ms_count} schemes",
                "ok": True,
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

    # Random hard question for question-of-the-day
    qod_rows = _query(
        DB_QUESTION_BANK,
        """
        SELECT q.id, q.raw_text, q.marks, q.difficulty, p.subject, p.module_code
        FROM questions q
        JOIN papers p ON q.paper_id = p.id
        WHERE q.raw_text IS NOT NULL AND LENGTH(TRIM(q.raw_text)) > 40
          AND q.difficulty >= 4 AND q.marks >= 4
        ORDER BY RANDOM()
        LIMIT 1
        """,
    )

    qod = None
    if qod_rows:
        r = qod_rows[0]
        qod = {
            "id": str(r["id"]),
            "topic": r["module_code"] or r["subject"] or "Unknown",
            "unit": r["module_code"] or "",
            "marks": r["marks"] or 5,
            "difficulty": "Hard",
            "text": (r["raw_text"] or "").strip()[:300],
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
    from config.settings import DB_ANALYTICS, DB_EXAMINER

    trends = _query(
        DB_ANALYTICS,
        """
        SELECT subject, module_code, topic, avg_score, attempt_count, trend_direction
        FROM performance_trends
        ORDER BY avg_score ASC, attempt_count DESC
        LIMIT 20
        """,
    )

    result = []
    for r in trends:
        misc = _query(
            DB_EXAMINER,
            """
            SELECT description FROM misconceptions
            WHERE subject = ? AND module_code = ? AND topic = ?
            ORDER BY frequency DESC LIMIT 2
            """,
            (r["subject"], r["module_code"], r["topic"]),
        )
        primary   = misc[0]["description"] if misc else "No data yet"
        secondary = misc[1]["description"] if len(misc) > 1 else ""

        result.append({
            "subject": SUBJECT_ID.get(r["subject"] or "", (r["subject"] or "").lower()),
            "unit":     r["module_code"] or "",
            "topic":    r["topic"] or "",
            "subtopic": r["topic"] or "",
            "attempts": int(r["attempt_count"] or 0),
            "avg":      round(float(r["avg_score"] or 0)),
            "lost":     0,
            "primary":  primary,
            "secondary": secondary,
            "trap":     True,
            "trend":    r["trend_direction"] or "flat",
            "breakdown": [],
        })

    return result


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
        SELECT marks_awarded, marks_available, start_time
        FROM revision_sessions
        WHERE marks_available > 0
        ORDER BY start_time ASC
        LIMIT 30
        """,
    )

    trend = [
        round(s["marks_awarded"] / s["marks_available"] * 100)
        for s in sessions
        if (s["marks_available"] or 0) > 0
    ]

    return {"score_trend": trend, "sessions": len(sessions)}
