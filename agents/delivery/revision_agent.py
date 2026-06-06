from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

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
) -> RevisionPack:
    """Build a prioritized revision pack: weak → difficult → unreviewed → misconceptions."""
    raise NotImplementedError


def build_mock_exam(
    subject: str,
    module_code: str,
    total_marks: int = 75,
) -> list[dict[str, Any]]:
    """Assemble a mock exam from question_bank.db, representative of real paper difficulty."""
    raise NotImplementedError


def get_spaced_repetition_queue(limit: int = 20) -> list[dict[str, Any]]:
    """Return specification points due for review today, sorted by urgency."""
    raise NotImplementedError
