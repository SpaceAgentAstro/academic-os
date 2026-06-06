from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_question_blocks(raw_text: str) -> list[dict[str, Any]]:
    """Parse raw OCR text into individual question blocks."""
    raise NotImplementedError


def extract_markscheme_blocks(raw_text: str) -> list[dict[str, Any]]:
    """Parse raw OCR text of a mark scheme into mark entries per question."""
    raise NotImplementedError


def extract_report_observations(raw_text: str) -> list[dict[str, Any]]:
    """Parse raw OCR text of an examiner report into observation records."""
    raise NotImplementedError
