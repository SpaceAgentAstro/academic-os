from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

COMMAND_WORDS = frozenset({
    "find", "show that", "prove", "prove that", "show", "state",
    "write down", "calculate", "determine", "evaluate", "sketch",
    "describe", "explain", "suggest", "deduce", "hence", "hence or otherwise",
    "using your answer", "verify", "simplify", "expand", "factorise",
    "differentiate", "integrate", "solve", "given that",
})


def classify_difficulty(question: dict[str, Any]) -> int:
    """Assign difficulty 1–5 based on marks, command word, and topic."""
    raise NotImplementedError


def classify_tags(question: dict[str, Any]) -> list[str]:
    """Assign question tags: Proof, Modelling, Calculation, etc."""
    raise NotImplementedError


def classify_topic(
    question: dict[str, Any],
    subject: str,
    module_code: str,
) -> tuple[str, str]:
    """Return (topic, subtopic) for a question."""
    raise NotImplementedError


def extract_command_word(question_text: str) -> str | None:
    """Identify the command word from question text."""
    lower = question_text.lower().strip()
    for cw in sorted(COMMAND_WORDS, key=len, reverse=True):
        if lower.startswith(cw) or f"\n{cw}" in lower:
            return cw
    return None
