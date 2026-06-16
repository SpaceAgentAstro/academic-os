from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ingestion.ocr import extract_full_text, extract_text_pdfplumber
from ingestion.extractor import extract_question_blocks
from ingestion.classifier import extract_command_word, classify_difficulty, classify_tags, classify_topic

logger = logging.getLogger(__name__)

_MS_PATTERNS = re.compile(r"\b(mark scheme|marking scheme|mark sheet|MS)\b", re.I)
_ER_PATTERNS = re.compile(
    r"\b(examiner.{0,10}report|chief examiner|principal examiner)\b", re.I
)


@dataclass
class PaperMetadata:
    qualification: str
    subject: str
    module_code: str
    paper_code: str
    session: str
    year: int
    paper_type: str    # question_paper | mark_scheme | examiner_report
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


_YEAR_PATTERN    = re.compile(r"\b(20\d{2})\b")
_SESSION_PATTERN = re.compile(
    r"\b(January|February|June|October|November|Jan|Feb|Jun|Oct|Nov)\s*(20\d{2})\b",
    re.I,
)
_MODULE_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    # Mathematics — 2018 spec (pure)
    (re.compile(r"\bWMA11\b", re.I), "Edexcel IAL", "Mathematics", "P1"),
    (re.compile(r"\bWMA12\b", re.I), "Edexcel IAL", "Mathematics", "P2"),
    (re.compile(r"\bWMA13\b", re.I), "Edexcel IAL", "Mathematics", "P3"),
    (re.compile(r"\bWMA14\b", re.I), "Edexcel IAL", "Mathematics", "P4"),
    # Mathematics — pre-2018 spec (pure)
    (re.compile(r"\bWMA01\b", re.I), "Edexcel IAL", "Mathematics", "P1"),
    (re.compile(r"\bWMA02\b", re.I), "Edexcel IAL", "Mathematics", "P2"),
    (re.compile(r"\bWME03\b", re.I), "Edexcel IAL", "Mathematics", "P3"),
    (re.compile(r"\bWME04\b", re.I), "Edexcel IAL", "Mathematics", "P4"),
    # Mathematics — mechanics
    (re.compile(r"\bWME01\b", re.I), "Edexcel IAL", "Mathematics", "M1"),
    (re.compile(r"\bWME02\b", re.I), "Edexcel IAL", "Mathematics", "M2"),
    # Mathematics — statistics
    (re.compile(r"\bWST01\b", re.I), "Edexcel IAL", "Mathematics", "S1"),
    (re.compile(r"\bWST02\b", re.I), "Edexcel IAL", "Mathematics", "S2"),
    (re.compile(r"\bWST03\b", re.I), "Edexcel IAL", "Mathematics", "S3"),
    # Further Mathematics — 2018 spec
    (re.compile(r"\bWFM01\b", re.I), "Edexcel IAL", "Further Mathematics", "FP1"),
    (re.compile(r"\bWFM02\b", re.I), "Edexcel IAL", "Further Mathematics", "FP2"),
    (re.compile(r"\bWFM03\b", re.I), "Edexcel IAL", "Further Mathematics", "FP3"),
    (re.compile(r"\bWDM11\b", re.I), "Edexcel IAL", "Further Mathematics", "D1"),
    # Further Mathematics — pre-2018 spec
    (re.compile(r"\bWME11\b", re.I), "Edexcel IAL", "Further Mathematics", "FP1"),
    (re.compile(r"\bWME12\b", re.I), "Edexcel IAL", "Further Mathematics", "FP2"),
    (re.compile(r"\bWME13\b", re.I), "Edexcel IAL", "Further Mathematics", "FP3"),
    (re.compile(r"\bWDM01\b", re.I), "Edexcel IAL", "Further Mathematics", "D1"),
    # Physics — 2018 spec
    (re.compile(r"\bWPH11\b", re.I), "Edexcel IAL", "Physics", "Unit 1"),
    (re.compile(r"\bWPH12\b", re.I), "Edexcel IAL", "Physics", "Unit 2"),
    (re.compile(r"\bWPH13\b", re.I), "Edexcel IAL", "Physics", "Unit 3"),
    (re.compile(r"\bWPH14\b", re.I), "Edexcel IAL", "Physics", "Unit 4"),
    (re.compile(r"\bWPH15\b", re.I), "Edexcel IAL", "Physics", "Unit 5"),
    (re.compile(r"\bWPH16\b", re.I), "Edexcel IAL", "Physics", "Unit 6"),
    # Physics — pre-2018 spec
    (re.compile(r"\bWPH01\b", re.I), "Edexcel IAL", "Physics", "Unit 1"),
    (re.compile(r"\bWPH02\b", re.I), "Edexcel IAL", "Physics", "Unit 2"),
    (re.compile(r"\bWPH03\b", re.I), "Edexcel IAL", "Physics", "Unit 3"),
    (re.compile(r"\bWPH04\b", re.I), "Edexcel IAL", "Physics", "Unit 4"),
    (re.compile(r"\bWPH05\b", re.I), "Edexcel IAL", "Physics", "Unit 5"),
    (re.compile(r"\bWPH06\b", re.I), "Edexcel IAL", "Physics", "Unit 6"),
    (re.compile(r"\bWPH07\b", re.I), "Edexcel IAL", "Physics", "Unit 7"),
    # Chemistry
    (re.compile(r"\bWCH01\b", re.I), "Edexcel IAL", "Chemistry", "Unit 1"),
    (re.compile(r"\bWCH02\b", re.I), "Edexcel IAL", "Chemistry", "Unit 2"),
    (re.compile(r"\bWCH03\b", re.I), "Edexcel IAL", "Chemistry", "Unit 3"),
    (re.compile(r"\bWCH04\b", re.I), "Edexcel IAL", "Chemistry", "Unit 4"),
    (re.compile(r"\bWCH05\b", re.I), "Edexcel IAL", "Chemistry", "Unit 5"),
    (re.compile(r"\bWCH06\b", re.I), "Edexcel IAL", "Chemistry", "Unit 6"),
    # Computer Science
    (re.compile(r"\b9608\b", re.I), "Cambridge AS & A Level", "Computer Science", "CS"),
]


def detect_paper_type(pdf_path: Path) -> str:
    """Identify whether a PDF is a question_paper, mark_scheme, or examiner_report."""
    name_lower = pdf_path.stem.lower()
    # Edexcel IAL filename conventions: _msc_ = mark scheme, _pef_ = examiner report, _que_ = question paper
    if "_msc_" in name_lower or any(k in name_lower for k in ("mark_scheme", "markscheme", "_ms", "-ms")):
        return "mark_scheme"
    if "_pef_" in name_lower or any(k in name_lower for k in ("examiner_report", "examiners_report", "_er", "-er")):
        return "examiner_report"
    if "_que_" in name_lower:
        return "question_paper"

    try:
        pages = extract_text_pdfplumber(pdf_path)
        sample = " ".join(p["text"] for p in pages[:2])
    except Exception:
        return "question_paper"

    if _ER_PATTERNS.search(sample):
        return "examiner_report"
    if _MS_PATTERNS.search(sample):
        return "mark_scheme"
    return "question_paper"


def extract_metadata(pdf_path: Path) -> PaperMetadata:
    """Extract qualification, subject, module, paper code, and session from a PDF."""
    try:
        pages = extract_text_pdfplumber(pdf_path)
        sample = " ".join(p["text"] for p in pages[:2])
    except Exception:
        sample = ""

    combined = f"{pdf_path.stem} {sample}"

    qualification = "Edexcel IAL"
    subject = "Unknown"
    module_code = "Unknown"
    paper_code = pdf_path.stem

    for pattern, qual, subj, mod in _MODULE_PATTERNS:
        if pattern.search(combined):
            qualification = qual
            subject = subj
            module_code = mod
            break

    session_match = _SESSION_PATTERN.search(combined)
    if session_match:
        session = f"{session_match.group(1).capitalize()} {session_match.group(2)}"
        year = int(session_match.group(2))
    else:
        year_match = _YEAR_PATTERN.search(combined)
        year = int(year_match.group(1)) if year_match else 0
        session = str(year) if year else "Unknown"

    paper_type = detect_paper_type(pdf_path)

    return PaperMetadata(
        qualification=qualification,
        subject=subject,
        module_code=module_code,
        paper_code=paper_code,
        session=session,
        year=year,
        paper_type=paper_type,
        source_file=str(pdf_path),
    )


def extract_questions(pdf_path: Path, metadata: PaperMetadata) -> list[ExtractedQuestion]:
    """Extract all questions from a question paper PDF."""
    full_text = extract_full_text(pdf_path)
    raw_blocks = extract_question_blocks(full_text)

    questions: list[ExtractedQuestion] = []
    for block in raw_blocks:
        q_text = block.get("raw_text", "")
        marks = block.get("marks", 0)
        cw = extract_command_word(q_text)
        has_diagram = bool(re.search(r"\b(figure|diagram|sketch|draw|graph)\b", q_text, re.I))

        q_dict = {"raw_text": q_text, "marks": marks, "command_word": cw}
        difficulty = classify_difficulty(q_dict)
        tags = classify_tags(q_dict)
        topic, subtopic = classify_topic(q_dict, metadata.subject, metadata.module_code)

        questions.append(ExtractedQuestion(
            question_number=block["question_number"],
            marks=marks,
            raw_text=q_text,
            latex_text="",
            command_word=cw,
            has_diagram=has_diagram,
            difficulty=difficulty,
            tags=tags,
            topic=topic,
            subtopic=subtopic,
        ))

    logger.info("Extracted %d questions from %s", len(questions), pdf_path.name)
    return questions


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_paper_to_db(
    conn: sqlite3.Connection,
    metadata: PaperMetadata,
    questions: list[ExtractedQuestion],
) -> int:
    """Insert paper + questions into question_bank.db. Returns paper_id."""
    conn.execute(
        """
        INSERT INTO papers
            (qualification, subject, module_code, paper_code, session, year,
             paper_type, source_file, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_code, session, paper_type) DO UPDATE SET
            source_file=excluded.source_file,
            processed_at=excluded.processed_at
        """,
        (
            metadata.qualification, metadata.subject, metadata.module_code,
            metadata.paper_code, metadata.session, metadata.year,
            metadata.paper_type, metadata.source_file, _now_iso(),
        ),
    )
    # Always re-query: lastrowid=0 on the UPDATE path of ON CONFLICT DO UPDATE
    paper_row = conn.execute(
        "SELECT id FROM papers WHERE paper_code=? AND session=? AND paper_type=?",
        (metadata.paper_code, metadata.session, metadata.paper_type),
    ).fetchone()
    paper_id: int = paper_row["id"]  # type: ignore[index]

    seen_q_nums: set[str] = set()
    for q in questions:
        if q.question_number in seen_q_nums:
            continue  # extractor occasionally emits the same number twice; skip duplicates
        seen_q_nums.add(q.question_number)

        conn.execute(
            """
            INSERT INTO questions
                (paper_id, question_number, marks, command_word, difficulty,
                 raw_text, latex_text, has_diagram)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id, question_number) DO NOTHING
            """,
            (
                paper_id, q.question_number, q.marks, q.command_word,
                q.difficulty, q.raw_text, q.latex_text, int(q.has_diagram),
            ),
        )
        # Re-query id: ON CONFLICT DO NOTHING leaves lastrowid unchanged
        q_row = conn.execute(
            "SELECT id FROM questions WHERE paper_id=? AND question_number=?",
            (paper_id, q.question_number),
        ).fetchone()
        q_id = q_row["id"] if q_row else None
        if q_id:
            if q.tags:
                for tag in q.tags:
                    conn.execute(
                        "INSERT OR IGNORE INTO question_tags (question_id, tag) VALUES (?, ?)",
                        (q_id, tag),
                    )
            if q.topic:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO question_topics
                        (question_id, subject, module_code, topic, subtopic, is_primary)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (q_id, metadata.subject, metadata.module_code, q.topic, q.subtopic),
                )

    return paper_id


def ingest_paper(pdf_path: Path, db_conn: sqlite3.Connection | None = None) -> None:
    """Full ingestion pipeline: detect type → extract → classify → write to question_bank.db."""
    from config.settings import DB_QUESTION_BANK
    from db.models import get_db

    logger.info("Ingesting: %s", pdf_path.name)
    metadata = extract_metadata(pdf_path)

    if metadata.paper_type != "question_paper":
        logger.info(
            "Skipping %s (type=%s); use specialist agent for mark schemes and reports",
            pdf_path.name, metadata.paper_type,
        )
        return

    questions = extract_questions(pdf_path, metadata)
    if not questions:
        logger.warning("No questions extracted from %s", pdf_path.name)
        return

    if db_conn is not None:
        _write_paper_to_db(db_conn, metadata, questions)
        logger.info("Written %d questions (conn provided)", len(questions))
    else:
        with get_db(DB_QUESTION_BANK) as conn:
            paper_id = _write_paper_to_db(conn, metadata, questions)
            logger.info("Paper %d written to question_bank.db (%d questions)", paper_id, len(questions))


def scan_papers_directory(papers_dir: Path | None = None) -> list[Path]:
    """Find all unprocessed PDFs in the papers/ directory."""
    from config.settings import PAPERS_DIR, DB_QUESTION_BANK
    from db.models import get_db

    if papers_dir is None:
        papers_dir = PAPERS_DIR

    all_pdfs = list(papers_dir.rglob("*.pdf"))

    with get_db(DB_QUESTION_BANK) as conn:
        rows = conn.execute("SELECT source_file FROM papers").fetchall()
        known = {row["source_file"] for row in rows}

    unprocessed = [p for p in all_pdfs if str(p) not in known]
    logger.info("%d PDFs found, %d unprocessed", len(all_pdfs), len(unprocessed))
    return unprocessed
