-- progress.sql
-- Owned by: Curriculum Agent (sole write authority)
-- Purpose: Syllabus tracking, topic progression, review scheduling

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Top-level qualification/subject registry
CREATE TABLE IF NOT EXISTS subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,           -- e.g., "Mathematics", "Physics"
    board       TEXT NOT NULL,                  -- e.g., "Pearson Edexcel", "Cambridge"
    qualification TEXT NOT NULL,               -- e.g., "IAL", "AS & A Level"
    code        TEXT NOT NULL UNIQUE            -- e.g., "MATH", "PHY", "CHEM", "CS"
);

CREATE TABLE IF NOT EXISTS modules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id),
    name        TEXT NOT NULL,                  -- e.g., "Pure Mathematics 1", "Statistics 1"
    code        TEXT NOT NULL,                  -- e.g., "P1", "S2", "FP3", "Unit 1"
    sequence    INTEGER NOT NULL DEFAULT 0,     -- display/study order
    UNIQUE(subject_id, code)
);

CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL REFERENCES modules(id),
    name        TEXT NOT NULL,                  -- e.g., "Differentiation", "Normal Distribution"
    sequence    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(module_id, name)
);

CREATE TABLE IF NOT EXISTS subtopics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id    INTEGER NOT NULL REFERENCES topics(id),
    name        TEXT NOT NULL,                  -- e.g., "Chain Rule", "Z-score calculation"
    sequence    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(topic_id, name)
);

CREATE TABLE IF NOT EXISTS specification_points (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subtopic_id     INTEGER NOT NULL REFERENCES subtopics(id),
    spec_ref        TEXT NOT NULL,              -- e.g., "3.2.1", "4.5.2"
    description     TEXT NOT NULL,
    UNIQUE(subtopic_id, spec_ref)
);

-- Curriculum Agent write target
CREATE TABLE IF NOT EXISTS syllabus_completion (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_point_id   INTEGER NOT NULL UNIQUE REFERENCES specification_points(id),
    status          TEXT NOT NULL DEFAULT 'not_started'
                    CHECK(status IN ('not_started','in_progress','taught','reviewed','mastered')),
    confidence      INTEGER CHECK(confidence BETWEEN 1 AND 5),
    first_taught    TEXT,                       -- ISO 8601 date
    last_reviewed   TEXT,                       -- ISO 8601 date
    next_review     TEXT,                       -- ISO 8601 date (spaced repetition target)
    review_count    INTEGER NOT NULL DEFAULT 0,
    notes           TEXT
);

-- Curriculum Agent write target
CREATE TABLE IF NOT EXISTS review_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_point_id   INTEGER NOT NULL REFERENCES specification_points(id),
    reviewed_at     TEXT NOT NULL,              -- ISO 8601 datetime
    outcome         TEXT NOT NULL
                    CHECK(outcome IN ('strong','adequate','weak','failed')),
    notes           TEXT
);

-- Spaced-repetition state, one row per (subject, unit, topic).
-- Materialised by db/seed_syllabus.py from the normalised topic tree above.
-- Read/updated by backend/main.py (adaptive revision engine) and
-- briefing/generator.py. This is the flat projection the API consumes;
-- the normalised tree remains the source of truth for syllabus structure.
CREATE TABLE IF NOT EXISTS spaced_repetition_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject       TEXT NOT NULL,                 -- e.g., "Mathematics"
    unit          TEXT NOT NULL,                 -- module code, e.g., "P1", "Unit 1"
    topic         TEXT NOT NULL,                 -- e.g., "Differentiation"
    subtopic      TEXT,
    mastery       REAL NOT NULL DEFAULT 0.0,     -- 0.0–1.0
    ease_factor   REAL NOT NULL DEFAULT 2.5,     -- SM-2 ease (1.3–3.0)
    interval_days REAL NOT NULL DEFAULT 1.0,     -- days until next review
    due_date      TEXT NOT NULL DEFAULT (DATE('now')),  -- ISO 8601 date
    last_reviewed TEXT,                          -- ISO 8601 date, NULL until first review
    UNIQUE(subject, unit, topic)
);

CREATE INDEX IF NOT EXISTS idx_sri_due_date ON spaced_repetition_items(due_date);
CREATE INDEX IF NOT EXISTS idx_sri_subject ON spaced_repetition_items(subject);
CREATE INDEX IF NOT EXISTS idx_sri_mastery ON spaced_repetition_items(mastery);

CREATE INDEX IF NOT EXISTS idx_syllabus_completion_status ON syllabus_completion(status);
CREATE INDEX IF NOT EXISTS idx_syllabus_completion_next_review ON syllabus_completion(next_review);
CREATE INDEX IF NOT EXISTS idx_review_history_spec_point ON review_history(spec_point_id);
CREATE INDEX IF NOT EXISTS idx_specification_points_subtopic ON specification_points(subtopic_id);
