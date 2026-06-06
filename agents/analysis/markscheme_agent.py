from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

MARK_TYPES = frozenset({"M", "A", "B", "E", "Q", "dM", "ddM", "ft"})


@dataclass
class MarkEntry:
    sequence: int
    mark_type: str
    marks_value: int
    description: str
    conditionality: str | None = None
    alternatives: list[str] = field(default_factory=list)
    required_terms: list[str] = field(default_factory=list)


def parse_markscheme(pdf_path: Path) -> dict[str, list[MarkEntry]]:
    """Parse a mark scheme PDF, returning mark entries keyed by question number."""
    raise NotImplementedError


def ingest_markscheme(pdf_path: Path, paper_id: int) -> None:
    """Full mark scheme ingestion: parse → link to questions → write to markscheme.db."""
    raise NotImplementedError
