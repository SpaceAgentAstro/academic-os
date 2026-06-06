---
tags: [architecture, system]
---

# System Overview

## Ingestion Pipeline

```
PDF Drop → detect_paper_type()
         → extract_metadata()    (filename + page 1 text)
         → extract_full_text()   (pdfplumber + tesseract fallback)
         → extract_question_blocks()
         → classify_difficulty() + classify_tags() + classify_topic()
         → _write_paper_to_db()  → question_bank.db
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Python | 3.11+ |
| Package manager | uv |
| Databases | SQLite (6 separate .db files) |
| PDF text extraction | pdfplumber |
| Scanned page OCR | pytesseract (Tesseract 5) |
| LaTeX OCR | pix2tex (optional) |
| Image conversion | pdf2image (poppler) |
| Telegram | python-telegram-bot |
| Scheduler | APScheduler (blocking) |
| Testing | pytest + pytest-cov |

## Data Flow

```
papers/              →  Past Paper Agent   →  question_bank.db
papers/ (MS)         →  Markscheme Agent   →  markscheme.db
papers/ (ER)         →  Examiner Report    →  examiner_reports.db
question_bank.db     →  Retrieval Agent    →  RevisionPack
RevisionPack         →  Briefing Generator →  DailyBriefing
DailyBriefing        →  Telegram Agent     →  User's phone
progress.db          ↔  Curriculum Agent   (sole write authority)
analytics.db         ↔  Analytics Agent
```

## Related Notes
- [[Agent Ownership]]
- [[Database Map]]
