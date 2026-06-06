---
tags: [schema, database]
file: schemas/question_bank.sql
---

# question_bank.sql

```sql
-- question_bank.sql
-- Owned by: Past Paper Agent
-- Purpose: All extracted questions with full metadata

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS papers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    qualification   TEXT NOT NULL,              -- e.g., "IAL", "AS & A Level"
    subject         TEXT NOT NULL,              -- e.g., "Mathematics", "Physics"
    module_code     TEXT NOT NULL,              -- e.g., "P1", "S2", "Unit 4"
    paper_code      TEXT NOT NULL,              -- official paper code, e.g., "WMA11/01"
    session         TEXT NOT NULL,              -- e.g., "January 2023", "October 2022"
    year            INTEGER NOT NULL,
    paper_type      TEXT NOT NULL
                    CHECK(paper_type IN ('question_paper','mark_scheme','examiner_report')),
    source_file     TEXT NOT NULL,              -- original filename
    processed_at    TEXT NOT NULL,              -- ISO 8601 datetime
    UNIQUE(paper_code, session, paper_type)
);

CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id        INTEGER NOT NULL REFERENCES papers(id),
    question_number TEXT NOT NULL,              -- e.g., "1", "3(b)(ii)"
    marks           INTEGER NOT NULL,
    command_word    TEXT,                       -- e.g., "Show that", "Find", "Prove"
    difficulty      INTEGER NOT NULL DEFAULT 2
                    CHECK(difficulty BETWEEN 1 AND 5),
    raw_text        TEXT,                       -- plain text as extracted
    latex_text      TEXT,                       -- LaTeX-converted mathematical content
    has_diagram     INTEGER NOT NULL DEFAULT 0 CHECK(has_diagram IN (0,1)),
    UNIQUE(paper_id, question_number)
);

-- Many-to-many: questions ↔ specification points
CREATE TABLE IF NOT EXISTS question_spec_links (
    question_id     INTEGER NOT NULL REFERENCES questions(id),
    spec_point_id   INTEGER NOT NULL,           -- references progress.db specification_points.id
    PRIMARY KEY(question_id, spec_point_id)
);

-- Many-to-many: questions ↔ topics (denormalized for fast retrieval)
CREATE TABLE IF NOT EXISTS question_topics (
    question_id     INTEGER NOT NULL REFERENCES questions(id),
    subject         TEXT NOT NULL,
    module_code     TEXT NOT NULL,
    topic           TEXT NOT NULL,
    subtopic        TEXT,
    is_primary      INTEGER NOT NULL DEFAULT 1 CHECK(is_primary IN (0,1)),
    PRIMARY KEY(question_id, subject, module_code, topic)
);

-- Question tags (Proof, Modelling, Calculation, etc.)
CREATE TABLE IF NOT EXISTS question_tags (
    question_id     INTEGER NOT NULL REFERENCES questions(id),
    tag             TEXT NOT NULL
                    CHECK(tag IN (
                        'Proof','Modelling','Calculation','Interpretation',
                        'Evaluation','Data Analysis','Diagram Based','Multi Topic'
                    )),
    PRIMARY KEY(question_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_questions_paper ON questions(paper_id);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_question_topics_module ON question_topics(module_code);
CREATE INDEX IF NOT EXISTS idx_question_topics_topic ON question_topics(topic);
CREATE INDEX IF NOT EXISTS idx_papers_subject ON papers(subject);
CREATE INDEX IF NOT EXISTS idx_papers_module ON papers(module_code);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
```
