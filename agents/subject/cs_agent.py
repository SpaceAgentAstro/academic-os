from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SUBJECT = "Computer Science"
DOMAINS = [
    "Theory Fundamentals", "Algorithms", "Data Structures", "Databases",
    "Networking", "Operating Systems", "Logic", "OOP", "Software Engineering",
    "Practical Programming", "Pseudocode", "Computational Thinking",
]


def get_questions_by_domain(
    domain: str,
    difficulty: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_pseudocode_exercises(topic: str, limit: int = 5) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_revision_pack(domain: str, weak_topics: list[str]) -> list[dict[str, Any]]:
    raise NotImplementedError


def get_topic_coverage_summary(domain: str) -> dict[str, Any]:
    raise NotImplementedError
