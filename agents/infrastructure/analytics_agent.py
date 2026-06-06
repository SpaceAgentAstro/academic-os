from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_mastery_score(
    spec_point_id: int,
    score: float,
    method: str,
) -> None:
    """Record a mastery score for a specification point in analytics.db."""
    raise NotImplementedError


def record_revision_session(
    subject: str,
    module_code: str | None,
    session_type: str,
    questions: list[dict[str, Any]],
) -> int:
    """Record a completed revision session. Returns the session_id."""
    raise NotImplementedError


def compute_performance_trends(
    subject: str,
    module_code: str,
    window_days: int = 30,
) -> dict[str, Any]:
    """Compute performance trends for a subject/module over a rolling window."""
    raise NotImplementedError


def get_weak_topics(
    subject: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return topics ranked by weakness score (low mastery + declining trend)."""
    raise NotImplementedError
