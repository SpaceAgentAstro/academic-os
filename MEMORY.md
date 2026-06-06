# MEMORY.md — Architectural Decisions and Key Discoveries

## Session: 2026-06-06 — Repository Bootstrap

### Decision: SQLite over PostgreSQL
Using separate SQLite files per domain (not PostgreSQL) because the system runs on a single laptop with no need for concurrent multi-process writes beyond what SQLite can handle. Simpler deployment, no server process, easy backup (just copy the .db files).

### Decision: Separate database files per domain
`progress.db`, `question_bank.db`, `markscheme.db`, `examiner_reports.db`, `diagrams.db`, `analytics.db` kept separate rather than a single monolithic DB. This enforces agent ownership boundaries at the filesystem level and makes individual backups trivial.

### Decision: pdfplumber + pytesseract + pix2tex for OCR
- `pdfplumber`: text extraction with layout awareness (good for structured question paper text)
- `pytesseract`: fallback OCR for scanned pages
- `pix2tex`: LaTeX extraction from mathematical expression images
- `pdf2image`: PDF page to image conversion for OCR pipeline

### Decision: Retrieval-first, generation-last
All content delivery must attempt database retrieval before calling an LLM. LLM generation is reserved for synthesis tasks (daily briefing summaries, corrective interventions) that cannot be served from stored data.

### Constraint: Telegram delivery only
The sole student-facing delivery channel is Telegram. No web UI planned. Telegram API via python-telegram-bot.

### Discovery: Curriculum Agent is sole progression authority
No subject agent, revision agent, or any other agent may write syllabus progression state. Only the Curriculum Agent may advance topic status in progress.db. This prevents race conditions and ensures the student's confirmed understanding drives progression.

---

*Add entries chronologically. Keep each entry concise and factual. Include the date.*
