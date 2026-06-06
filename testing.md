# testing.md — Testing Policy

## Principle

Every feature requires:
1. Validation steps
2. Testing instructions
3. Rollback strategy

## Test Runner

`pytest` with `pytest-cov` for coverage.

Run all tests: `uv run pytest tests/ -v`
Run with coverage: `uv run pytest tests/ --cov=. --cov-report=term-missing`

## Test Structure

Mirror the main module structure:

```
tests/
├── test_db/
│   ├── test_models.py
│   └── test_queries.py
├── test_ingestion/
│   ├── test_ocr.py
│   ├── test_extractor.py
│   └── test_classifier.py
├── test_agents/
│   ├── test_subject/
│   ├── test_analysis/
│   ├── test_delivery/
│   └── test_infrastructure/
├── test_briefing/
│   └── test_generator.py
├── fixtures/
│   ├── pdfs/           ← small fixture PDFs for OCR testing
│   └── data/           ← pre-seeded SQLite test databases
└── conftest.py         ← shared fixtures and in-memory DB setup
```

## Database Testing Policy

- Use in-memory SQLite for all DB tests: `sqlite3.connect(":memory:")`
- Never mock the database (past incident: mock/prod divergence caused missed bugs)
- `conftest.py` provides a `test_db` fixture that creates all tables in memory and seeds minimal data
- Each test gets a fresh in-memory DB (no state leakage between tests)

## OCR Testing Policy

- Use small fixture PDFs in `tests/fixtures/pdfs/`
- Each fixture PDF has a corresponding expected output JSON in `tests/fixtures/data/`
- Test that extracted text matches expected output within a configurable tolerance
- Test LaTeX conversion on known math expressions

## Agent Testing Policy

- Test each agent's core logic against a pre-seeded in-memory DB
- Do not test Telegram delivery in automated tests (integration-only, manual)
- Do not test external LLM calls in automated tests (mock the LLM client)

## Rollback Strategy

For every DB-writing operation:
1. Open a transaction before writing
2. Validate the data before committing
3. If validation fails, rollback and log the error
4. Never commit partial ingestion results

For paper ingestion:
- Use a staging area: parse into memory, validate fully, then write to DB
- If any question fails validation, skip the paper and log the failure (do not partially insert)

## Continuous Validation

After each ingestion:
1. Count questions inserted vs. expected (based on paper metadata)
2. Verify all spec point links resolve
3. Verify all required fields are populated
4. Alert via Telegram if counts deviate by more than 10%
