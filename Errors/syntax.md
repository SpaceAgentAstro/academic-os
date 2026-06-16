# AcademicOS — Codebase-Wide Syntax & Structure Audit

**Audit date:** 2026-06-16
**Branch:** `claude/determined-cerf-kauck5`
**Auditor:** Automated syntax/parse/compile sweep (independent re-run)
**Scope:** Every tracked source, configuration, script, test, migration, schema,
build, and infrastructure file in the repository.

---

## Executive Summary

AcademicOS is **syntactically clean and builds successfully** across every
language present in the repository. All available compilers, type checkers,
linters, parsers, and bundlers were executed and their output validated against
the relevant language specification.

| Stage / Tool | Command | Result |
|---|---|---|
| Python byte-compile (all tracked `.py`) | `python -m compileall` | ✅ 0 syntax errors |
| Ruff syntax + undefined-name + redefinition | `ruff check --select E9,F63,F7,F82,F811,F821,F822` | ✅ All checks passed |
| Ruff unused-import | `ruff check --select F401` | ⚠️ 15 findings (SYN-002, non-blocking) |
| Python import smoke-test (34 modules) | `importlib.import_module` | ✅ 0 code errors (3 missing-dep only — out of scope) |
| Internal module symbol references | manual + `ruff` | ⚠️ 1 invalid runtime import (SYN-001) |
| TypeScript type check | `tsc --noEmit` | ✅ 0 errors |
| ESLint | `next lint` | ✅ 0 warnings / 0 errors |
| Next.js production build | `next build` | ✅ Compiled successfully, 5/5 pages |
| JSON (all curriculum/syllabus/config) | `json.load` | ✅ All valid |
| TOML | `tomllib.load` (`pyproject.toml`) | ✅ Valid |
| SQL (7 schema files) | `sqlite3.executescript` | ✅ All valid |
| Shell | `bash -n start-backend.sh` | ✅ Valid |
| `.mjs` configs | `node --check` | ✅ Valid |
| CSS (`globals.css`) | brace/at-rule check | ✅ Balanced (430/430) |
| HTML (`docs/index.html`) | `html.parser` | ✅ All tags closed |
| YAML / XML | — | None present in repo |

**Net finding:** There are **no** parse-blocking, compile-blocking, or
build-blocking syntax errors anywhere in the repository. One genuine
**runtime-breaking invalid import** exists (**SYN-001**), plus a set of
**non-blocking lint-hygiene** unused imports (**SYN-002**) recorded per the
audit's "all findings, regardless of severity" requirement.

> **Note on environment:** The Python import smoke-test reported three
> `ModuleNotFoundError`s (`fastapi`, `dotenv` in `backend/main.py`,
> `config/settings.py`, `db/models.py`). These are **not** syntax or code
> errors — both packages are correctly declared in `requirements.txt`
> (`fastapi[standard]>=0.115.0`, `python-dotenv>=1.0.0`) and were simply not
> installed in the audit environment. They are explicitly **out of scope** for
> a syntax audit and are listed here only for completeness.

---

## SYN-001 — Invalid import + async-call misuse on the `--send-now` path

### Severity
**High** — guaranteed runtime crash (`ImportError`) on a real, user-invokable
code path. Not a compile/parse error, so it passes all static checks.

### Language/File Type
Python

### Location
`briefing/generator.py:286–288`

### Error Description
The `__main__` block, reached when the module is executed with
`python briefing/generator.py --send-now`, attempts to import a class
`TelegramAgent` from `agents.delivery.telegram_agent` and call it like a
synchronous object:

```python
from agents.delivery.telegram_agent import TelegramAgent
TelegramAgent().send_message(text)
```

Two distinct defects compound here:

1. **No such symbol.** `agents/delivery/telegram_agent.py` exposes only
   **module-level functions** — `send_message`, `send_daily_briefing`,
   `_split_message`, `start_bot`, and command handlers. There is **no
   `TelegramAgent` class**, so the `import` raises `ImportError` immediately.
2. **Sync call to an async coroutine.** Even if the symbol existed,
   `send_message` is declared `async def send_message(text, parse_mode="Markdown")`.
   Calling it without `await` / `asyncio.run(...)` would only create a coroutine
   that is never awaited (`RuntimeWarning: coroutine ... was never awaited`),
   sending nothing.

Because the import is local to the `if "--send-now" in sys.argv:` branch, it is
invisible to `py_compile`, `ruff` (F401/F821 do not flag function-local imports
of non-existent attributes), and to any module-import test — it only fails when
that branch actually executes.

### Compiler/Linter Output
No static tool flags this (function-scoped import of a non-existent attribute).
At runtime:
```
ImportError: cannot import name 'TelegramAgent' from 'agents.delivery.telegram_agent'
```

### Evidence
`agents/delivery/telegram_agent.py` symbol inventory:
```
11: async def send_message(text: str, parse_mode: str = "Markdown") -> None
42: def       _split_message(text: str, max_len: int) -> list[str]
60: async def send_daily_briefing(briefing_text: str) -> None
66: def       start_bot() -> None
83+: async def _cmd_briefing / _cmd_status / _cmd_coverage / _cmd_quiz / _cmd_revise / _cmd_progress
```
The correct, working pattern already exists in `scripts/send_briefing.py:42–43`:
```python
from agents.delivery.telegram_agent import send_daily_briefing
asyncio.run(send_daily_briefing(text))
```

### Impact
Running `python briefing/generator.py --send-now` crashes with `ImportError`
before any message is sent. Any scheduler/automation wired to that entry point
fails. Briefing generation itself (without `--send-now`) is unaffected.

### Recommended Fix
Mirror the verified pattern from `scripts/send_briefing.py`:
```python
if "--send-now" in sys.argv:
    import asyncio
    from agents.delivery.telegram_agent import send_daily_briefing
    asyncio.run(send_daily_briefing(text))
    print("\n[sent to Telegram]")
```

### Confidence
**High** — symbol absence and the `async def` signature are both directly
verified in source, and the correct sibling implementation exists.

---

## SYN-002 — Unused imports (F401) across 12 modules

### Severity
**Low** — lint-hygiene only. Does **not** affect parsing, compilation,
bundling, testing, or execution. Recorded per the audit's "all findings"
mandate.

### Language/File Type
Python

### Location
15 occurrences across 12 files:

| # | File | Line | Unused symbol |
|---|------|------|---------------|
| 1 | `agents/analysis/markscheme_agent.py` | 6 | `datetime.datetime` |
| 2 | `agents/analysis/markscheme_agent.py` | 6 | `datetime.timezone` |
| 3 | `agents/analysis/past_paper_agent.py` | 9 | `typing.Any` |
| 4 | `agents/delivery/revision_agent.py` | 6 | `datetime.datetime` |
| 5 | `agents/delivery/revision_agent.py` | 6 | `datetime.timezone` |
| 6 | `agents/infrastructure/curriculum_agent.py` | 27 | `config.settings.DB_PROGRESS` |
| 7 | `agents/infrastructure/curriculum_agent.py` | 28 | `db.models.get_db` |
| 8 | `agents/infrastructure/scheduler_agent.py` | 28 | `apscheduler.schedulers.base.BaseScheduler` |
| 9 | `backend/main.py` | 26 | `config.settings.DB_ANALYTICS` |
| 10 | `briefing/generator.py` | 4 | `dataclasses.field` |
| 11 | `ingestion/ocr.py` | 10 | `PIL.Image.Image` |
| 12 | `tests/test_agents/test_phase3_agents.py` | 71 | `agents.analysis.markscheme_agent._write_markscheme_entry` |
| 13 | `tests/test_ingestion/test_classifier.py` | 4 | `pytest` |
| 14 | `tests/test_ingestion/test_extractor.py` | 4 | `pytest` |
| 15 | `tests/test_ingestion/test_ocr.py` | 4 | `sqlite3` |

### Error Description
Each listed name is imported but never referenced in its module. These are dead
imports — harmless at runtime but flagged by Ruff's `F401` rule and would be
reported by any CI lint gate configured to fail on warnings.

### Compiler/Linter Output
```
$ ruff check --select F401 .
Found 15 errors.
[*] 15 fixable with the `--fix` option.
```
(Representative line:)
```
agents/analysis/markscheme_agent.py:6:22: F401 [*] `datetime.datetime` imported but unused
```

### Evidence
See the table above; all 15 are auto-confirmed by `ruff check --select F401`.

### Impact
None on compilation, bundling, or execution. Only relevant if the project's
CI/lint policy treats lint findings as failures (the audit goal states "without
warnings or errors"). Removing them is purely cosmetic/hygienic.

### Recommended Fix
Run the auto-fixer:
```bash
ruff check --select F401 --fix .
```
or remove each unused name manually. (The unused `pytest`/`sqlite3` imports in
the test files are likewise safe to drop.)

### Confidence
**High** — every occurrence is machine-verified by Ruff with exact location.

---

## Files & Languages Verified Clean (no findings)

| Category | Files | Validation |
|---|---|---|
| Python (all tracked `.py`) | 53 | `compileall` + `ruff E9,F63,F7,F82,F811,F821,F822` — 0 errors |
| TypeScript / TSX | `frontend/**` | `tsc --noEmit` — 0 errors |
| React / JSX nesting / hooks | `frontend/components/**`, `frontend/app/**` | `next build` + `next lint` — 0 errors |
| JSON | curriculum (33), `db/syllabus` (5), `frontend/*.json`, `vercel.json`, `.eslintrc.json`, `tsconfig.json` | `json.load` — all valid |
| TOML | `pyproject.toml` | `tomllib.load` — valid |
| SQL schemas | `schemas/*.sql` (7) | `sqlite3.executescript` — all valid |
| Shell | `start-backend.sh` | `bash -n` — valid |
| `.mjs` build config | `next.config.mjs`, `postcss.config.mjs` | `node --check` — valid |
| CSS | `frontend/app/globals.css` | brace/at-rule balance — 430/430 |
| HTML | `docs/index.html` | `html.parser` — all tags closed |
| YAML / XML | — | none present in repo |

---

## Methodology

1. Enumerated every tracked file and grouped by language/type.
2. Byte-compiled all Python; ran Ruff's syntax, undefined-name, and
   redefinition rule sets, then the unused-import rule.
3. Performed a runtime `importlib` smoke-test of all 34 first-party modules to
   surface import-time errors that byte-compilation cannot detect.
4. Installed frontend dependencies (`npm install`) and ran `tsc --noEmit`,
   `next lint`, and a full production `next build`.
5. Parsed every JSON, TOML, SQL, shell, `.mjs`, CSS, and HTML file with a
   language-appropriate parser.
6. Manually cross-checked the one non-static finding (function-local import of
   a non-existent symbol) against the module's actual exports and against the
   correct sibling implementation.

**Conclusion:** The repository compiles, type-checks, lints, and builds with no
syntax- or structure-level blockers. The only execution-affecting defect is the
single invalid Telegram import (**SYN-001**); everything else is non-blocking
lint hygiene (**SYN-002**).
