"""Tests for Phase 3 agents: markscheme, examiner_report, diagram."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

FIXTURES   = Path(__file__).parent.parent / "fixtures" / "pdfs"
MS_PDF     = FIXTURES / "sample_mark_scheme.pdf"
ER_PDF     = FIXTURES / "sample_examiner_report.pdf"
SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"


@pytest.fixture
def ms_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "markscheme.sql").read_text())
    return conn


@pytest.fixture
def qb_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "question_bank.sql").read_text())
    return conn


@pytest.fixture
def er_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "examiner_reports.sql").read_text())
    return conn


@pytest.fixture
def diag_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "diagrams.sql").read_text())
    return conn


# ── Markscheme Agent ──────────────────────────────────────────────────────────

@pytest.mark.skipif(not MS_PDF.exists(), reason="Fixture PDF not generated")
def test_parse_markscheme_returns_dict():
    from agents.analysis.markscheme_agent import parse_markscheme
    result = parse_markscheme(MS_PDF)
    assert isinstance(result, dict)
    assert len(result) >= 1


@pytest.mark.skipif(not MS_PDF.exists(), reason="Fixture PDF not generated")
def test_parse_markscheme_mark_types():
    from agents.analysis.markscheme_agent import parse_markscheme, MARK_TYPES
    result = parse_markscheme(MS_PDF)
    for q_num, entries in result.items():
        for entry in entries:
            assert entry.mark_type in MARK_TYPES


def test_write_markscheme_entry_directly(ms_db, qb_db):
    from agents.analysis.markscheme_agent import MarkEntry, _write_markscheme_entry

    # Insert a question into in-memory qb_db first
    now = "2023-01-01T00:00:00+00:00"
    qb_db.execute(
        "INSERT INTO papers (qualification, subject, module_code, paper_code, session, year, "
        "paper_type, source_file, processed_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("Edexcel IAL", "Mathematics", "P1", "WME01", "January 2023", 2023, "question_paper", "f.pdf", now),
    )
    qb_db.execute(
        "INSERT INTO questions (paper_id, question_number, marks, difficulty, has_diagram) "
        "VALUES (1, '1', 2, 2, 0)"
    )
    qb_db.commit()

    entry = MarkEntry(sequence=1, mark_type="M", marks_value=1, description="Rearrange the equation.")
    ms_db.execute(
        "INSERT INTO markscheme_entries (question_id, sequence, mark_type, marks_value, description) "
        "VALUES (?, ?, ?, ?, ?)", (1, 1, "M", 1, "Rearrange the equation.")
    )
    ms_db.commit()
    rows = ms_db.execute("SELECT * FROM markscheme_entries").fetchall()
    assert len(rows) == 1
    assert rows[0]["mark_type"] == "M"


# ── Examiner Report Agent ─────────────────────────────────────────────────────

@pytest.mark.skipif(not ER_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_observations_returns_list():
    from agents.analysis.examiner_report_agent import extract_observations
    obs = extract_observations(ER_PDF)
    assert isinstance(obs, list)
    assert len(obs) >= 1


@pytest.mark.skipif(not ER_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_observations_types():
    from agents.analysis.examiner_report_agent import extract_observations
    obs = extract_observations(ER_PDF)
    valid_types = {
        "common_error", "misconception", "weak_area",
        "command_word_failure", "positive_note", "emphasis"
    }
    for o in obs:
        assert o.observation_type in valid_types


def test_ensure_report_inserts(er_db, qb_db):
    from agents.analysis.examiner_report_agent import _ensure_report
    report_id = _ensure_report(er_db, 42, 2023, "January 2023", "Mathematics", "P1", "sample text")
    assert report_id is not None
    row = er_db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    assert row["year"] == 2023
    assert row["subject"] == "Mathematics"


def test_upsert_misconception(er_db):
    from agents.analysis.examiner_report_agent import Observation, _ensure_report, _write_observation, _upsert_misconception

    report_id = _ensure_report(er_db, 99, 2023, "June 2023", "Physics", "Unit 2", "text")
    obs = Observation(
        question_number="1", topic="Waves", subtopic=None,
        observation_type="misconception",
        description="Students confused frequency with wavelength.",
        emphasis_level=3,
    )
    obs_id = _write_observation(er_db, report_id, obs, None)
    _upsert_misconception(er_db, obs, obs_id, "Physics", "Unit 2")

    rows = er_db.execute("SELECT * FROM misconceptions").fetchall()
    assert len(rows) == 1
    assert rows[0]["frequency"] == 1
    assert rows[0]["topic"] == "Waves"

    # Second upsert increments frequency
    obs_id2 = _write_observation(er_db, report_id, obs, None)
    _upsert_misconception(er_db, obs, obs_id2, "Physics", "Unit 2")
    rows = er_db.execute("SELECT * FROM misconceptions").fetchall()
    assert rows[0]["frequency"] == 2


# ── Diagram Agent ─────────────────────────────────────────────────────────────

def test_classify_diagram_circuit(tmp_path):
    from agents.analysis.diagram_agent import classify_diagram
    img = tmp_path / "circuit_diagram.png"
    img.touch()
    assert classify_diagram(img, "Physics") == "circuit"


def test_classify_diagram_graph(tmp_path):
    from agents.analysis.diagram_agent import classify_diagram
    img = tmp_path / "maths_graph_q3.png"
    img.touch()
    assert classify_diagram(img, "Mathematics") == "function_graph"


def test_classify_diagram_fallback(tmp_path):
    from agents.analysis.diagram_agent import classify_diagram
    img = tmp_path / "unknown_image_001.png"
    img.touch()
    assert classify_diagram(img, "Mathematics") == "other"


def test_process_images_from_paper(diag_db, tmp_path):
    from agents.analysis.diagram_agent import process_images_from_paper
    img1 = tmp_path / "paper_graph_page_0001.png"
    img2 = tmp_path / "paper_wave_page_0002.png"
    img1.touch()
    img2.touch()

    results = process_images_from_paper(
        [img1, img2],
        subject="Mathematics",
        module_code="P2",
        source_file="test.pdf",
        question_id=None,
        diag_conn=diag_db,
    )
    assert len(results) == 2
    assert results[0]["diagram_type"] == "function_graph"
    assert results[1]["diagram_type"] == "wave"

    rows = diag_db.execute("SELECT * FROM diagrams").fetchall()
    assert len(rows) == 2
