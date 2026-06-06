-- analytics.sql
-- Owned by: Analytics Agent
-- Purpose: Performance tracking, mastery scores, revision statistics, trends

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Mastery scores per specification point over time
-- spec_point_id references progress.db specification_points.id
CREATE TABLE IF NOT EXISTS mastery_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_point_id   INTEGER NOT NULL,           -- FK to progress.db specification_points.id
    score           REAL NOT NULL CHECK(score BETWEEN 0.0 AND 1.0),
    assessed_at     TEXT NOT NULL,              -- ISO 8601 datetime
    method          TEXT NOT NULL
                    CHECK(method IN ('quiz','past_paper','revision_session','self_assessment'))
);

-- Revision session records
CREATE TABLE IF NOT EXISTS revision_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at          TEXT NOT NULL,          -- ISO 8601 datetime
    ended_at            TEXT,
    subject             TEXT NOT NULL,
    module_code         TEXT,
    questions_attempted INTEGER NOT NULL DEFAULT 0,
    questions_correct   INTEGER NOT NULL DEFAULT 0,
    questions_partial   INTEGER NOT NULL DEFAULT 0,
    session_type        TEXT NOT NULL
                        CHECK(session_type IN ('quiz','mock_exam','topic_review','spaced_repetition'))
);

-- Questions attempted within revision sessions
-- question_id references question_bank.db questions.id
CREATE TABLE IF NOT EXISTS session_questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES revision_sessions(id),
    question_id     INTEGER NOT NULL,           -- FK to question_bank.db questions.id
    marks_awarded   INTEGER,
    marks_available INTEGER NOT NULL,
    outcome         TEXT NOT NULL
                    CHECK(outcome IN ('correct','partial','incorrect','skipped'))
);

-- Aggregated performance trends per topic over rolling windows
CREATE TABLE IF NOT EXISTS performance_trends (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject         TEXT NOT NULL,
    module_code     TEXT NOT NULL,
    topic           TEXT NOT NULL,
    computed_at     TEXT NOT NULL,              -- ISO 8601 date
    window_days     INTEGER NOT NULL DEFAULT 30,
    avg_score       REAL CHECK(avg_score BETWEEN 0.0 AND 1.0),
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    trend_direction TEXT
                    CHECK(trend_direction IN ('improving','stable','declining','insufficient_data'))
);

-- Per-topic difficulty ratings (student's experienced difficulty vs. nominal)
-- topic_id references progress.db topics.id
CREATE TABLE IF NOT EXISTS topic_difficulty_ratings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id        INTEGER NOT NULL UNIQUE,    -- FK to progress.db topics.id
    nominal_difficulty INTEGER CHECK(nominal_difficulty BETWEEN 1 AND 5),
    experienced_difficulty REAL CHECK(experienced_difficulty BETWEEN 1.0 AND 5.0),
    last_updated    TEXT NOT NULL               -- ISO 8601 date
);

CREATE INDEX IF NOT EXISTS idx_mastery_scores_spec ON mastery_scores(spec_point_id);
CREATE INDEX IF NOT EXISTS idx_mastery_scores_date ON mastery_scores(assessed_at);
CREATE INDEX IF NOT EXISTS idx_revision_sessions_subject ON revision_sessions(subject);
CREATE INDEX IF NOT EXISTS idx_session_questions_session ON session_questions(session_id);
CREATE INDEX IF NOT EXISTS idx_performance_trends_topic ON performance_trends(subject, module_code, topic);
CREATE INDEX IF NOT EXISTS idx_performance_trends_date ON performance_trends(computed_at);
