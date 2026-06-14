# AcademicOS — Codebase-Wide Syntax & Structure Audit

**Audit date:** 2026-06-14
**Branch:** `claude/determined-cerf-ehahd0`
**Scope:** Every tracked source, configuration, script, test, migration, schema, and build file.

---

## Executive Summary

AcademicOS is **syntactically clean and builds successfully**. Every compiler,
type checker, linter, parser, and bundler available in the repository was
executed and the results validated against each language specification.

| Stage / Tool | Result |
|---|---|
| Python `py_compile` (all 53 tracked `.py`) | ✅ 0 syntax errors |
| Ruff syntax/error rules (`E9,F63,F7,F82`) | ✅ All checks passed |
| Internal Python module references (`from X import Y`) | ⚠️ 1 invalid symbol (SYN-001) |
| TypeScript `tsc --noEmit` (after `npm install`) | ✅ 0 errors |
| ESLint (`next lint`) | ✅ 0 warnings / 0 errors |
| `next build` (production compile + static gen) | ✅ Compiled successfully, 5/5 pages |
| JSON (43 files) | ✅ All valid |
| TOML (`pyproject.toml`) | ✅ Valid |
| SQL (7 schema files, `executescript`) | ✅ All valid |
| Shell (`bash -n`) | ✅ Valid |
| `.mjs` configs (`node --check`) | ✅ Valid |
| CSS (`globals.css`) | ✅ Brace-balanced, valid at-rules |
| HTML (`docs/index.html`) | ✅ Parses |
| YAML / XML | — None present in repo |

**Net finding:** There are **no** parse-blocking, compile-blocking, or
build-blocking syntax errors anywhere in the repository. One genuine
**runtime-breaking invalid import** exists (SYN-001), and a set of
**non-blocking lint-hygiene** issues (SYN-002–SYN-004) that do not affect
compilation or execution but are recorded per the audit's "all findings"
requirement.

---

## SYN-001 — Invalid import: `TelegramAgent` class does not exist

### Severity
**High** (runtime crash on a real code path; not a compile/parse error)

### Language/File Type
Python

### Location
`briefing/generator.py:286–288`

### Error Description
The `__main__` block (run via `python briefing/generator.py --send-now`)
imports and instantiates a class `TelegramAgent`:

```python
from agents.delivery.telegram_agent import TelegramAgent
TelegramAgent().send_message(text)
```

However, `agents/delivery/telegram_agent.py` defines **no `TelegramAgent`
class**. The module is entirely function-based; its public delivery surface is:

- `async def send_message(text: str, parse_mode: str = "Markdown") -> None`
- `async def send_daily_briefing(briefing_text: str) -> None`
- `def start_bot() -> None`

This is the **only** place in the codebase that assumes a class-based agent;
every other call site (`scripts/send_briefing.py:42`,
`agents/infrastructure/scheduler_agent.py:71`) correctly imports the
module-level `send_daily_briefing` function.

There is a **second, compounding** defect: even if the symbol existed,
`send_message` is a coroutine. The call `TelegramAgent().send_message(text)`
is not awaited, so it would create and discard a coroutine and never send —
and it also omits the required `asyncio.run(...)` driver used everywhere else.

### Compiler/Linter Output
Not surfaced by `py_compile`, `ruff`, `tsc`, or `next build` because the
import is **local to a function/`__main__` block** and only resolves at
execution time. At runtime:

```
ImportError: cannot import name 'TelegramAgent' from 'agents.delivery.telegram_agent'
```

### Evidence
`briefing/generator.py`:
```python
278  if __name__ == "__main__":
279      import sys
280
281      briefing = generate_daily_briefing()
282      text = format_for_telegram(briefing)
283      print(text)
284
285      if "--send-now" in sys.argv:
286          from agents.delivery.telegram_agent import TelegramAgent   # ← no such symbol
287
288          TelegramAgent().send_message(text)                          # ← not awaited
```

`agents/delivery/telegram_agent.py` (top-level symbols only):
```python
11  async def send_message(text: str, parse_mode: str = "Markdown") -> None: ...
60  async def send_daily_briefing(briefing_text: str) -> None: ...
66  def start_bot() -> None: ...
```

### Impact
- Running `python briefing/generator.py --send-now` raises `ImportError`
  immediately and the briefing is never delivered.
- The manual-send / verification path for the delivery pipeline is broken.
- No effect on import of the module, on the scheduler path, or on
  `scripts/send_briefing.py` (those use the correct function).

### Recommended Fix
Mirror the canonical pattern already used in `scripts/send_briefing.py`:

```python
    if "--send-now" in sys.argv:
        import asyncio
        from agents.delivery.telegram_agent import send_daily_briefing

        asyncio.run(send_daily_briefing(text))
        print("\n[sent to Telegram]")
```

### Confidence
**High** — verified the symbol is absent (`grep`/AST), and confirmed the
correct pattern elsewhere in the repo.

---

## SYN-002 — Unused imports (F401)

### Severity
**Low** (lint hygiene; does not affect compilation, build, or execution)

### Language/File Type
Python

### Location
15 occurrences:

| File | Line | Unused symbol |
|---|---|---|
| `agents/analysis/markscheme_agent.py` | 6 | `datetime.datetime`, `datetime.timezone` |
| `agents/analysis/past_paper_agent.py` | 9 | `typing.Any` |
| `agents/delivery/revision_agent.py` | 6 | `datetime.datetime`, `datetime.timezone` |
| `agents/infrastructure/curriculum_agent.py` | 27–28 | `config.settings.DB_PROGRESS`, `db.models.get_db` |
| `agents/infrastructure/scheduler_agent.py` | 28 | `apscheduler.schedulers.base.BaseScheduler` |
| `backend/main.py` | 26 | `config.settings.DB_ANALYTICS` |
| `briefing/generator.py` | 4 | `dataclasses.field` |
| `ingestion/ocr.py` | 10 | `PIL.Image.Image` |
| `tests/test_agents/test_phase3_agents.py` | 71 | `agents.analysis.markscheme_agent._write_markscheme_entry` |
| `tests/test_ingestion/test_classifier.py` | 4 | `pytest` |
| `tests/test_ingestion/test_extractor.py` | 4 | `pytest` |
| `tests/test_ingestion/test_ocr.py` | 4 | `sqlite3` |

### Error Description / Compiler Output
```
F401 [*] `<name>` imported but unused
```

### Impact
None on execution. Adds dead imports; if the project later enables
"lint must pass with zero warnings" in CI (an explicit audit goal), these
would fail the gate.

### Recommended Fix
Remove the unused names, or run `ruff check . --fix` (all 15 are
auto-fixable). Verify that genuinely re-exported names (none here) are not
removed.

### Confidence
**High**

---

## SYN-003 — Module-level import not at top of file (E402)

### Severity
**Low** (intentional pattern; reported for completeness)

### Language/File Type
Python

### Location
- `scripts/extract_examiner.py:11–13`
- `scripts/extract_markschemes.py:16–18`

### Error Description
```
E402 Module level import not at top of file
```
These imports deliberately follow a `sys.path.insert(0, str(ROOT))` call so
that the repository root is on the path before local packages are imported.
This is a **valid and intentional** bootstrapping pattern, not a defect.

### Evidence
`scripts/extract_examiner.py`:
```python
8   ROOT = Path(__file__).resolve().parent.parent
9   sys.path.insert(0, str(ROOT))
10
11  from db.models import get_db                 # E402 (by design)
12  from config.settings import DB_QUESTION_BANK, DB_EXAMINER
13  from agents.analysis.examiner_report_agent import ingest_report
```

### Impact
None on compilation or execution.

### Recommended Fix
No action required. If a zero-warning CI gate is desired, silence per-line
with `# noqa: E402` on lines 11–13 (and 16–18), or add a per-file ignore for
`scripts/*` in the ruff config.

### Confidence
**High**

---

## SYN-004 — Assigned-but-never-used local variables (F841)

### Severity
**Low** (lint hygiene; dead assignment)

### Language/File Type
Python

### Location
- `agents/analysis/past_paper_agent.py:252` — local `q_cur`
- `tests/test_agents/test_phase3_agents.py:86` — local `entry`

### Error Description
```
F841 Local variable `<name>` is assigned to but never used
```

### Impact
None on execution. Indicates a possibly-incomplete code path (the `q_cur`
cursor in `past_paper_agent.py` is opened/assigned but never read — worth a
glance to confirm no intended use was dropped).

### Recommended Fix
Remove the assignment, or use the variable. For `q_cur`, confirm whether a
cursor operation was intended before deleting.

### Confidence
**High**

---

## Coverage Notes & Methodology

- **Dependencies:** `frontend/node_modules` was absent on checkout; running
  `tsc`/`eslint`/`next build` against it without installing produced ~hundreds
  of *spurious* `TS2307 Cannot find module` / `TS7026 JSX.IntrinsicElements`
  errors. These were **artifacts of missing packages, not code defects** —
  after `npm install` (385 packages), `tsc`, `eslint`, and `next build` all
  reported **zero** errors. This is documented so the noise is not mistaken
  for real findings.
- **Python runtime deps** (`requirements.txt`: fastapi, pdfplumber, pix2tex,
  python-telegram-bot, etc.) were **not** installed. All external imports were
  validated at the AST/parse level; internal cross-module references were
  validated structurally (every `from <internal> import …` resolves to an
  existing module, and — except SYN-001 — to an existing symbol).
- **Files validated:** 53 `.py`, 19 `.tsx`, 5 `.ts`, 43 `.json`, 7 `.sql`,
  2 `.mjs`, 1 `.toml`, 1 `.sh`, 1 `.css`, 1 `.html`, plus `vercel.json`,
  `tsconfig.json`, `.eslintrc.json`, `tailwind.config.ts`, `next.config.mjs`,
  `postcss.config.mjs`, `.env.example`.
- **No** YAML, XML, SCSS/SASS, or TOML build files beyond `pyproject.toml`
  exist in the repository.

## Remediation Priority

1. **Fix SYN-001** (the only functional defect) — restores the
   `generator.py --send-now` delivery path.
2. Optionally clear SYN-002 / SYN-004 with `ruff check . --fix` and address
   SYN-003 if a zero-warning lint gate is adopted in CI.
