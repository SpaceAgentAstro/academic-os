---
tags: [home, dashboard]
created: 2026-06-06
---

# 🎓 Academic OS — Dashboard

> Autonomous educational intelligence platform for Edexcel IAL + Cambridge CS

---

## 📊 Quick Status

| Domain | Status |
|--------|--------|
| **Phase 1** — Architecture & Schemas | ✅ Complete |
| **Phase 2** — OCR & Ingestion | ✅ Complete |
| **Phase 3** — Mark Schemes & Reports | ✅ Complete |
| **Phase 4** — Retrieval & Revision | ✅ Complete |
| **Phase 5** — Curriculum Agent | ✅ Complete |
| **Phase 6** — Briefing & Telegram | ✅ Complete |
| **Paper Bank** — Physics 2019–2026, Maths 2021–2026 | ✅ 331 papers · 2,226 questions |

---

## 🧭 Navigation

### Architecture
- [[Architecture/System Overview]] — Pipeline diagram, tech stack
- [[Architecture/Agent Ownership]] — 15 agents, write authority table
- [[Architecture/Database Map]] — 6 SQLite databases and their owners

### Agents
- [[Agents/Past Paper Agent]] — Ingestion pipeline
- [[Agents/Markscheme Agent]] — Mark parsing
- [[Agents/Examiner Report Agent]] — Observation extraction
- [[Agents/Curriculum Agent]] — Sole write authority for progress.db
- [[Agents/Revision Agent]] — Adaptive revision packs
- [[Agents/Retrieval Agent]] — Cross-database query interface
- [[Agents/Telegram Agent]] — Delivery and bot commands
- [[Agents/Scheduler Agent]] — APScheduler cron jobs

### Curriculum
- [[Curriculum/Mathematics]] — P1–P4, S1–S2, M1–M3
- [[Curriculum/Further Mathematics]] — FP1–FP3, M1–M3
- [[Curriculum/Physics]] — Units 1–6
- [[Curriculum/Chemistry]] — Units 1–6
- [[Curriculum/Computer Science]] — 12 Cambridge domains

### Schemas
- [[Schemas/progress.sql]] — Syllabus completion, spaced repetition
- [[Schemas/question_bank.sql]] — Papers and questions
- [[Schemas/markscheme.sql]] — Mark entries and alternatives
- [[Schemas/examiner_reports.sql]] — Observations and misconceptions
- [[Schemas/diagrams.sql]] — Classified diagram store
- [[Schemas/analytics.sql]] — Mastery scores and session data

### Briefing
- [[Daily_Briefing/Format]] — 4-section daily structure
- [[Daily_Briefing/Telegram Commands]] — /briefing, /status, /coverage

### Progress
- [[Progress/Governing Principles]] — Hard rules, priority order
- [[Progress/Test Coverage]] — 83 tests, all green
- [[Progress/Roadmap]] — Long-term vision
- [[Progress/Paper_Bank_Status]] — 331 papers, 2,226 questions ingested (Physics 2019–2026 · Maths 2021–2026)

---

## 🔑 Hard Rules

1. **Never delete user data**
2. **Never overwrite a database without backup**
3. **Never reorganise the repository without approval**
4. **Always retrieve before generating** — databases before prompt memory
5. **Curriculum Agent is sole write authority** for `progress.db` syllabus state

---

## 🗂 Repository Structure

```
academic-os/
├── agents/
│   ├── analysis/        # past_paper, markscheme, examiner_report, diagram, misconception
│   ├── delivery/        # retrieval, revision, telegram
│   ├── infrastructure/  # curriculum, analytics, scheduler
│   └── subject/         # maths, further_maths, physics, chemistry, cs
├── briefing/            # generator.py — 4-section daily briefing
├── config/              # settings.py — typed env-var config
├── curriculum/          # JSON syllabus files (to be populated)
├── data/                # SQLite databases (gitignored)
├── db/                  # models.py — connection helpers
├── ingestion/           # ocr.py, extractor.py, classifier.py
├── obsidian/            # This Obsidian vault ← you are here
├── papers/              # Raw PDFs (gitignored)
├── schemas/             # 6 SQL schema files
└── tests/               # 83 tests, all passing
```
