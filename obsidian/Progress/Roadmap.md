---
tags: [roadmap, phases]
---

# Roadmap

## Completed Phases

### Phase 1 — Architecture ✅
- 55 files, 2324 insertions
- All 6 schemas validated in-memory SQLite
- All 15 agents scaffolded
- Governing documents complete

### Phase 2 — Ingestion ✅
- `ingestion/ocr.py` — pdfplumber + tesseract fallback
- `ingestion/extractor.py` — question blocks, mark scheme, report parsing
- `ingestion/classifier.py` — difficulty, tags, topic classification
- `agents/analysis/past_paper_agent.py` — full pipeline

### Phase 3 — Classification ✅
- `agents/analysis/markscheme_agent.py` — mark entry parsing + DB write
- `agents/analysis/examiner_report_agent.py` — observations + misconception upsert
- `agents/analysis/diagram_agent.py` — image classification + DB write

### Phase 4 — Retrieval ✅
- `agents/delivery/retrieval_agent.py` — filtered cross-DB queries
- `agents/delivery/revision_agent.py` — adaptive revision packs, mock exams, SR queue

### Phase 5 — Curriculum Agent ✅
- `agents/infrastructure/curriculum_agent.py` — spaced repetition, coverage, progression

### Phase 6 — Briefing & Delivery ✅
- `briefing/generator.py` — 4-section retrieval-first briefing
- `agents/delivery/telegram_agent.py` — send, split, bot commands
- `agents/infrastructure/scheduler_agent.py` — APScheduler cron jobs

## Pending / Backlog

### High Priority
- **Syllabus JSON files** — seed progress.db with spec points for each module
- **Real past paper ingestion** — drop actual Edexcel PDFs into papers/
- **pix2tex integration** — LaTeX extraction from diagram/equation images
- **.env setup** — configure real Telegram bot token and chat ID

### Medium Priority
- SQLAlchemy ORM (optional ergonomics improvement)
- Alembic migrations for schema evolution
- Redis async queue for large batch ingestion

### Long Term Vision
- 10-year question database (all past papers since IAL launch)
- Adaptive difficulty curve per spec point
- AI-generated corrective interventions for misconceptions
- Cross-subject pattern detection (e.g. calculus in Physics)
