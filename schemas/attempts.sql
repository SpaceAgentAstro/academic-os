-- attempts.sql
-- Owned by: Frontend API (backend/main.py)
-- Purpose: Timed paper sessions, per-question marking attempts, mistake taxonomy

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- One row per timed paper sitting
CREATE TABLE IF NOT EXISTS sessions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id              INTEGER NOT NULL,      -- FK to question_bank.db papers.id
    started_at            TEXT NOT NULL,         -- ISO 8601 datetime
    ended_at              TEXT,                  -- ISO 8601 datetime, NULL while running
    official_time_seconds INTEGER NOT NULL DEFAULT 0,
    target_time_seconds   INTEGER NOT NULL DEFAULT 0,
    total_time_seconds    INTEGER                -- set on completion
);

-- Per-question timing within a session
CREATE TABLE IF NOT EXISTS question_times (
    session_id    INTEGER NOT NULL REFERENCES sessions(id),
    question_id   INTEGER NOT NULL,              -- FK to question_bank.db questions.id
    time_seconds  INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'complete'
                  CHECK(status IN ('complete','skipped')),
    PRIMARY KEY(session_id, question_id)
);

-- One row per marked question attempt
CREATE TABLE IF NOT EXISTS attempts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        INTEGER REFERENCES sessions(id),
    question_id       INTEGER NOT NULL,          -- FK to question_bank.db questions.id
    marks_awarded     INTEGER NOT NULL,
    marks_available   INTEGER NOT NULL,
    confidence        INTEGER CHECK(confidence BETWEEN 1 AND 5),
    time_seconds      INTEGER NOT NULL DEFAULT 0,
    notes             TEXT,
    answer_image_path TEXT,
    created_at        TEXT NOT NULL,             -- ISO 8601 datetime
    CHECK(marks_awarded >= 0 AND marks_awarded <= marks_available)
);

-- Categorised mistakes per attempt
CREATE TABLE IF NOT EXISTS attempt_mistakes (
    attempt_id    INTEGER NOT NULL REFERENCES attempts(id),
    mistake_type  TEXT NOT NULL,
    PRIMARY KEY(attempt_id, mistake_type)
);

CREATE INDEX IF NOT EXISTS idx_sessions_paper ON sessions(paper_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_attempts_question ON attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_attempts_created ON attempts(created_at);
