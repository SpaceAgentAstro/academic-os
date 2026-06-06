---
tags: [schema, database]
file: schemas/diagrams.sql
---

# diagrams.sql

```sql
-- diagrams.sql
-- Owned by: Diagram Agent
-- Purpose: Extracted and classified diagrams from past papers

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS diagrams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file     TEXT NOT NULL,              -- original PDF filename
    page_number     INTEGER NOT NULL,
    image_path      TEXT NOT NULL UNIQUE,       -- path to extracted image file
    subject         TEXT NOT NULL,
    module_code     TEXT NOT NULL,
    diagram_type    TEXT NOT NULL
                    CHECK(diagram_type IN (
                        -- Physics
                        'circuit','electric_field','magnetic_field','mechanics',
                        'vector','physics_graph','wave','ray_diagram',
                        -- Chemistry
                        'reaction_mechanism','spectrum','molecular_structure',
                        'lab_apparatus','energy_profile',
                        -- Mathematics
                        'function_graph','geometric_figure','statistical_chart',
                        'coordinate_geometry',
                        -- Computer Science
                        'logic_gate','flowchart','network_diagram',
                        'system_architecture','state_machine','entity_relationship',
                        -- Generic
                        'table','other'
                    )),
    description     TEXT,                       -- auto-generated description
    width_px        INTEGER,
    height_px       INTEGER,
    processed_at    TEXT NOT NULL               -- ISO 8601 datetime
);

-- Link diagrams to the questions they appear in
-- question_id references question_bank.db questions.id
CREATE TABLE IF NOT EXISTS diagram_question_links (
    diagram_id      INTEGER NOT NULL REFERENCES diagrams(id),
    question_id     INTEGER NOT NULL,           -- FK to question_bank.db questions.id
    position        TEXT                        -- e.g., "above question", "within part (b)"
                    CHECK(position IN ('above','within','below','separate_figure',NULL)),
    PRIMARY KEY(diagram_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_diagrams_subject ON diagrams(subject, module_code);
CREATE INDEX IF NOT EXISTS idx_diagrams_type ON diagrams(diagram_type);
CREATE INDEX IF NOT EXISTS idx_diagram_question_links_question ON diagram_question_links(question_id);
```
