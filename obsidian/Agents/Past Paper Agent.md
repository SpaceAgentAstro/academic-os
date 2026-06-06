---
tags: [agent, ingestion]
file: agents/analysis/past_paper_agent.py
---

# Past Paper Agent

## Responsibility
Sole owner of ingestion from PDF → `question_bank.db`.

## Functions

| Function | Purpose |
|----------|---------|
| `detect_paper_type(pdf_path)` | Returns `question_paper`, `mark_scheme`, or `examiner_report` |
| `extract_metadata(pdf_path)` | Returns `PaperMetadata` (qualification, subject, module, session, year) |
| `extract_questions(pdf_path, metadata)` | Returns `list[ExtractedQuestion]` |
| `ingest_paper(pdf_path)` | Full pipeline: detect → extract → classify → write to DB |
| `scan_papers_directory()` | Find all unprocessed PDFs in papers/ |

## Module Code Detection

Uses `_MODULE_PATTERNS` with official Edexcel paper codes:
- WME01 → P1, WME02 → P2, WME03 → P3, WME04 → P4
- WST01 → S1, WST02 → S2
- WPH01–WPH06 → Physics Units 1–6
- WCH01–WCH06 → Chemistry Units 1–6

## Ingestion Pipeline
```
PDF → detect_paper_type() → extract_metadata()
    → extract_full_text() [pdfplumber + tesseract]
    → extract_question_blocks() [extractor.py]
    → classify_difficulty() [1–5]
    → classify_tags() [Proof, Calculation, ...]
    → classify_topic() [keyword heuristics]
    → _write_paper_to_db()
```

## Related
- [[Agents/Markscheme Agent]]
- [[Agents/Examiner Report Agent]]
- [[Schemas/question_bank.sql]]
