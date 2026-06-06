from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _create_in_memory_db(schema_file: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema_sql = (SCHEMA_DIR / schema_file).read_text()
    conn.executescript(schema_sql)
    return conn


@pytest.fixture
def progress_db() -> sqlite3.Connection:
    return _create_in_memory_db("progress.sql")


@pytest.fixture
def question_bank_db() -> sqlite3.Connection:
    return _create_in_memory_db("question_bank.sql")


@pytest.fixture
def markscheme_db() -> sqlite3.Connection:
    return _create_in_memory_db("markscheme.sql")


@pytest.fixture
def examiner_db() -> sqlite3.Connection:
    return _create_in_memory_db("examiner_reports.sql")


@pytest.fixture
def diagrams_db() -> sqlite3.Connection:
    return _create_in_memory_db("diagrams.sql")


@pytest.fixture
def analytics_db() -> sqlite3.Connection:
    return _create_in_memory_db("analytics.sql")
