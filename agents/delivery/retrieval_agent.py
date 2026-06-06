from __future__ import annotations

import logging
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
) -> list[dict[str, Any]]:
    """Retrieve questions from question_bank.db with full filter support."""
    raise NotImplementedError


def get_questions_by_spec_point(spec_point_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve questions linked to a specific specification point."""
    raise NotImplementedError


def get_misconceptions(
    subject: str | None = None,
    module_code: str | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Retrieve misconceptions from examiner_reports.db."""
    raise NotImplementedError


def get_weak_topics(subject: str, window_days: int = 30) -> list[dict[str, Any]]:
    """Return topics ranked by weakness (low mastery + high misconception frequency)."""
    raise NotImplementedError


def get_diagrams(
    subject: str,
    diagram_type: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve diagrams from diagrams.db."""
    raise NotImplementedError
