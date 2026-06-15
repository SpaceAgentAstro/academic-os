"""Tests for agents/analysis/past_paper_agent.py using in-memory SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

FIXTURES    = Path(__file__).parent.parent / "fixtures" / "pdfs"
QP_PDF      = FIXTURES / "sample_question_paper.pdf"
MS_PDF      = FIXTURES / "sample_mark_scheme.pdf"
ER_PDF      = FIXTURES / "sample_examiner_report.pdf"
SCHEMA_DIR  = Path(__file__).parent.parent.parent / "schemas"


@pytest.fixture
def question_bank_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "question_bank.sql").read_text())
    return conn


def test_detect_paper_type_question_paper():
    from agents.analysis.past_paper_agent import detect_paper_type
    assert detect_paper_type(QP_PDF) == "question_paper"


def test_detect_paper_type_mark_scheme():
    from agents.analysis.past_paper_agent import detect_paper_type
    assert detect_paper_type(MS_PDF) == "mark_scheme"


def test_detect_paper_type_examiner_report():
    from agents.analysis.past_paper_agent import detect_paper_type
    assert detect_paper_type(ER_PDF) == "examiner_report"


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_metadata_module_code():
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
    from agents.analysis.past_paper_agent import extract_metadata
    meta = extract_metadata(QP_PDF)
    assert meta.module_code == "M1"
    assert meta.subject == "Mathematics"
    assert meta.year == 2023


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_metadata_session():
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
    from agents.analysis.past_paper_agent import extract_metadata
    meta = extract_metadata(QP_PDF)
    assert "2023" in meta.session


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_questions_returns_list():
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
    from agents.analysis.past_paper_agent import extract_metadata, extract_questions
    meta = extract_metadata(QP_PDF)
    questions = extract_questions(QP_PDF, meta)
    assert isinstance(questions, list)
    assert len(questions) >= 2


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_write_paper_to_db(question_bank_db):
    from agents.analysis.past_paper_agent import (
        PaperMetadata, ExtractedQuestion, _write_paper_to_db
    )
    meta = PaperMetadata(
        qualification="Edexcel IAL",
        subject="Mathematics",
        module_code="P1",
        paper_code="WME01",
        session="January 2023",
        year=2023,
        paper_type="question_paper",
        source_file="sample_question_paper.pdf",
    )
    questions = [
        ExtractedQuestion(
            question_number="1",
            marks=2,
            raw_text="Find x such that 2x + 5 = 13.",
            latex_text="",
            command_word="find",
            has_diagram=False,
            difficulty=2,
            tags=["Calculation"],
            topic="Algebra",
            subtopic="Linear Equations",
        ),
        ExtractedQuestion(
            question_number="2",
            marks=3,
            raw_text="Differentiate f(x) = 3x^2 + 2x - 7.",
            latex_text="",
            command_word="differentiate",
            has_diagram=False,
            difficulty=2,
            tags=["Calculation"],
            topic="Calculus",
            subtopic="Differentiation",
        ),
    ]
    paper_id = _write_paper_to_db(question_bank_db, meta, questions)
    assert paper_id is not None

    rows = question_bank_db.execute("SELECT * FROM questions WHERE paper_id=?", (paper_id,)).fetchall()
    assert len(rows) == 2

    tag_rows = question_bank_db.execute("SELECT * FROM question_tags").fetchall()
    assert len(tag_rows) == 2  # one "Calculation" per question

    topic_rows = question_bank_db.execute("SELECT * FROM question_topics").fetchall()
    assert len(topic_rows) == 2


def test_no_duplicate_paper_insert(question_bank_db):
    from agents.analysis.past_paper_agent import PaperMetadata, ExtractedQuestion, _write_paper_to_db
    meta = PaperMetadata(
        qualification="Edexcel IAL", subject="Mathematics", module_code="P2",
        paper_code="WME02", session="June 2022", year=2022,
        paper_type="question_paper", source_file="test.pdf",
    )
    questions = [
        ExtractedQuestion("1", 3, "Solve the equation.", "", "solve", False, 2, ["Calculation"], [], "Algebra", "General"),
    ]
    _write_paper_to_db(question_bank_db, meta, questions)
    # Second insert should not raise
    _write_paper_to_db(question_bank_db, meta, questions)
    rows = question_bank_db.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    assert rows == 1  # ON CONFLICT → still just one row
