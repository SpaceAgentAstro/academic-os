from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SUBJECT = "Chemistry"
UNITS = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5", "Unit 6"]


def get_questions_by_topic(
    unit: str,
    topic: str,
    difficulty: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_mechanisms_for_topic(unit: str, topic: str) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_revision_pack(unit: str, weak_topics: list[str]) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_topic_coverage_summary(unit: str) -> dict[str, Any]:
    raise NotImplementedError
