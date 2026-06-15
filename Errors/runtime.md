# AcademicOS — Runtime, Stability & Reliability Audit

**Original audit date:** 2026-06-14 (`claude/sharp-tesla-et52fe`)
**Re-audit date:** 2026-06-15
**Branch:** `claude/sharp-tesla-2x8dd5`
**Scope:** Full repository — FastAPI backend (`backend/`), agents (`agents/`),
ingestion pipeline (`ingestion/`), briefing (`briefing/`), database layer
(`db/`, `schemas/`), scheduler, Telegram delivery, and the Next.js frontend
(`frontend/`).

> **Re-audit status (2026-06-15):** All 19 issues below were re-verified
> against the current tree and **remain open** — none have been remediated.
> Live re-execution again reproduced the dashboard 500, the briefing 500, the
> missing `spaced_repetition_items` table, the `backend.server:app`
> mis-entrypoint, and the localhost-only CORS list. The test suite is unchanged
> (**101 passed, 20 failed**). Four newly-identified issues (**RT-020 … RT-023**)
> are appended after RT-019.

## Method

- Static review of every Python module and every TypeScript component.
- Live execution: created a fresh virtualenv, installed core deps
  (`fastapi`, `pydantic`, `python-dotenv`, `pytest`, `httpx`), initialised all
  databases via `db.models.init_all_databases()`, and exercised every GET
  endpoint plus the session/attempt write paths through FastAPI's `TestClient`.
- Ran the existing test suite (`pytest`): **101 passed, 20 failed**.
- Reproduced the headline defects (dashboard 500, briefing 500, silent mastery
  no-op, spaced-repetition date overflow) directly.
- Re-audit (2026-06-15) repeated the live reproduction; see refreshed evidence
  in the appendix.

## Severity summary

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 2 | RT-001, RT-002 |
| High | 4 | RT-003, RT-004, RT-005, RT-006 |
| Medium | 8 | RT-007 … RT-013, RT-020 |
| Low | 9 | RT-014 … RT-019, RT-021, RT-022, RT-023 |

> **Headline:** The application ships with a fatal data-model schism. The
> backend API and the daily briefing are built on a `spaced_repetition_items`
> table that **no schema creates and no seeder populates**. On a clean install
> the main dashboard and the briefing both return HTTP 500, and the adaptive
> revision engine silently never updates mastery. These are not edge cases —
> they are the default state of a fresh deployment.

---

## RT-001 — `spaced_repetition_items` table is queried everywhere but created nowhere

### Severity
Critical

### Category
Crash / Reliability / Data Integrity

### Location
- `backend/main.py` — `_todays_priorities`, `_subject_mastery`,
  `_predicted_grades`, `_examiner_traps`, `_update_mastery`, `get_health`,
  `get_status` (lines 98–101, 426–469, 523–599, 602–638, 643–656, 831–881,
  1067)
- `briefing/generator.py` — `get_due_review_items` (lines 20–55),
  `select_question_of_the_day` (lines 58–118)
- `schemas/progress.sql` — schema that *should* define the table
- `db/seed_syllabus.py` — seeder that *should* populate it

### Description
Every progress/mastery feature reads from a table named
`spaced_repetition_items` (columns `topic, subtopic, unit, subject, due_date,
mastery, ease_factor, interval_days, last_reviewed`). `schemas/progress.sql`
only defines `subjects, modules, topics, subtopics, specification_points,
syllabus_completion, review_history`. A repository-wide search finds **zero**
`CREATE TABLE` statements for `spaced_repetition_items` in any `.sql`, `.py`,
or `.md` file, and `seed_syllabus.py` only fills the normalised
`specification_points` tree.

The codebase therefore contains **two incompatible progress data models**:
the Curriculum Agent (`agents/infrastructure/curriculum_agent.py`) uses the
normalised `specification_points` / `syllabus_completion` model, while the
backend API and briefing use a flat `spaced_repetition_items` model that does
not exist.

### Trigger Conditions
1. `init_all_databases()` (or any clean clone) → `progress.db` lacks the table.
2. `GET /api/dashboard` or `GET /api/briefing`.

### Expected Behavior
Endpoints return data (or an honest empty payload) from a table the schema
defines.

### Actual Behavior
- `GET /api/dashboard` → **HTTP 500**, unhandled
  `sqlite3.OperationalError: no such table: spaced_repetition_items`
  (raised inside `_question_of_day` → `select_question_of_the_day` →
  `get_due_review_items`, which uses `get_db` directly and does **not** go
  through the error-swallowing `_query`).
- `GET /api/briefing` → **HTTP 500** (same root cause via
  `_section3_adaptive_revision`).

### Evidence
```
$ DATA_DIR=/tmp/aos python -c "from db.models import init_all_databases; init_all_databases()"
$ # then via TestClient:
Scalar query failed on progress.db: no such table: spaced_repetition_items
/api/dashboard EXCEPTION OperationalError('no such table: spaced_repetition_items')
/api/briefing 500

$ grep -rn "CREATE TABLE.*spaced_repetition" . --include=*.sql --include=*.py
(no matches)
$ grep -iE "create table" schemas/progress.sql
subjects / modules / topics / subtopics / specification_points /
syllabus_completion / review_history     # spaced_repetition_items absent
```
Verification that the table is the *only* blocker: after manually creating
`spaced_repetition_items` and inserting one row, `GET /api/dashboard` returns
**200** with a correct payload.

### Impact
Total failure of the primary screen and the daily briefing on every fresh
deployment. The Telegram scheduled briefing job (`scheduler_agent._job`) also
throws and produces no message. This is a production-blocking defect.

### Recommended Fix
Add a `spaced_repetition_items` table to `schemas/progress.sql` and populate it
from the seeded `specification_points` in `db/seed_syllabus.py` (one SR item per
topic/subtopic with sensible defaults: `mastery=0.0`, `ease_factor=2.5`,
`interval_days=1`, `due_date=today`). Alternatively, refactor the backend and
briefing to use the existing `syllabus_completion` model — but a single source
of truth must be chosen. Until then, wrap `get_due_review_items` /
`select_question_of_the_day` in the same defensive handling as `_query`.

### Confidence
High

---

## RT-002 — Spaced-repetition mastery update is a silent no-op

### Severity
Critical

### Category
Reliability / Data Integrity (hidden failure)

### Location
`backend/main.py` — `_update_mastery` (lines 831–881), called by
`create_attempt` (line 922)

### Description
`_update_mastery` reads the matching SR items via the error-swallowing
`_query`/`get_db` path. Because `spaced_repetition_items` does not exist
(RT-001), the lookup returns nothing and the function returns `(None, None)`.
`POST /api/attempts` therefore succeeds (HTTP 200), records the attempt, and
reports `new_mastery: null` — **the entire adaptive learning engine never
advances**. No error is surfaced to the user or the logs at error level.

### Trigger Conditions
Submit any attempt via `POST /api/attempts` on a default install.

### Expected Behavior
Mastery, ease factor, interval and due date update for the question's topic;
the response carries the new mastery and next-review date.

### Actual Behavior
```
$ POST /api/attempts {question_id, marks_awarded:3, marks_available:5, confidence:4, ...}
attempt 200 {'attempt_id': 1, 'new_mastery': None, 'next_review': None, ...}
```
Attempt stored, mastery unchanged forever.

### Impact
The product's core value proposition (adaptive spaced repetition, predicted
grades, "today's priorities", weakness tracking) is non-functional and fails
silently — the worst failure class because nothing looks broken. Violates the
project's #1 governing principle (Data Integrity).

### Recommended Fix
Fix RT-001. Additionally, make `_update_mastery` log at `WARNING` when it finds
no SR items for a topic so the no-op is observable, and add an integration test
asserting mastery changes after an attempt.

### Confidence
High

---

## RT-003 — CORS allow-list hardcoded to localhost blocks the deployed frontend

### Severity
High

### Category
Reliability / Deployment

### Location
`backend/main.py` lines 38–44

### Description
```python
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"], ...)
```
The frontend is built for Vercel (`vercel.json`, `@vercel/next`) and reads its
API base from `NEXT_PUBLIC_API_URL`. In any non-local deployment the browser
origin is the Vercel domain, which is **not** in `allow_origins`, so every
cross-origin API call is blocked by the browser.

### Trigger Conditions
Deploy the frontend anywhere other than `localhost` and point it at the API.

### Expected Behavior
The deployed frontend can call the API.

### Actual Behavior
All API requests fail CORS preflight; every screen shows the error/retry state.

### Impact
The web app is unusable in production despite a healthy backend.

### Recommended Fix
Drive `allow_origins` from an environment variable
(e.g. `ALLOWED_ORIGINS` comma-split), include the production domain, and keep
localhost for dev.

### Confidence
High

---

## RT-004 — Unbounded spaced-repetition interval causes a `date` overflow → 500

### Severity
High

### Category
Runtime Exception / Reliability

### Location
`backend/main.py` — `_update_mastery` lines 861–869

### Description
On each ≥80% attempt the interval grows multiplicatively
(`interval = interval * ease`, with `ease` rising to a 3.0 cap) and is never
clamped. `due = date.today() + timedelta(days=round(interval))` raises
`OverflowError: date value out of range` once the result passes year 9999.
Because `_update_mastery` is called **outside** the `with get_db(...)` block in
`create_attempt`, the attempt row is already committed when the exception
propagates — the endpoint returns 500 with partially-applied state.

### Trigger Conditions
~15 consecutive strong (≥80%) attempts on the same topic (entirely realistic
for a diligent student over a term).

### Expected Behavior
Intervals are capped (e.g. at 365 days) and the endpoint never 500s.

### Actual Behavior
```
OverflowError at consecutive-strong-review #15: interval=8414837 days -> date value out of range
```

### Impact
Once a topic matures, all further attempts on it return 500; the attempt is
saved but mastery/next-review are not, corrupting the SR state for that topic.

### Recommended Fix
Clamp: `interval = min(interval * ease, 365)` and guard the `timedelta`
construction. Move the mastery update inside a single transaction with the
attempt insert so failures don't leave partial state.

### Confidence
High

---

## RT-005 — Telegram command handlers crash on Markdown parse errors (no fallback)

### Severity
High

### Category
Runtime Exception / Reliability

### Location
`agents/delivery/telegram_agent.py` — `_cmd_briefing`, `_cmd_status`,
`_cmd_coverage`, `_cmd_quiz`, `_cmd_revise`, `_cmd_progress` (lines 83–199)

### Description
The reusable `send_message` helper retries in plain text if Telegram rejects
the Markdown (lines 32–39). The command handlers, however, call
`update.message.reply_text(text, parse_mode="Markdown")` directly with **no**
fallback. Question text, topic names and examiner observations frequently
contain `_`, `*`, `[`, `` ` `` — all of which break legacy Telegram Markdown
parsing and raise `telegram.error.BadRequest`. Since these run inside async
command handlers, the exception bubbles up uncaught and the command fails for
the user.

### Trigger Conditions
Any `/quiz`, `/revise`, `/briefing`, etc. whose content contains a Markdown
metacharacter (the common case for maths/physics text).

### Expected Behavior
The bot replies with readable text even when Markdown can't be parsed.

### Actual Behavior
Handler raises `BadRequest: can't parse entities`; no reply, error logged by
PTB.

### Impact
Telegram commands — a primary delivery channel (Phase 6) — are unreliable for
realistic content.

### Recommended Fix
Route all bot replies through `send_message` (which already has the plain-text
fallback), or wrap each `reply_text` in a try/except that retries without
`parse_mode`. Prefer `MarkdownV2` with proper escaping, or escape content.

### Confidence
High

---

## RT-006 — Vercel backend entrypoint points at a non-existent module

### Severity
High

### Category
Startup / Deployment

### Location
`pyproject.toml` (`[tool.vercel] entrypoint = "backend.server:app"`);
`start-backend.sh`

### Description
`pyproject.toml` declares the serverless entrypoint as `backend.server:app`,
but the FastAPI app lives in `backend/main.py` (`backend.main:app`). There is
no `backend/server.py`. Any deployment honoring that entrypoint fails to import
the app at boot.

### Trigger Conditions
Deploying the backend using the declared entrypoint.

### Expected Behavior
The configured entrypoint resolves to the actual ASGI app.

### Actual Behavior
`ModuleNotFoundError: No module named 'backend.server'` at startup.

### Evidence
```
$ ls backend/server.py
ls: cannot access 'backend/server.py': No such file or directory
$ grep entrypoint pyproject.toml
entrypoint = "backend.server:app"
```

### Impact
Backend cannot start under the documented deployment path.

### Recommended Fix
Change the entrypoint to `backend.main:app` (or rename/forward the module).
Note the current `vercel.json` only builds the frontend, so the backend has **no
working deploy target at all** — this needs an explicit hosting decision.

### Confidence
High

---

## RT-007 — Blanket `sqlite3.Error` swallowing hides real failures

### Severity
Medium

### Category
Reliability (hidden failure)

### Location
`backend/main.py` — `_query` (56–63), `_scalar` (66–73)

### Description
Both helpers catch every `sqlite3.Error` and return an empty list / default,
logging only at `WARNING`. The design intent ("empty databases produce honest
empty responses") conflates *empty data* with *broken queries*. Schema drift
(RT-001), corruption, a locked database (RT-011), or a typo'd column all
manifest as silent empty responses indistinguishable from "no data yet".

### Trigger Conditions
Any DB error during a read.

### Expected / Actual Behavior
Expected: genuine errors are surfaced/alerted. Actual: they're masked as empty
results; the UI shows "no data" rather than an error.

### Impact
Operational blindness — exactly how RT-001 went unnoticed.

### Recommended Fix
Distinguish "table empty" from "query/connectivity error". Re-raise (or return a
typed error) on `OperationalError`/`DatabaseError`; only treat
"missing optional DB file" as empty. Emit metrics/alerts on error.

### Confidence
High

---

## RT-008 — PDF is re-parsed many times per ingest (O(n²) OCR cost)

### Severity
Medium

### Category
Performance

### Location
`ingestion/ocr.py` — `extract_full_text` (120–141), `ocr_page_with_fallback`
(89–117); `agents/analysis/past_paper_agent.py` — `extract_metadata` (134–176),
`detect_paper_type` (110–131)

### Description
`extract_full_text` calls `extract_text_pdfplumber(pdf_path)` to read all pages,
then for **each scanned page** calls `ocr_page_with_fallback`, which **re-opens
and re-parses the entire PDF** with pdfplumber again. For a paper with *k*
scanned pages, pdfplumber parses the whole document *k+1* times. Separately,
`extract_metadata` parses the PDF, then calls `detect_paper_type` which parses
it a second time. A single ingest of a scanned paper can parse the same PDF a
dozen-plus times.

### Trigger Conditions
Ingesting any multi-page scanned PDF (the common case for past papers); runs
hourly via `schedule_paper_scan`.

### Expected Behavior
Parse each PDF once; pass page text/images forward.

### Actual Behavior
Repeated full-document parsing scaling with page count.

### Impact
Slow ingestion, high CPU, and the hourly scheduler can stack up if a batch of
scanned PDFs lands. Degrades responsiveness of the whole host.

### Recommended Fix
Parse once (cache the `extract_text_pdfplumber` result and the
`convert_from_path` images) and thread the page data through
`ocr_page_with_fallback`. Have `extract_metadata` reuse the pages already read
by `detect_paper_type`.

### Confidence
High

---

## RT-009 — `LatexOCR` model reloaded on every call

### Severity
Medium

### Category
Performance / Memory

### Location
`ingestion/ocr.py` — `extract_math_latex` (67–86)

### Description
`extract_math_latex` instantiates `LatexOCR()` on every invocation. The model's
own docstring warns "pix2tex is expensive to load — caller should cache the
LatexOCR instance," yet no caching exists. Per-call construction reloads model
weights into memory each time a maths region is OCR'd.

### Trigger Conditions
Any LaTeX OCR pass across multiple images/questions.

### Expected / Actual Behavior
Expected: load once, reuse. Actual: repeated multi-hundred-MB model loads →
seconds of latency and memory churn per call, risking OOM on small hosts.

### Impact
Severe ingestion slowdown and memory pressure when LaTeX OCR is enabled.

### Recommended Fix
Memoize the model (module-level `@lru_cache` or lazy singleton) and reuse across
calls; release it when ingestion completes.

### Confidence
High

---

## RT-010 — New connection + PRAGMA churn on every query; dozens per request

### Severity
Medium

### Category
Performance

### Location
`db/models.py` — `get_db` (42–55); `backend/main.py` (every `_query`/`_scalar`)

### Description
`get_db` opens a fresh `sqlite3.connect`, then runs `PRAGMA foreign_keys=ON` and
`PRAGMA journal_mode=WAL` on **every** call, and closes the connection in
`finally`. `GET /api/dashboard` fans out to ~15+ separate `_query`/`_scalar`
calls (priorities, recent papers, subject mastery, predicted grades, traps,
QOD, streak), each opening and tearing down its own connection and re-issuing
`journal_mode=WAL` (a no-op write each time). There is no connection pooling.

### Trigger Conditions
Every dashboard/analytics request, multiplied under load.

### Expected / Actual Behavior
Expected: reuse a connection per request. Actual: connection setup/teardown and
PRAGMA overhead repeated 15+ times per page load.

### Impact
Unnecessary latency and syscall/WAL overhead; amplifies the locking risk in
RT-011 under concurrency.

### Recommended Fix
Open one connection per request (FastAPI dependency) and share it across the
helper queries; set `PRAGMA journal_mode=WAL` once at startup (it persists per
database file). Set `busy_timeout` via PRAGMA at connect.

### Confidence
High

---

## RT-011 — SQLite write contention: no busy-timeout tuning, no retry

### Severity
Medium

### Category
Concurrency

### Location
`db/models.py` — `get_db`; write endpoints in `backend/main.py`
(`create_session`, `log_question_time`, `complete_session`, `create_attempt`)

### Description
The endpoints are synchronous `def` handlers, so FastAPI runs them in a
thread pool — multiple concurrent writers are possible. SQLite permits only one
writer; `get_db` relies on the default Python busy timeout (5 s) with no
explicit `busy_timeout` PRAGMA and no retry/backoff. `create_attempt`
additionally performs writes to `attempts.db` and then a second write
transaction to `progress.db` (`_update_mastery`), widening the window.

### Trigger Conditions
Concurrent writes (e.g., rapid question-time logging during a session, or
multiple clients).

### Expected / Actual Behavior
Expected: writes serialize gracefully. Actual: under contention,
`sqlite3.OperationalError: database is locked` surfaces as a 500 (write paths
don't go through `_query`).

### Impact
Intermittent write failures and lost logs under load.

### Recommended Fix
Set `PRAGMA busy_timeout=5000` on connect, add a short retry/backoff around
write transactions, and keep transactions minimal.

### Confidence
Medium

---

## RT-012 — Frontend fetch has no timeout, abort, or retry policy

### Severity
Medium

### Category
Reliability / UX

### Location
`frontend/lib/api.ts` — `request` (17–28); `frontend/lib/hooks.ts` — `useFetch`

### Description
`request` issues `fetch` with no `AbortController` and no timeout. If the
backend hangs or a response stalls, the promise never settles, so `useFetch`
stays `loading: true` indefinitely with no way to recover except the manual
retry button (which itself can hang the same way). There is no automatic retry
or backoff for transient network errors.

### Trigger Conditions
Slow/hung backend, dropped connection, or a request that never completes.

### Expected / Actual Behavior
Expected: requests time out and surface an error/retry. Actual: permanent
spinner.

### Impact
Application "freeze" perception; broken loading state under poor connectivity
or backend stalls.

### Recommended Fix
Add an `AbortController` with a timeout (e.g. 15 s) to `request`; surface
timeouts as errors; consider one automatic retry with backoff for idempotent
GETs.

### Confidence
High

---

## RT-013 — Async tests never execute (`pytest-asyncio` missing)

### Severity
Medium

### Category
Reliability (test coverage gap)

### Location
`requirements.txt`; `tests/test_agents/test_seed_and_commands.py`

### Description
Nine async tests are decorated `@pytest.mark.asyncio`, but `pytest-asyncio`
is not in `requirements.txt`. pytest emits `PytestUnknownMarkWarning` and the
coroutine tests error out with "async def functions are not natively
supported." All Telegram command handlers (the surface most prone to RT-005)
are therefore effectively untested.

### Evidence
```
FAILED tests/test_agents/test_seed_and_commands.py::test_cmd_quiz_returns_question
  async def functions are not natively supported.
  You need to install a suitable plugin ... pytest-asyncio
```
(20 of 121 tests fail; the remainder of the 20 are optional-dependency gaps —
`pdfplumber`/`telegram` not installed.)

### Impact
False confidence in CI; the riskiest code paths are unverified.

### Recommended Fix
Add `pytest-asyncio` to `requirements.txt`, register the `asyncio` marker in
`pyproject.toml`/`pytest.ini`, and mark optional-dependency tests with
`importorskip` so they skip cleanly rather than fail.

### Confidence
High

---

## RT-014 — Hardcoded developer path in `start-backend.sh`

### Severity
Low

### Category
Deployment / Environment

### Location
`start-backend.sh` lines 9–11

### Description
The launcher falls back to a hardcoded absolute path
`/Users/mouadmaamma/academic-os/.venv/bin/uvicorn`. On any other machine the
primary relative path (`../../../.venv/...`) is also fragile, and the fallback
is meaningless.

### Impact
Backend fails to start outside the original developer's machine.

### Recommended Fix
Resolve the venv relative to the repo root, or require `uvicorn` on `PATH`
(`exec uvicorn backend.main:app ...`).

### Confidence
High

---

## RT-015 — Theme flash / hydration-time class flip

### Severity
Low

### Category
Hydration / UX

### Location
`frontend/components/ClientLayout.tsx` lines 50–62

### Description
`dark` initialises to `false`; a post-mount `useEffect` reads
`prefers-color-scheme` and flips it. For dark-mode users the first paint is
light, then snaps to dark — a flash of incorrectly-themed content. No SSR
mismatch error (the attribute is set in an effect), but a visible FOUC.

### Impact
Cosmetic flicker on load for dark-mode users.

### Recommended Fix
Apply the theme via an inline blocking script in `app/layout.tsx` (or a cookie)
before hydration, then sync React state.

### Confidence
Medium

---

## RT-016 — New Telegram `Bot` instance per send

### Severity
Low

### Category
Resource Leak

### Location
`agents/delivery/telegram_agent.py` — `send_message` line 23

### Description
`Bot(token=...)` is constructed on every `send_message` call. python-telegram-
bot v21 Bot objects own an HTTPX request pool; repeatedly creating them (e.g.
multi-chunk briefings) churns connection resources and skips proper
`initialize()/shutdown()` lifecycle.

### Impact
Minor resource churn; potential connection accumulation under frequent sends.

### Recommended Fix
Construct one `Bot`/`Application` and reuse it; manage its async lifecycle.

### Confidence
Medium

---

## RT-017 — Scheduler crashes on malformed `BRIEFING_TIME`

### Severity
Low

### Category
Startup

### Location
`agents/infrastructure/scheduler_agent.py` — `schedule_daily_briefing` line 30

### Description
`hour, minute = (int(x) for x in time_str.split(":"))` assumes a well-formed
`HH:MM`. An env value like `7` , `07:30:00`, or `morning` raises `ValueError`/
unpacking error at scheduler startup, taking down the whole scheduler (and thus
all jobs, including paper scanning).

### Impact
A single bad env var disables all scheduled automation.

### Recommended Fix
Validate/parse defensively (`datetime.strptime(time_str, "%H:%M")`), fall back
to the documented default `07:30`, and log a warning.

### Confidence
High

---

## RT-018 — Daily briefing Markdown is unescaped (frequent plain-text fallback)

### Severity
Low

### Category
Reliability

### Location
`briefing/generator.py` — `format_for_telegram` (264–275) and the section
builders; consumed by `telegram_agent.send_message`

### Description
Briefing sections interpolate raw DB content (topic names, question text,
misconception descriptions) into `*bold*`/`_italic_` legacy-Markdown without
escaping. Real content routinely contains `_`, `*`, `[`, `` ` ``. Via
`send_message` this is caught and retried as plain text (good), but it means the
formatted briefing will *often* silently degrade to unstyled text, and any path
not using `send_message` (RT-005) fails outright.

### Impact
Briefings frequently lose all formatting; brittle coupling to a fragile parse
mode.

### Recommended Fix
Switch to `MarkdownV2` with a proper escaper applied to interpolated values, or
build the message with an escaping helper. Add a test that briefing output
parses under the chosen mode.

### Confidence
Medium

---

## RT-019 — Client-side-only switch routing: no URL state, history, or deep links

### Severity
Low

### Category
Other (UX / reliability)

### Location
`frontend/components/ClientLayout.tsx` — `route` state + `Screen()` switch
(48–101)

### Description
Navigation is a single `useState` switch in one client component. There is no
URL routing: the browser back/forward buttons don't change screens, no screen is
linkable or refresh-stable (a reload always returns to `home`), and shared
session state (`paperId`, `sessionId`) is lost on refresh mid-session.

### Impact
Refreshing during a timed paper loses the in-progress session context; no
deep-linking or bookmarking; back button appears broken.

### Recommended Fix
Adopt Next.js App Router routes (or at least sync `route` to the URL hash/query)
and persist active-session IDs (sessionStorage) so a refresh recovers state.

### Confidence
Medium

---

## RT-020 — Import-time `mkdir` crashes startup on a nested or read-only `DATA_DIR`

### Severity
Medium

### Category
Startup / Deployment

### Location
`config/settings.py` lines 14–16

### Description
`config/settings.py` runs filesystem side effects **at import time**:
```python
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DIAGRAMS_DIR = DATA_DIR / "diagrams"
DATA_DIR.mkdir(exist_ok=True)                 # no parents=True
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
```
`DATA_DIR.mkdir(exist_ok=True)` omits `parents=True`, so if `DATA_DIR` points at
a path whose parent does not yet exist (a normal production layout such as
`/var/lib/academic-os/data`), the very first import of `config.settings` raises
`FileNotFoundError`. Because *every* backend module, agent, scheduler job and
CLI entry imports `config.settings` transitively, the failure takes down the
whole process at boot — before any handler or logger runs. The same line also
fails on read-only filesystems (e.g. a serverless image whose only writable area
is `/tmp`), since the mkdir is unconditional and happens on import rather than
lazily on first DB use.

### Trigger Conditions
Set `DATA_DIR` to any path with a missing parent directory, or deploy to an
environment with a read-only application filesystem.

### Expected Behavior
The app starts; data directories are created on demand (recursively) or a clear
configuration error is raised after logging is configured.

### Actual Behavior
```
$ DATA_DIR=/tmp/nope_nested/deep/data python -c "import config.settings"
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/nope_nested/deep/data'
```
Process aborts at import; no API, scheduler, or briefing comes up.

### Impact
Hard startup failure that is invisible to the application's own error handling
and easy to hit with a standard non-local data path. Couples configuration
loading to writable-filesystem assumptions.

### Recommended Fix
Use `DATA_DIR.mkdir(parents=True, exist_ok=True)` for consistency with
`DIAGRAMS_DIR`, and prefer creating directories lazily (in `init_all_databases`
or a startup hook) rather than as an import side effect, so a bad path surfaces
as a handled startup error rather than an import crash.

### Confidence
High

---

## RT-021 — `init_all_databases()` leaks SQLite connections

### Severity
Low

### Category
Resource Leak

### Location
`db/models.py` — `init_all_databases` (36–39)

### Description
```python
for db_path, schema_file in _DB_SCHEMA_MAP.items():
    with sqlite3.connect(db_path) as conn:
        _apply_schema(conn, schema_file)
```
A `sqlite3.Connection` used as a context manager **commits/rolls back the
transaction but does not close the connection** (unlike the project's own
`get_db`, which closes in `finally`). All seven connections opened here are left
open and only reclaimed when the objects are garbage-collected, leaking file
handles for the lifetime of the call's scope. Harmless in a one-shot CLI, but in
any process that calls `init_all_databases()` repeatedly (tests, a re-init
endpoint, a long-lived worker) the open WAL/SHM handles accumulate.

### Trigger Conditions
Repeated invocation of `init_all_databases()` within one process.

### Expected / Actual Behavior
Expected: each connection is closed deterministically. Actual: connections rely
on GC; file handles linger.

### Impact
Minor file-handle/WAL-handle leakage; can interfere with cleanup/deletion of the
DB files on Windows and accumulate under repeated init.

### Recommended Fix
Reuse `get_db(db_path)` (which closes the connection) or wrap in
`try/finally: conn.close()`.

### Confidence
High

---

## RT-022 — Dashboard "today's priorities" issues cross-database N+1 queries

### Severity
Low

### Category
Performance

### Location
`backend/main.py` — `_todays_priorities` (426–469); `get_weaknesses` confidence
-trap loop (969–976)

### Description
For each of the (up to 5) due topics, `_todays_priorities` runs a fresh
`question_bank.db` query to find matching question IDs and then a separate
`attempts.db` query to find the most common mistake — each via its own
`get_db()` connection (RT-010). `get_weaknesses` similarly runs one
`question_bank.db` topic lookup per confidence-trap row. The per-row count is
bounded by `LIMIT 5`/`LIMIT 6`, so this is not unbounded, but it multiplies the
already-heavy per-request connection churn: a single `/api/dashboard` opens and
tears down well over a dozen connections across three database files, several of
them inside row loops with `LIKE '%' || ? || '%'` predicates that cannot use an
index.

### Trigger Conditions
Every `/api/dashboard` and `/api/weaknesses` request once real attempt/topic
data exists.

### Expected / Actual Behavior
Expected: batch the per-topic lookups into single set-based queries. Actual:
one-query-per-row fan-out across databases, with full-scan `LIKE` joins.

### Impact
Avoidable latency and CPU on the two most-hit analytics endpoints; compounds
RT-010 under concurrent load.

### Recommended Fix
Collect the topics first and resolve mistakes/topics with a single `IN (...)`
query per database (as `_recent_papers` already does for papers). Replace the
substring `LIKE` topic match with a normalised join key where possible.

### Confidence
High

---

## RT-023 — Hourly paper-scan job runs unbounded blocking ingest with no misfire/coalesce guard

### Severity
Low

### Category
Concurrency / Reliability

### Location
`agents/infrastructure/scheduler_agent.py` — `schedule_paper_scan` (49–70),
`start_scheduler` (9–23)

### Description
The paper-scan job is registered on a `BlockingScheduler` with
`trigger="interval", minutes=60` and **no** `max_instances`, `coalesce`, or
`misfire_grace_time` settings. Its `_job` synchronously iterates **all**
unprocessed PDFs and calls `ingest_paper` on each in series. Given the OCR cost
documented in RT-008/RT-009 (the PDF is re-parsed many times per paper and the
LaTeX model is reloaded per call), a batch of scanned papers can easily make one
run exceed the 60-minute interval. With APScheduler defaults
(`max_instances=1`), the next run is then **missed** and dropped once it slips
past the default misfire grace, so ingestion silently stalls; and because the
scheduler is *blocking*, a long ingest also delays the cron-scheduled daily
briefing job that shares the same scheduler.

### Trigger Conditions
A drop of several multi-page scanned PDFs into `papers/` such that one scan cycle
exceeds the interval.

### Expected / Actual Behavior
Expected: overruns coalesce or queue without being dropped, and ingestion does
not block time-sensitive jobs. Actual: missed runs are discarded; a long ingest
blocks the briefing.

### Impact
Ingestion can quietly fall behind under load, and the daily briefing can be
delayed or skipped while a large ingest runs.

### Recommended Fix
Set `coalesce=True`, an explicit `misfire_grace_time`, and `max_instances=1` on
the scan job; move ingestion to its own executor/process pool (or a
`BackgroundScheduler` thread pool) so it cannot block the briefing cron; and
process papers incrementally with a bounded batch size per cycle.

### Confidence
Medium

---

## Appendix — Test run snapshot

```
$ pytest -q
20 failed, 101 passed, 9 warnings

# Failure breakdown:
#  - 9 async Telegram tests: pytest-asyncio not installed (RT-013)
#  - ~11 ingestion/agent tests: optional deps (pdfplumber, telegram, etc.)
#    not installed → ImportError or empty-metadata assertions
# None of the 101 passing tests cover the dashboard/briefing API paths,
# which is why RT-001/RT-002 escaped the suite.
```

## Appendix — 2026-06-15 re-audit evidence

```
$ DATA_DIR=/tmp/aosdata python -c "from db.models import init_all_databases; init_all_databases()"
$ # via TestClient(raise_server_exceptions=False):
Scalar query failed on progress.db: no such table: spaced_repetition_items
Query failed on progress.db: no such table: spaced_repetition_items   (x6)
/api/health    -> 200
/api/dashboard -> 500      # RT-001 still reproduces
/api/briefing  -> 500      # RT-001 still reproduces
/api/papers    -> 200
/api/status    -> 200

$ grep -rn "spaced_repetition_items" schemas/ db/      # RT-001: still no CREATE TABLE
(no matches)
$ grep entrypoint pyproject.toml                       # RT-006: unchanged
entrypoint = "backend.server:app"   (backend/server.py does not exist)
$ grep -n "allow_origins" backend/main.py              # RT-003: unchanged
40:    allow_origins=["http://localhost:3000", "http://localhost:3001"],

$ pytest -q
20 failed, 101 passed, 9 warnings    # unchanged from original audit
```

## Closing assessment

The biggest risks are **structural, not exotic**: a missing core table that
breaks the two most important read paths and silently neutralises the adaptive
engine (RT-001/RT-002), a CORS/deploy configuration that prevents the app from
running anywhere but localhost (RT-003/RT-006), and a swallow-everything error
strategy that hid all of the above (RT-007). These four should be fixed before
any scale or polish work. The performance items (RT-008/009/010/022) matter once
ingestion runs on real paper volumes; the remainder harden reliability and UX.

**Re-audit note (2026-06-15):** none of the original 19 issues have been
remediated — every headline defect still reproduces live on the current branch.
The newly-added RT-020 (import-time `mkdir` startup crash) compounds the existing
deployment story (RT-003/RT-006): the backend currently has no environment in
which it both starts *and* serves a working dashboard. Recommended order of
attack is unchanged: **RT-001 → RT-006/RT-020 → RT-003 → RT-007**, then the
performance and UX items.
