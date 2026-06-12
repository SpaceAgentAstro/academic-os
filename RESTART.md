# RESTART.md — Session Continuity

## Current State (2026-06-12)

**All 6 development phases complete. Bulk past-paper ingestion in progress.**

## Phase Completion Summary

### Phase 1 — Architecture ✅
- All 6 schemas validated; all 15 agents implemented
- Curriculum syllabus in `progress.db` (5 subjects, 31 modules, 486 spec points)
  and exported to `curriculum/<subject>/<module>.json`

### Phase 2 — Ingestion ✅
- `ingestion/ocr.py` — pdfplumber + tesseract fallback + pdf2image + pix2tex
- **OCR deps installed and verified 2026-06-12**: `tesseract` (brew) and
  `pix2tex` (in `.venv`, weights cached) — LaTeX math OCR functional
- `ingestion/extractor.py`, `ingestion/classifier.py`
- `agents/analysis/past_paper_agent.py` — full pipeline to question_bank.db

### Phase 3 — Classification ✅
- `agents/analysis/markscheme_agent.py` — mark entry parsing (M/A/B/E/Q/dM/ddM/ft)
- `agents/analysis/examiner_report_agent.py` — observations + misconception upsert
- `agents/analysis/diagram_agent.py` — image classification + DB write

### Phase 4 — Retrieval ✅
- `agents/delivery/retrieval_agent.py` — filtered cross-DB queries (no writes)
- `agents/delivery/revision_agent.py` — revision packs, mock exams, SR queue

### Phase 5 — Curriculum Agent ✅
- `agents/infrastructure/curriculum_agent.py` — spaced repetition, status progression, coverage
- **Confirmation gate enforced (2026-06-12)**: `advance_topic` raises
  `PermissionError` unless called with `confirmed=True` after explicit
  student confirmation (context.md / AGENTS.md constraint)

### Phase 6 — Briefing & Delivery ✅
- `briefing/generator.py` — 4-section retrieval-first daily briefing
- `agents/delivery/telegram_agent.py` — verified live (briefing delivered)
- `agents/infrastructure/scheduler_agent.py` — APScheduler cron + interval jobs
- Telegram bot token lives ONLY in gitignored `.env`

## Test Suite
- **84 tests, all passing**
- Run: `PYTHONPATH=. .venv/bin/pytest tests/ -q`

## Web Presence
- GitHub repo: SpaceAgentAstro/academic-os (PR #1 GitHub Pages from /docs; PR #2 Vercel)
- Vercel: root `vercel.json` builds `frontend/` (Next.js) — production READY.
  Deployment protection (401 on *.vercel.app) is a setting, not an error.
- Local main and origin/main have diverged (local holds ingestion-era commits;
  origin holds frontend/vercel merges) — reconcile before next push.

## Bulk Ingestion ✅ (completed 2026-06-12, zero errors across all 3 stages)
- Source: `papers/` (chemistry, cs, further_maths, maths, physics)
- Pre-ingest DB backup: `data/backups/pre-ingest-20260611-211201/`
- Stage 1 question papers: 1,130 PDFs read, 0 errors
- Stage 2 mark schemes: 1,402/1,605 matched, 0 errors (203 unmatched = no QP in bank)
- Stage 3 examiner reports: 371 new + 737 already ingested, 212 unmatched, 0 errors
- All 5 DBs pass `PRAGMA integrity_check`

### Final database counts
| Subject | Papers | Questions |
|---|---|---|
| Mathematics | 655 | 6,427 |
| Chemistry | 294 | 4,594 |
| Physics | 284 | 4,212 |
| Computer Science | 91 | 769 |
| Further Mathematics | 91 | 792 |
| **Total** | **1,415** | **16,794** |

- markscheme.db: 18,139 mark entries across 3,323 questions
- examiner_reports.db: 602 reports, 69,239 observations, 498 misconceptions
- Re-running ingestion is safe (idempotent: skips `papers.source_file`,
  MS upserts, ER skips already-ingested paper_ids)
- Known limitation: scanned-only pages now OCR-able (tesseract installed);
  earlier-ingested scanned papers were skipped (re-ingest only if needed)

## Go-Live Checklist
1. `.env`: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID set ✅ (briefing verified)
2. Databases initialised ✅ (`db.models.init_all_databases`)
3. Past papers: bulk ingestion in progress (see above)
4. Start scheduler: `PYTHONPATH=. .venv/bin/python -c "from agents.infrastructure.scheduler_agent import start_scheduler; start_scheduler()"`
5. Obsidian vault: open `obsidian/` in Obsidian

## Environment Notes
- Python 3.11 at `.venv/`; package manager: uv
- tesseract + poppler via Homebrew; pix2tex in `.venv`
- Background long-running jobs: use `nohup ... &` (session-tied
  run_in_background processes die when the session ends)
