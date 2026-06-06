from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PaperMetadata:
    qualification: str
    subject: str
    module_code: str
    paper_code: str
    session: str
    year: int
    paper_type: str  # question_paper | mark_scheme | examiner_report
    source_file: str


@dataclass
class ExtractedQuestion:
    question_number: str
    marks: int
    raw_text: str
    latex_text: str
    command_word: str | None
    has_diagram: bool
    difficulty: int = 2
    tags: list[str] = field(default_factory=list)
    spec_point_refs: list[str] = field(default_factory=list)
    topic: str = ""
    subtopic: str = ""


def detect_paper_type(pdf_path: Path) -> str:
    """Identify whether a PDF is a question paper, mark scheme, or examiner report."""
    raise NotImplementedError


def extract_metadata(pdf_path: Path) -> PaperMetadata:
    """Extract qualification, subject, module, paper code, and session from a PDF."""
    raise NotImplementedError


def extract_questions(pdf_path: Path, metadata: PaperMetadata) -> list[ExtractedQuestion]:
    """Extract all questions from a question paper PDF."""
    raise NotImplementedError


def ingest_paper(pdf_path: Path) -> None:
    """Full ingestion pipeline: detect type → extract → classify → write to question_bank.db."""
    raise NotImplementedError


def scan_papers_directory() -> list[Path]:
    """Find all unprocessed PDFs in the papers/ directory."""
    raise NotImplementedError
