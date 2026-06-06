from __future__ import annotations

import sqlite3


def test_progress_schema_creates_tables(progress_db: sqlite3.Connection) -> None:
    tables = {row[0] for row in progress_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {
        "subjects", "modules", "topics", "subtopics",
        "specification_points", "syllabus_completion", "review_history",
    }
    assert expected.issubset(tables)


def test_question_bank_schema_creates_tables(question_bank_db: sqlite3.Connection) -> None:
    tables = {row[0] for row in question_bank_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {"papers", "questions", "question_spec_links", "question_topics", "question_tags"}
    assert expected.issubset(tables)


def test_markscheme_schema_creates_tables(markscheme_db: sqlite3.Connection) -> None:
    tables = {row[0] for row in markscheme_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {"markscheme_entries", "mark_alternatives", "required_terms", "follow_through_rules"}
    assert expected.issubset(tables)


def test_examiner_schema_creates_tables(examiner_db: sqlite3.Connection) -> None:
    tables = {row[0] for row in examiner_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {
        "reports", "observations", "misconceptions",
        "misconception_sources", "corrective_interventions",
    }
    assert expected.issubset(tables)


def test_diagrams_schema_creates_tables(diagrams_db: sqlite3.Connection) -> None:
    tables = {row[0] for row in diagrams_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {"diagrams", "diagram_question_links"}
    assert expected.issubset(tables)


def test_analytics_schema_creates_tables(analytics_db: sqlite3.Connection) -> None:
    tables = {row[0] for row in analytics_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {
        "mastery_scores", "revision_sessions", "session_questions",
        "performance_trends", "topic_difficulty_ratings",
    }
    assert expected.issubset(tables)
