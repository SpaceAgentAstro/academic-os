"""Tests for Phase 3 agents: markscheme, examiner_report, diagram, misconception."""
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
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
    from agents.analysis.markscheme_agent import parse_markscheme
    result = parse_markscheme(MS_PDF)
    assert isinstance(result, dict)
    assert len(result) >= 1


@pytest.mark.skipif(not MS_PDF.exists(), reason="Fixture PDF not generated")
def test_parse_markscheme_mark_types():
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
    from agents.analysis.markscheme_agent import parse_markscheme, MARK_TYPES
    result = parse_markscheme(MS_PDF)
    for q_num, entries in result.items():
        for entry in entries:
            assert entry.mark_type in MARK_TYPES


def test_write_markscheme_entry_directly(ms_db, qb_db):

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
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
    from agents.analysis.examiner_report_agent import extract_observations
    obs = extract_observations(ER_PDF)
    assert isinstance(obs, list)
    assert len(obs) >= 1


@pytest.mark.skipif(not ER_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_observations_types():
    pytest.importorskip("pdfplumber")  # optional ingestion dep (RT-013)
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


# ── Extractor: alternative and required-term extraction ──────────────────────

def test_extract_alternatives_oe():
    from ingestion.extractor import extract_alternatives
    alts = extract_alternatives("M1: Write the formula (oe)")
    assert len(alts) == 1
    assert "oe" in alts[0].lower()


def test_extract_alternatives_accept():
    from ingestion.extractor import extract_alternatives
    alts = extract_alternatives("B1: Accept 'velocity' or 'speed'")
    assert any("velocity" in a.lower() or "speed" in a.lower() for a in alts)


def test_extract_alternatives_none():
    from ingestion.extractor import extract_alternatives
    alts = extract_alternatives("M1: Correct substitution")
    assert alts == []


def test_extract_required_terms():
    from ingestion.extractor import extract_required_terms
    terms = extract_required_terms("B1: Must include 'conservation of momentum'")
    assert len(terms) >= 1
    assert any("conservation" in t.lower() for t in terms)


def test_extract_required_terms_none():
    from ingestion.extractor import extract_required_terms
    terms = extract_required_terms("A1: Correct answer 12.0")
    assert terms == []


def test_parse_mark_lines_alt_method_flag():
    from ingestion.extractor import _parse_mark_lines
    body = "M1: Primary approach\nA1: Answer\nOR\nM1: Alternative approach\nA1: Alt answer"
    entries = _parse_mark_lines("1", body)
    assert len(entries) == 4
    primary = [e for e in entries if not e["is_alternative_method"]]
    alts = [e for e in entries if e["is_alternative_method"]]
    assert len(primary) == 2
    assert len(alts) == 2


def test_parse_mark_lines_alt_method_is_tagged():
    from ingestion.extractor import _parse_mark_lines
    body = "M1: First\nOR\nM1: Second"
    entries = _parse_mark_lines("1", body)
    alt_entries = [e for e in entries if e["is_alternative_method"]]
    # The extractor tags the flag; markscheme_agent applies the sequence offset
    assert len(alt_entries) == 1
    assert alt_entries[0]["mark_type"] == "M"


# ── Markscheme Agent: alternative and ft rule writing ────────────────────────

def _seed_question(ms_db, qb_db) -> int:
    """Seed a paper + question, returning question_id."""
    now = "2023-01-01T00:00:00+00:00"
    qb_db.execute(
        "INSERT INTO papers (qualification, subject, module_code, paper_code, session, year, "
        "paper_type, source_file, processed_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("Edexcel IAL", "Physics", "Unit 5", "WPH15", "June 2023", 2023, "question_paper", "f.pdf", now),
    )
    qb_db.execute(
        "INSERT INTO questions (paper_id, question_number, marks, difficulty, has_diagram) "
        "VALUES (1, '3', 5, 3, 0)"
    )
    qb_db.commit()
    # ms_db doesn't have FK enforcement cross-DB in tests
    ms_db.execute(
        "INSERT INTO markscheme_entries (question_id, sequence, mark_type, marks_value, description) "
        "VALUES (1, 1, 'M', 1, 'Write equation V = V0 e^(-t/RC) (oe)')"
    )
    ms_db.commit()
    return 1


def test_write_mark_alternative(ms_db, qb_db):
    from agents.analysis.markscheme_agent import _write_mark_alternative
    _seed_question(ms_db, qb_db)
    entry_id = ms_db.execute("SELECT id FROM markscheme_entries LIMIT 1").fetchone()[0]
    _write_mark_alternative(ms_db, entry_id, "(oe) — any equivalent form", "oe")
    rows = ms_db.execute("SELECT * FROM mark_alternatives").fetchall()
    assert len(rows) == 1
    assert rows[0]["markscheme_entry_id"] == entry_id
    assert "oe" in rows[0]["alternative_text"].lower()


def test_write_mark_alternative_no_duplicate(ms_db, qb_db):
    from agents.analysis.markscheme_agent import _write_mark_alternative
    _seed_question(ms_db, qb_db)
    entry_id = ms_db.execute("SELECT id FROM markscheme_entries LIMIT 1").fetchone()[0]
    _write_mark_alternative(ms_db, entry_id, "same text")
    _write_mark_alternative(ms_db, entry_id, "same text")
    rows = ms_db.execute("SELECT * FROM mark_alternatives").fetchall()
    assert len(rows) == 1


def test_write_required_term(ms_db, qb_db):
    from agents.analysis.markscheme_agent import _write_required_term
    _seed_question(ms_db, qb_db)
    entry_id = ms_db.execute("SELECT id FROM markscheme_entries LIMIT 1").fetchone()[0]
    _write_required_term(ms_db, entry_id, "exponential decay")
    rows = ms_db.execute("SELECT * FROM required_terms").fetchall()
    assert len(rows) == 1
    assert rows[0]["term"] == "exponential decay"
    assert rows[0]["is_mandatory"] == 1


def test_write_ft_rules(ms_db, qb_db):
    from agents.analysis.markscheme_agent import MarkEntry, _write_ft_rules
    _seed_question(ms_db, qb_db)
    question_id = 1
    entries = [
        MarkEntry(sequence=1, mark_type="M", marks_value=1, description="Primary"),
        MarkEntry(sequence=2, mark_type="A", marks_value=1, description="Answer (ft)",
                  conditionality="follow_through"),
    ]
    _write_ft_rules(ms_db, question_id, entries)
    rules = ms_db.execute("SELECT * FROM follow_through_rules").fetchall()
    assert len(rules) == 1
    assert rules[0]["from_mark_sequence"] == 1
    assert rules[0]["to_mark_sequence"] == 2


def test_write_ft_rules_no_duplicate(ms_db, qb_db):
    from agents.analysis.markscheme_agent import MarkEntry, _write_ft_rules
    _seed_question(ms_db, qb_db)
    entries = [
        MarkEntry(sequence=1, mark_type="M", marks_value=1, description="Primary"),
        MarkEntry(sequence=2, mark_type="A", marks_value=1, description="ft mark",
                  conditionality="follow_through"),
    ]
    _write_ft_rules(ms_db, 1, entries)
    _write_ft_rules(ms_db, 1, entries)  # second call should not duplicate
    rules = ms_db.execute("SELECT * FROM follow_through_rules").fetchall()
    assert len(rules) == 1


# ── Misconception Agent ───────────────────────────────────────────────────────

def _seed_misconception(er_db) -> int:
    """Insert a misconception and return its id."""
    from datetime import date
    today = date.today().isoformat()
    er_db.execute(
        "INSERT INTO misconceptions "
        "(subject, module_code, topic, description, frequency, last_seen, is_active) "
        "VALUES (?,?,?,?,?,?,?)",
        ("Physics", "Unit 5", "Capacitance",
         "Students drop the negative sign when taking ln of both sides.", 3, today, 1),
    )
    er_db.commit()
    return er_db.execute("SELECT last_insert_rowid()").fetchone()[0]


def test_aggregate_misconceptions(er_db):
    from agents.analysis.misconception_agent import aggregate_misconceptions
    _seed_misconception(er_db)
    results = aggregate_misconceptions("Physics", "Unit 5", er_conn=er_db)
    assert len(results) == 1
    assert results[0]["topic"] == "Capacitance"
    assert results[0]["frequency"] == 3


def test_aggregate_misconceptions_empty(er_db):
    from agents.analysis.misconception_agent import aggregate_misconceptions
    results = aggregate_misconceptions("Chemistry", "Unit 4", er_conn=er_db)
    assert results == []


def test_get_active_misconceptions_no_filter(er_db):
    from agents.analysis.misconception_agent import get_active_misconceptions
    _seed_misconception(er_db)
    results = get_active_misconceptions(er_conn=er_db)
    assert len(results) == 1


def test_get_active_misconceptions_subject_filter(er_db):
    from agents.analysis.misconception_agent import get_active_misconceptions
    _seed_misconception(er_db)
    results = get_active_misconceptions(subject="Chemistry", er_conn=er_db)
    assert results == []
    results = get_active_misconceptions(subject="Physics", er_conn=er_db)
    assert len(results) == 1


def test_get_active_misconceptions_limit(er_db):
    from agents.analysis.misconception_agent import get_active_misconceptions
    from datetime import date
    today = date.today().isoformat()
    for i in range(5):
        er_db.execute(
            "INSERT INTO misconceptions "
            "(subject, module_code, topic, description, frequency, last_seen, is_active) "
            "VALUES (?,?,?,?,?,?,?)",
            ("Mathematics", "P2", "Logs", f"Error variant {i}", i + 1, today, 1),
        )
    er_db.commit()
    results = get_active_misconceptions(subject="Mathematics", limit=3, er_conn=er_db)
    assert len(results) == 3


def test_generate_corrective_intervention(er_db):
    from agents.analysis.misconception_agent import generate_corrective_intervention
    misc_id = _seed_misconception(er_db)
    text = generate_corrective_intervention(misc_id, er_conn=er_db)
    assert isinstance(text, str)
    assert len(text) > 20
    assert "Capacitance" in text


def test_generate_corrective_intervention_persisted(er_db):
    from agents.analysis.misconception_agent import generate_corrective_intervention
    misc_id = _seed_misconception(er_db)
    text1 = generate_corrective_intervention(misc_id, er_conn=er_db)
    text2 = generate_corrective_intervention(misc_id, er_conn=er_db)
    assert text1 == text2
    rows = er_db.execute(
        "SELECT * FROM corrective_interventions WHERE misconception_id=?", (misc_id,)
    ).fetchall()
    assert len(rows) == 1  # only stored once


def test_generate_corrective_intervention_not_found(er_db):
    from agents.analysis.misconception_agent import generate_corrective_intervention
    with pytest.raises(ValueError, match="not found"):
        generate_corrective_intervention(9999, er_conn=er_db)
