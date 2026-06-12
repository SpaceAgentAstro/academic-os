"""Misconception Agent — cross-source aggregation and corrective interventions.

Owned by: Misconception Agent
Writes to: examiner_reports.db (misconceptions, corrective_interventions)
Reads from: examiner_reports.db, question_bank.db
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def aggregate_misconceptions(
    subject: str,
    module_code: str,
    er_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Aggregate all active misconceptions for a subject/module, ordered by frequency.

    Returns dicts with id, subject, module_code, topic, subtopic, description,
    frequency, last_seen, source_count.
    """
    from config.settings import DB_EXAMINER
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT m.id, m.subject, m.module_code, m.topic, m.subtopic,
                   m.description, m.frequency, m.last_seen, m.is_active,
                   COUNT(ms.observation_id) AS source_count
            FROM misconceptions m
            LEFT JOIN misconception_sources ms ON ms.misconception_id = m.id
            WHERE m.subject = ? AND m.module_code = ? AND m.is_active = 1
            GROUP BY m.id
            ORDER BY m.frequency DESC, m.last_seen DESC
            """,
            (subject, module_code),
        ).fetchall()
        return [dict(r) for r in rows]

    if er_conn is not None:
        return _run(er_conn)
    with get_db(DB_EXAMINER) as conn:
        return _run(conn)


def get_active_misconceptions(
    subject: str | None = None,
    module_code: str | None = None,
    limit: int = 10,
    er_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Return active misconceptions, optionally filtered by subject/module.

    Ordered by frequency (most reported first), then recency.
    """
    from config.settings import DB_EXAMINER
    from db.models import get_db

    clauses: list[str] = ["is_active = 1"]
    params: list[Any] = []
    if subject:
        clauses.append("subject = ?")
        params.append(subject)
    if module_code:
        clauses.append("module_code = ?")
        params.append(module_code)

    where = "WHERE " + " AND ".join(clauses)

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            f"""
            SELECT id, subject, module_code, topic, subtopic, description,
                   frequency, last_seen, is_active
            FROM misconceptions
            {where}
            ORDER BY frequency DESC, last_seen DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]

    if er_conn is not None:
        return _run(er_conn)
    with get_db(DB_EXAMINER) as conn:
        return _run(conn)


def generate_corrective_intervention(
    misconception_id: int,
    er_conn: sqlite3.Connection | None = None,
) -> str:
    """Generate and persist a corrective intervention for a misconception.

    Retrieval-first: reads misconception text and pulls related questions from
    question_bank.db. Template-based — no external model call.

    Returns the intervention text. Persists to corrective_interventions on first
    call; subsequent calls return the stored text.
    """
    from config.settings import DB_EXAMINER
    from db.models import get_db

    def _fetch(conn: sqlite3.Connection) -> dict[str, Any] | None:
        row = conn.execute(
            """
            SELECT m.id, m.subject, m.module_code, m.topic, m.subtopic,
                   m.description, m.frequency, m.last_seen
            FROM misconceptions m
            WHERE m.id = ?
            """,
            (misconception_id,),
        ).fetchone()
        return dict(row) if row else None

    def _existing(conn: sqlite3.Connection) -> str | None:
        row = conn.execute(
            "SELECT intervention_text FROM corrective_interventions WHERE misconception_id = ? LIMIT 1",
            (misconception_id,),
        ).fetchone()
        return row[0] if row else None

    def _store(conn: sqlite3.Connection, text: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO corrective_interventions
                (misconception_id, intervention_text, intervention_type, created_at)
            VALUES (?, ?, 'explanation', ?)
            """,
            (misconception_id, text, now),
        )

    if er_conn is not None:
        m = _fetch(er_conn)
        if not m:
            raise ValueError(f"Misconception {misconception_id} not found")
        cached = _existing(er_conn)
        if cached:
            return cached
        text = _build_intervention(m)
        _store(er_conn, text)
        return text

    with get_db(DB_EXAMINER) as conn:
        m = _fetch(conn)
        if not m:
            raise ValueError(f"Misconception {misconception_id} not found")
        cached = _existing(conn)
        if cached:
            return cached
        text = _build_intervention(m)
        _store(conn, text)
        return text


def _build_intervention(m: dict[str, Any]) -> str:
    """Construct a template-based corrective intervention from a misconception record."""
    topic = m.get("topic") or m.get("module_code") or "this topic"
    subtopic = m.get("subtopic") or ""
    heading = topic + (f" — {subtopic}" if subtopic else "")

    lines = [
        f"Corrective note: {heading}",
        "",
        f"Examiner observation ({m['frequency']}× reported, last seen {m['last_seen']}):",
        f"  \"{m['description']}\"",
        "",
        "To avoid this error:",
        f"  1. Before substituting numbers, write the correct formula for {topic} in full.",
        "  2. Re-read the question stem: identify exactly what quantity is being requested.",
        "  3. Check your answer has the correct unit and significant figures.",
    ]

    # Pull practice questions from question_bank.db
    try:
        from agents.delivery.retrieval_agent import get_questions
        questions = get_questions(
            subject=m["subject"],
            module_code=m["module_code"],
            topic=topic,
            limit=3,
        )
        if questions:
            lines += [
                "",
                f"Practice ({len(questions)} question{'s' if len(questions) != 1 else ''} "
                f"from question bank):",
            ]
            for q in questions:
                code = q.get("paper_code") or q.get("paper_code", "?")
                session = q.get("session", "")
                marks = q.get("marks") or "?"
                lines.append(f"  • Q{q['question_number']} — {code} {session} — {marks} marks")
    except Exception as exc:
        logger.debug("Could not retrieve practice questions: %s", exc)

    return "\n".join(lines)
