from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config.settings import (
    DB_ANALYTICS,
    DB_DIAGRAMS,
    DB_EXAMINER,
    DB_MARKSCHEME,
    DB_PROGRESS,
    DB_QUESTION_BANK,
)

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

_DB_SCHEMA_MAP: dict[Path, str] = {
    DB_PROGRESS:      "progress.sql",
    DB_QUESTION_BANK: "question_bank.sql",
    DB_MARKSCHEME:    "markscheme.sql",
    DB_EXAMINER:      "examiner_reports.sql",
    DB_DIAGRAMS:      "diagrams.sql",
    DB_ANALYTICS:     "analytics.sql",
}


def _apply_schema(conn: sqlite3.Connection, schema_file: str) -> None:
    schema_path = SCHEMA_DIR / schema_file
    conn.executescript(schema_path.read_text())


def init_all_databases() -> None:
    for db_path, schema_file in _DB_SCHEMA_MAP.items():
        with sqlite3.connect(db_path) as conn:
            _apply_schema(conn, schema_file)


@contextmanager
def get_db(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_progress_db() -> contextmanager:
    return get_db(DB_PROGRESS)


def get_question_bank_db() -> contextmanager:
    return get_db(DB_QUESTION_BANK)


def get_markscheme_db() -> contextmanager:
    return get_db(DB_MARKSCHEME)


def get_examiner_db() -> contextmanager:
    return get_db(DB_EXAMINER)


def get_diagrams_db() -> contextmanager:
    return get_db(DB_DIAGRAMS)


def get_analytics_db() -> contextmanager:
    return get_db(DB_ANALYTICS)
