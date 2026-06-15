# AcademicOS — Logic Error Audit

**Audit date:** 2026-06-14 · **Re-audit:** 2026-06-15 (branch `claude/vigilant-lovelace-oa3mmq`)
**Scope:** Full codebase — backend API (`backend/main.py`), briefing generator, agents, database schemas/seeders, and the Next.js frontend (screens, components, hooks, lib).
**Objective:** Identify every logic error that negatively affects real-world usability from the client's perspective.

**Method:** Static trace of every data flow from SQLite → FastAPI → frontend fetch hooks → rendered components, cross-checking schemas against queries and backend output shapes against TypeScript types. The critical finding was additionally **reproduced at runtime** (see LOGIC-001 evidence).

**Re-audit note (2026-06-15):** All 20 findings below were re-verified line-by-line against the current code on this branch and **all still hold** (the audited files are unchanged since 2026-06-14). This pass additionally surfaced **6 new issues — LOGIC-021 through LOGIC-026** — documented after LOGIC-020.

---

## Summary Table

| ID | Severity | Area | One-line |
|----|----------|------|----------|
| LOGIC-001 | **Critical** | DB / backend | `spaced_repetition_items` table is queried everywhere but never created → entire dashboard/progress is silently empty |
| LOGIC-002 | **Critical** | Config / deploy | Frontend API URL defaults to `localhost:8000` and backend CORS only allows localhost → deployed app is fully non-functional |
| LOGIC-003 | High | Grades | Backend and frontend use different grade boundaries → the same paper shows different grades on different screens, and both disagree with real Edexcel boundaries |
| LOGIC-004 | High | Marking | Re-marking a question inserts a **duplicate** attempt (no upsert) → inflated counts, double-counted marks, scores exceeding paper total |
| LOGIC-005 | High | Navigation | Clicking any past/recent paper opens Marking for the *currently-loaded* paper, not the clicked one |
| LOGIC-006 | High | Examiner traps | When no weak topics exist, `/api/dashboard` returns examiner traps in the wrong shape → blank trap text on Home/Briefing/Weaknesses |
| LOGIC-007 | High | Fake data | Sidebar footer hardcodes `Physics A · Maths A* · Chem B` |
| LOGIC-008 | High | Aggregation | Home "Papers completed" caps at 5; "Average score" computed over a different set than Analytics → inconsistent headline numbers |
| LOGIC-009 | Medium | Backend crash | `_question_of_day` can raise `IndexError`/`TypeError` on out-of-range/NULL difficulty → 500 on the whole dashboard |
| LOGIC-010 | Medium | Settings | Settings form is a non-functional placeholder (hardcoded name, exam session, briefing time, toggles never persist) |
| LOGIC-011 | Medium | Attempts | `submitAttempt` always sends `time_seconds: 0`; per-question timings are logged but never linked to attempts |
| LOGIC-012 | Medium | Charts | Scatter chart y-axis hardcoded `min: 40` → any paper scoring below 40% is clipped/invisible |
| LOGIC-013 | Medium | Prediction | "Predicted grade" = mastery + flat 0.10 regardless of trend/data → misleading prediction |
| LOGIC-014 | Medium | Dead source | `/api/briefing` (and the whole 4-section generated briefing) is never consumed by the frontend |
| LOGIC-015 | Low | Streak | Streak counts *started* sessions, so merely opening the timer inflates the streak |
| LOGIC-016 | Low | UX/copy | Hardcoded greeting "Good morning, Mouad." regardless of time of day |
| LOGIC-017 | Low | Subjects | Default active subject hardcoded to `physics` → empty-state flash if Physics has no data |
| LOGIC-018 | Low | Time zones | UTC-stored timestamps compared against local `date.today()` → off-by-one for `days_ago`/streak near midnight |
| LOGIC-019 | Low | Dead code | `_subject_mastery` computes `weak_topics` but never returns it; `grade_contribution` computed but never displayed |
| LOGIC-020 | Low | Data integrity | Backend does not verify a submitted attempt's question belongs to the session's paper |
| LOGIC-021 | **High** | Timer / config | Official exam time hardcoded to 90 min (target 60 min) for *every* paper → "two-thirds rule" badge, pace status, and all "vs target" deltas are wrong for most papers |
| LOGIC-022 | Medium | Aggregation | Home "Recent papers" includes **in-progress (never-completed) sessions**, unlike Papers/Analytics → inflates "Papers completed"/average and shows grades for unfinished work |
| LOGIC-023 | Medium | Marking | "Live grade" is computed over only the questions marked *so far*, not the whole paper → marking one easy question first shows "Grade A*" for the paper |
| LOGIC-024 | Medium | Marking | Zero-mark questions are admitted into Marking but rejected by the backend (`marks_available > 0`) → "Save failed" with a cryptic message, no path to record them |
| LOGIC-025 | Low | Aggregation | `/api/coverage` can report **>100%** attempted because `attempted` counts all attempts while `total_questions` counts only `question_paper` rows |
| LOGIC-026 | Low | UI consistency | Mastery/coverage bars use **two different colour-band thresholds** (80/50 vs 60/40) across screens for visually identical bars |

---

## LOGIC-001

### Severity
**Critical**

### Location
`backend/main.py` — `_todays_priorities`, `_subject_mastery`, `_predicted_grades`, `_examiner_traps`, `_update_mastery`, `get_health`, `get_status` (11 references); `briefing/generator.py` — `get_due_review_items`, `select_question_of_the_day`. Root cause: `schemas/progress.sql` + `db/seed_syllabus.py`.

### Description
The entire progress/mastery feature set queries a table named `spaced_repetition_items` (columns `topic, subtopic, unit, subject, due_date, mastery, ease_factor, interval_days, last_reviewed`). **This table is never created anywhere** — not in `schemas/progress.sql`, not by `db.models.init_all_databases()`, and not by `db/seed_syllabus.py`. The schema instead defines a *normalized* tree (`subjects → modules → topics → subtopics → specification_points → syllabus_completion`), and the seeder populates only that tree. The Curriculum Agent (the documented sole authority) reads/writes `syllabus_completion`, never `spaced_repetition_items`.

Because `_query`/`_scalar` catch `sqlite3.Error` and return `[]`/`0` (lines 56–73), every failure is **silent**. The result is a dashboard that loads "successfully" but is completely empty.

### Expected Behavior
After the documented setup (`init_all_databases()` + `seed_syllabus.py`), the dashboard should show today's priorities, the mastery heatmap, subject mastery, predicted grades, and a question of the day, all derived from real syllabus/progress data.

### Actual Behavior
Every progress-derived field is empty/zero:
- `todays_priorities = []`, `subject_mastery = []`, `predicted_grades = []`, `examiner_traps` unprioritized.
- `/api/health` reports `progress.topics = 0`, `due_today = 0`, and therefore `briefing_ready = False` permanently.
- `/api/status` shows progress.db `0 review items` and `ok: false`.
- `_update_mastery` finds no rows → every marked attempt returns `new_mastery: null` → the Marking screen's "mastery now X%" badge never appears.
- Home shows "No syllabus data. Seed progress.db first." and Subjects/University show empty grades — even when the user *has* seeded progress.db as instructed.

### Evidence
RESTART.md line 15 claims: *"progress.db: 94 syllabus topics + NEW `spaced_repetition_items` (94 rows, SM-2 state)"* — but no code creates it.

Reproduced at runtime in this audit:
```
$ PYTHONPATH=. python -c "init_all_databases(); seed_all(); ..."
seeded spec points: 486
progress.db tables: ['modules', 'review_history', 'specification_points',
                     'sqlite_sequence', 'subjects', 'subtopics',
                     'syllabus_completion', 'topics']
spaced_repetition_items present? False
API QUERY FAILS: OperationalError - no such table: spaced_repetition_items
```
The exact query the API runs (`SELECT COUNT(*) FROM spaced_repetition_items`) fails on a fully set-up database.

### Impact
The core value proposition of the app — adaptive, spaced-repetition-driven revision with mastery tracking and predicted grades — is entirely non-functional in production. The failure is silent (no error surfaced), so a client would believe their data simply "isn't there yet," eroding trust. This is a contradictory source of truth: the data model is normalized, but the API was written against a denormalized table that nothing produces.

### Recommended Fix
Decide on one source of truth and make them agree. Two options:
1. **Add the table + populate it.** Define `spaced_repetition_items` in `schemas/progress.sql` and have `seed_syllabus.py` (or the Curriculum Agent) materialize one row per topic with initial SM-2 state (`mastery`, `ease_factor`, `interval_days`, `due_date`). This matches RESTART.md's stated design.
2. **Rewrite the API queries** to read from the existing normalized tables (`topics`/`syllabus_completion`) and derive mastery from `syllabus_completion.confidence`/`review_count`.
Additionally, `_query`/`_scalar` should distinguish "table missing" from "no rows" and surface a setup error rather than masquerading missing infrastructure as empty data.

### Confidence
High

---

## LOGIC-002

### Severity
**Critical**

### Location
`frontend/lib/api.ts:15` (`BASE_URL`); `backend/main.py:38-44` (CORS); `.env.example`; `vercel.json`.

### Description
The frontend computes `BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`. No `NEXT_PUBLIC_API_URL` is defined anywhere (no `frontend/.env*`, and `.env.example` omits it). The repo deploys the frontend to Vercel (`vercel.json`). Separately, the backend CORS config only allows origins `http://localhost:3000` / `http://localhost:3001`.

### Expected Behavior
A deployed frontend should reach the deployed backend, and the backend should accept requests from the production origin.

### Actual Behavior
- In production the browser issues requests to `http://localhost:8000`, which resolves to the *user's own machine* and fails → every screen renders its `ErrorState` ("Could not load … Is the backend running on port 8000?").
- Even if `NEXT_PUBLIC_API_URL` were set to a real backend, CORS would reject the Vercel origin, blocking all requests.

### Evidence
`frontend/lib/api.ts:15`:
```ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```
`backend/main.py:40`:
```py
allow_origins=["http://localhost:3000", "http://localhost:3001"],
```

### Impact
The application is completely unusable when deployed — every data-bearing screen errors out. For a "production-bound" app this is a release blocker.

### Recommended Fix
Set `NEXT_PUBLIC_API_URL` for the deployed environment (document it in `.env.example`), and drive backend `allow_origins` from an env var that includes the production frontend origin(s).

### Confidence
High

---

## LOGIC-003

### Severity
High

### Location
`backend/main.py:76-85` (`_grade_from_mastery`) vs `frontend/lib/data.ts:6-13` (`gradeFromPct`). Consumers: `_recent_papers` (Home) vs `Analytics.tsx`, `Subjects.tsx`, `Marking.tsx`.

### Description
Two independent grade scales exist and disagree:

| Percent | Backend `_grade_from_mastery` | Frontend `gradeFromPct` |
|--------:|:-----------------------------:|:-----------------------:|
| ≥90 | A* | A* |
| 80–89 | A | A |
| **72** | **A** (≥0.70) | **B** (70–79 → B) |
| 60–69 | B / B | C |
| 50–59 | B / C | D |
| <40 | U | E (no U) |

The backend computes the grade for **recent papers** (`_recent_papers`, line 514) using mastery bands, while Marking, Analytics, and Subjects compute grades from the same percentage using `gradeFromPct`. The backend also never emits "D"/"E" and the frontend never emits "U".

### Expected Behavior
A paper scored at a given percentage should show one consistent grade everywhere, and that grade should match Edexcel IAL boundaries (≈A*=90, A=80, B=70, C=60, D=50, E=40).

### Actual Behavior
A 72% paper shows **grade A** on the Home "Recent papers" card (backend) but **grade B** in the Analytics session log and Subjects table (frontend) for the *same paper*. Backend grades are also inflated relative to real boundaries (A at 70%).

### Evidence
`backend/main.py:514`: `"grade": _grade_from_mastery(pct / 100) ...`
`frontend/components/screens/Analytics.tsx:185`: `<td>{gradeFromPct(pct)}</td>`

### Impact
Contradictory grades across screens directly undermine trust and violate the project's #2 governing principle (Educational Accuracy). A student could believe they are an A grade when their actual boundary grade is B.

### Recommended Fix
Define grade boundaries in exactly one place (ideally per-subject Edexcel boundaries, or a single shared constant), and have both the recent-papers grade and the frontend display use it. Do not reuse mastery-band thresholds for exam-percentage grades.

### Confidence
High

---

## LOGIC-004

### Severity
High

### Location
`frontend/components/screens/Marking.tsx:104-133` (`save`); `backend/main.py:884-930` (`create_attempt`).

### Description
The Marking screen lets the user click any question pill to revisit and re-save a question. Each `save()` calls `POST /api/attempts`, which **always INSERTs a new row** — there is no update/upsert keyed on (session, question). Re-marking a question therefore creates duplicate attempts.

### Expected Behavior
Re-marking a question within the same session should replace the previous mark, leaving one attempt per question per session.

### Actual Behavior
Each re-save adds another `attempts` row. Downstream aggregations sum *all* attempts:
- Session score (`get_papers`/`_recent_papers`/`get_analytics` sum `marks_awarded`/`marks_available` over attempts) can exceed the paper's total marks.
- `/api/weaknesses` `attempts` counts and `lost` marks are inflated.
- Confidence calibration and "questions attempted" coverage are inflated.

### Evidence
`backend/main.py:902` unconditional `INSERT INTO attempts ...`. No `ON CONFLICT`/dedup; `attempts` has an autoincrement PK with no uniqueness on (session_id, question_id).

### Impact
Corrupted scores and statistics — the live in-session display (computed from local de-duplicated state) will not match what the dashboard/analytics later report, and totals can be nonsensical (e.g., 78/72). Data-integrity is the #1 governing principle.

### Recommended Fix
Either upsert attempts on `(session_id, question_id)` (replace prior mark), or have the frontend `PATCH` an existing attempt when re-marking, or have aggregations select only the latest attempt per `(session_id, question_id)`.

### Confidence
High

---

## LOGIC-005

### Severity
High

### Location
`frontend/components/screens/Home.tsx:126`; `Analytics.tsx:179`; `Subjects.tsx:150`.

### Description
Every "past paper" row across Home (recent papers), Analytics (session log), and Subjects (recent attempts) has `onClick={() => go("marking")}` but **never sets `session.paperId`** to the clicked paper. Marking renders whatever paper is currently in `session.paperId` (the last *timed* paper), or an empty state if none.

### Expected Behavior
Clicking a specific past paper should open that paper for review/marking.

### Actual Behavior
Clicking any past paper navigates to Marking showing an unrelated paper (the last one started in the Timer) or "No paper selected for marking." The click target implies navigation to that paper but does something else.

### Evidence
`Home.tsx:126`: `<div ... onClick={() => go("marking")}>` — `p.paper_id`/`p.session_id` are available on the row but unused for navigation.

### Impact
A core review flow is broken: users cannot open a previously-completed paper from any of the three places that list them. Worse, combined with LOGIC-004/LOGIC-020, marking in the wrong context can attach attempts to a mismatched session.

### Recommended Fix
On row click, set `session.setPaperId(p.paper_id)` (and clear/sets the relevant `sessionId`) before `go("marking")`, or route to a read-only review of that session.

### Confidence
High

---

## LOGIC-006

### Severity
High

### Location
`backend/main.py:641-679` (`_examiner_traps`), specifically the early return at line 657-658.

### Description
`_examiner_traps` selects raw rows with keys `description, topic, subject, module_code, frequency`. When there are weak topics it maps them to the contract shape `{text, topic, subject, freq}`. But the early-return path when `weak` is empty returns the **raw rows unmapped**: `if not weak: return traps[:limit]`.

### Expected Behavior
`examiner_traps` items always have `{text, topic, subject, freq}` as declared by `ExaminerTrap` in `frontend/lib/types.ts`.

### Actual Behavior
When no weak topics exist (e.g., LOGIC-001 makes `weak` empty *always*, since it reads `spaced_repetition_items`), the API returns objects with `description`/`module_code`/`frequency` instead of `text`/`freq`. The frontend reads `t.text` (undefined → blank) and `t.freq` (undefined).

### Evidence
`backend/main.py:647-658`:
```py
traps = _query(DB_EXAMINER, "SELECT description, topic, subject, module_code, frequency ...")
if not weak:
    return traps[:limit]          # <-- wrong shape
```
Consumed at `Home.tsx:217` (`{t.text}`), `Briefing.tsx:92`, `Weaknesses.tsx:52`.

### Impact
Examiner traps render with empty text and "seen undefined×" on the Home dashboard, Briefing, and Weakness centre — broken, low-trust UI. Note this path is currently *always* taken because of LOGIC-001.

### Recommended Fix
Map the early-return rows through the same `{text, topic, subject, freq}` transformation used in the main return.

### Confidence
High

---

## LOGIC-007

### Severity
High

### Location
`frontend/components/shell/Sidebar.tsx:100`.

### Description
The sidebar footer renders a hardcoded, fabricated grade summary: `Physics A · Maths A* · Chem B`. These are not derived from any API data.

### Expected Behavior
Per CLAUDE.md ("Never display fake data"; Data Integrity is principle #1), any grades shown must come from `predicted_grades`/`subject_mastery`, or not be shown.

### Actual Behavior
Fixed fake grades are always displayed on every screen, regardless of the user's real performance.

### Evidence
`Sidebar.tsx:100`: `<div className="aos-foot-grades">Physics A · Maths A* · Chem B</div>`

### Impact
Directly misleads the user with invented grades on a persistent UI element. Contradicts the rest of the app's "every number from a real query" claim (Analytics subtitle).

### Recommended Fix
Either remove the footer grade line or populate it from `getDashboard().predicted_grades`, with an honest placeholder when empty.

### Confidence
High

---

## LOGIC-008

### Severity
High

### Location
`frontend/components/screens/Home.tsx:22-26, 51-60`; `backend/main.py:472-485` (`_recent_papers(limit=5)`); compare `Analytics.tsx:41-43`.

### Description
Home derives "Papers completed" and "Average score" from `recent_papers`, which the backend caps at **5** rows. Analytics derives the same "Average score" from `analytics.score_trend` (up to 30 completed sessions). The two screens label these the same but compute them over different populations.

### Expected Behavior
"Papers completed" should reflect the true number of marked papers; "Average score" should be consistent across screens (or clearly scoped).

### Actual Behavior
- "Papers completed" on Home can never exceed 5 and excludes any paper where `available == 0`.
- "Average score" on Home (mean of ≤5 recent papers) differs numerically from "Average score" on Analytics (mean of ≤30 sessions) for the same user.

### Evidence
`Home.tsx:23` `const completedPapers = d.recent_papers.filter((p) => p.pct != null);` where `recent_papers` is `_recent_papers(limit=5)`. `Analytics.tsx:42` averages `a.score_trend`.

### Impact
Headline KPIs are wrong/inconsistent — a student with 20 marked papers sees "Papers completed: 5," and the same "Average score" metric shows two different values on two screens.

### Recommended Fix
Add a dedicated total-completed count and an all-papers average to the dashboard payload (separate from the 5-row "recent" list), and compute Home/Analytics averages from the same source.

### Confidence
High

---

## LOGIC-009

### Severity
Medium

### Location
`backend/main.py:703` (`_question_of_day`); also `frontend/components/screens/QuestionReview.tsx:55` (`DIFFICULTY[q.difficulty]`).

### Description
`difficulty` is mapped to a label via fixed-length array indexing:
```py
["", "Recall", "Standard", "Multi-step", "Advanced", "Trap"][qod["difficulty"]]
```
The schema constrains `difficulty BETWEEN 1 AND 5`, but if any ingested row has `difficulty` `NULL`, `0`, or `>5` (e.g., from a buggy extractor), this raises `IndexError`/`TypeError`. Because this runs inside `get_dashboard`, the **entire dashboard returns HTTP 500**.

### Expected Behavior
An unexpected difficulty value should degrade gracefully (e.g., blank label), never 500 the dashboard.

### Actual Behavior
Out-of-range or NULL difficulty crashes `/api/dashboard`; the Home/Briefing/Subjects/University screens all show "Could not load data."

### Evidence
`backend/main.py:703`. The frontend has the analogous `DIFFICULTY[q.difficulty]` at `QuestionReview.tsx:55` and the difficulty badge at `:55`, which would render `undefined` for out-of-range values.

### Impact
A single malformed question takes down every dashboard-backed screen. Indexer crashes are also unhandled (no try/except around `_question_of_day` in `get_dashboard`).

### Recommended Fix
Guard the index: `labels[d] if isinstance(d, int) and 0 <= d < len(labels) else ""`, and wrap optional dashboard sections so one failing section doesn't 500 the whole endpoint.

### Confidence
Medium

---

## LOGIC-010

### Severity
Medium

### Location
`frontend/components/screens/Settings.tsx:31, 43, 52, 56-66`.

### Description
The Settings screen presents editable controls that are not wired to any persistence:
- "Name" is an `<input defaultValue="Mouad Maamma">` — hardcoded and never saved.
- "Exam session" is a static badge "June 2026".
- "Telegram briefing time" is local `useState` only; never sent to the backend (`BRIEFING_TIME` lives in env).
- "Spaced-repetition reminders", "Examiner-trap alerts", "Review difficult items first" toggles are cosmetic (`<Toggle on />`, no `onChange`/persistence).

### Expected Behavior
Either the controls persist real settings, or they are clearly read-only/disabled.

### Actual Behavior
Users can change settings that silently do nothing — a classic "silent failure with no feedback." The displayed name/exam session are hardcoded placeholders.

### Evidence
`Settings.tsx:43` `<input className="aos-input" defaultValue="Mouad Maamma" />`; toggles at `:64-65, :70` have no handlers.

### Impact
Misleads users into thinking preferences are saved (briefing time, reminders), and shows fake profile data. Low data-integrity, erodes trust.

### Recommended Fix
Wire controls to a settings endpoint, or mark them disabled/"coming soon." Replace hardcoded profile values with real data or honest placeholders.

### Confidence
High

---

## LOGIC-011

### Severity
Medium

### Location
`frontend/components/screens/Marking.tsx:113-122` (`time_seconds: 0`); `frontend/components/screens/Timer.tsx:179-185` (`logQuestionTime`); `backend/main.py` `question_times` vs `attempts`.

### Description
The Timer records per-question time into `question_times`, but Marking submits each attempt with `time_seconds: 0` hardcoded. The two are never reconciled — `attempts.time_seconds` is always 0, and `question_times` is never joined back into anything user-facing.

### Expected Behavior
Per-question attempt time should reflect the time actually spent (from the Timer), and be visible (e.g., in Question Review "last attempt").

### Actual Behavior
Every attempt stores 0 seconds. `QuestionReview` previous-attempt data carries `time_seconds: 0`. The captured `question_times` data is orphaned.

### Evidence
`Marking.tsx:120`: `time_seconds: 0,`. `Timer.tsx:182`: `logQuestionTime(sid, qs[cur].id, { time_seconds: qTimes[cur], status })`.

### Impact
Time-on-question analytics are impossible; a feature that appears to work (timing is logged) produces no usable result. Minor but contradicts the "real data" promise.

### Recommended Fix
On marking, look up the logged `question_times` for the session/question and submit it as `time_seconds`, or have the backend derive attempt time from `question_times`.

### Confidence
High

---

## LOGIC-012

### Severity
Medium

### Location
`frontend/components/charts/index.tsx:238-242` (`ScatterChart`), used by `Analytics.tsx:133`.

### Description
The "Time vs score" scatter chart hardcodes the y-axis to `min: 40, max: 100`. Any paper scored below 40% plots off the bottom of the chart (clipped/invisible).

### Expected Behavior
All marked papers should appear; the axis should start at 0 (or auto-scale).

### Actual Behavior
A student's weakest papers (<40%) — arguably the most important to see — silently disappear from the scatter plot.

### Evidence
`charts/index.tsx:240`: `y: { ... min: 40, max: 100, ... }`.

### Impact
Misleading visualization that omits low scores without indication; users may believe all their papers are ≥40%.

### Recommended Fix
Set `min: 0` (or omit `min` to auto-scale).

### Confidence
High

---

## LOGIC-013

### Severity
Medium

### Location
`backend/main.py:596` (`_subject_mastery`), `:634` (`_predicted_grades`).

### Description
"Predicted grade" is computed as `_grade_from_mastery(min(1.0, mastery + 0.10))` — a flat +10 percentage-point bump applied uniformly, independent of score trend, attempt count, or recency. Confidence is derived solely from attempt count.

### Expected Behavior
A "predicted grade" presented to a student should reflect a defensible projection (trend, recent performance, coverage), not a constant offset.

### Actual Behavior
Predicted grade is always "current mastery + 10%," so it is essentially a relabeled current grade and frequently overstates the outcome (and the University Readiness screen presents it as the basis for university decisions).

### Evidence
`backend/main.py:596`: `"predicted_grade": _grade_from_mastery(min(1.0, mastery + 0.10))`.

### Impact
Misleading core metric shown prominently (Home headline, Subjects, University). Overstates readiness; affects high-stakes decisions.

### Recommended Fix
Replace the flat bump with a model using `score_trend`/attempt history, or relabel honestly (e.g., "Projected (mastery + buffer)") and disclose the assumption.

### Confidence
Medium

---

## LOGIC-014

### Severity
Medium

### Location
`backend/main.py:1136-1147` (`/api/briefing`); `frontend/lib/api.ts:117` (`getBriefing` unused); `frontend/components/screens/Briefing.tsx`.

### Description
The backend exposes `/api/briefing` returning the 4-section generated briefing (academic intelligence, curriculum progress, adaptive revision, system status) from `briefing.generator`. The frontend `Briefing` screen never calls it; it reconstructs a briefing from `getDashboard()` + `getCoverage()` instead. `getBriefing`/`BriefingData` are dead.

### Expected Behavior
Either the generated briefing content is shown, or the unused endpoint/types are removed to avoid two divergent "briefing" definitions.

### Actual Behavior
Two parallel, divergent briefing implementations exist; the richer generated one (misconceptions per subject, curriculum coverage %, revision packs) is never seen by the user.

### Evidence
`Briefing.tsx:11-12` uses `getDashboard`/`getCoverage`; no import of `getBriefing`.

### Impact
Contradictory sources of truth for "the briefing," and the documented Telegram-style briefing content is invisible in the UI. Maintenance hazard.

### Recommended Fix
Pick one source of truth: render `/api/briefing` in the Briefing screen, or remove the endpoint/types.

### Confidence
High

---

## LOGIC-015

### Severity
Low

### Location
`backend/main.py:712-728` (`_streak`).

### Description
Streak counts distinct days that have a row in `sessions`. A `sessions` row is created the moment a paper is *started* in the Timer (`create_session`), not when work is completed. Opening the Timer (which auto-creates a session on paper load) is enough to count the day.

### Expected Behavior
A study streak should count days with genuine study activity (e.g., a completed session or at least one marked attempt).

### Actual Behavior
Merely opening a paper in the Timer — even abandoning it immediately — increments the streak for that day.

### Evidence
`Timer.tsx:124` creates a session as soon as `data` loads; `_streak` counts any `sessions.started_at` day.

### Impact
Inflated/gameable streak; minor trust issue.

### Recommended Fix
Count streak from completed sessions (`ended_at IS NOT NULL`) or from attempt activity.

### Confidence
Medium

---

## LOGIC-016

### Severity
Low

### Location
`frontend/components/screens/Home.tsx:35`.

### Description
The greeting is hardcoded `Good morning, Mouad.` regardless of the actual time of day or user.

### Expected Behavior
Greeting should reflect time of day (and ideally the configured user name).

### Actual Behavior
Says "Good morning" at all hours; name is fixed.

### Evidence
`Home.tsx:35`: `<h1>Good morning, Mouad.</h1>`

### Impact
Minor polish/credibility issue; "good morning" at 11pm reads as broken.

### Recommended Fix
Compute greeting from local time; source the name from settings/profile.

### Confidence
High

---

## LOGIC-017

### Severity
Low

### Location
`frontend/components/screens/Subjects.tsx:11`.

### Description
The Subjects screen initializes `active = "physics"`. If Physics has no `subject_mastery` row (but other subjects do), `s` is undefined and the screen shows "No syllabus data for this subject" until the user manually clicks another tab.

### Expected Behavior
Default to the first subject that actually has data.

### Actual Behavior
Possible misleading empty state on load even when data exists for other subjects.

### Evidence
`Subjects.tsx:11`: `const [active, setActive] = useState("physics");` then `:22` `const s = subjectList.find((x) => x.subject_id === active);`

### Impact
Minor confusing first render.

### Recommended Fix
Initialize `active` to `subjectList[0]?.subject_id` once data loads.

### Confidence
Medium

---

## LOGIC-018

### Severity
Low

### Location
`backend/main.py:166-178` (`days_ago` in `get_papers`), `:712-728` (`_streak`).

### Description
Sessions are stored with UTC ISO timestamps (`datetime.now(timezone.utc)`), but `days_ago` and the streak compare against `date.today()` (server local time) and `DATE('now')` (SQLite UTC). Mixing UTC and local dates produces off-by-one results near midnight.

### Expected Behavior
Day-difference calculations should use a single, consistent timezone (the student's).

### Actual Behavior
"X days ago" and streak day boundaries can be off by one depending on server timezone and time of day.

### Evidence
`backend/main.py:764` stores UTC; `:175` `started = datetime.fromisoformat(...).date(); days_ago = (today - started).days` with `today = date.today()`.

### Impact
Minor inaccuracy in relative dates and streaks.

### Recommended Fix
Standardize on the user's timezone for all day-boundary math.

### Confidence
Medium

---

## LOGIC-019

### Severity
Low

### Location
`backend/main.py:538` (`weak_topics` unused), `:929`/`AttemptResult.grade_contribution` (unused).

### Description
`_subject_mastery` computes `weak_topics` per unit (`SUM(CASE WHEN mastery < 0.4 ...)`) but never includes it in the returned `units` objects. `create_attempt` returns `grade_contribution` (a per-question grade from mastery bands), which the frontend never displays.

### Expected Behavior
Either expose/display these values or remove the dead computation.

### Actual Behavior
Wasted computation and an unused, semantically dubious field (`grade_contribution` applies mastery bands to a single question's percentage).

### Evidence
`backend/main.py:538`, `:589-598` (no `weak_topics` in output); `:929`.

### Impact
Maintainability/clarity only.

### Recommended Fix
Remove or surface intentionally.

### Confidence
High

---

## LOGIC-020

### Severity
Low

### Location
`backend/main.py:884-919` (`create_attempt`).

### Description
`create_attempt` validates that the question exists and (if provided) the session exists, but does **not** verify the question actually belongs to the session's paper. Combined with LOGIC-005 (navigating to Marking without updating `paperId`/`sessionId`), an attempt for one paper's question can be recorded against a session for a different paper.

### Expected Behavior
An attempt's question should belong to the paper of its session.

### Actual Behavior
Mismatched session/question pairs are accepted silently, corrupting per-session score aggregation.

### Evidence
`backend/main.py:895-898` only checks session existence, not paper membership.

### Impact
Potential cross-paper contamination of session scores; low likelihood in normal use but enabled by LOGIC-005.

### Recommended Fix
When `session_id` is provided, verify the question's `paper_id` matches the session's `paper_id`; reject with 422 otherwise.

### Confidence
Medium

---

## LOGIC-021

### Severity
**High**

### Location
`frontend/components/screens/Timer.tsx:14` (`OFFICIAL_DEFAULT = 90 * 60`), `:117-118` (`official`/`target`), `:124-128` (`createSession`). Consumed by `backend/main.py:191-192` (`get_papers` time/target), `_recent_papers:515-516`, and rendered in `Analytics.tsx:177,187-189`, `Subjects.tsx:148,159-160`, `Home.tsx:122-140`.

### Description
The Timer hardcodes the official exam duration to **90 minutes for every paper**, and derives the target as a flat two-thirds (`60 minutes`). These values are written into the session (`official_time_seconds`, `target_time_seconds`) and then used everywhere to compute "vs target" deltas and the pace indicator. Real Edexcel/Cambridge IAL papers have materially different durations (e.g., many Physics/Chemistry units are 75–105 min; Maths papers 90 min; FP papers 90 min), and there is no per-paper duration in the question bank or any UI to set it.

### Expected Behavior
Each paper's official time (and therefore target) should reflect that paper's real exam length, so pace tracking and "vs target" deltas are meaningful.

### Actual Behavior
- The "two-thirds rule" badge and the timer's "Target 60 min" are identical for every paper regardless of its true length.
- The pace status ("On pace"/"At risk"/"Over time") flips at 60/90 min for all papers — wrong for any paper not 90 min long.
- The "Δ" / "vs target" columns in Analytics and Subjects compare against a constant 60 min, so the numbers misrepresent whether the student was actually fast or slow.

### Evidence
`Timer.tsx:14`: `const OFFICIAL_DEFAULT = 90 * 60;`
`Timer.tsx:117-118`: `const official = OFFICIAL_DEFAULT; const target = Math.round(official * (2 / 3));`
These are passed verbatim to `createSession`, persisted, and later surfaced as `target` in `/api/papers`.

### Impact
A headline feature (exam-condition timing with pace analysis) produces misleading results for the majority of papers. A student is told they were "over time" or "on pace" against a duration their exam does not have. Violates Educational Accuracy.

### Recommended Fix
Store an official duration per paper (in the question bank / papers table) and seed it from the syllabus; have the Timer read it instead of a constant. Until then, prompt the user for the paper's official time rather than assuming 90 min.

### Confidence
High

---

## LOGIC-022

### Severity
Medium

### Location
`backend/main.py:472-485` (`_recent_papers` query — no `ended_at` filter), consumed by `Home.tsx:23-26` (`completedPapers`/`avgScore`). Contrast `get_papers:158` and `get_analytics:1164`, which both filter `WHERE s.ended_at IS NOT NULL`.

### Description
`_recent_papers` selects sessions with `FROM sessions s ORDER BY s.started_at DESC LIMIT ?` and **no `ended_at IS NOT NULL` filter**. Every other session aggregation in the codebase restricts to completed sessions. Home then treats any recent paper with a non-null `pct` (i.e., any session that has at least one marked attempt, even if never completed) as a "completed paper," counts it, averages it, and shows its grade.

### Expected Behavior
"Recent papers" / "Papers completed" / "Average score" on Home should be drawn from the same population as Analytics — completed, marked sessions — so the numbers agree.

### Actual Behavior
- An in-progress session (paper started, a few questions marked, never finished) appears in Home's "Recent papers" with a score and grade.
- It is counted in "Papers completed" and folded into "Average score," while Analytics (which requires `ended_at`) excludes it — so the two screens disagree, on top of LOGIC-008.
- The row's `completed: false` flag is computed but Home ignores it.

### Evidence
`backend/main.py:480-484`:
```py
FROM sessions s
ORDER BY s.started_at DESC
LIMIT ?
```
No `WHERE s.ended_at IS NOT NULL`, unlike `get_papers`/`get_analytics`.

### Impact
Headline KPIs on the landing screen count and average unfinished papers, inconsistent with the rest of the app. Erodes trust in the dashboard numbers.

### Recommended Fix
Add `WHERE s.ended_at IS NOT NULL` to `_recent_papers` (or have Home filter on the `completed` flag it already receives) so all session metrics share one definition of "completed."

### Confidence
High

---

## LOGIC-023

### Severity
Medium

### Location
`frontend/components/screens/Marking.tsx:74-78` (`scored`, `possibleSoFar`, `pct`, `liveGrade`); rendered at `:161-165` and the sticky bar `:319-325`.

### Description
The "Live grade" badge is `gradeFromPct(pct)` where `pct = round(scored / possibleSoFar * 100)` and `possibleSoFar` is **only the marks of questions already marked** (`awarded[x.id] == null ? 0 : x.marks`). So the grade is a percentage of the marked subset, not of the paper. Meanwhile the score readout shows `scored / maxMarks` (whole-paper denominator), so the two displayed figures use different denominators.

### Expected Behavior
A grade shown for a paper should be relative to the paper's total (or clearly labelled as provisional/partial), and should not read as a final grade after a single question.

### Actual Behavior
After marking just the first (easy) question fully correct, the page shows "Live grade A* · 100%" for the whole paper, while the score reads e.g. "4 / 72." The grade swings wildly as marking proceeds and only becomes meaningful at the last question.

### Evidence
`Marking.tsx:75-78`:
```ts
const possibleSoFar = qs.reduce((a, x) => a + (awarded[x.id] == null ? 0 : x.marks), 0);
const pct = possibleSoFar > 0 ? Math.round((scored / possibleSoFar) * 100) : 0;
const liveGrade = gradeFromPct(pct);
```

### Impact
Misleading grade prominently displayed (header and sticky footer) during marking; a student could believe they are scoring an A* when most of the paper is unmarked.

### Recommended Fix
Either label it explicitly as "provisional (marked so far)," or compute the grade against `maxMarks` once all questions are marked and show "—"/percentage-marked progress until then.

### Confidence
High

---

## LOGIC-024

### Severity
Medium

### Location
`frontend/components/screens/Marking.tsx:50-53` (question filter), `:119` (`marks_available: q.marks`); `backend/main.py:823` (`marks_available: int = Field(gt=0)`), `:893-894`.

### Description
Marking includes any question where `q.marks > 0` **or** `(q.question_text ?? "").length > 20`. A question that was extracted with `marks = 0` but has body text passes the filter and is shown with a single "0" marks-awarded button. Saving it sends `marks_available: 0`, which the backend's `AttemptCreate` model rejects (`marks_available` must be `> 0`) → HTTP 422.

### Expected Behavior
Either zero-mark/unscored questions are not presented as markable, or the app records them without erroring.

### Actual Behavior
The user can select the only option (0), click "Save & next," and gets "Save failed: API 422: …" with no actionable explanation. The question cannot be marked (only skipped).

### Evidence
`Marking.tsx:51`: `.filter((q) => q.marks > 0 || (q.question_text ?? "").length > 20)`
`Marking.tsx:119`: `marks_available: q.marks,`
`backend/main.py:823`: `marks_available: int = Field(gt=0)`

### Impact
Silent-ish failure with a cryptic error on a core flow for any paper containing a 0-mark extracted question (common with imperfect OCR/extraction). Low-trust dead end.

### Recommended Fix
Exclude `marks <= 0` questions from the markable set (or render them read-only), and surface a human-readable message instead of the raw 422 string.

### Confidence
High

---

## LOGIC-025

### Severity
Low

### Location
`backend/main.py:1082-1129` (`get_coverage`): `total_questions` from a `WHERE p.paper_type = 'question_paper'` query (`:1092`) vs `attempted` counted with **no `paper_type` filter** (`:1100-1114`). Surfaced in `Briefing.tsx:115-125` and `Analytics.tsx:71-72`.

### Description
`total_questions` per subject counts only questions belonging to `paper_type = 'question_paper'`. The attempted count, however, is derived from `DISTINCT question_id` in `attempts` joined to questions with no paper-type restriction. If any attempt references a question on a non-`question_paper` paper (specimen, sample, mark-scheme-attached, etc.), `attempted` can exceed `total_questions`, yielding `pct = round(attempted / total_q * 100) > 100`.

### Expected Behavior
Coverage percentage is bounded 0–100 and compares like with like (attempted question-paper questions ÷ total question-paper questions).

### Actual Behavior
Coverage can render e.g. "112%" in the Briefing coverage bar and skew the Analytics "% of bank" metric.

### Evidence
`backend/main.py:1092` (`WHERE p.paper_type = 'question_paper'`) vs `:1100` (`SELECT DISTINCT question_id FROM attempts`) and `:1106-1112` (no `paper_type` filter on the attempted-count join).

### Impact
Implausible >100% values undermine trust in the coverage figure; minor because most papers are `question_paper`.

### Recommended Fix
Apply the same `paper_type = 'question_paper'` filter to the attempted-count join, and/or clamp `pct` to 100.

### Confidence
Medium

---

## LOGIC-026

### Severity
Low

### Location
`frontend/lib/data.ts:15-16` (`masteryBand`: 80/50); `frontend/components/screens/Briefing.tsx:120` (coverage band: 60/40); `Home.tsx:184-188` (legend states >80 / 50–80 / <50); `Subjects.tsx:79,96` (unit bars via `masteryBand`).

### Description
The app colours progress bars green/amber/red using two different threshold sets for visually identical bars. `masteryBand` (used by Home heatmap, Subjects units/topics) splits at **80/50**, and the Home legend documents that. The Briefing "Coverage summary" bars split at **60/40**. A 65% bar is therefore amber in one place and green in another.

### Expected Behavior
Either one consistent banding scale, or clearly distinct visual treatments with labelled thresholds when two different metrics (mastery vs coverage) are intentionally banded differently.

### Actual Behavior
Identical-looking bars imply identical meaning but use different cut-offs across screens, so the same percentage shows a different colour/severity depending on the screen.

### Evidence
`data.ts:16`: `return m >= 80 ? "green" : m >= 50 ? "amber" : "red";`
`Briefing.tsx:120`: `band={c.pct >= 60 ? "green" : c.pct >= 40 ? "amber" : "red"}`

### Impact
Inconsistent visual signalling; low severity but contradicts the otherwise-consistent design language.

### Recommended Fix
Centralise band thresholds (per metric type) in `lib/data.ts` and reuse them; if coverage is intentionally banded differently from mastery, label the thresholds so the difference is explicit.

### Confidence
Medium

---

## Cross-Cutting Observations

- **Silent failure pattern.** `_query`/`_scalar` (`backend/main.py:56-73`) swallow all `sqlite3.Error`s and return empty/zero. This converts schema/infrastructure bugs (LOGIC-001) into invisible "empty data," defeating the app's own honesty goal. Recommend distinguishing "missing table/setup error" from "no rows."
- **Two grade systems / two briefing systems.** LOGIC-003 and LOGIC-014 are both symptoms of duplicated, divergent sources of truth between backend and frontend. Consolidate.
- **Documentation drift.** RESTART.md describes a `spaced_repetition_items` table with 94 SM-2 rows that does not exist in code (LOGIC-001). Docs should match the shipped schema.

## Verification Performed
- Reproduced LOGIC-001 at runtime (init + seed → table absent → API query raises `no such table`).
- Statically traced every endpoint's output shape against `frontend/lib/types.ts` and each screen's consumption.
- Cross-checked all backend SQL table/column names against `schemas/*.sql` (markscheme, examiner, attempts, question_bank all match; **progress** does not — see LOGIC-001).

### Re-audit pass — 2026-06-15 (branch `claude/vigilant-lovelace-oa3mmq`)
- Re-confirmed LOGIC-001's root cause directly in `db/seed_syllabus.py` + `schemas/progress.sql` + `db/models.py`: the seeder only populates the normalized tree (`subjects → modules → topics → subtopics → specification_points`) and `progress.sql` defines no `spaced_repetition_items` table, while `backend/main.py` (11 sites) and `briefing/generator.py` (`get_due_review_items`, `select_question_of_the_day`) query `spaced_repetition_items` (and a flat `unit` column that the normalized schema also lacks). Every such query fails silently via `_query`/`_scalar`.
- Re-verified all hardcoded/fake-data findings exist verbatim: `Sidebar.tsx:99-100` (`Mouad Maamma`, `Physics A · Maths A* · Chem B`), `Home.tsx:35` greeting, `Settings.tsx:43,51` (`Mouad Maamma`, `June 2026`), `Subjects.tsx:11` (`useState("physics")`), `charts/index.tsx:240` (`min: 40`), `QuestionReview.tsx:55` (`DIFFICULTY[q.difficulty]`).
- New issues this pass: **LOGIC-021** (hardcoded 90-min official time for all papers), **LOGIC-022** (`_recent_papers` omits the `ended_at IS NOT NULL` filter that every other session query uses), **LOGIC-023** (Marking live grade uses a partial denominator), **LOGIC-024** (zero-mark questions are markable but 422 on save), **LOGIC-025** (coverage can exceed 100%), **LOGIC-026** (inconsistent colour-band thresholds).
