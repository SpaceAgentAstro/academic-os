from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from agents.delivery.retrieval_agent import (
    get_questions,
    get_misconceptions,
    get_weak_topics,
)

logger = logging.getLogger(__name__)


@dataclass
class RevisionPack:
    subject: str
    module_code: str
    focus_topics: list[str]
    questions: list[dict[str, Any]] = field(default_factory=list)
    misconception_reminders: list[str] = field(default_factory=list)
    estimated_duration_minutes: int = 30


def build_revision_pack(
    subject: str,
    module_code: str | None = None,
    max_questions: int = 15,
    qb_conn: sqlite3.Connection | None = None,
    er_conn: sqlite3.Connection | None = None,
    analytics_conn: sqlite3.Connection | None = None,
) -> RevisionPack:
    """Build a prioritized revision pack: weak → difficult → unreviewed → misconceptions.

    Priority:
      1. Questions from weak topics (low avg_score from analytics)
      2. High-difficulty questions (4–5) not yet attempted
      3. Active misconception reminders
    """
    focus_topics: list[str] = []
    questions: list[dict[str, Any]] = []
    seen_ids: list[int] = []

    # Step 1: Weak topics from analytics
    weak = get_weak_topics(subject, window_days=30, analytics_conn=analytics_conn)
    for t in weak[:3]:
        focus_topics.append(t["topic"])
        qs = get_questions(
            subject=subject,
            module_code=module_code or t.get("module_code"),
            topic=t["topic"],
            limit=5,
            exclude_ids=seen_ids,
            qb_conn=qb_conn,
        )
        questions.extend(qs)
        seen_ids.extend(q["id"] for q in qs)
        if len(questions) >= max_questions:
            break

    # Step 2: Hard questions if still under quota
    if len(questions) < max_questions:
        hard_qs = get_questions(
            subject=subject,
            module_code=module_code,
            difficulty=4,
            limit=max_questions - len(questions),
            exclude_ids=seen_ids,
            qb_conn=qb_conn,
        )
        if not hard_qs:
            hard_qs = get_questions(
                subject=subject,
                module_code=module_code,
                difficulty=3,
                limit=max_questions - len(questions),
                exclude_ids=seen_ids,
                qb_conn=qb_conn,
            )
        questions.extend(hard_qs)
        seen_ids.extend(q["id"] for q in hard_qs)

    # Step 3: Misconception reminders
    misconceptions = get_misconceptions(
        subject=subject,
        module_code=module_code,
        active_only=True,
        er_conn=er_conn,
    )
    reminders = [m["description"] for m in misconceptions[:5]]

    marks = sum(q.get("marks", 0) for q in questions)
    # Rough estimate: 1.5 minutes per mark
    duration = max(15, int(marks * 1.5))

    return RevisionPack(
        subject=subject,
        module_code=module_code or "All",
        focus_topics=focus_topics or [module_code or "General"],
        questions=questions[:max_questions],
        misconception_reminders=reminders,
        estimated_duration_minutes=duration,
    )


def build_mock_exam(
    subject: str,
    module_code: str,
    total_marks: int = 75,
    qb_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Assemble a mock exam from question_bank.db, representative of real paper difficulty.

    Selects questions proportional to the real difficulty distribution:
      ~30% difficulty 2, ~40% difficulty 3, ~30% difficulty 4–5.
    """
    selected: list[dict[str, Any]] = []
    used_ids: list[int] = []
    marks_so_far = 0

    target_distribution = [
        (2, int(total_marks * 0.30)),
        (3, int(total_marks * 0.40)),
        (4, int(total_marks * 0.20)),
        (5, int(total_marks * 0.10)),
    ]

    for difficulty, target_marks in target_distribution:
        while marks_so_far < target_marks and marks_so_far < total_marks:
            qs = get_questions(
                subject=subject,
                module_code=module_code,
                difficulty=difficulty,
                limit=5,
                exclude_ids=used_ids,
                qb_conn=qb_conn,
            )
            if not qs:
                break
            for q in qs:
                if marks_so_far + q["marks"] > total_marks:
                    continue
                selected.append(q)
                used_ids.append(q["id"])
                marks_so_far += q["marks"]
                if marks_so_far >= target_marks:
                    break

    logger.info(
        "Mock exam assembled: %d questions, %d marks (target %d)",
        len(selected), marks_so_far, total_marks,
    )
    return selected


def get_spaced_repetition_queue(
    limit: int = 20,
    progress_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Return specification points due for review today, sorted by urgency.

    Urgency: overdue first, then due today, ordered by low confidence.
    """
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
