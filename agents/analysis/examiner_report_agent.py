from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Observation:
    question_number: str | None
    topic: str | None
    subtopic: str | None
    observation_type: str
    description: str
    emphasis_level: int = 1


def extract_observations(pdf_path: Path) -> list[Observation]:
    """Extract all observations from an examiner report PDF."""
    raise NotImplementedError


def ingest_report(pdf_path: Path, paper_id: int) -> None:
    """Full report ingestion: extract observations → write to examiner_reports.db."""
    raise NotImplementedError
