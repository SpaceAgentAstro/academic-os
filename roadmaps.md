# roadmaps.md — Development Roadmap

## Phase 1 — Architecture, Documentation, Schemas
**Status**: In Progress
**Goal**: Complete project foundation before any implementation

Deliverables:
- [x] Directory structure
- [x] CLAUDE.md
- [x] AGENTS.md
- [x] MEMORY.md
- [x] RESTART.md
- [x] BACKLOG.md
- [x] context.md
- [x] systemArchitecture.md
- [x] conventions.md
- [x] testing.md
- [x] roadmaps.md
- [ ] schemas/progress.sql
- [ ] schemas/question_bank.sql
- [ ] schemas/markscheme.sql
- [ ] schemas/examiner_reports.sql
- [ ] schemas/diagrams.sql
- [ ] schemas/analytics.sql
- [ ] db/models.py
- [ ] config/settings.py
- [ ] .env.example
- [ ] requirements.txt
- [ ] .gitignore
- [ ] Agent stub files (all 15 agents)
- [ ] curriculum JSON files (all 5 subjects)

---

## Phase 2 — Ingestion, OCR, Extraction
**Status**: Planned
**Goal**: Be able to drop a past paper PDF and have structured questions in the database

Deliverables:
- [ ] OCR Agent: pdfplumber text extraction
- [ ] OCR Agent: pytesseract fallback for scanned pages
- [ ] OCR Agent: pix2tex for LaTeX from math images
- [ ] Past Paper Agent: PDF discovery and type detection
- [ ] Past Paper Agent: paper metadata extraction
- [ ] Past Paper Agent: question boundary detection
- [ ] Past Paper Agent: question-to-spec-point classification
- [ ] Integration tests with fixture PDFs

---

## Phase 3 — Classification, Markschemes, Examiner Reports, Diagrams
**Status**: Planned
**Goal**: Extract full intelligence from all paper types

Deliverables:
- [ ] Markscheme Agent: M/A/B/E/Q mark parsing
- [ ] Markscheme Agent: alternative method extraction
- [ ] Examiner Report Agent: observation extraction
- [ ] Examiner Report Agent: misconception detection and storage
- [ ] Misconception Agent: cross-source aggregation
- [ ] Diagram Agent: image boundary detection
- [ ] Diagram Agent: Physics diagram classifier
- [ ] Diagram Agent: Chemistry diagram classifier
- [ ] Diagram Agent: CS diagram classifier
- [ ] Diagram Agent: Maths diagram classifier

---

## Phase 4 — Retrieval, Adaptive Revision
**Status**: Planned
**Goal**: Serve intelligent, prioritized revision content from the database

Deliverables:
- [ ] Retrieval Agent: topic-based question retrieval
- [ ] Retrieval Agent: difficulty-ranked retrieval
- [ ] Retrieval Agent: tag-filtered retrieval
- [ ] Revision Agent: weakness-prioritized revision pack builder
- [ ] Revision Agent: spaced repetition scheduling
- [ ] Revision Agent: mock exam generator
- [ ] Analytics Agent: mastery score calculation
- [ ] Analytics Agent: trend detection

---

## Phase 5 — Curriculum Agents
**Status**: Planned
**Goal**: Automated syllabus tracking with student-confirmed progression

Deliverables:
- [ ] Curriculum Agent: specification coverage tracker
- [ ] Curriculum Agent: confirmation-gated topic advancement
- [ ] Curriculum Agent: topic scheduling
- [ ] Structured syllabus JSON for all 5 subjects (every specification point)

---

## Phase 6 — Daily Briefing, Telegram, Scheduler
**Status**: Planned
**Goal**: Fully autonomous daily educational delivery

Deliverables:
- [ ] Telegram Agent: bot setup, command routing
- [ ] Telegram Agent: daily briefing delivery
- [ ] Telegram Agent: /quiz, /revise, /progress, /status commands
- [ ] Scheduler Agent: daily briefing trigger
- [ ] Scheduler Agent: new paper detection trigger
- [ ] Briefing Generator: Section 1 (Academic Intelligence)
- [ ] Briefing Generator: Section 2 (Curriculum Progress)
- [ ] Briefing Generator: Section 3 (Adaptive Revision)
- [ ] Briefing Generator: Section 4 (System Status)

---

## Long-Term Vision (Post Phase 6)

- Local LLM inference for question generation (using NVIDIA GPU)
- Voice briefings via text-to-speech
- Cross-subject pattern detection (e.g., calculus skills informing Physics mechanics)
- Automated download of newly published past papers
- Performance prediction before mock exams
