from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# SOLE AUTHORITY over progress.db syllabus state.
# No other agent may call advance_topic, update_completion, or schedule_review.

_STATUS_ORDER = ["not_started", "in_progress", "taught", "reviewed", "mastered"]

# Spaced repetition intervals (days) per outcome+confidence
# confidence 1 = weak, 5 = strong
_SR_INTERVALS: dict[str, list[int]] = {
    "correct":   [1, 3, 7, 14, 30],   # indexed by confidence-1
    "partial":   [1, 1, 3,  7, 14],
    "incorrect": [1, 1, 1,  1,  3],
}


def _get_conn(progress_conn: sqlite3.Connection | None) -> sqlite3.Connection:
    if progress_conn is not None:
        return progress_conn
    from config.settings import DB_PROGRESS
    from db.models import get_db
    # Caller must use as context manager when progress_conn is None
    raise ValueError("progress_conn required for direct use; use with get_db(DB_PROGRESS)")


def advance_topic(
    spec_point_id: int,
    new_status: str,
    confidence: int,
    progress_conn: sqlite3.Connection | None = None,
) -> None:
    """Advance a specification point's status.

    Validates that new_status is a forward progression (no backwards moves unless
    explicitly forced). Requires student confirmation before calling.
    """
    from config.settings import DB_PROGRESS
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> None:
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT status FROM syllabus_completion WHERE spec_point_id=?",
            (spec_point_id,),
        ).fetchone()

        if row:
            current_idx = _STATUS_ORDER.index(row[0]) if row[0] in _STATUS_ORDER else 0
            new_idx     = _STATUS_ORDER.index(new_status) if new_status in _STATUS_ORDER else 0
            if new_idx < current_idx:
                logger.warning(
                    "Ignoring backwards status move for spec_point %d: %s → %s",
                    spec_point_id, row[0], new_status,
                )
                return
            conn.execute(
                """
                UPDATE syllabus_completion
                   SET status=?, confidence=?, last_reviewed=?
                 WHERE spec_point_id=?
                """,
                (new_status, confidence, today, spec_point_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO syllabus_completion
                    (spec_point_id, status, confidence, first_taught, last_reviewed, review_count)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (spec_point_id, new_status, confidence, today, today),
            )
        conn.commit()
        logger.info("Spec point %d → %s (confidence %d)", spec_point_id, new_status, confidence)

    if progress_conn is not None:
        _run(progress_conn)
    else:
        from db.models import get_db
        with get_db(DB_PROGRESS) as conn:
            _run(conn)


def update_completion(
    spec_point_id: int,
    status: str,
    confidence: int | None = None,
    notes: str | None = None,
    progress_conn: sqlite3.Connection | None = None,
) -> None:
    """Update the completion record for a specification point (any field)."""
    from config.settings import DB_PROGRESS
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> None:
        today = date.today().isoformat()
        existing = conn.execute(
            "SELECT id FROM syllabus_completion WHERE spec_point_id=?",
            (spec_point_id,),
        ).fetchone()

        if existing:
            sets = ["status=?", "last_reviewed=?"]
            params: list[Any] = [status, today]
            if confidence is not None:
                sets.append("confidence=?")
                params.append(confidence)
            if notes is not None:
                sets.append("notes=?")
                params.append(notes)
            params.append(spec_point_id)
            conn.execute(
                f"UPDATE syllabus_completion SET {', '.join(sets)} WHERE spec_point_id=?",
                params,
            )
        else:
            conn.execute(
                """
                INSERT INTO syllabus_completion
                    (spec_point_id, status, confidence, notes, first_taught, last_reviewed, review_count)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (spec_point_id, status, confidence, notes, today, today),
            )
        conn.commit()

    if progress_conn is not None:
        _run(progress_conn)
    else:
        with get_db(DB_PROGRESS) as conn:
            _run(conn)


def get_current_progression(
    subject: str,
    module_code: str,
    progress_conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Return current syllabus completion state for a subject/module.

    Returns {total, by_status: {status: count}, coverage_pct, spec_points: [...]}.
    """
    from config.settings import DB_PROGRESS
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> dict[str, Any]:
        rows = conn.execute(
            """
            SELECT sp.id, sp.spec_ref, sp.description,
                   sc.status, sc.confidence, sc.next_review, sc.review_count
            FROM specification_points sp
            JOIN subtopics st ON sp.subtopic_id = st.id
            JOIN topics t ON st.topic_id = t.id
            JOIN modules m ON t.module_id = m.id
            JOIN subjects s ON m.subject_id = s.id
            LEFT JOIN syllabus_completion sc ON sc.spec_point_id = sp.id
            WHERE s.name = ? AND m.code = ?
            """,
            (subject, module_code),
        ).fetchall()

        total = len(rows)
        by_status: dict[str, int] = {s: 0 for s in _STATUS_ORDER}
        points: list[dict[str, Any]] = []
        for row in rows:
            status = row["status"] or "not_started"
            by_status[status] += 1
            points.append(dict(row))

        mastered = by_status.get("mastered", 0) + by_status.get("reviewed", 0)
        coverage = (mastered / total * 100) if total > 0 else 0.0

        return {
            "subject": subject,
            "module_code": module_code,
            "total": total,
            "by_status": by_status,
            "coverage_pct": round(coverage, 1),
            "spec_points": points,
        }

    if progress_conn is not None:
        return _run(progress_conn)
    with get_db(DB_PROGRESS) as conn:
        return _run(conn)


def get_next_review_queue(
    limit: int = 20,
    progress_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Return specification points due for review today, sorted by next_review date."""
    from config.settings import DB_PROGRESS
    from db.models import get_db

    today = date.today().isoformat()

    def _run(conn: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT sc.id, sc.spec_point_id, sc.status, sc.confidence,
                   sc.next_review, sc.review_count,
                   sp.spec_ref, sp.description
            FROM syllabus_completion sc
            JOIN specification_points sp ON sp.id = sc.spec_point_id
            WHERE sc.next_review IS NOT NULL
              AND sc.next_review <= ?
              AND sc.status NOT IN ('not_started')
            ORDER BY sc.next_review ASC, sc.confidence ASC
            LIMIT ?
            """,
            (today, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    if progress_conn is not None:
        return _run(progress_conn)
    with get_db(DB_PROGRESS) as conn:
        return _run(conn)


def schedule_review(
    spec_point_id: int,
    outcome: str,
    progress_conn: sqlite3.Connection | None = None,
) -> None:
    """Calculate and set next_review date based on spaced repetition algorithm.

    outcome: 'correct' | 'partial' | 'incorrect'
    """
    from config.settings import DB_PROGRESS
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT confidence, review_count FROM syllabus_completion WHERE spec_point_id=?",
            (spec_point_id,),
        ).fetchone()
        if not row:
            logger.warning("No completion record for spec_point %d", spec_point_id)
            return

        confidence = row["confidence"] or 3
        intervals = _SR_INTERVALS.get(outcome, _SR_INTERVALS["correct"])
        interval_days = intervals[max(0, min(confidence - 1, 4))]
        next_review = (date.today() + timedelta(days=interval_days)).isoformat()
        today = date.today().isoformat()

        conn.execute(
            """
            UPDATE syllabus_completion
               SET next_review=?, last_reviewed=?, review_count=review_count+1
             WHERE spec_point_id=?
            """,
            (next_review, today, spec_point_id),
        )
        conn.commit()
        logger.info(
            "Spec point %d → next review %s (%d days, outcome=%s)",
            spec_point_id, next_review, interval_days, outcome,
        )

    if progress_conn is not None:
        _run(progress_conn)
    else:
        with get_db(DB_PROGRESS) as conn:
            _run(conn)


def get_specification_coverage(
    subject: str,
    progress_conn: sqlite3.Connection | None = None,
) -> dict[str, float]:
    """Return percentage coverage per module for a subject.

    Returns {module_code: coverage_pct}.
    """
    from config.settings import DB_PROGRESS
    from db.models import get_db

    def _run(conn: sqlite3.Connection) -> dict[str, float]:
        rows = conn.execute(
            """
            SELECT m.code,
                   COUNT(sp.id) AS total,
                   SUM(CASE WHEN sc.status IN ('reviewed','mastered') THEN 1 ELSE 0 END) AS covered
            FROM modules m
            JOIN subjects s ON m.subject_id = s.id
            JOIN topics t ON t.module_id = m.id
            JOIN subtopics st ON st.topic_id = t.id
            JOIN specification_points sp ON sp.subtopic_id = st.id
            LEFT JOIN syllabus_completion sc ON sc.spec_point_id = sp.id
            WHERE s.name = ?
            GROUP BY m.code
            """,
            (subject,),
        ).fetchall()

        return {
            row["code"]: round((row["covered"] or 0) / row["total"] * 100, 1)
            if row["total"] > 0 else 0.0
            for row in rows
        }

    if progress_conn is not None:
        return _run(progress_conn)
    with get_db(DB_PROGRESS) as conn:
        return _run(conn)
