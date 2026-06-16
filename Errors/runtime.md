# AcademicOS — Runtime, Stability & Reliability Audit

**Audit date:** 2026-06-16
**Branch:** `claude/sharp-tesla-4ridqy`
**Auditor:** Automated runtime/execution audit (scheduled routine)
**Scope:** Full repository — FastAPI backend (`backend/`), agents (`agents/`),
ingestion (`ingestion/`), briefing (`briefing/`), scheduler & Telegram delivery,
database layer (`db/`, `schemas/`), and the Next.js frontend (`frontend/`).

> This audit re-verifies and supersedes the prior runtime audit
> (2026-06-14, branch `claude/sharp-tesla-et52fe`). The headline data-model
> defect (`spaced_repetition_items`) **remains unfixed** and was reproduced
> again here with fresh evidence, alongside additional verified findings.

## Method

- Created a clean virtualenv, installed core deps (`fastapi`, `uvicorn`,
  `pydantic`, `python-dotenv`, `pytest`, `httpx`).
- Initialised all databases via `db.models.init_all_databases()` and inspected
  the resulting table set in each `.db`.
- Exercised every GET endpoint and the attempt/session write paths through
  FastAPI's `TestClient` and by calling the route functions directly to capture
  full tracebacks.
- Ran the test suite: **101 passed, 20 failed**.
- Reproduced the headline defects directly (dashboard 500, briefing 500,
  `POST /api/attempts` 500-after-commit, spaced-repetition date overflow).
- Frontend reviewed statically for hydration, effect/leak, error-boundary,
  data-fetch, and render-performance defects.

## Severity summary

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 3 | RT-001 … RT-003 |
| High | 7 | RT-004 … RT-010 |
| Medium | 10 | RT-011 … RT-020 |
| Low | 5 | RT-021 … RT-025 |

> **Headline:** On a clean install the application's two primary read surfaces
> (`/api/dashboard`, `/api/briefing`) **both return HTTP 500**, and the single
> most important write flow — recording a marked attempt (`POST /api/attempts`)
> — **returns HTTP 500 _after_ committing the row**, so the user sees an error,
> retries, and silently accumulates duplicate attempts. The root cause is a
> data-model schism: the backend, briefing and scheduler are built on a
> `spaced_repetition_items` table that **no schema creates and no seeder
> populates**. These are the default state of a fresh deployment, not edge
> cases.

---

## RT-001 — `spaced_repetition_items` is queried everywhere but created nowhere → dashboard & briefing 500 on a clean install

### Severity
Critical

### Category
Crash / Reliability / Data Integrity

### Location
- `backend/main.py` — `get_health` (98–101), `_todays_priorities` (426–469),
  `_subject_mastery` (523–599), `_predicted_grades` (602–638),
  `_examiner_traps` (641–679), `_update_mastery` (831–881), `get_status` (1067).
- `briefing/generator.py` — `get_due_review_items` (20–55),
  `select_question_of_the_day` (58–118), `_section3_adaptive_revision` (172–217).
- `schemas/progress.sql` — defines `subjects`, `modules`, `topics`,
  `subtopics`, `specification_points`, `syllabus_completion`, `review_history`.
  It does **not** define `spaced_repetition_items`.
- `db/seed_syllabus.py` — does not create or populate the table.

### Description
Two parallel and incompatible progress models exist. The Curriculum Agent and
`progress.sql` use a normalised `specification_points` / `syllabus_completion`
model. The backend API, the daily briefing, and the scheduler instead read and
write a flat `spaced_repetition_items` table with columns
`topic, subtopic, unit, subject, due_date, mastery, ease_factor, interval_days,
last_reviewed`. That table is created by no schema file and populated by no
seeder, so it never exists on a fresh install.

The read helpers `_query`/`_scalar` in `backend/main.py` swallow
`sqlite3.Error` and return `[]`/default, which masks the failure on some
endpoints (health, status). But the briefing helpers use `get_db(...)`
**directly with no error handling**, so they raise and the exception propagates
all the way to the HTTP layer.

### Trigger Conditions
Clone the repo, `init_all_databases()`, start the API, and request
`/api/dashboard` or `/api/briefing`. No special data required — this is the
clean-install default.

### Expected Behavior
Empty databases produce empty (honest) 200 responses, per the module docstring
("Empty databases produce empty (honest) responses").

### Actual Behavior
HTTP 500 on both `/api/dashboard` and `/api/briefing`.

### Evidence
```text
$ python -c "from db.models import init_all_databases; init_all_databases()"
progress.db tables: ['subjects','modules','topics','subtopics',
  'specification_points','syllabus_completion','review_history']
has spaced_repetition_items: False

# TestClient against fresh DBs:
200  /api/health
500  /api/dashboard
500  /api/briefing
200  /api/status
200  /api/weaknesses
200  /api/analytics
200  /api/coverage
200  /api/papers

# Traceback (dashboard and briefing identical root):
  File "briefing/generator.py", line 30, in get_due_review_items
    rows = conn.execute(
sqlite3.OperationalError: no such table: spaced_repetition_items
```

### Impact
The application's two main screens are broken out of the box. The adaptive
revision engine, question-of-the-day, subject mastery, predicted grades, and
examiner traps all depend on data that can never exist. This is a fatal,
default-state failure.

### Recommended Fix
Pick one progress model and make the whole stack agree on it. Either (a) add a
`spaced_repetition_items` table to `schemas/progress.sql` and seed it from the
curriculum JSON, or (b) rewrite `backend/main.py` + `briefing/generator.py` to
read the existing `syllabus_completion`/`specification_points` model (which the
Curriculum Agent already owns and `progress.sql` already creates). Option (b) is
architecturally cleaner because it removes the duplicate model entirely. Until
then, at minimum wrap the briefing helpers in the same error-swallowing pattern
as `_query`.

### Confidence
High

---

## RT-002 — `POST /api/attempts` returns 500 *after* committing the attempt → broken marking flow + duplicate rows on retry

### Severity
Critical

### Category
Crash / State Corruption / Data Integrity

### Location
`backend/main.py` — `create_attempt` (884–930) → `_update_mastery` (831–881).

### Description
`create_attempt` inserts the attempt and its mistake tags inside one
`get_db(DB_ATTEMPTS)` block (committed on exit), then calls `_update_mastery`,
which opens `get_db(DB_PROGRESS)` and runs an **unguarded** query against
`spaced_repetition_items`. For any question that has a primary topic, that query
raises `sqlite3.OperationalError: no such table` *after* the attempt has already
been committed to `attempts.db`.

The exception is not caught, so the endpoint returns HTTP 500. The client treats
it as a failed save and retries, but the row was already persisted — every retry
inserts another attempt. This corrupts every downstream aggregate (weakness
analysis, calibration, score trend, coverage) by double/triple counting.

### Trigger Conditions
`POST /api/attempts` with a `question_id` whose `question_topics.is_primary = 1`
row exists. This is the normal path — every classified question has a primary
topic.

### Expected Behavior
Attempt is saved once; mastery updates if possible; HTTP 200 returned with the
new mastery (or `null` mastery when no SR item exists).

### Actual Behavior
Attempt is committed, then the request 500s. Client retries duplicate the row.

### Evidence
```text
using existing qid 1
EXCEPTION: sqlite3.OperationalError: no such table: spaced_repetition_items
attempts before=1 after=2   (row persisted but the request returned 500)
```

### Impact
The core "mark a question" user flow fails on a fresh install, *and* silently
double-records data on the retry the failure encourages. Direct violation of
Governing Principle #1 (Data Integrity).

### Recommended Fix
Fix RT-001 (the missing table). Independently: make the write atomic and
non-fatal — wrap `_update_mastery` so a mastery-update failure logs a warning
and returns `(None, None)` instead of bubbling a 500 after the attempt is
already committed. Also make `POST /api/attempts` idempotent or de-duplicate on
`(session_id, question_id)` to neutralise retries.

### Confidence
High

---

## RT-003 — Scheduled daily briefing job crashes and APScheduler swallows it → briefing silently never delivered

### Severity
Critical

### Category
Reliability / Background Job Failure / Silent Failure

### Location
`agents/infrastructure/scheduler_agent.py` — `schedule_daily_briefing._job`
(36–41); `briefing/generator.py` — `generate_daily_briefing` (247–261).

### Description
The cron job calls `generate_daily_briefing()`, which fails for the same reason
as RT-001 (`get_due_review_items` raises on the missing table). The job body has
no try/except; APScheduler catches unhandled job exceptions, logs them, and
keeps the scheduler alive. So the process appears healthy while the user's
single delivery channel produces nothing, every day, with no surfaced error.

### Trigger Conditions
Run `start_scheduler()` (or `scripts/send_briefing.py`) against a clean install.

### Expected Behavior
A briefing is generated and delivered to Telegram at `BRIEFING_TIME`.

### Actual Behavior
The job raises `OperationalError` and is silently absorbed by APScheduler; no
briefing is delivered and the scheduler keeps running as if nothing is wrong.

### Evidence
`generate_daily_briefing()` raised `sqlite3.OperationalError: no such table:
spaced_repetition_items` when invoked directly (same traceback as RT-001). The
job in `scheduler_agent.py` wraps no error handling around it.

### Impact
The product's flagship deliverable (the daily Telegram briefing) never arrives,
and the failure is invisible — no alert, no retry, no dead-letter.

### Recommended Fix
Fix RT-001. Add a try/except around the job that logs failures at ERROR and
sends a fallback/alert message so silent failure is impossible. Consider a job
listener (`scheduler.add_listener(..., EVENT_JOB_ERROR)`) for observability.

### Confidence
High

---

## RT-004 — Frontend `fetch` has no timeout or `AbortController` → screens stuck on the loading spinner forever

### Severity
High

### Category
Reliability / Network Error Handling / UX

### Location
`frontend/lib/api.ts` (`request`, ~17–28); `frontend/lib/hooks.ts`
(`useFetch`, 17–53 — uses a `cancelled` boolean but never aborts the request).

### Description
`fetch` is issued with no timeout and no `AbortSignal`. `useFetch` guards
against post-unmount `setState` via a `cancelled` flag but does not abort the
underlying request, so a backend that accepts the connection but never responds
leaves `loading === true` indefinitely — the screen shows a spinner with no
error and no retry. On rapid dependency changes responses can also resolve out
of order.

### Trigger Conditions
Slow, hung, or unreachable backend; or fast toggling of filters that change
`useFetch` deps.

### Expected Behavior
Requests time out, surface an error state with a retry, and in-flight requests
are cancelled on unmount/dep-change.

### Actual Behavior
Permanent spinner; wasted in-flight requests; possible out-of-order data.

### Impact
Hard-to-diagnose "frozen app" UX whenever the backend is slow — which, given
RT-001/RT-002, is a common state.

### Recommended Fix
Thread an `AbortSignal` from `useFetch` into `fetch`, abort it in the effect
cleanup, and add a timeout (`AbortSignal.timeout(ms)`); render an error+retry
state on timeout.

### Confidence
High

---

## RT-005 — No React error boundary + unguarded `qs[cur].id` in the live exam Timer → white-screen crash mid-session

### Severity
High

### Category
Crash / Runtime Exception (frontend)

### Location
No `frontend/app/error.tsx` and no class error boundary around
`ClientLayout`'s `<Screen />` switch. `frontend/components/screens/Timer.tsx`
— `qTimes` (state, starts length 1) vs `qs` (derived from fetched data);
`logCurrent`/`finish` read `qs[cur].id` where `cur = qTimes.length - 1`.

### Description
`qTimes` grows independently of `qs`. When `cur` exceeds `qs.length - 1`,
`qs[cur]` is `undefined` and `qs[cur].id` throws `Cannot read properties of
undefined`. With no error boundary anywhere, any render-time throw (this one, or
a malformed API row elsewhere) unmounts the entire React tree → blank white
screen with no recovery.

### Trigger Conditions
Advancing/finishing in the Timer when `qTimes` and `qs` desynchronise (small or
filtered question set, fast navigation), or any uncaught render exception in any
screen.

### Expected Behavior
A bad row or index is contained to a fallback UI with retry; the rest of the app
stays usable.

### Actual Behavior
Whole-app white screen, mid-exam — the worst possible time to lose state.

### Impact
Total loss of the SPA from a single bad data row or index, during an active
timed session.

### Recommended Fix
Add `app/error.tsx` and/or wrap `<Screen />` in a class ErrorBoundary with a
retry fallback. In Timer, guard `const q = qs[cur]; if (!q) return;` and clamp
`cur` to `qs.length - 1`.

### Confidence
High

---

## RT-006 — `config/settings.py` creates `DATA_DIR` without `parents=True` → import-time crash on a nested path

### Severity
High

### Category
Startup Failure / Crash

### Location
`config/settings.py:15` — `DATA_DIR.mkdir(exist_ok=True)`.

### Description
`DATA_DIR` is configurable via env. If it points at a path whose parent does not
yet exist (e.g. `DATA_DIR=/srv/academicos/data`), `mkdir(exist_ok=True)` (no
`parents=True`) raises `FileNotFoundError` at module import. Because
`config.settings` is imported by virtually everything, the entire backend,
scheduler, and CLI scripts fail to start. (`DIAGRAMS_DIR` two lines below
correctly uses `parents=True`, so the inconsistency is clearly unintended.)

### Trigger Conditions
Set `DATA_DIR` to any path with a non-existent parent directory (a normal
deployment/containerisation scenario) and import any module.

### Expected Behavior
The data directory tree is created.

### Actual Behavior
`FileNotFoundError` at import; everything that imports settings fails to start.

### Impact
Deployment-specific hard startup failure that won't reproduce in the repo-local
default (`BASE_DIR/data`), so it is easy to ship.

### Recommended Fix
`DATA_DIR.mkdir(parents=True, exist_ok=True)`.

### Confidence
High

---

## RT-007 — Production deployment is non-functional: frontend defaults API to `localhost:8000`, CORS allows only localhost, and Vercel deploys no backend

### Severity
High

### Category
Deployment / Environment Failure / Reliability

### Location
`frontend/lib/api.ts:15` (`NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`);
`backend/main.py:40` (`allow_origins=["http://localhost:3000", "...:3001"]`);
`vercel.json` (builds only `frontend/package.json`).

### Description
Three independent facts combine into a guaranteed production outage:
1. If `NEXT_PUBLIC_API_URL` is not baked in at **build time** (NEXT_PUBLIC vars
   are inlined at build, not runtime), every browser API call targets
   `http://localhost:8000`. On an HTTPS-hosted site these are blocked as
   mixed-content.
2. The backend's CORS allowlist is hardcoded to `localhost:3000/3001`, so a
   deployed frontend origin is rejected even if the URL is correct.
3. `vercel.json` only builds the Next.js frontend; there is no backend
   deployment, so there is nothing for the frontend to talk to in prod.

### Trigger Conditions
Deploy as configured (e.g. to Vercel) without manually setting build-time env
and a backend host.

### Expected Behavior
Frontend talks to a configured backend over HTTPS with the deployed origin
allowed by CORS.

### Actual Behavior
All API calls fail (mixed content / wrong host / CORS); every screen falls back
to an error state.

### Impact
The product does not work when deployed by following the repo's own config.

### Recommended Fix
Require `NEXT_PUBLIC_API_URL` at build (fail the build if missing in
non-dev); drive `allow_origins` from an env var; document/host the backend
(serverless function or separate service) and wire it into deployment.

### Confidence
High

---

## RT-008 — `--send-now` briefing path imports a non-existent `TelegramAgent` class → `ImportError`

### Severity
High

### Category
Runtime Exception / Reliability

### Location
`briefing/generator.py:286–288` —
`from agents.delivery.telegram_agent import TelegramAgent` then
`TelegramAgent().send_message(text)`. `agents/delivery/telegram_agent.py`
exposes module-level `async def send_message(...)` and `send_daily_briefing(...)`
— there is no `TelegramAgent` class.

### Description
The only `TelegramAgent` references in the codebase are these two lines; the
class does not exist. Running `python -m briefing.generator --send-now` raises
`ImportError`. (Calling `send_message` as a class method would also be wrong —
it is an async function and must be awaited.) The correct, working path lives in
`scripts/send_briefing.py`, which uses `asyncio.run(send_daily_briefing(...))`.

### Trigger Conditions
`python -m briefing.generator --send-now`.

### Expected Behavior
The briefing is generated and sent to Telegram.

### Actual Behavior
`ImportError: cannot import name 'TelegramAgent'`.

### Impact
A documented manual-send entry point is dead. Low blast radius (an alternative
script exists) but it is a guaranteed crash on a stated workflow.

### Recommended Fix
Replace with `from agents.delivery.telegram_agent import send_daily_briefing`
and `asyncio.run(send_daily_briefing(text))`, matching `scripts/send_briefing.py`.

### Confidence
High

---

## RT-009 — Spaced-repetition `interval_days` grows unbounded → `OverflowError` in `timedelta`

### Severity
High

### Category
Runtime Exception / Reliability

### Location
`backend/main.py` — `_update_mastery` (857–869):
`interval = interval * ease` on every score ≥ 0.8, then
`due = (date.today() + timedelta(days=round(interval)))`.

### Description
On each high-scoring attempt the interval is multiplied by `ease` (capped at
3.0) with no upper bound. Sustained good performance on a topic compounds the
interval exponentially. Once `round(interval)` exceeds `timedelta`'s day limit
(~`999999999` days), `date + timedelta(...)` raises `OverflowError`, crashing
`create_attempt` (HTTP 500). (Currently latent only because the table is missing
per RT-001 — fixing RT-001 activates this path.)

### Trigger Conditions
Repeated attempts ≥ 80% on the same topic (a deliberately studying user, over
time), once `spaced_repetition_items` exists.

### Evidence
```text
# interval *= 2.5 repeatedly:
OverflowError; interval=8271806125530275.0  (well beyond timedelta's day range)
```

### Expected Behavior
Intervals are clamped to a sane maximum (e.g. 365 days).

### Actual Behavior
Eventually `OverflowError` → 500 on a normal write.

### Impact
A long-term, hard-to-reproduce crash that punishes the most engaged users.

### Recommended Fix
Clamp: `interval = min(365.0, interval * ease)` (and floor at 1.0). Validate the
stored interval on read.

### Confidence
High

---

## RT-010 — Theme is applied only after mount → flash of wrong theme on every load, and the toggle does not persist

### Severity
High

### Category
Hydration Mismatch / UX

### Location
`frontend/app/layout.tsx:30` (`data-theme="light"` hardcoded on the server);
`frontend/components/ClientLayout.tsx:50,55–62` (reads `matchMedia` and sets
`data-theme` only in `useEffect`); `frontend/components/screens/Settings.tsx`
(toggle never persisted).

### Description
The server always emits `data-theme="light"`. After hydration the client reads
`prefers-color-scheme` and flips the attribute, producing a visible flash for
dark-mode users on every load. The Settings toggle is never written to
`localStorage`, so the user's explicit choice is re-derived (and lost) on each
reload.

### Trigger Conditions
Any load with OS dark mode, or any reload after toggling the theme.

### Expected Behavior
Correct theme on first paint; explicit preference persists across reloads.

### Actual Behavior
Light→dark flash (FOUC); toggle resets on refresh.

### Impact
Persistent visual jank and a non-functional-feeling settings control.

### Recommended Fix
Inline a blocking `<script>` in `<head>` that sets `data-theme` from
`localStorage`/`matchMedia` before paint; persist the toggle to `localStorage`.

### Confidence
High

---

## RT-011 — No SQLite `busy_timeout`; a fresh connection is opened per query → "database is locked" under concurrency and per-request overhead

### Severity
Medium

### Category
Concurrency / Performance / Resource Use

### Location
`db/models.py` — `get_db` (42–55) opens a new connection, sets
`PRAGMA journal_mode=WAL`, and closes per use; no `busy_timeout` and no
`timeout=` on `sqlite3.connect`. `backend/main.py` issues ~68 separate
`_query`/`_scalar`/`get_db` calls, each its own connection; `/api/dashboard`
alone opens well over a dozen connections per request.

### Description
WAL allows concurrent readers with a single writer, but with the Python default
busy timeout and no explicit `busy_timeout`, concurrent writers (e.g. two
`POST /api/attempts` in flight) can raise `sqlite3.OperationalError: database is
locked` instead of waiting. Separately, opening/closing a connection (plus two
PRAGMAs) per individual query is wasteful — a single dashboard request pays that
cost a dozen-plus times.

### Trigger Conditions
Concurrent writes (multiple users / parallel requests); general load.

### Expected Behavior
Writers wait briefly and succeed; reads reuse a per-request connection.

### Actual Behavior
Possible "database is locked" errors under concurrency; redundant connection
churn per request.

### Impact
Intermittent write failures and elevated latency at production scale.

### Recommended Fix
Set `PRAGMA busy_timeout=5000` (or `sqlite3.connect(..., timeout=5)`) in
`get_db`. Refactor endpoints to open one connection per database per request and
pass it down (the agents already accept an optional `*_conn` for exactly this).

### Confidence
Medium

---

## RT-012 — N+1 query patterns in dashboard and weakness aggregation

### Severity
Medium

### Category
Performance / N+1

### Location
`backend/main.py` — `_todays_priorities` (441–468, two queries per priority
row), `get_weaknesses` (969–1050, one query per confidence trap and one per
aggregated topic), `_recent_papers`/`_subject_mastery` cross-DB fan-out.

### Description
Several handlers loop over a result set and issue per-row sub-queries (each
opening its own connection per RT-011). For example `get_weaknesses` runs a
mistake-frequency query for every aggregated `(topic, subtopic)` group, and
`_todays_priorities` runs two queries per priority topic.

### Trigger Conditions
Realistic data volumes (many attempts/topics).

### Expected Behavior
Bounded query count independent of row count.

### Actual Behavior
Query count scales linearly with rows; latency grows with data.

### Impact
Slow dashboard/weakness endpoints as the student's history grows.

### Recommended Fix
Batch with `IN (...)` / `GROUP BY` joins (some sites already do this) and reuse
a single connection per database.

### Confidence
Medium

---

## RT-013 — `useFetch` deps/fetcher design is fragile (stale closures, latent refetch storms)

### Severity
Medium

### Category
Race Condition / Excessive Re-render (frontend)

### Location
`frontend/lib/hooks.ts:17–53` — `fetcherRef` updated every render, but the
effect depends on `[attempt, ...deps]` with `fetcher` excluded; the
`react-hooks/exhaustive-deps` lint is suppressed.

### Description
The effect re-runs only when `attempt` or a listed `dep` changes. Because the
fetcher is read from a ref, a caller that captures changing state but forgets to
list it in `deps` silently fetches with the wrong inputs (stale data). The
inverse risk: passing a non-primitive (object/array) dep makes the array churn
every render and triggers a refetch storm. Correctness depends entirely on every
call site getting `deps` right.

### Trigger Conditions
A call site whose fetcher captures state not present in `deps`, or one that
passes a freshly-constructed object/array dep.

### Expected Behavior
Fetch re-runs exactly when its inputs change.

### Actual Behavior
Either stale data (missing dep) or a refetch loop (unstable dep).

### Impact
Latent wrong-data rendering (data-integrity risk) and potential backend
hammering.

### Recommended Fix
Adopt a stable-fetcher contract (`useCallback`) and include the fetcher in deps,
or key the effect off a serialized deps value; re-enable the lint rule.

### Confidence
Medium

---

## RT-014 — `pyproject.toml` Vercel entrypoint points at a non-existent module

### Severity
Medium

### Category
Deployment / Configuration

### Location
`pyproject.toml` — `[tool.vercel] entrypoint = "backend.server:app"`. There is
no `backend/server.py`; the app object lives at `backend.main:app`.

### Description
Any tool honouring this entrypoint (or a copy-paste of it into a
uvicorn/gunicorn command) fails with `ModuleNotFoundError: backend.server`.
Combined with RT-007, the backend has no correct, working deployment descriptor.

### Trigger Conditions
Deploying the backend using the declared entrypoint.

### Expected Behavior
Entrypoint resolves to the ASGI app.

### Actual Behavior
`ModuleNotFoundError: No module named 'backend.server'`.

### Impact
Backend deployment misconfiguration; wasted debugging time.

### Recommended Fix
Use `backend.main:app` (or add a `backend/server.py` that re-exports `app`).

### Confidence
High

---

## RT-015 — Unbounded list rendering / no virtualization on large datasets

### Severity
Medium

### Category
Performance / Rendering (frontend)

### Location
`frontend/lib/api.ts:38` (`getPapers` default `limit=500`);
`frontend/components/screens/Weaknesses.tsx` (`rows.map` with no slice, plus
re-sort on every click); `frontend/components/screens/Analytics.tsx`
(unbounded session-log `.map`).

### Description
Several tables render every row with no cap or virtualization, and sort/filter
recomputes and re-renders the entire list. With 500 papers and a long attempt
history this produces large DOM trees and janky interaction. (Some screens, e.g.
the paper picker, correctly `.slice(...)` — the inconsistency highlights the
gaps.)

### Trigger Conditions
Large paper library / long weakness or session history.

### Expected Behavior
Bounded/virtualized rendering; memoized sorted rows.

### Actual Behavior
Sluggish UI and full re-renders on every sort/filter.

### Impact
Degraded responsiveness at realistic data scale.

### Recommended Fix
Cap rendered rows (`.slice`) and/or virtualize; `useMemo` sorted/derived rows.

### Confidence
Medium

---

## RT-016 — Secondary fetch failures are swallowed → silent partial data

### Severity
Medium

### Category
Reliability / Error State (frontend)

### Location
`frontend/components/screens/Weaknesses.tsx` (`dash.data?.examiner_traps ?? []`
— `dash` error ignored); `frontend/components/screens/Analytics.tsx`
(`weak`/`papersFetch` errors not surfaced; only `analytics`/`coverage` gate the
screen).

### Description
Screens that issue more than one `useFetch` gate the UI on the primary fetch and
optional-chain the rest. If a secondary fetch fails, its section silently
disappears with no indication, so the user sees an incomplete screen believing it
is complete — contrary to the codebase's stated "never show stale/fabricated
data" intent.

### Trigger Conditions
One of multiple concurrent fetches fails (e.g. dashboard 500 per RT-001 while
weaknesses succeeds).

### Expected Behavior
Partial failures are surfaced (inline notice / retry).

### Actual Behavior
Section vanishes silently.

### Impact
Misleading "everything's fine" UI hiding real backend failures.

### Recommended Fix
Surface secondary-fetch errors inline instead of swallowing them.

### Confidence
Medium

---

## RT-017 — Timer state is component-local → orphaned open sessions and lost timing on navigation

### Severity
Medium

### Category
State Corruption / Data Integrity (frontend)

### Location
`frontend/components/screens/Timer.tsx` (timer state `elapsed`/`qTimes`/`running`
in component state; session created via `createSession`);
`frontend/components/screens/Marking.tsx:114–122` (`session_id` may be `null`,
`time_seconds: 0` hardcoded).

### Description
Timer state lives in the component, which unmounts when the user navigates to
another screen (ClientLayout swaps `<Screen/>`). Navigating away mid-session
clears the interval but loses `elapsed`/`qTimes` and never completes the backend
session → orphaned open sessions accumulate in `attempts.db`. Marking then sends
`session_id: session.sessionId` (possibly `null`) and `time_seconds: 0`,
dropping the per-question timing the Timer captured.

### Trigger Conditions
Start a timed paper, then navigate away or mark questions after leaving Timer.

### Expected Behavior
Session timing persists across navigation; attempts link to their session with
real per-question time; sessions are completed or explicitly abandoned.

### Actual Behavior
Orphaned open sessions; attempts saved with `session_id: null` and
`time_seconds: 0`.

### Impact
Corrupted analytics (timing, calibration) and dangling DB rows.

### Recommended Fix
Lift timer/session state into the shared `AppSession` (or persist to backend on
unmount), pass real per-question times to `submitAttempt`, and complete/abandon
the session on navigation.

### Confidence
Medium

---

## RT-018 — Curriculum Agent commits on borrowed connections (premature/double commit)

### Severity
Medium

### Category
Reliability / Transaction Handling

### Location
`agents/infrastructure/curriculum_agent.py` — `advance_topic`,
`update_completion`, `schedule_review` call `conn.commit()` inside `_run` (e.g.
90, 142, 274). When `progress_conn` is supplied by a caller, the helper commits
the caller's transaction; when it opens its own via `get_db`, the context
manager also commits on exit (double commit).

### Description
Committing a connection the function does not own breaks transaction
composability: a caller batching several curriculum updates in one transaction
will have it partially committed by the first helper, defeating atomicity. The
self-owned path commits twice (harmless but redundant).

### Trigger Conditions
Any caller that passes a shared `progress_conn` expecting a single atomic
transaction.

### Expected Behavior
Commit is the caller's responsibility when a connection is injected.

### Actual Behavior
The helper commits a borrowed connection mid-batch.

### Impact
Partial writes / lost atomicity for batched curriculum updates.

### Recommended Fix
Only commit on the self-owned path (rely on `get_db`'s commit), and do not
commit when `progress_conn` is provided.

### Confidence
Medium

---

## RT-019 — `ATTACH DATABASE` without `DETACH` in `select_question_of_the_day`

### Severity
Medium

### Category
Resource Handling / Reliability

### Location
`briefing/generator.py:81` —
`conn.execute("ATTACH DATABASE ? AS att", (str(DB_ATTEMPTS),))` with no matching
`DETACH`.

### Description
The attempts DB is attached for the duration of the connection and never
detached. Because the connection is closed at the end of the `with get_db(...)`
block this does not leak across requests today, but it is fragile: if this
connection is ever reused/pooled (the recommended fix for RT-011) the attach will
accumulate or fail ("database att is already in use"). It also attaches by
absolute path on every call.

### Trigger Conditions
Reusing/pooling the question-bank connection across calls.

### Expected Behavior
Attach is scoped and detached, or a cross-DB query avoids ATTACH.

### Actual Behavior
Attach persists for the connection lifetime; safe only because the connection is
discarded immediately.

### Impact
Latent failure that surfaces precisely when connection reuse is introduced for
performance.

### Recommended Fix
`DETACH DATABASE att` in a `finally`, or run the two-DB lookup as separate
queries joined in Python.

### Confidence
Medium

---

## RT-020 — Unchecked array-index lookups render `undefined` for out-of-range backend values

### Severity
Medium

### Category
Null/Undefined Access (frontend & backend)

### Location
`frontend/components/screens/QuestionReview.tsx` (`DIFFICULTY[q.difficulty]`,
length-6 array); `Marking.tsx` / `Weaknesses.tsx` (`CONF_COLORS[conf-1]`,
length-5); `backend/main.py:703`
(`["", "Recall", ... "Trap"][qod["difficulty"]]` — server side, same risk).

### Description
`difficulty` and `confidence` are typed as plain numbers with no clamp. An
out-of-range value (0, >5, or negative — possible from ingestion/classification)
indexes past the lookup arrays, rendering `undefined`. The server-side variant in
`_question_of_day` would raise `IndexError` for a difficulty outside 0–5.

### Trigger Conditions
A question/attempt whose `difficulty`/`confidence` falls outside the expected
1–5 / 0–5 range.

### Expected Behavior
Clamped index with a sensible fallback label.

### Actual Behavior
`undefined` text in the UI; potential `IndexError` server-side.

### Impact
Confusing labels; a possible 500 in `/api/dashboard`'s question-of-the-day.

### Recommended Fix
Clamp indices and use `?? "Unknown"`; validate `difficulty`/`confidence` ranges
at ingestion and in Pydantic models.

### Confidence
Medium

---

## RT-021 — 20 failing tests; missing optional dep masks the suite, and one real extraction defect

### Severity
Low

### Category
Reliability / Test Signal

### Location
`tests/` (20 failures); `ingestion/ocr.py:20` (`import pdfplumber`);
`agents/analysis/past_paper_agent.py` — `extract_metadata` (134–170).

### Description
`pytest` reports 101 passed / 20 failed. Most failures are
`ModuleNotFoundError: No module named 'pdfplumber'` (an optional/heavy dep not
installed), which collapses OCR/markscheme/examiner/past-paper tests and hides
their real signal. One failure is a genuine defect:
`test_extract_metadata_module_code` expects `M1` but `extract_metadata` returns
`"Unknown"`, indicating the module-code regex doesn't match the fixture format.

### Trigger Conditions
Run `pytest` in an environment without `pdfplumber`, or ingest a paper whose
module code the regex misses.

### Expected Behavior
Tests skip cleanly when optional deps are absent; metadata extraction returns the
real module code.

### Actual Behavior
20 hard failures; `module_code == "Unknown"` for a known-good fixture.

### Evidence
```text
20 failed, 101 passed
ModuleNotFoundError: No module named 'pdfplumber'  (ingestion/ocr.py:20)
assert meta.module_code == "M1"  ->  AssertionError: assert 'Unknown' == 'M1'
```

### Impact
CI is red and uninformative; some ingested papers will be filed under module
"Unknown", degrading retrieval/coverage accuracy.

### Recommended Fix
Guard optional imports with `pytest.importorskip("pdfplumber")` (or make OCR
imports lazy/optional); fix/broaden the module-code regex and add fixtures for
the real formats.

### Confidence
High

---

## RT-022 — Icons loaded from a CDN at `@latest` (unpinned third-party dependency)

### Severity
Low

### Category
Reliability (external dependency, frontend)

### Location
`frontend/app/layout.tsx:32–35` —
`https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/...`.

### Description
`@latest` can change without notice (breaking icon names) and a CDN outage
removes all icons. `@tabler/icons-react` is already a dependency, so icon
delivery is duplicated.

### Impact
Icons break/disappear on CDN issues or upstream version bumps.

### Recommended Fix
Pin a version and/or self-host; consolidate on the installed React icon package.

### Confidence
High

---

## RT-023 — List keys use the array index on sortable/filterable lists

### Severity
Low

### Category
Reconciliation Correctness (frontend)

### Location
`Weaknesses.tsx` (`rows.map((w,i) => <tr key={i}>`, sorted/filtered),
`Briefing.tsx`, `Home.tsx`, `Marking.tsx` (various index keys).

### Description
Index keys on lists that re-sort/filter cause React to mis-associate row DOM and
local state after reordering, producing subtle visual glitches and occasional
wrong-row interactions.

### Impact
Minor UI correctness bugs on sort/filter.

### Recommended Fix
Use stable keys derived from data (e.g. `w.topic + w.subtopic`).

### Confidence
High

---

## RT-024 — `ScatterChart` y-axis hardcoded `min: 40` clips low scores

### Severity
Low

### Category
Data Display Correctness (frontend)

### Location
`frontend/components/charts/index.tsx:240` (`min: 40`).

### Description
Scores below 40% render off the visible axis, hiding the worst (most important)
performances from the calibration scatter.

### Impact
Misleading visualization that omits poor results.

### Recommended Fix
Use `min: 0` or a dynamic minimum.

### Confidence
High

---

## RT-025 — Charts read CSS variables during render → SSR/client value divergence

### Severity
Low

### Category
Hydration Mismatch (frontend)

### Location
`frontend/components/charts/index.tsx` — `getCSSVar` returns `""` on the server,
real colors on the client; called during render.

### Description
Color props computed during render differ between the server pass (`""`) and the
client pass. Chart.js renders to `<canvas>` so React doesn't diff it directly,
but the divergence (combined with RT-010's post-mount theme application) shows as
wrong/empty chart colors on first paint before correcting.

### Impact
Brief incorrect chart colors on initial render.

### Recommended Fix
Read CSS vars in `useEffect`/state after mount, or pass colors from a theme
context rather than reading the DOM during render.

### Confidence
Medium

---

## Appendix — Reproduction quickstart

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install fastapi 'uvicorn[standard]' python-dotenv pytest httpx pydantic
python -c "from db.models import init_all_databases; init_all_databases()"
python - <<'PY'
from fastapi.testclient import TestClient
from backend.main import app
c = TestClient(app, raise_server_exceptions=False)
for ep in ['/api/dashboard','/api/briefing','/api/health']:
    print(c.get(ep).status_code, ep)   # 500 /api/dashboard, 500 /api/briefing
PY
pytest -q   # 101 passed, 20 failed
```

## Most urgent remediation order

1. **RT-001 / RT-002 / RT-003** — resolve the `spaced_repetition_items` schism;
   it breaks the dashboard, the briefing, the scheduler, and the marking write
   path on every fresh install.
2. **RT-006 / RT-007 / RT-014** — fix the startup `mkdir` and the production
   deployment config (API URL, CORS, entrypoint) so the app can run outside the
   repo-local default.
3. **RT-004 / RT-005** — add fetch timeouts/abort and a React error boundary so
   backend failures degrade gracefully instead of freezing or white-screening.
4. **RT-009 / RT-011** — clamp the SR interval and set a SQLite busy timeout
   before going multi-user.

---

## Post-audit note (merge, 2026-06-16)

This audit was run against `main` prior to the integration of the
`hopeful-volta-qz7w1a` and `hopeful-volta-1j0tm7` remediation branches
(see `MERGE_REPORT.md`). Several findings recorded above may already be
addressed by that merge. Re-run this audit against the post-merge tree
before treating any item here as still open.
