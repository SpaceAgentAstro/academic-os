from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def get_questions(
    subject: str,
    module_code: str | None = None,
    topic: str | None = None,
    difficulty: int | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
    exclude_ids: list[int] | None = None,
    qb_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Retrieve questions from question_bank.db with full filter support.

    Returns retrieval-ready dicts with all fields needed for a revision session.
    """
    from config.settings import DB_QUESTION_BANK
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        clauses: list[str] = ["p.subject = ?"]
        params: list[Any] = [subject]

        if module_code:
            clauses.append("p.module_code = ?")
            params.append(module_code)
        if difficulty:
            clauses.append("q.difficulty = ?")
            params.append(difficulty)

        where = "WHERE " + " AND ".join(clauses)

        if topic:
            where += " AND EXISTS (SELECT 1 FROM question_topics qt WHERE qt.question_id=q.id AND qt.topic=?)"
            params.append(topic)

        if tags:
            for tag in tags:
                where += (
                    " AND EXISTS (SELECT 1 FROM question_tags qt2 "
                    "WHERE qt2.question_id=q.id AND qt2.tag=?)"
                )
                params.append(tag)

        if exclude_ids:
            placeholders = ",".join("?" * len(exclude_ids))
            where += f" AND q.id NOT IN ({placeholders})"
            params.extend(exclude_ids)

        sql = f"""
            SELECT q.id, q.question_number, q.marks, q.command_word, q.difficulty,
                   q.raw_text, q.latex_text, q.has_diagram,
                   p.subject, p.module_code, p.session, p.year, p.paper_code
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            {where}
            ORDER BY q.difficulty DESC, RANDOM()
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    if qb_conn is not None:
        return _run(qb_conn)
    with get_db(DB_QUESTION_BANK) as conn:
        return _run(conn)


def get_questions_by_spec_point(
    spec_point_id: int,
    limit: int = 10,
    qb_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Retrieve questions linked to a specific specification point."""
    from config.settings import DB_QUESTION_BANK
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT q.id, q.question_number, q.marks, q.command_word, q.difficulty,
                   q.raw_text, q.latex_text, q.has_diagram
            FROM questions q
            JOIN question_spec_links qsl ON qsl.question_id = q.id
            WHERE qsl.spec_point_id = ?
            ORDER BY q.difficulty DESC
            LIMIT ?
            """,
            (spec_point_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    if qb_conn is not None:
        return _run(qb_conn)
    with get_db(DB_QUESTION_BANK) as conn:
        return _run(conn)


def get_misconceptions(
    subject: str | None = None,
    module_code: str | None = None,
    active_only: bool = True,
    er_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Retrieve misconceptions from examiner_reports.db."""
    from config.settings import DB_EXAMINER
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if active_only:
            clauses.append("is_active = 1")
        if subject:
            clauses.append("subject = ?")
            params.append(subject)
        if module_code:
            clauses.append("module_code = ?")
            params.append(module_code)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT id, subject, module_code, topic, subtopic, description,
                   frequency, last_seen, is_active
            FROM misconceptions
            {where}
            ORDER BY frequency DESC, last_seen DESC
        """
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    if er_conn is not None:
        return _run(er_conn)
    with get_db(DB_EXAMINER) as conn:
        return _run(conn)


def get_weak_topics(
    subject: str,
    window_days: int = 30,
    analytics_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Return topics ranked by weakness: low avg_score, high misconception frequency.

    Returns a list of {topic, module_code, avg_score, attempt_count, trend_direction}.
    """
    from config.settings import DB_ANALYTICS
    from db.models import get_db

    cutoff = (date.today() - timedelta(days=window_days)).isoformat()

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT topic, module_code, avg_score, attempt_count, trend_direction
            FROM performance_trends
            WHERE subject = ? AND computed_at >= ?
            ORDER BY avg_score ASC, attempt_count DESC
            """,
            (subject, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]

    if analytics_conn is not None:
        return _run(analytics_conn)
    with get_db(DB_ANALYTICS) as conn:
        return _run(conn)


def get_diagrams(
    subject: str,
    diagram_type: str | None = None,
    limit: int = 5,
    diag_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Retrieve diagrams from diagrams.db."""
    from config.settings import DB_DIAGRAMS
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        clauses = ["subject = ?"]
        params: list[Any] = [subject]
        if diagram_type:
            clauses.append("diagram_type = ?")
            params.append(diagram_type)
        where = "WHERE " + " AND ".join(clauses)
        sql = f"""
            SELECT id, source_file, page_number, image_path, subject, module_code,
                   diagram_type, description, width_px, height_px
            FROM diagrams
            {where}
            ORDER BY processed_at DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    if diag_conn is not None:
        return _run(diag_conn)
    with get_db(DB_DIAGRAMS) as conn:
        return _run(conn)
