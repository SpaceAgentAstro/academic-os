from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SUBJECT = "Further Mathematics"
MODULES = ["FP1", "FP2", "FP3", "M1", "M2", "M3"]


def get_questions_by_topic(
    module: str,
    topic: str,
    difficulty: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_revision_pack(module: str, weak_topics: list[str]) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_topic_coverage_summary(module: str) -> dict[str, Any]:
    raise NotImplementedError
