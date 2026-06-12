"""Tests for Phase 5: curriculum_agent."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import date, timedelta

import pytest

SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"


@pytest.fixture
def progress_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "progress.sql").read_text())
    return conn


def _seed_progress(conn: sqlite3.Connection) -> int:
    """Seed a subject → module → topic → subtopic → spec_point chain. Returns spec_point_id."""
    conn.execute(
        "INSERT INTO subjects (name, board, qualification, code) "
        "VALUES ('Mathematics', 'Pearson Edexcel', 'IAL', 'MATH')"
    )
    conn.execute(
        "INSERT INTO modules (subject_id, code, name, sequence) VALUES (1, 'P1', 'Pure 1', 1)"
    )
    conn.execute(
        "INSERT INTO topics (module_id, name, sequence) VALUES (1, 'Calculus', 1)"
    )
    conn.execute(
        "INSERT INTO subtopics (topic_id, name, sequence) VALUES (1, 'Differentiation', 1)"
    )
    conn.execute(
        "INSERT INTO specification_points (subtopic_id, spec_ref, description) "
        "VALUES (1, '3.1.1', 'Differentiate polynomials.')"
    )
    conn.commit()
    return 1  # spec_point_id


def test_advance_topic_inserts_new(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "taught", 3, progress_conn=progress_db, confirmed=True)
    row = progress_db.execute(
        "SELECT status, confidence FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    assert row["status"] == "taught"
    assert row["confidence"] == 3


def test_advance_topic_updates_existing(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "taught", 3, progress_conn=progress_db, confirmed=True)
    advance_topic(sp_id, "reviewed", 4, progress_conn=progress_db, confirmed=True)
    row = progress_db.execute(
        "SELECT status FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    assert row["status"] == "reviewed"


def test_advance_topic_blocks_backwards_move(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "mastered", 5, progress_conn=progress_db, confirmed=True)
    advance_topic(sp_id, "in_progress", 2, progress_conn=progress_db, confirmed=True)  # Should be ignored
    row = progress_db.execute(
        "SELECT status FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    assert row["status"] == "mastered"


def test_update_completion_adds_notes(progress_db):
    from agents.infrastructure.curriculum_agent import update_completion
    sp_id = _seed_progress(progress_db)
    update_completion(sp_id, "taught", confidence=3, notes="Needs more practice", progress_conn=progress_db)
    row = progress_db.execute(
        "SELECT status, notes FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    assert row["notes"] == "Needs more practice"


def test_schedule_review_sets_next_review(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic, schedule_review
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "taught", 3, progress_conn=progress_db, confirmed=True)
    schedule_review(sp_id, "correct", progress_conn=progress_db)
    row = progress_db.execute(
        "SELECT next_review FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    assert row["next_review"] is not None
    # confidence=3 + "correct" → 7 days
    expected = (date.today() + timedelta(days=7)).isoformat()
    assert row["next_review"] == expected


def test_schedule_review_incorrect_short_interval(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic, schedule_review
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "in_progress", 1, progress_conn=progress_db, confirmed=True)
    schedule_review(sp_id, "incorrect", progress_conn=progress_db)
    row = progress_db.execute(
        "SELECT next_review FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    # confidence=1 + "incorrect" → 1 day
    expected = (date.today() + timedelta(days=1)).isoformat()
    assert row["next_review"] == expected


def test_get_next_review_queue_empty(progress_db):
    from agents.infrastructure.curriculum_agent import get_next_review_queue
    _seed_progress(progress_db)
    queue = get_next_review_queue(progress_conn=progress_db)
    assert queue == []


def test_get_next_review_queue_returns_due(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic, get_next_review_queue
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "taught", 2, progress_conn=progress_db, confirmed=True)
    # Force next_review to today
    progress_db.execute(
        "UPDATE syllabus_completion SET next_review=date('now') WHERE spec_point_id=?", (sp_id,)
    )
    progress_db.commit()
    queue = get_next_review_queue(progress_conn=progress_db)
    assert len(queue) == 1
    assert queue[0]["spec_point_id"] == sp_id


def test_get_specification_coverage_empty(progress_db):
    from agents.infrastructure.curriculum_agent import get_specification_coverage
    _seed_progress(progress_db)
    coverage = get_specification_coverage("Mathematics", progress_conn=progress_db)
    assert "P1" in coverage
    assert coverage["P1"] == 0.0


def test_get_specification_coverage_partial(progress_db):
    from agents.infrastructure.curriculum_agent import advance_topic, get_specification_coverage
    sp_id = _seed_progress(progress_db)
    advance_topic(sp_id, "mastered", 5, progress_conn=progress_db, confirmed=True)
    coverage = get_specification_coverage("Mathematics", progress_conn=progress_db)
    assert coverage["P1"] == 100.0


def test_get_current_progression_structure(progress_db):
    from agents.infrastructure.curriculum_agent import get_current_progression
    _seed_progress(progress_db)
    result = get_current_progression("Mathematics", "P1", progress_conn=progress_db)
    assert result["total"] == 1
    assert "by_status" in result
    assert result["coverage_pct"] == 0.0


def test_advance_topic_requires_confirmation(progress_db):
    import pytest
    from agents.infrastructure.curriculum_agent import advance_topic
    sp_id = _seed_progress(progress_db)
    with pytest.raises(PermissionError):
        advance_topic(sp_id, "taught", 3, progress_conn=progress_db)
    row = progress_db.execute(
        "SELECT status FROM syllabus_completion WHERE spec_point_id=?", (sp_id,)
    ).fetchone()
    assert row is None  # nothing written without confirmation
