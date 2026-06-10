# BACKLOG.md — Future Work Tracker

## Legend
- `[P1]` Phase 1 — Architecture / Documentation / Schemas
- `[P2]` Phase 2 — Ingestion / OCR / Extraction
- `[P3]` Phase 3 — Classification / Markschemes / Examiner Reports / Diagrams
- `[P4]` Phase 4 — Retrieval / Adaptive Revision
- `[P5]` Phase 5 — Curriculum Agents
- `[P6]` Phase 6 — Daily Briefing / Telegram / Scheduler
- `[TD]` Technical Debt
- `[BUG]` Bug

---

## Phase 1 — In Progress

- [P1] Write all database schemas (schemas/*.sql)
- [P1] Write requirements.txt
- [P1] Write config/settings.py
- [P1] Write .env.example
- [P1] Write .gitignore
- [P1] Write db/models.py
- [P1] Scaffold all agent stub files with correct signatures
- [P1] Write curriculum syllabus JSON for all 5 subjects

## Phase 2 — Planned

- [P2] Implement OCR Agent: PDF text extraction with pdfplumber
- [P2] Implement OCR Agent: scanned page fallback with pytesseract
- [P2] Implement OCR Agent: LaTeX extraction with pix2tex
- [P2] Implement Past Paper Agent: PDF discovery and ingestion pipeline
- [P2] Implement Past Paper Agent: paper metadata extraction (year, session, unit, paper code)
- [P2] Implement Past Paper Agent: question boundary detection
- [P2] Implement Past Paper Agent: question-to-spec-point mapping logic

## Phase 3 — Complete ✅ (2026-06-09)

- ~~[P3] Implement Markscheme Agent: M/A/B/E/Q mark type parsing~~
- ~~[P3] Implement Markscheme Agent: alternative method extraction~~
- ~~[P3] Implement Markscheme Agent: follow-through rule detection~~
- ~~[P3] Implement Examiner Report Agent: observation extraction~~
- ~~[P3] Implement Examiner Report Agent: misconception detection~~
- ~~[P3] Implement Diagram Agent: diagram boundary detection in extracted images~~
- ~~[P3] Implement Diagram Agent: Physics diagram classifier (circuits, fields, mechanics, vectors)~~
- ~~[P3] Implement Diagram Agent: Chemistry diagram classifier (mechanisms, spectra, molecules)~~
- ~~[P3] Implement Diagram Agent: CS diagram classifier (logic gates, flowcharts, network, architecture)~~
- ~~[P3] Implement Diagram Agent: Maths diagram classifier (graphs, geometry)~~
- ~~[P3] Implement Misconception Agent: cross-source aggregation from examiner reports~~
- ~~[P3] Implement Misconception Agent: corrective intervention generator~~

## Phase 4 — Planned

- [P4] Implement Retrieval Agent: topic-based question retrieval with filters
- [P4] Implement Retrieval Agent: difficulty-ranked retrieval
- [P4] Implement Retrieval Agent: tag-filtered retrieval
- [P4] Implement Revision Agent: weakness-prioritized revision pack builder
- [P4] Implement Revision Agent: spaced repetition scheduling
- [P4] Implement Revision Agent: mock exam generator from question bank
- [P4] Implement Analytics Agent: mastery score calculation
- [P4] Implement Analytics Agent: trend detection (improving / declining / stagnant)

## Phase 5 — Complete ✅ (2026-06-09)

- ~~[P5] Implement Curriculum Agent: syllabus coverage tracker~~
- ~~[P5] Implement Curriculum Agent: specification point completion workflow~~
- ~~[P5] Implement Curriculum Agent: topic scheduling with spaced repetition~~
- ~~[P5] Implement Curriculum Agent: confirmation-gated progression~~
- ~~[P5] Write complete syllabus specification for all 5 subjects in structured JSON~~

## Phase 6 — Complete ✅ (2026-06-09)

- ~~[P6] Implement Telegram Agent: bot setup and command routing~~
- ~~[P6] Implement Telegram Agent: daily briefing delivery~~
- ~~[P6] Implement Telegram Agent: interactive revision commands (/quiz, /revise, /progress)~~
- ~~[P6] Implement Scheduler Agent: daily briefing trigger (configurable time)~~
- ~~[P6] Implement Scheduler Agent: paper processing trigger (on new file detection)~~
- ~~[P6] Implement Briefing Generator: all 4 sections (Academic Intelligence, Curriculum Progress, Adaptive Revision, System Status)~~

## Technical Debt

- [TD] Evaluate pix2tex accuracy on Edexcel Mathematics notation vs. commercial alternatives
- [TD] Consider moving from raw sqlite3 to SQLAlchemy ORM if query complexity grows
- [TD] Add database migration system (Alembic) if schema evolves after data is loaded
- [TD] Consider Redis for async task queue if SQLite-backed queue becomes a bottleneck

---

*Add items as discovered. Mark done items with ~~strikethrough~~ and date.*
