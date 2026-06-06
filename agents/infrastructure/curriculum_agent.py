from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# SOLE AUTHORITY over progress.db syllabus state.
# No other agent may call advance_topic or update_completion.


def advance_topic(spec_point_id: int, new_status: str, confidence: int) -> None:
    """Advance a specification point's status. Requires student confirmation before calling."""
    raise NotImplementedError


def update_completion(
    spec_point_id: int,
    status: str,
    confidence: int | None = None,
    notes: str | None = None,
) -> None:
    """Update the completion record for a specification point."""
    raise NotImplementedError


def get_current_progression(subject: str, module_code: str) -> dict[str, Any]:
    """Return current syllabus completion state for a subject/module."""
    raise NotImplementedError


def get_next_review_queue(limit: int = 20) -> list[dict[str, Any]]:
    """Return specification points due for review today, sorted by next_review date."""
    raise NotImplementedError


def schedule_review(spec_point_id: int, outcome: str) -> None:
    """Calculate and set next_review date based on spaced repetition algorithm."""
    raise NotImplementedError


def get_specification_coverage(subject: str) -> dict[str, float]:
    """Return percentage coverage per module for a subject."""
    raise NotImplementedError
