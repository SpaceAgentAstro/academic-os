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

## Bulk Ingestion (in progress 2026-06-12)
- Source: `papers/` (chemistry, cs, further_maths, maths, physics) — ~4,000 PDFs
- Pre-ingest DB backup: `data/backups/pre-ingest-20260611-211201/`
- Stage 1 (question papers): `nohup` python PID — log
  `/Users/mouadmaamma/.claude/jobs/774e4792/tmp/ingest_qp.out`; done when
  `=== STAGE1 DONE ===` appears. Idempotent — safe to relaunch; skips
  PDFs already in `papers.source_file`.
- Stage 2 (mark schemes): `/Users/mouadmaamma/.claude/jobs/774e4792/tmp/ingest_ms.py`
- Stage 3 (examiner reports): `/Users/mouadmaamma/.claude/jobs/774e4792/tmp/ingest_er.py`
  (skips paper_ids already in reports — observations are blind INSERTs)
- Run stages sequentially with `PYTHONUNBUFFERED=1 nohup .venv/bin/python <script> >> <log> 2><errlog> &`
- Known limitation: scanned-only pages OCR via tesseract now available;
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
