from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ingestion.ocr import extract_full_text
from ingestion.extractor import extract_markscheme_blocks

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
    full_text = extract_full_text(pdf_path)
    raw_entries = extract_markscheme_blocks(full_text)

    result: dict[str, list[MarkEntry]] = {}
    for entry in raw_entries:
        q_num = entry["question_number"]
        mark_type = entry["mark_type"]
        if mark_type not in MARK_TYPES:
            logger.debug("Unknown mark type '%s' — defaulting to M", mark_type)
            mark_type = "M"

        me = MarkEntry(
            sequence=entry["sequence"],
            mark_type=mark_type,
            marks_value=entry["marks_value"],
            description=entry["description"],
            conditionality=entry.get("conditionality"),
        )
        result.setdefault(q_num, []).append(me)

    logger.info("Parsed %d questions from mark scheme %s", len(result), pdf_path.name)
    return result


def _find_question_id(
    qb_conn: sqlite3.Connection,
    paper_id: int,
    question_number: str,
) -> int | None:
    """Look up a question_id in question_bank.db by paper_id + question_number."""
    row = qb_conn.execute(
        "SELECT id FROM questions WHERE paper_id=? AND question_number=?",
        (paper_id, question_number),
    ).fetchone()
    return row[0] if row else None


def _write_markscheme_entry(
    ms_conn: sqlite3.Connection,
    question_id: int,
    entry: MarkEntry,
) -> int:
    """Insert a single mark entry. Returns markscheme_entry_id."""
    cur = ms_conn.execute(
        """
        INSERT INTO markscheme_entries
            (question_id, sequence, mark_type, marks_value, description, conditionality)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(question_id, sequence) DO UPDATE SET
            mark_type=excluded.mark_type,
            marks_value=excluded.marks_value,
            description=excluded.description,
            conditionality=excluded.conditionality
        """,
        (
            question_id, entry.sequence, entry.mark_type,
            entry.marks_value, entry.description, entry.conditionality,
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def ingest_markscheme(
    pdf_path: Path,
    paper_id: int,
    ms_conn: sqlite3.Connection | None = None,
    qb_conn: sqlite3.Connection | None = None,
) -> None:
    """Full mark scheme ingestion: parse → link to questions → write to markscheme.db.

    Accepts optional connection arguments for testability (in-memory SQLite).
    """
    from config.settings import DB_MARKSCHEME, DB_QUESTION_BANK
    from db.models import get_db

    logger.info("Ingesting mark scheme: %s (paper_id=%d)", pdf_path.name, paper_id)
    parsed = parse_markscheme(pdf_path)

    def _run(ms: sqlite3.Connection, qb: sqlite3.Connection) -> None:
        for q_num, entries in parsed.items():
            question_id = _find_question_id(qb, paper_id, q_num)
            if question_id is None:
                logger.warning(
                    "No question %s found for paper_id=%d — mark scheme entry skipped",
                    q_num, paper_id,
                )
                continue
            for entry in entries:
                _write_markscheme_entry(ms, question_id, entry)
        ms.commit()
        logger.info("Mark scheme for paper %d written (%d questions)", paper_id, len(parsed))

    if ms_conn is not None and qb_conn is not None:
        _run(ms_conn, qb_conn)
    else:
        with get_db(DB_MARKSCHEME) as ms, get_db(DB_QUESTION_BANK) as qb:
            _run(ms, qb)
