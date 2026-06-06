-- markscheme.sql
-- Owned by: Markscheme Agent
-- Purpose: Structured marking logic for all extracted questions

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- One row per mark allocation within a question
-- question_id references question_bank.db questions.id
CREATE TABLE IF NOT EXISTS markscheme_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id     INTEGER NOT NULL,           -- FK to question_bank.db questions.id
    sequence        INTEGER NOT NULL DEFAULT 1, -- ordering within a question
    mark_type       TEXT NOT NULL
                    CHECK(mark_type IN ('M','A','B','E','Q','dM','ddM','ft')),
                    -- M=method, A=accuracy, B=independent (not reliant on M),
                    -- E=evaluation/explanation, Q=quality of written communication,
                    -- dM=dependent method (needs preceding M), ft=follow-through
    marks_value     INTEGER NOT NULL DEFAULT 1,
    description     TEXT NOT NULL,              -- what earns this mark
    conditionality  TEXT,                       -- condition for earning this mark (e.g., "requires M1")
    UNIQUE(question_id, sequence)
);

-- Accepted alternative methods or answers for a mark entry
CREATE TABLE IF NOT EXISTS mark_alternatives (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    markscheme_entry_id INTEGER NOT NULL REFERENCES markscheme_entries(id),
    alternative_text    TEXT NOT NULL,
    alternative_latex   TEXT,
    note                TEXT                    -- e.g., "oe" (or equivalent), "isw" (ignore subsequent working)
);

-- Terms that must appear in a student answer to earn marks
CREATE TABLE IF NOT EXISTS required_terms (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    markscheme_entry_id INTEGER NOT NULL REFERENCES markscheme_entries(id),
    term                TEXT NOT NULL,
    is_mandatory        INTEGER NOT NULL DEFAULT 1 CHECK(is_mandatory IN (0,1))
);

-- Follow-through rules: which marks can be earned after an error
CREATE TABLE IF NOT EXISTS follow_through_rules (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id         INTEGER NOT NULL,
    from_mark_sequence  INTEGER NOT NULL,       -- error occurred at this mark
    to_mark_sequence    INTEGER NOT NULL,       -- this mark can be earned on follow-through
    condition           TEXT                    -- additional condition for ft to apply
);

CREATE INDEX IF NOT EXISTS idx_markscheme_question ON markscheme_entries(question_id);
CREATE INDEX IF NOT EXISTS idx_mark_alternatives_entry ON mark_alternatives(markscheme_entry_id);
CREATE INDEX IF NOT EXISTS idx_required_terms_entry ON required_terms(markscheme_entry_id);
