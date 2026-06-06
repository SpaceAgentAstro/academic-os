# conventions.md — Coding Conventions

## Language

Python 3.11+. No other languages in the core system.

## Module Layout

```
academic-os/
├── agents/
│   ├── subject/        ← Subject Agents (read-only from DBs)
│   ├── analysis/       ← Analysis Agents (write to their owned DB)
│   ├── delivery/       ← Delivery Agents (read-only, output to Telegram)
│   └── infrastructure/ ← Infrastructure Agents (scheduler, analytics, curriculum)
├── db/
│   ├── models.py       ← Table creation and connection helpers
│   ├── queries.py      ← Reusable parameterized query functions
│   └── migrations/     ← Schema migration scripts
├── ingestion/
│   ├── ocr.py          ← OCR pipeline functions
│   ├── extractor.py    ← Question/markscheme/report extraction logic
│   └── classifier.py  ← Question classification logic
├── curriculum/
│   ├── maths/          ← Maths syllabus JSON files per module
│   ├── further_maths/
│   ├── physics/
│   ├── chemistry/
│   └── cs/
├── papers/             ← Raw input PDFs (gitignored)
├── briefing/
│   ├── generator.py    ← Briefing assembly
│   └── templates/      ← Jinja2 templates for briefing sections
├── config/
│   ├── settings.py     ← Typed config via pydantic-settings
│   └── .env.example
├── tests/
│   └── (mirror of main structure)
├── schemas/            ← SQL schema files (one per database)
└── data/               ← Database files (gitignored)
    ├── progress.db
    ├── question_bank.db
    ├── markscheme.db
    ├── examiner_reports.db
    ├── diagrams.db
    └── analytics.db
```

## Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Database tables: `snake_case`
- Database columns: `snake_case`

## Type Hints

All function signatures must have type hints. Use `from __future__ import annotations` for forward references.

```python
def get_questions_by_topic(topic_id: int, difficulty: int | None = None) -> list[Question]:
    ...
```

## Comments

Write no comments unless the WHY is non-obvious. A non-obvious WHY includes:
- A constraint imposed by an external specification (e.g., "Edexcel mark scheme uses 'oe' for 'or equivalent'")
- A subtle invariant or ordering requirement
- A workaround for a specific library bug

Never comment what the code does (the code already says that).

## Error Handling

- Only validate at system boundaries: user input, external APIs, raw file I/O.
- Do not add try/except for scenarios that cannot happen.
- Use specific exception types, not bare `except Exception`.
- Log errors with context using the standard `logging` module.

## Database Access

- Never use raw SQL strings with f-strings. Always use parameterized queries.
- All DB connections use `with sqlite3.connect(...) as conn:` context manager.
- Connection helpers live in `db/models.py`.
- Query functions live in `db/queries.py` and accept typed parameters.

## Configuration

- All config comes from environment variables via `config/settings.py`.
- No hardcoded paths, tokens, or secrets anywhere in the codebase.
- `.env.example` lists all required environment variables with descriptions.

## Logging

```python
import logging
logger = logging.getLogger(__name__)
```

Log levels:
- `DEBUG`: pipeline internals, query results
- `INFO`: agent start/stop, papers processed, briefings sent
- `WARNING`: unexpected but recoverable state
- `ERROR`: operation failed, will be retried or skipped
- `CRITICAL`: data integrity risk, requires human attention

## Testing

See `testing.md` for full policy. Short version:
- All DB-touching code gets an integration test against a test DB.
- No mocking of database (use an in-memory SQLite DB in tests).
- OCR tests use known fixture PDFs with expected outputs.
