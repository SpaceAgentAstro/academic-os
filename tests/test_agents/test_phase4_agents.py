"""Tests for Phase 4: retrieval_agent and revision_agent."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"


def _seed_question_bank(conn: sqlite3.Connection) -> None:
    now = "2023-01-01T00:00:00+00:00"
    conn.execute(
        "INSERT INTO papers (qualification, subject, module_code, paper_code, session, "
        "year, paper_type, source_file, processed_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("Edexcel IAL", "Mathematics", "P1", "WME01", "January 2023", 2023, "question_paper", "f.pdf", now),
    )
    for q_num, marks, diff in [("1", 2, 2), ("2", 3, 3), ("3", 4, 4), ("4", 6, 4)]:
        conn.execute(
            "INSERT INTO questions (paper_id, question_number, marks, difficulty, has_diagram) "
            "VALUES (1, ?, ?, ?, 0)", (q_num, marks, diff),
        )
    conn.execute(
        "INSERT INTO question_topics (question_id, subject, module_code, topic, subtopic, is_primary) "
        "VALUES (1, 'Mathematics', 'P1', 'Calculus', 'Differentiation', 1)"
    )
    conn.execute(
        "INSERT INTO question_tags (question_id, tag) VALUES (1, 'Calculation')"
    )
    conn.commit()


@pytest.fixture
def qb_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "question_bank.sql").read_text())
    _seed_question_bank(conn)
    return conn


@pytest.fixture
def er_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "examiner_reports.sql").read_text())
    return conn


@pytest.fixture
def analytics_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "analytics.sql").read_text())
    return conn


@pytest.fixture
def progress_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "progress.sql").read_text())
    return conn


# ── Retrieval Agent ───────────────────────────────────────────────────────────

def test_get_questions_by_subject(qb_db):
    from agents.delivery.retrieval_agent import get_questions
    results = get_questions(subject="Mathematics", qb_conn=qb_db)
    assert len(results) == 4


def test_get_questions_by_module(qb_db):
    from agents.delivery.retrieval_agent import get_questions
    results = get_questions(subject="Mathematics", module_code="P1", qb_conn=qb_db)
    assert len(results) == 4


def test_get_questions_by_difficulty(qb_db):
    from agents.delivery.retrieval_agent import get_questions
    results = get_questions(subject="Mathematics", difficulty=4, qb_conn=qb_db)
    assert all(r["difficulty"] == 4 for r in results)
    assert len(results) == 2


def test_get_questions_by_topic(qb_db):
    from agents.delivery.retrieval_agent import get_questions
    results = get_questions(subject="Mathematics", topic="Calculus", qb_conn=qb_db)
    assert len(results) == 1


def test_get_questions_exclude_ids(qb_db):
    from agents.delivery.retrieval_agent import get_questions
    all_qs = get_questions(subject="Mathematics", qb_conn=qb_db)
    first_id = all_qs[0]["id"]
    filtered = get_questions(subject="Mathematics", exclude_ids=[first_id], qb_conn=qb_db)
    assert all(q["id"] != first_id for q in filtered)


def test_get_questions_empty_result(qb_db):
    from agents.delivery.retrieval_agent import get_questions
    results = get_questions(subject="Chemistry", qb_conn=qb_db)
    assert results == []


def test_get_misconceptions_empty(er_db):
    from agents.delivery.retrieval_agent import get_misconceptions
    results = get_misconceptions(subject="Mathematics", er_conn=er_db)
    assert results == []


def test_get_misconceptions_returns_active(er_db):
    from agents.delivery.retrieval_agent import get_misconceptions
    # Seed a misconception
    er_db.execute(
        "INSERT INTO misconceptions (subject, module_code, topic, description, frequency, last_seen, is_active) "
        "VALUES ('Physics', 'Unit 2', 'Waves', 'Frequency/wavelength confusion.', 3, '2023-01-01', 1)"
    )
    er_db.commit()
    results = get_misconceptions(subject="Physics", er_conn=er_db)
    assert len(results) == 1
    assert results[0]["frequency"] == 3


def test_get_weak_topics_empty(analytics_db):
    from agents.delivery.retrieval_agent import get_weak_topics
    results = get_weak_topics("Mathematics", analytics_conn=analytics_db)
    assert results == []


def test_get_weak_topics_returns_ordered(analytics_db):
    from agents.delivery.retrieval_agent import get_weak_topics
    analytics_db.execute(
        "INSERT INTO performance_trends (subject, module_code, topic, computed_at, window_days, avg_score, attempt_count, trend_direction) "
        "VALUES ('Mathematics', 'P1', 'Calculus', date('now'), 30, 0.4, 10, 'declining')"
    )
    analytics_db.execute(
        "INSERT INTO performance_trends (subject, module_code, topic, computed_at, window_days, avg_score, attempt_count, trend_direction) "
        "VALUES ('Mathematics', 'P2', 'Algebra', date('now'), 30, 0.7, 5, 'stable')"
    )
    analytics_db.commit()
    results = get_weak_topics("Mathematics", analytics_conn=analytics_db)
    assert results[0]["avg_score"] <= results[-1]["avg_score"]  # ascending by weakness


# ── Revision Agent ─────────────────────────────────────────────────────────────

def test_build_revision_pack_returns_pack(qb_db, er_db, analytics_db):
    from agents.delivery.revision_agent import build_revision_pack, RevisionPack
    pack = build_revision_pack(
        subject="Mathematics",
        module_code="P1",
        max_questions=5,
        qb_conn=qb_db,
        er_conn=er_db,
        analytics_conn=analytics_db,
    )
    assert isinstance(pack, RevisionPack)
    assert pack.subject == "Mathematics"
    assert 0 <= len(pack.questions) <= 5


def test_build_revision_pack_with_weak_topics(qb_db, er_db, analytics_db):
    from agents.delivery.revision_agent import build_revision_pack
    analytics_db.execute(
        "INSERT INTO performance_trends (subject, module_code, topic, computed_at, window_days, avg_score, attempt_count, trend_direction) "
        "VALUES ('Mathematics', 'P1', 'Calculus', date('now'), 30, 0.2, 8, 'declining')"
    )
    analytics_db.commit()
    pack = build_revision_pack(
        subject="Mathematics",
        module_code="P1",
        max_questions=10,
        qb_conn=qb_db,
        er_conn=er_db,
        analytics_conn=analytics_db,
    )
    assert "Calculus" in pack.focus_topics


def test_build_mock_exam(qb_db):
    from agents.delivery.revision_agent import build_mock_exam
    exam = build_mock_exam(
        subject="Mathematics",
        module_code="P1",
        total_marks=10,
        qb_conn=qb_db,
    )
    assert isinstance(exam, list)
    total = sum(q["marks"] for q in exam)
    assert total <= 10


def test_spaced_repetition_queue_empty(progress_db):
    from agents.delivery.revision_agent import get_spaced_repetition_queue
    queue = get_spaced_repetition_queue(progress_conn=progress_db)
    assert queue == []
