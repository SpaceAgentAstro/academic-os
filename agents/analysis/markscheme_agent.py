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

# Sequence offset so alternative-method entries don't collide with primary ones
_ALT_METHOD_SEQ_OFFSET = 100


@dataclass
class MarkEntry:
    sequence: int
    mark_type: str
    marks_value: int
    description: str
    conditionality: str | None = None
    alternatives: list[str] = field(default_factory=list)
    required_terms: list[str] = field(default_factory=list)
    is_alternative_method: bool = False


def parse_markscheme(pdf_path: Path) -> dict[str, list[MarkEntry]]:
    """Parse a mark scheme PDF, returning mark entries keyed by question number."""
    full_text = extract_full_text(pdf_path)
    raw_entries = extract_markscheme_blocks(full_text)

    result: dict[str, list[MarkEntry]] = {}
    alt_seq_counters: dict[str, int] = {}  # track per-question alt method sequence

    for entry in raw_entries:
        q_num = entry["question_number"]
        mark_type = entry["mark_type"]
        if mark_type not in MARK_TYPES:
            logger.debug("Unknown mark type '%s' — defaulting to M", mark_type)
            mark_type = "M"

        is_alt = entry.get("is_alternative_method", False)
        if is_alt:
            # Assign sequence in the alt-method range (100+)
            counter = alt_seq_counters.get(q_num, 0) + 1
            alt_seq_counters[q_num] = counter
            seq = _ALT_METHOD_SEQ_OFFSET + counter
        else:
            seq = entry["sequence"]

        me = MarkEntry(
            sequence=seq,
            mark_type=mark_type,
            marks_value=entry["marks_value"],
            description=entry["description"],
            conditionality=entry.get("conditionality"),
            alternatives=entry.get("alternatives", []),
            required_terms=entry.get("required_terms", []),
            is_alternative_method=is_alt,
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


def _write_mark_alternative(
    ms_conn: sqlite3.Connection,
    entry_id: int,
    alternative_text: str,
    note: str | None = None,
) -> None:
    """Insert a mark alternative. Silently skips duplicates."""
    # Check for existing to avoid duplication on re-ingestion
    exists = ms_conn.execute(
        "SELECT 1 FROM mark_alternatives WHERE markscheme_entry_id=? AND alternative_text=?",
        (entry_id, alternative_text),
    ).fetchone()
    if not exists:
        ms_conn.execute(
            "INSERT INTO mark_alternatives (markscheme_entry_id, alternative_text, note) VALUES (?,?,?)",
            (entry_id, alternative_text, note),
        )


def _write_required_term(
    ms_conn: sqlite3.Connection,
    entry_id: int,
    term: str,
) -> None:
    """Insert a required term. Silently skips duplicates."""
    exists = ms_conn.execute(
        "SELECT 1 FROM required_terms WHERE markscheme_entry_id=? AND term=?",
        (entry_id, term),
    ).fetchone()
    if not exists:
        ms_conn.execute(
            "INSERT INTO required_terms (markscheme_entry_id, term, is_mandatory) VALUES (?,?,1)",
            (entry_id, term),
        )


def _write_ft_rules(
    ms_conn: sqlite3.Connection,
    question_id: int,
    entries: list[MarkEntry],
) -> None:
    """Write follow-through rules for a question's mark entries.

    For each ft entry, links it to the most recent non-ft preceding entry.
    """
    last_primary_seq: int | None = None
    for entry in sorted(entries, key=lambda e: e.sequence):
        if entry.conditionality != "follow_through":
            last_primary_seq = entry.sequence
            continue
        if last_primary_seq is None:
            continue
        # Avoid duplicate rules
        exists = ms_conn.execute(
            """SELECT 1 FROM follow_through_rules
               WHERE question_id=? AND from_mark_sequence=? AND to_mark_sequence=?""",
            (question_id, last_primary_seq, entry.sequence),
        ).fetchone()
        if not exists:
            ms_conn.execute(
                """INSERT INTO follow_through_rules
                   (question_id, from_mark_sequence, to_mark_sequence, condition)
                   VALUES (?,?,?,?)""",
                (question_id, last_primary_seq, entry.sequence, "follow_through"),
            )


def ingest_markscheme(
    pdf_path: Path,
    paper_id: int,
    ms_conn: sqlite3.Connection | None = None,
    qb_conn: sqlite3.Connection | None = None,
) -> None:
    """Full mark scheme ingestion: parse → link to questions → write to markscheme.db.

    Writes:
    - markscheme_entries (primary mark entries)
    - mark_alternatives (oe / accept variants)
    - required_terms (must-include phrases)
    - follow_through_rules (ft mark dependencies)

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
                entry_id = _write_markscheme_entry(ms, question_id, entry)
                # Write inline alternative answers / "oe" / "accept" entries
                for alt in entry.alternatives:
                    _write_mark_alternative(ms, entry_id, alt)
                # Write required terms
                for term in entry.required_terms:
                    _write_required_term(ms, entry_id, term)

            # Write follow-through dependency rules for this question
            _write_ft_rules(ms, question_id, entries)

        ms.commit()
        logger.info("Mark scheme for paper %d written (%d questions)", paper_id, len(parsed))

    if ms_conn is not None and qb_conn is not None:
        _run(ms_conn, qb_conn)
    else:
        with get_db(DB_MARKSCHEME) as ms, get_db(DB_QUESTION_BANK) as qb:
            _run(ms, qb)
