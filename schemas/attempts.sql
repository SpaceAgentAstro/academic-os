-- attempts.sql
-- Owned by: Analytics Agent
-- Purpose: Timed exam sessions, per-question timings, marked attempts and
--          mistake tags written by the frontend marking/timer flows.
-- NOTE: mirrors the live data/attempts.db schema; statements are additive
--       (CREATE IF NOT EXISTS) so applying it never overwrites data.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- One row per timed paper session started from the exam timer
CREATE TABLE IF NOT EXISTS sessions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id              INTEGER NOT NULL,      -- FK to question_bank.db papers.id
    started_at            TEXT NOT NULL,         -- ISO 8601 datetime
    ended_at              TEXT,                  -- ISO 8601 datetime, NULL while running
    official_time_seconds INTEGER NOT NULL DEFAULT 0,
    target_time_seconds   INTEGER NOT NULL DEFAULT 0,
    total_time_seconds    INTEGER                -- set on completion
);

-- Time spent per question inside a session
CREATE TABLE IF NOT EXISTS question_times (
    session_id    INTEGER NOT NULL REFERENCES sessions(id),
    question_id   INTEGER NOT NULL,              -- FK to question_bank.db questions.id
    time_seconds  INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'complete'
                  CHECK(status IN ('complete','skipped')),
    PRIMARY KEY(session_id, question_id)
);

-- Marked attempts (session-linked or standalone when session_id IS NULL)
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

-- Mistake classification tags per attempt
CREATE TABLE IF NOT EXISTS attempt_mistakes (
    attempt_id    INTEGER NOT NULL REFERENCES attempts(id),
    mistake_type  TEXT NOT NULL,
    PRIMARY KEY(attempt_id, mistake_type)
);

CREATE INDEX IF NOT EXISTS idx_sessions_paper ON sessions(paper_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_attempts_question ON attempts(question_id);
