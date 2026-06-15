# AcademicOS — Codebase-Wide Syntax & Structure Audit

**Audit date:** 2026-06-15
**Branch:** `claude/determined-cerf-38fz1s`
**Scope:** Every tracked source, configuration, script, test, migration, schema, and build file in the repository.

---

## Executive Summary

AcademicOS is **syntactically clean and builds successfully.** Every compiler,
type checker, linter, parser, and bundler available in the repository was
executed and its output validated against the relevant language specification.

| Stage / Tool | Result |
|---|---|
| Python `py_compile` (all 53 tracked `.py`) | ✅ 0 syntax errors |
| Ruff syntax/error rules (`E9,F63,F7,F82`) | ✅ All checks passed |
| Ruff name-resolution rules (`F811,F821,F822`) | ✅ All checks passed |
| Internal Python module references (AST audit of `from X import Y`) | ⚠️ 1 invalid symbol (SYN-001) |
| TypeScript `tsc --noEmit` (after `npm install`) | ✅ 0 errors |
| ESLint (`next lint`) | ✅ 0 warnings / 0 errors |
| `next build` (production compile + static generation) | ✅ Compiled successfully, 5/5 pages |
| JSON (43 files) | ✅ All valid |
| TOML (`pyproject.toml`) | ✅ Valid |
| SQL (7 schema files, `executescript`) | ✅ All valid |
| Shell (`bash -n` on `start-backend.sh`) | ✅ Valid |
| `.mjs` configs (`node --check`) | ✅ Valid |
| CSS (`globals.css`) | ✅ Brace-balanced (430/430), valid at-rules |
| HTML (`docs/index.html`) | ✅ Parses |
| `.env.example`, `vercel.json`, `requirements.txt`, `tsconfig.json` | ✅ Well-formed |
| YAML / XML | — None present in repo |

**Net finding:** There are **no** parse-blocking, compile-blocking, or
build-blocking syntax errors anywhere in the repository. One genuine
**runtime-breaking invalid import** persists (SYN-001), plus a set of
**non-blocking lint-hygiene** issues (SYN-002–SYN-004) that do not affect
compilation, bundling, or execution but are recorded per the audit's
"all findings regardless of severity" requirement.

This run reproduces the findings of the 2026-06-14 audit; none of the
affected files changed in the interim, so all four entries remain open.

### Tooling environment

- Python 3.11.15, Ruff 0.15.8
- Node v22.22.2, npm 10.9.7
- Next.js 14.2.35, TypeScript 5.x, ESLint 8.x (`eslint-config-next`)

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
class.** The module is entirely function-based; its public delivery surface is:

- `async def send_message(text: str, parse_mode: str = "Markdown") -> None`
- `async def send_daily_briefing(briefing_text: str) -> None`
- `def start_bot() -> None`

This is the **only** place in the codebase that assumes a class-based agent;
every other call site (`scripts/send_briefing.py`,
`agents/infrastructure/scheduler_agent.py`) correctly imports the module-level
`send_daily_briefing` function.

There is a **second, compounding** defect: even if the symbol existed,
`send_message` is a coroutine. The call `TelegramAgent().send_message(text)`
is not awaited, so it would create and discard a coroutine and never send —
and it omits the required `asyncio.run(...)` driver used everywhere else.

### Compiler/Linter Output
Not surfaced by `py_compile`, `ruff`, `tsc`, or `next build` because the
import is **local to a `__main__` block** and only resolves at execution time.
Confirmed by AST-based internal-import audit:

```
briefing/generator.py:286  `TelegramAgent` not in module agents.delivery.telegram_agent
```

At runtime:

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
- No effect on importing the module, on the scheduler path, or on
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
**High** — verified the symbol is absent (`grep` + AST defined-names audit),
and confirmed the correct pattern elsewhere in the repo.

---

## SYN-002 — Unused imports (F401)

### Severity
**Low** (lint hygiene; does not block compile, build, test, or runtime)

### Language/File Type
Python

### Location
15 occurrences across 13 files:

| File:Line | Unused symbol(s) |
|---|---|
| `agents/analysis/markscheme_agent.py:6` | `datetime`, `timezone` (`from datetime import datetime, timezone`) |
| `agents/analysis/past_paper_agent.py:9` | `Any` (`from typing import Any`) |
| `agents/delivery/revision_agent.py:6` | `datetime`, `timezone` (`from datetime import date, datetime, timezone`) |
| `agents/infrastructure/curriculum_agent.py:27` | `DB_PROGRESS` (`from config.settings import DB_PROGRESS`) |
| `agents/infrastructure/curriculum_agent.py:28` | `get_db` (`from db.models import get_db`) |
| `agents/infrastructure/scheduler_agent.py:28` | `BaseScheduler` (`from apscheduler.schedulers.base import BaseScheduler`) |
| `backend/main.py:26` | `DB_ANALYTICS` (within the `from config.settings import (...)` block) |
| `briefing/generator.py:4` | `field` (`from dataclasses import dataclass, field`) |
| `ingestion/ocr.py:10` | `Image` (`from PIL.Image import Image`) |
| `tests/test_agents/test_phase3_agents.py:71` | `_write_markscheme_entry` |
| `tests/test_ingestion/test_classifier.py:4` | `pytest` |
| `tests/test_ingestion/test_extractor.py:4` | `pytest` |
| `tests/test_ingestion/test_ocr.py:4` | `sqlite3` |

### Error Description
Symbols are imported but never referenced. Pure dead imports; the Python
parser and interpreter accept them.

### Compiler/Linter Output
```
$ ruff check --select F401 .
F401 [*] `datetime` imported but unused
F401 [*] `pytest` imported but unused
... (15 total)
```

### Evidence
```python
# agents/analysis/markscheme_agent.py
6  from datetime import datetime, timezone   # neither name used

# tests/test_ingestion/test_ocr.py
4  import sqlite3                             # never referenced
```

### Impact
- No effect on compilation, bundling, testing, or runtime.
- Minor maintainability cost; flagged by `ruff`/`next lint`-equivalent gates
  if the CI lint policy is tightened to fail on warnings.

### Recommended Fix
Remove the unused names. All 15 are auto-fixable:
```
ruff check --select F401 --fix .
```
Verify nothing in those modules relied on an import side effect (none do here).

### Confidence
**High** — confirmed by `ruff` static analysis.

---

## SYN-003 — Module-level import not at top of file (E402)

### Severity
**Low** (lint hygiene / style; does not block compile, build, test, or runtime)

### Language/File Type
Python

### Location
6 occurrences across 2 files:

| File | Lines |
|---|---|
| `scripts/extract_examiner.py` | 11, 12, 13 |
| `scripts/extract_markschemes.py` | 16, 17, 18 |

### Error Description
These scripts perform `sys.path` manipulation (to add the project root to the
import path) before importing project modules, so the project imports
deliberately appear **after** executable statements. `ruff` flags this as
`E402` (module-import-not-at-top-of-file). The code is valid and runs
correctly; this is a stylistic ordering rule, not a syntax error.

### Compiler/Linter Output
```
$ ruff check --select E402 .
E402 module-import-not-at-top-of-file
 --> scripts/extract_examiner.py:11:1
 --> scripts/extract_markschemes.py:16:1
... (6 total)
```

### Evidence
```python
# scripts/extract_examiner.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.analysis...   # ← E402: import after sys.path mutation
```

### Impact
- No effect on compilation or runtime; the import order is intentional and
  required for the path bootstrap to work.
- Only relevant if CI enforces `E402`.

### Recommended Fix
Either keep as-is (the pattern is legitimate) or silence per-line where the
bootstrap genuinely requires late imports:
```python
from agents.analysis... import ...  # noqa: E402
```
Alternatively run the scripts as modules (`python -m scripts.extract_examiner`)
and drop the `sys.path` shim so imports can sit at the top.

### Confidence
**High** — confirmed by `ruff`; ordering is intentional.

---

## SYN-004 — Assigned-but-never-used local variables (F841)

### Severity
**Low** (lint hygiene; does not block compile, build, test, or runtime)

### Language/File Type
Python

### Location
2 occurrences:

| File:Line | Variable |
|---|---|
| `agents/analysis/past_paper_agent.py:252` | `q_cur` |
| `tests/test_agents/test_phase3_agents.py:86` | `entry` |

### Error Description
A local variable is assigned the result of an expression and then never read.
In `past_paper_agent.py:252`, `q_cur = conn.execute(INSERT ...)` keeps the
cursor handle but only the insert's side effect is needed. In
`test_phase3_agents.py:86`, `entry = MarkEntry(...)` is constructed but the
subsequent insert uses literal column values rather than the object.

### Compiler/Linter Output
```
$ ruff check --select F841 .
F841 Local variable `q_cur` is assigned to but never used
 --> agents/analysis/past_paper_agent.py:252:9
F841 Local variable `entry` is assigned to but never used
 --> tests/test_agents/test_phase3_agents.py:86:5
```

### Evidence
```python
# agents/analysis/past_paper_agent.py:252
q_cur = conn.execute(            # cursor captured but never read
    """
    INSERT INTO questions
    ...
```

### Impact
- No effect on compilation or runtime; the `execute()` side effect still runs.
- In the test case it suggests a latent intent (the `entry` object was likely
  meant to feed the insert) — worth confirming the test asserts what it claims.

### Recommended Fix
- `past_paper_agent.py`: drop the assignment — `conn.execute(...)` — unless the
  cursor's `lastrowid` is needed downstream (it is not used here).
- `test_phase3_agents.py`: either remove the unused `entry` or pass its fields
  into the insert so the constructed object is actually exercised.

### Confidence
**High** — confirmed by `ruff`; flagged the test case as a possible logic smell
(tracked separately under `logic.md` if the test's intent is affected).

---

## Validation Coverage (what was executed)

- **Python:** `py_compile` over all 53 tracked `.py` files (0 errors);
  `ruff check --select E9,F63,F7,F82` and `--select F811,F821,F822`
  (all passed); full `ruff check` (23 hygiene findings → SYN-002/003/004);
  custom AST audit resolving every internal `from {agents,briefing,curriculum,
  db,ingestion,backend,scripts,config,schemas} import …` against the target
  module's defined symbols (1 unresolved → SYN-001).
- **Frontend / TypeScript:** `npm install`, `tsc --noEmit` (0 errors),
  `next lint` (0 warnings/errors), `next build` (compiled successfully,
  5/5 static pages).
- **Data / config:** 43 JSON files parsed; `pyproject.toml` parsed with
  `tomllib`; 7 `.sql` schemas loaded via `sqlite3.executescript`;
  `start-backend.sh` checked with `bash -n`; `next.config.mjs` and
  `postcss.config.mjs` checked with `node --check`; `globals.css` brace-balance
  verified; `docs/index.html` parsed; `.env.example`, `vercel.json`,
  `requirements.txt`, `tsconfig.json`, `tailwind.config.ts` reviewed.
- **Absent formats:** No YAML or XML files exist in the tracked tree.
