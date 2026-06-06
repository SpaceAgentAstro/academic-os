from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SUBJECT = "Mathematics"
MODULES = ["P1", "P2", "P3", "P4", "S1", "S2", "M1", "M2", "M3"]


def get_questions_by_topic(
    module: str,
    topic: str,
    difficulty: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Retrieve questions for a given module and topic from question_bank.db."""
    raise NotImplementedError


def get_revision_pack(module: str, weak_topics: list[str]) -> list[dict[str, Any]]:
    """Build a revision pack targeting weak topics within a module."""
    raise NotImplementedError


def get_topic_coverage_summary(module: str) -> dict[str, Any]:
    """Return a summary of specification coverage for a given module."""
    raise NotImplementedError
