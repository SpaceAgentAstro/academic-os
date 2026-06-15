"""Tests for db/seed_syllabus.py and the three new Telegram command handlers."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"
SYLLABUS_DIR = Path(__file__).parent.parent.parent / "db" / "syllabus"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def progress_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SCHEMA_DIR / "progress.sql").read_text())
    return conn


_AUTHORISED_CHAT_ID = 123456789


@pytest.fixture(autouse=True)
def _authorise_chat(monkeypatch):
    """Configure the authorised Telegram chat so command handlers run (AOS-005)."""
    monkeypatch.setattr("config.settings.TELEGRAM_CHAT_ID", str(_AUTHORISED_CHAT_ID))


def _make_update_context(cmd_args=None):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    # Commands are only honoured from the configured chat (AOS-005).
    update.effective_chat.id = _AUTHORISED_CHAT_ID
    context = MagicMock()
    context.args = cmd_args or []
    return update, context


# ── Seed Syllabus ─────────────────────────────────────────────────────────────

def test_seed_all_returns_counts(progress_db):
    from db.seed_syllabus import seed_all
    totals = seed_all(conn=progress_db)
    assert isinstance(totals, dict)
    assert len(totals) == 5
    for fname, count in totals.items():
        assert count > 0, f"{fname} returned 0 spec points"


def test_seed_all_is_idempotent(progress_db):
    from db.seed_syllabus import seed_all
    first = seed_all(conn=progress_db)
    second = seed_all(conn=progress_db)
    assert first == second


def test_seed_all_subjects_inserted(progress_db):
    from db.seed_syllabus import seed_all
    seed_all(conn=progress_db)
    rows = progress_db.execute("SELECT code FROM subjects ORDER BY code").fetchall()
    codes = {r["code"] for r in rows}
    assert {"MATH", "FM", "PHY", "CHEM", "CS"} <= codes


def test_seed_all_modules_inserted(progress_db):
    from db.seed_syllabus import seed_all
    seed_all(conn=progress_db)
    count = progress_db.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    # 5 subjects × at minimum 3 modules each
    assert count >= 15


def test_seed_all_spec_points_inserted(progress_db):
    from db.seed_syllabus import seed_all
    seed_all(conn=progress_db)
    count = progress_db.execute("SELECT COUNT(*) FROM specification_points").fetchone()[0]
    assert count > 50


def test_seed_all_dry_run_inserts_nothing(progress_db):
    from db.seed_syllabus import seed_all
    totals = seed_all(conn=progress_db, dry_run=True)
    assert all(v > 0 for v in totals.values())
    subject_count = progress_db.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    assert subject_count == 0


def test_seed_subject_mathematics(progress_db):
    from db.seed_syllabus import _seed_subject
    data = json.loads((SYLLABUS_DIR / "mathematics.json").read_text())
    count = _seed_subject(progress_db, data)
    progress_db.commit()
    assert count > 0
    row = progress_db.execute("SELECT name FROM subjects WHERE code='MATH'").fetchone()
    assert row is not None


def test_seed_foreign_keys_valid(progress_db):
    """Every spec_point must reference an existing subtopic."""
    from db.seed_syllabus import seed_all
    seed_all(conn=progress_db)
    bad = progress_db.execute(
        """
        SELECT sp.id FROM specification_points sp
        LEFT JOIN subtopics st ON st.id = sp.subtopic_id
        WHERE st.id IS NULL
        """
    ).fetchall()
    assert len(bad) == 0


# ── Authorisation (AOS-005) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_drops_unauthorised_chat():
    """Commands from any chat other than the configured one are ignored."""
    from agents.delivery.telegram_agent import _cmd_quiz
    update, context = _make_update_context(["Mathematics"])
    update.effective_chat.id = 999  # not the authorised chat

    with patch("agents.delivery.retrieval_agent.get_questions", return_value=[{"x": 1}]) as mock_gq:
        await _cmd_quiz(update, context)

    mock_gq.assert_not_called()
    update.message.reply_text.assert_not_called()


# ── /quiz ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_quiz_no_questions():
    from agents.delivery.telegram_agent import _cmd_quiz
    update, context = _make_update_context()

    with patch("agents.delivery.retrieval_agent.get_questions", return_value=[]):
        await _cmd_quiz(update, context)

    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "No questions" in text or "Ingest" in text


@pytest.mark.asyncio
async def test_cmd_quiz_returns_question():
    from agents.delivery.telegram_agent import _cmd_quiz
    update, context = _make_update_context(["Mathematics"])

    q = {
        "id": 1, "question_number": "3", "marks": 4, "difficulty": 3,
        "paper_code": "WMA11", "session": "June 2023",
        "raw_text": "Find dy/dx for y = 3x^2 + 2x. [4]",
        "latex_text": "",
    }
    with patch("agents.delivery.retrieval_agent.get_questions", return_value=[q]):
        await _cmd_quiz(update, context)

    text = update.message.reply_text.call_args[0][0]
    assert "Mathematics" in text
    assert "Q3" in text
    assert "WMA11" in text


@pytest.mark.asyncio
async def test_cmd_quiz_defaults_to_mathematics():
    from agents.delivery.telegram_agent import _cmd_quiz
    update, context = _make_update_context()  # no args

    q = {
        "id": 1, "question_number": "1", "marks": 2, "difficulty": 2,
        "paper_code": "WMA11", "session": "Jan 2023",
        "raw_text": "State the chain rule. [2]",
        "latex_text": "",
    }
    with patch("agents.delivery.retrieval_agent.get_questions", return_value=[q]) as mock_gq:
        await _cmd_quiz(update, context)

    mock_gq.assert_called_once()
    assert mock_gq.call_args[1]["subject"] == "Mathematics"


# ── /revise ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_revise_no_questions():
    from agents.delivery.telegram_agent import _cmd_revise
    from agents.delivery.revision_agent import RevisionPack
    update, context = _make_update_context(["Chemistry"])

    empty = RevisionPack(
        subject="Chemistry", module_code="All", focus_topics=[],
        questions=[], misconception_reminders=[], estimated_duration_minutes=15,
    )
    with patch("agents.delivery.revision_agent.build_revision_pack", return_value=empty):
        await _cmd_revise(update, context)

    text = update.message.reply_text.call_args[0][0]
    assert "No questions" in text or "Ingest" in text


@pytest.mark.asyncio
async def test_cmd_revise_with_questions():
    from agents.delivery.telegram_agent import _cmd_revise
    from agents.delivery.revision_agent import RevisionPack
    update, context = _make_update_context()  # defaults to Mathematics

    pack = RevisionPack(
        subject="Mathematics", module_code="P1",
        focus_topics=["Calculus", "Algebra"],
        questions=[
            {"id": 1, "question_number": "1", "marks": 3, "difficulty": 2,
             "paper_code": "WMA11", "session": "Jan 2023"},
            {"id": 2, "question_number": "4", "marks": 5, "difficulty": 4,
             "paper_code": "WMA12", "session": "Jun 2023"},
        ],
        misconception_reminders=["Check log laws carefully."],
        estimated_duration_minutes=20,
    )
    with patch("agents.delivery.revision_agent.build_revision_pack", return_value=pack):
        await _cmd_revise(update, context)

    text = update.message.reply_text.call_args[0][0]
    assert "Mathematics" in text
    assert "Calculus" in text
    assert "Q1" in text
    assert "Watch out" in text


@pytest.mark.asyncio
async def test_cmd_revise_defaults_to_mathematics():
    from agents.delivery.telegram_agent import _cmd_revise
    from agents.delivery.revision_agent import RevisionPack
    update, context = _make_update_context()

    pack = RevisionPack(
        subject="Mathematics", module_code="All", focus_topics=["General"],
        questions=[
            {"id": 1, "question_number": "2", "marks": 3, "difficulty": 2,
             "paper_code": "WMA11", "session": "Jun 2023"},
        ],
        misconception_reminders=[], estimated_duration_minutes=10,
    )
    with patch("agents.delivery.revision_agent.build_revision_pack", return_value=pack) as mock_brp:
        await _cmd_revise(update, context)

    mock_brp.assert_called_once()
    assert mock_brp.call_args[1]["subject"] == "Mathematics"


# ── /progress ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_progress_no_data():
    from agents.delivery.telegram_agent import _cmd_progress
    update, context = _make_update_context()

    with patch("agents.infrastructure.curriculum_agent.get_specification_coverage", return_value={}):
        await _cmd_progress(update, context)

    text = update.message.reply_text.call_args[0][0]
    assert "Curriculum Progress" in text
    assert "seed_syllabus" in text or "No syllabus" in text


@pytest.mark.asyncio
async def test_cmd_progress_shows_modules():
    from agents.delivery.telegram_agent import _cmd_progress
    update, context = _make_update_context()

    coverage_data = {"P1": 45.0, "P2": 60.0, "P3": 30.0}
    with patch(
        "agents.infrastructure.curriculum_agent.get_specification_coverage",
        return_value=coverage_data,
    ):
        await _cmd_progress(update, context)

    text = update.message.reply_text.call_args[0][0]
    assert "P1: 45.0%" in text
    assert "P2: 60.0%" in text


@pytest.mark.asyncio
async def test_cmd_progress_handles_exception():
    from agents.delivery.telegram_agent import _cmd_progress
    update, context = _make_update_context()

    with patch(
        "agents.infrastructure.curriculum_agent.get_specification_coverage",
        side_effect=Exception("db locked"),
    ):
        await _cmd_progress(update, context)

    text = update.message.reply_text.call_args[0][0]
    # Generic message — raw exception text must not leak to the chat (AOS-013).
    assert "unavailable" in text
    assert "db locked" not in text
