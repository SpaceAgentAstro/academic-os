# roadmaps.md — Development Roadmap

## Phase 1 — Architecture, Documentation, Schemas
**Status**: Complete
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
- [x] schemas/progress.sql
- [x] schemas/question_bank.sql
- [x] schemas/markscheme.sql
- [x] schemas/examiner_reports.sql
- [x] schemas/diagrams.sql
- [x] schemas/analytics.sql
- [x] db/models.py
- [x] config/settings.py
- [x] .env.example
- [x] requirements.txt
- [x] .gitignore
- [x] Agent stub files (all 15 agents)
- [x] curriculum JSON files (all 5 subjects)

---

## Phase 2 — Ingestion, OCR, Extraction
**Status**: Complete
**Goal**: Be able to drop a past paper PDF and have structured questions in the database

Deliverables:
- [x] OCR Agent: pdfplumber text extraction
- [x] OCR Agent: pytesseract fallback for scanned pages
- [x] OCR Agent: pix2tex for LaTeX from math images
- [x] Past Paper Agent: PDF discovery and type detection
- [x] Past Paper Agent: paper metadata extraction
- [x] Past Paper Agent: question boundary detection
- [x] Past Paper Agent: question-to-spec-point classification
- [x] Integration tests with fixture PDFs

---

## Phase 3 — Classification, Markschemes, Examiner Reports, Diagrams
**Status**: Complete
**Goal**: Extract full intelligence from all paper types

Deliverables:
- [x] Markscheme Agent: M/A/B/E/Q mark parsing
- [x] Markscheme Agent: alternative method extraction
- [x] Examiner Report Agent: observation extraction
- [x] Examiner Report Agent: misconception detection and storage
- [x] Misconception Agent: cross-source aggregation
- [x] Diagram Agent: image boundary detection
- [x] Diagram Agent: Physics diagram classifier
- [x] Diagram Agent: Chemistry diagram classifier
- [x] Diagram Agent: CS diagram classifier
- [x] Diagram Agent: Maths diagram classifier

---

## Phase 4 — Retrieval, Adaptive Revision
**Status**: Complete
**Goal**: Serve intelligent, prioritized revision content from the database

Deliverables:
- [x] Retrieval Agent: topic-based question retrieval
- [x] Retrieval Agent: difficulty-ranked retrieval
- [x] Retrieval Agent: tag-filtered retrieval
- [x] Revision Agent: weakness-prioritized revision pack builder
- [x] Revision Agent: spaced repetition scheduling
- [x] Revision Agent: mock exam generator
- [x] Analytics Agent: mastery score calculation
- [x] Analytics Agent: trend detection

---

## Phase 5 — Curriculum Agents
**Status**: Complete
**Goal**: Automated syllabus tracking with student-confirmed progression

Deliverables:
- [x] Curriculum Agent: specification coverage tracker
- [x] Curriculum Agent: confirmation-gated topic advancement
- [x] Curriculum Agent: topic scheduling
- [x] Structured syllabus JSON for all 5 subjects (every specification point)

---

## Phase 6 — Daily Briefing, Telegram, Scheduler
**Status**: Complete
**Goal**: Fully autonomous daily educational delivery

Deliverables:
- [x] Telegram Agent: bot setup, command routing
- [x] Telegram Agent: daily briefing delivery
- [x] Telegram Agent: /quiz, /revise, /progress, /status commands
- [x] Scheduler Agent: daily briefing trigger
- [x] Scheduler Agent: new paper detection trigger
- [x] Briefing Generator: Section 1 (Academic Intelligence)
- [x] Briefing Generator: Section 2 (Curriculum Progress)
- [x] Briefing Generator: Section 3 (Adaptive Revision)
- [x] Briefing Generator: Section 4 (System Status)

---

## Long-Term Vision (Post Phase 6)

- Local LLM inference for question generation (using NVIDIA GPU)
- Voice briefings via text-to-speech
- Cross-subject pattern detection (e.g., calculus skills informing Physics mechanics)
- Automated download of newly published past papers
- Performance prediction before mock exams
