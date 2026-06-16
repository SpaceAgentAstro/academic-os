# AcademicOS — Logic Error Audit

**Audit date:** 2026-06-16
**Scope:** Full codebase — FastAPI backend (`backend/main.py`), briefing generator, all agents (`agents/**`), ingestion pipeline (`ingestion/**`), scripts (`scripts/**`), database schemas/seeders (`schemas/**`, `db/**`), configuration (`config/**`, `vercel.json`, `.env*`), and the Next.js frontend (`frontend/**` — screens, shell, charts, ui, lib/hooks).
**Objective:** Identify every logic error that negatively affects real-world usability from the client's perspective.

**Method:** Static trace of every data flow SQLite → FastAPI → frontend fetch hooks → rendered components, cross-checking schemas against queries and backend output shapes against the TypeScript types in `frontend/lib/types.ts`. Critical findings were **reproduced at runtime** (see evidence in LOGIC-001, LOGIC-002, LOGIC-009).

> ⚠️ **Headline correction vs. prior audits:** earlier notes claimed the missing `spaced_repetition_items` table caused the dashboard to "load successfully but empty." Runtime reproduction shows it is worse — **`GET /api/dashboard` raises an uncaught `OperationalError` and returns HTTP 500**, because `get_due_review_items` bypasses the `_query` safety wrapper. Every dashboard-backed screen (Home, Briefing, Subjects, University) shows the error state, not empty data. See LOGIC-001.

---

## Summary Table

| ID | Severity | Area | One-line |
|----|----------|------|----------|
| LOGIC-001 | **Critical** | DB / backend | `spaced_repetition_items` is queried in 13 places but created/seeded nowhere → `/api/dashboard` returns **HTTP 500**, briefing send crashes |
| LOGIC-002 | **Critical** | Config / deploy | Frontend API URL defaults to `localhost:8000`; backend CORS allows only localhost → deployed app is fully non-functional |
| LOGIC-003 | **Critical** | Briefing crash | `briefing/generator.py` due-items / QotD calls are outside any try/except → the entire Telegram briefing aborts before sending |
| LOGIC-004 | **High** | Examiner traps | `_examiner_traps` early-return path emits the wrong object shape → trap text/freq render blank **on every dashboard** (path always taken) |
| LOGIC-005 | **High** | Grades | Backend (`A*/A/B/C/U`, mastery bands) and frontend (`A*/A/B/C/D/E`, pct) disagree → same paper shows different grades on different screens |
| LOGIC-006 | **High** | Marking | Re-marking inserts a duplicate attempt (no upsert) → inflated counts, scores can exceed paper total |
| LOGIC-007 | **High** | Navigation | Clicking any past/recent paper opens Marking for the *currently-loaded* paper, not the clicked one |
| LOGIC-008 | **High** | Navigation | "Practise now / this topic / this paper" buttons go to Timer without selecting the paper/topic |
| LOGIC-009 | **High** | Seeding | `seed_all()` populates the syllabus tree but leaves `syllabus_completion` empty → curriculum coverage permanently 0% even after documented setup |
| LOGIC-010 | **High** | Fake data | Sidebar footer hardcodes `Physics A · Maths A* · Chem B`; Home greeting hardcodes `Good morning, Mouad.` |
| LOGIC-011 | **High** | Settings | Profile name / exam session hardcoded; all toggles + briefing time silently never persist |
| LOGIC-012 | **High** | Marking | "Live grade" uses a partial denominator → shows A*/100% after one correct question |
| LOGIC-013 | **High** | Charts | Scatter chart y-axis hardcoded `min: 40` → every paper below 40% is clipped/invisible |
| LOGIC-014 | **High** | Curriculum | "SM-2" is a fixed lookup ladder; intervals never grow, ease factor unused |
| LOGIC-015 | **High** | Curriculum | Normal progression never sets `next_review` → review queue stays empty even with the correct schema |
| LOGIC-016 | **High** | Delivery | `briefing --send-now` imports a non-existent `TelegramAgent` class → `ImportError` |
| LOGIC-017 | **High** | Delivery | Bot commands send legacy `Markdown` with unescaped OCR text and no fallback → Telegram HTTP 400 |
| LOGIC-018 | **High** | Ownership | Backend reads/writes progress.db SR state directly, violating Curriculum-Agent sole-writer rule |
| LOGIC-019 | **High** | Aggregation | Home "Papers completed" caps at 5; "Average score" computed over a different population than Analytics |
| LOGIC-020 | **High** | Ingestion | Question-start regex over-splits on `\d{1,2}\s+[A-Z]` → fabricated/duplicate questions, wrong marks |
| LOGIC-021 | **High** | Ingestion | Markscheme line regex drops `B1`, `A1ft`, `A1cao`, `M1*` etc. → whole mark entries silently lost |
| LOGIC-022 | **High** | Ingestion | Observation topic/subtopic hardcoded `None` → all misconceptions collapse to "General" |
| LOGIC-023 | **High** | Ingestion | `paper_code` = filename stem; session falls back to bare year → duplicate papers, wrong dedup key |
| LOGIC-024 | **High** | Markscheme | `_find_question_id` exact-match drops MS entries on suffix mismatch (`1a` vs `1`) |
| LOGIC-025 | **High** | Examiner | Re-ingest duplicates observations and inflates misconception `frequency` every run |
| LOGIC-026 | **High** | Diagrams | `classify_diagram` keys on filenames the pipeline never produces → every diagram "other" |
| LOGIC-027 | **High** | Scripts | 330-day paper-match window + absolute fallback → mark scheme/examiner report attaches to the wrong sitting |
| LOGIC-028 | Medium | Backend | `_recent_papers` includes in-progress sessions and shows a partial score/grade as if final |
| LOGIC-029 | Medium | Prediction | "Predicted grade" = mastery + flat 0.10; "best prediction" = subject with most attempts |
| LOGIC-030 | Medium | Briefing UI | `/api/briefing` + `getBriefing`/`BriefingData` are dead; Briefing screen rebuilds from other endpoints |
| LOGIC-031 | Medium | Attempts | `submitAttempt` always sends `time_seconds: 0`; captured per-question times never linked |
| LOGIC-032 | Medium | Timer | Official exam length hardcoded to 90 min for every paper → wrong pace/target everywhere |
| LOGIC-033 | Medium | Timer | "Finished paper" only logs the current question → later questions get no timing rows |
| LOGIC-034 | Medium | Analytics | Calibration bars colored by raw score, not confidence-vs-score deviation → misleads about calibration |
| LOGIC-035 | Medium | Analytics | Paper library header says "N papers" but only 50 rows render, with no "showing 50 of N" |
| LOGIC-036 | Medium | Subjects | Default active subject hardcoded `physics` → empty-state flash if Physics has no data |
| LOGIC-037 | Medium | Curriculum | "Coverage %" counts only `reviewed`+`mastered`, excluding `taught`/`in_progress` → understates progress |
| LOGIC-038 | Medium | Curriculum | `review_history` table defined but never written → no outcome audit trail |
| LOGIC-039 | Medium | Retrieval | `get_weak_topics` filters by `computed_at`, ignoring each row's own `window_days` |
| LOGIC-040 | Medium | Ingestion | OCR re-parses the whole PDF per scanned page (O(n²)); examiner text OCR'd twice |
| LOGIC-041 | Medium | Ingestion | `_normalise_mark_type` defaults unknown tokens to "M"; `_extract_marks` returns last bracket not total |
| LOGIC-042 | Medium | Ingestion | `classify_difficulty` averaging + rounding mis-scores; command-word matched mid-question |
| LOGIC-043 | Medium | Ingestion | `classify_topic` fallback writes `module_code` into `question_topics.topic` |
| LOGIC-044 | Medium | Diagrams | `_write_diagram` trusts `lastrowid` on the ON CONFLICT UPDATE path → links to wrong diagram |
| LOGIC-045 | Medium | Misconception | Interventions pass "General" topic to `get_questions` → no practice questions returned |
| LOGIC-046 | Medium | Backend | Confidence calibration / weakness aggregation skewed by duplicate attempts (see LOGIC-006) |
| LOGIC-047 | Low | Streak | Streak counts *started* sessions → merely opening the Timer inflates the streak |
| LOGIC-048 | Low | Time zones | UTC-stored timestamps compared against local `date.today()` → off-by-one near midnight |
| LOGIC-049 | Low | Backend | `_question_of_day` difficulty index unguarded (mitigated by schema CHECK 1–5) |
| LOGIC-050 | Low | Dead code/data | `weak_topics`, `grade_contribution`, `ApiPaper.days_ago` computed but never displayed |
| LOGIC-051 | Low | Data integrity | Backend does not verify a submitted attempt's question belongs to the session's paper |
| LOGIC-052 | Low | Routing | No URL routing — refresh/bookmark resets to Home; all cross-screen context lost |
| LOGIC-053 | Low | UX | University / Tutor / Booklet are permanent empty states behind active nav items |
| LOGIC-054 | Low | UX | Subject filter chip lists hardcoded in Timer/Weaknesses → can drift from real subjects |
| LOGIC-055 | Low | Seeding | `seed_syllabus` reports "attempted inserts" not actual; dry-run counts are simulated |
| LOGIC-056 | Low | Config | `DATA_DIR.mkdir(exist_ok=True)` lacks `parents=True`; Telegram config unvalidated at startup |
| LOGIC-057 | Low | Timer | "Official time" marker hardcoded at 66.6% of the progress bar → mispositioned |
| LOGIC-058 | Low | Copy | QuestionReview difficulty label "Examiner trap" ≠ backend QotD label "Trap" |

---

## LOGIC-001

### Severity
**Critical**

### Location
`backend/main.py` — `get_health` (98,101), `_todays_priorities` (432), `_subject_mastery` (529,539,564), `_predicted_grades` (605), `_examiner_traps` (645), `_update_mastery` (847,872), `get_status` (1067), and `_question_of_day` (685) via `briefing/generator.py:get_due_review_items` (35,50) / `select_question_of_the_day` (70). Root cause: `schemas/progress.sql` + `db/models._DB_SCHEMA_MAP` + `db/seed_syllabus.py`.

### Description
The entire progress/mastery/spaced-repetition feature set queries a table named `spaced_repetition_items` (columns `topic, subtopic, unit, subject, due_date, mastery, ease_factor, interval_days, last_reviewed`). **This table is never created anywhere** — not in `schemas/progress.sql`, not by `init_all_databases()`, not by `seed_syllabus.py`. The schema instead defines a normalized tree (`subjects → modules → topics → subtopics → specification_points → syllabus_completion`), and the Curriculum Agent (the documented sole authority) reads/writes `syllabus_completion`, never `spaced_repetition_items`. Two incompatible progress models exist; only one is real.

Crucially, while `_query`/`_scalar` swallow `sqlite3.Error` (returning `[]`/`0`), `briefing/generator.get_due_review_items` uses a raw `conn.execute(...)` with **no error handling**. Because `get_dashboard` unconditionally calls `_question_of_day() → select_question_of_the_day() → get_due_review_items()`, the `OperationalError` propagates and the whole endpoint 500s.

### Expected Behavior
After the documented setup (`init_all_databases()` + `seed_syllabus.py`), the dashboard should return today's priorities, mastery heatmap, subject mastery, predicted grades, examiner traps, and a question of the day from real data.

### Actual Behavior
`GET /api/dashboard` returns **HTTP 500**. Home, Briefing, Subjects, and University all render "Could not load data." `/api/health` reports `progress.topics = 0` and `briefing_ready = false` permanently; `/api/status` shows `progress.db … ok: false`. `_update_mastery` finds no table → every marked attempt returns `new_mastery: null`, so the Marking "mastery now X%" badge never appears.

### Evidence
Reproduced at runtime in this audit:
```
$ DATA_DIR=$(mktemp -d) python -c "init_all_databases(); seed_all(); get_dashboard()"
seeded: subjects 5, modules 31, topics 94, subtopics 148, specification_points 486
progress tables: ['subjects','modules','topics','subtopics',
                  'specification_points','syllabus_completion','review_history', ...]
SRI present? False
Query failed on progress.db: no such table: spaced_repetition_items   (x5, swallowed)
Traceback ... briefing/generator.py:30 get_due_review_items
sqlite3.OperationalError: no such table: spaced_repetition_items      (NOT swallowed → 500)
```
`RESTART.md` line 15 claims *"progress.db: 94 syllabus topics + NEW `spaced_repetition_items` (94 rows, SM-2 state)"* — but no code creates it.

### Impact
The core value proposition — adaptive, spaced-repetition-driven revision with mastery tracking and predicted grades — is entirely non-functional. The main dashboard hard-crashes. This is a release blocker and a contradictory source of truth (normalized schema vs. denormalized queries).

### Recommended Fix
Pick one source of truth. Preferred: rewrite the backend/briefing queries to read SR state through the Curriculum Agent / `syllabus_completion` (`next_review`, `confidence`, `review_count`). Alternative: define and seed `spaced_repetition_items`. Additionally, `get_due_review_items` must use the same defensive error handling as `_query`, and `_query`/`_scalar` should distinguish "table missing" (setup error) from "no rows."

### Confidence
High

---

## LOGIC-002

### Severity
**Critical**

### Location
`frontend/lib/api.ts:15` (`BASE_URL`); `backend/main.py:38-44` (CORS); `.env.example`; `vercel.json`.

### Description
`BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`. No `NEXT_PUBLIC_API_URL` is defined anywhere (no `frontend/.env*`; `.env.example` omits it). The repo deploys the frontend to Vercel (`vercel.json`). Separately, backend CORS allows only `http://localhost:3000` / `:3001`.

### Expected Behavior
A deployed frontend reaches the deployed backend; the backend accepts the production origin.

### Actual Behavior
In production the browser requests `http://localhost:8000` (the user's own machine) → every screen renders `ErrorState`. Even with `NEXT_PUBLIC_API_URL` set, CORS would reject the Vercel origin.

### Evidence
`api.ts:15` `const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";`
`main.py:40` `allow_origins=["http://localhost:3000", "http://localhost:3001"]`

### Impact
The application is completely unusable when deployed — every data-bearing screen errors out.

### Recommended Fix
Set `NEXT_PUBLIC_API_URL` for the deployed environment (document it in `.env.example`); drive `allow_origins` from an env var that includes the production origin(s).

### Confidence
High

---

## LOGIC-003

### Severity
**Critical**

### Location
`briefing/generator.py:178, 189` (calls outside try/except) vs the `try/except` at `:199-215`; consumers `scripts/send_briefing.py`, scheduler.

### Description
In `_section3_adaptive_revision`, only the per-subject `build_revision_pack` loop is wrapped in `try/except`. `get_due_review_items(limit=5)` (178) and `select_question_of_the_day()` (189) are outside it. Given LOGIC-001, both raise `OperationalError`, which propagates through `generate_daily_briefing()` and aborts the whole send — before any Telegram message goes out.

### Expected Behavior
A failing section should degrade gracefully; the briefing should still send with the sections that work.

### Actual Behavior
The entire daily briefing crashes and never sends.

### Evidence
`generator.py:178` `due = get_due_review_items(limit=5)`; `:189` `qod = select_question_of_the_day()` — both before the `try:` at `:199`.

### Impact
The flagship Phase-6 feature (daily Telegram briefing) is fully broken whenever progress.db is involved (i.e., always, per LOGIC-001).

### Recommended Fix
Fix LOGIC-001; additionally wrap each section assembly so one failing section cannot abort the whole briefing.

### Confidence
High

---

## LOGIC-004

### Severity
**High**

### Location
`backend/main.py:641-679` (`_examiner_traps`), specifically the early return at `:657-658`.

### Description
`_examiner_traps` selects raw rows with keys `description, topic, subject, module_code, frequency`. When weak topics exist it maps them to the contract shape `{text, topic, subject, freq}`. But the early-return path when `weak` is empty returns the **raw rows unmapped**: `if not weak: return traps[:limit]`. Because `weak` reads `spaced_repetition_items` (LOGIC-001), `weak` is **always** empty, so this wrong-shape path is **always** taken.

### Expected Behavior
`examiner_traps` items always have `{text, topic, subject, freq}` as declared by `ExaminerTrap` in `frontend/lib/types.ts`.

### Actual Behavior
The API returns objects with `description`/`module_code`/`frequency`. The frontend reads `t.text` (→ blank) and `t.freq` (→ `undefined`).

### Evidence
Reproduced at runtime (one misconception seeded):
```
returned keys: ['description','topic','subject','module_code','frequency']
Frontend reads t.text -> None | t.freq -> None
```
Consumed at `Home.tsx:217` (`{t.text}`, `seen {t.freq}×`), `Briefing.tsx:92-94`, `Weaknesses.tsx:52`.

### Impact
Examiner traps render with empty text and "seen undefined×" on Home, Briefing, and Weakness centre — broken, low-trust UI, present whenever any misconception exists.

### Recommended Fix
Map the early-return rows through the same `{text, topic, subject, freq}` transformation used in the main return.

### Confidence
High

---

## LOGIC-005

### Severity
**High**

### Location
`backend/main.py:76-85` (`_grade_from_mastery`) vs `frontend/lib/data.ts:6-13` (`gradeFromPct`). Consumers: `_recent_papers` (514), `_subject_mastery` (595-596), `_predicted_grades` (633-634) vs `Marking.tsx:78`, `Analytics.tsx:185`, `Subjects.tsx:157`, `University.tsx`.

### Description
Two independent grade scales disagree on both boundaries and letters:

| Input | Backend `_grade_from_mastery` (0–1 mastery) | Frontend `gradeFromPct` (0–100 %) |
|------:|:--:|:--:|
| 90/0.90 | A* | A* |
| 85/0.85 | A* | A |
| 72/0.72 | A | B |
| 60/0.60 | B | C |
| 52/0.52 | U | D |
| 30/0.30 | U | E |

The backend never emits D/E; the frontend never emits U. The backend applies *mastery bands* to an exam *percentage* for recent papers.

### Expected Behavior
A paper at a given percentage shows one consistent grade everywhere, matching Edexcel IAL boundaries (≈A*=90, A=80, B=70, C=60, D=50, E=40).

### Actual Behavior
A 72% paper shows **A** on Home "Recent papers" (backend) but **B** in Analytics/Subjects (frontend). A 52% paper is **U** on the dashboard but **D** in live marking.

### Evidence
`main.py:514` `"grade": _grade_from_mastery(pct / 100)`; `data.ts:9` `if (p >= 70) return "B";`

### Impact
Contradictory grades across screens directly undermine trust and violate Governing Principle #2 (Educational Accuracy).

### Recommended Fix
Define grade boundaries once (shared constant / per-subject Edexcel boundaries) on a single input scale, and use it on both sides. Do not reuse mastery-band thresholds for exam-percentage grades.

### Confidence
High

---

## LOGIC-006

### Severity
**High**

### Location
`frontend/components/screens/Marking.tsx:104-133` (`save`), pill re-click at `:181`; `backend/main.py:884-919` (`create_attempt`); `schemas/attempts.sql:30-42` (no uniqueness on `(session_id, question_id)`).

### Description
The Marking screen lets the user click any question pill to revisit and re-save. Each `save()` calls `POST /api/attempts`, which **always INSERTs a new row** — no upsert keyed on `(session, question)`. Re-marking creates duplicate attempts.

### Expected Behavior
Re-marking a question within the same session should replace the previous mark — one attempt per question per session.

### Actual Behavior
Each re-save adds another `attempts` row. Downstream aggregations sum *all* attempts → session score can exceed paper total; `/api/weaknesses` counts and `lost` marks inflate; confidence calibration and coverage inflate.

### Evidence
`main.py:902` unconditional `INSERT INTO attempts ...`; `attempts.sql` PK is autoincrement `id`, no unique `(session_id, question_id)`.

### Impact
Corrupted scores and statistics; the live in-session display (de-duplicated local state) diverges from later dashboard/analytics figures. Violates Governing Principle #1 (Data Integrity).

### Recommended Fix
Upsert on `(session_id, question_id)` (replace prior mark), or `PATCH` an existing attempt, or aggregate only the latest attempt per `(session_id, question_id)`.

### Confidence
High

---

## LOGIC-007

### Severity
**High**

### Location
`frontend/components/screens/Home.tsx:126`; `Analytics.tsx:179`; `Subjects.tsx:150`.

### Description
Every past-paper row across Home (recent papers), Analytics (session log), and Subjects (recent attempts) has `onClick={() => go("marking")}` but **never sets `session.setPaperId(...)`**. Marking renders whatever paper is in `session.paperId` (the last *timed* paper) or an empty state.

### Expected Behavior
Clicking a specific past paper opens that paper for review/marking.

### Actual Behavior
Clicking any past paper navigates to Marking showing an unrelated paper or "No paper selected for marking." `p.paper_id`/`p.id` is available on the row but unused.

### Evidence
`Home.tsx:126` `<div className="aos-paper-row" onClick={() => go("marking")}>`; `Subjects.tsx:150`, `Analytics.tsx:179` identical.

### Impact
A core review flow is broken: users cannot open a previously-completed paper from any of the three lists. Combined with LOGIC-006/LOGIC-051, marking in the wrong context can attach attempts to a mismatched session.

### Recommended Fix
On row click, `session.setPaperId(p.paper_id)` (and set/clear `sessionId`) before `go("marking")`, or route to a read-only review of that session.

### Confidence
High

---

## LOGIC-008

### Severity
**High**

### Location
`Home.tsx:96` ("Practise now"); `Weaknesses.tsx:115` ("Practise this topic"); `QuestionReview.tsx:163-164` ("Practise this paper").

### Description
All three call `go("timer")` only, never setting `session.setPaperId(...)` or a topic context. Timer always renders the generic `PaperPicker`, ignoring what the user clicked. QuestionReview has `q.paper.id` readily available and discards it.

### Expected Behavior
"Practise this paper" should start that paper; "Practise this topic" should pre-filter practice to that topic.

### Actual Behavior
The user is dumped on an unfiltered paper list disconnected from the clicked item; the button copy lies about what happens.

### Evidence
`QuestionReview.tsx:163` `<Button ... onClick={() => go("timer")}>Practise this paper</Button>` — `q.paper.id` unused.

### Impact
A promised workflow (jump from a weakness/question into focused practice) is broken across three screens.

### Recommended Fix
In QuestionReview, `session.setPaperId(q.paper.id)` before `go("timer")`. For topic-based practice, pass topic context / pre-filter the picker.

### Confidence
High

---

## LOGIC-009

### Severity
**High**

### Location
`db/seed_syllabus.py` (`seed_all`); `schemas/progress.sql:51-62` (`syllabus_completion`); consumed by `agents/infrastructure/curriculum_agent.py:get_specification_coverage` and `briefing/generator.py:_section2_curriculum_progress`.

### Description
The documented setup runs `seed_all()`, which populates `subjects/modules/topics/subtopics/specification_points` but inserts **zero** `syllabus_completion` rows. Coverage is computed from `syllabus_completion`, so it is permanently 0% / "No syllabus data yet" until something else writes completion rows — and nothing in the standard flow does.

### Expected Behavior
After the documented seed, curriculum coverage should reflect real syllabus state (even if "not started").

### Actual Behavior
`syllabus_completion` is empty after seeding; the briefing's "Curriculum Progress" section always reports "No syllabus data yet — seed progress.db" even though progress.db *was* seeded.

### Evidence
Runtime: `seed_all()` →
```
subjects 5 | modules 31 | topics 94 | subtopics 148 | specification_points 486 | syllabus_completion 0
```

### Impact
The curriculum-coverage feature looks broken/empty after a correct install, contradicting the setup docs and eroding trust.

### Recommended Fix
Have `seed_all()` create a `syllabus_completion` row per spec point with status `not_started` (LEFT JOINs already tolerate missing rows, but an explicit baseline makes coverage and review scheduling well-defined).

### Confidence
High

---

## LOGIC-010

### Severity
**High**

### Location
`frontend/components/shell/Sidebar.tsx:97-100`; `frontend/components/screens/Home.tsx:35`.

### Description
The sidebar footer renders fabricated grades `Physics A · Maths A* · Chem B`, a hardcoded name `Mouad Maamma`, and avatar `MM`, none derived from API data. The Home greeting is hardcoded `Good morning, Mouad.` regardless of user or time of day.

### Expected Behavior
Per CLAUDE.md (Data Integrity #1; "no hardcoded data"), shown grades must come from `predicted_grades`/`subject_mastery`, the name from a real profile, and the greeting from the local hour.

### Actual Behavior
Fixed fake grades and name appear on every screen; the greeting says "Good morning" at all hours and contradicts the real (possibly all-U) grades elsewhere.

### Evidence
`Sidebar.tsx:100` `<div className="aos-foot-grades">Physics A · Maths A* · Chem B</div>`; `Home.tsx:35` `<h1>Good morning, Mouad.</h1>`

### Impact
Persistent UI elements mislead users with invented grades/identity — directly contradicting the Analytics subtitle "every number from a real query."

### Recommended Fix
Populate from `getDashboard().predicted_grades` (with honest empty state) and a real profile; compute the greeting from local time.

### Confidence
High

---

## LOGIC-011

### Severity
**High**

### Location
`frontend/components/screens/Settings.tsx:43, 51, 56-66, 69-70`; `Toggle` in `frontend/components/ui/index.tsx`.

### Description
Settings presents editable controls wired to nothing:
- Name: `<input defaultValue="Mouad Maamma">` (uncontrolled, no save).
- Exam session: static badge "June 2026".
- Telegram briefing time: local `useState` only, never sent to the backend (`BRIEFING_TIME` is env-only).
- "Spaced-repetition reminders", "Examiner-trap alerts", "Review difficult items first": `<Toggle on />` with no `onChange`/persistence.

### Expected Behavior
Controls persist real settings, or are clearly read-only/disabled.

### Actual Behavior
Every control is a silent no-op; edits vanish on reload with no feedback. Profile name/exam session are hardcoded placeholders.

### Evidence
`Settings.tsx:43` `<input className="aos-input" defaultValue="Mouad Maamma" />`; `:64-65,:70` toggles have no handlers; `:31` `const [time, setTime] = useState("07:30")` with no submit.

### Impact
Classic silent failure: users believe preferences (briefing time, reminders) are saved when nothing persists.

### Recommended Fix
Wire controls to a settings endpoint, or mark them disabled/"coming soon"; replace hardcoded profile values with real data.

### Confidence
High

---

## LOGIC-012

### Severity
**High**

### Location
`frontend/components/screens/Marking.tsx:73-78, 158-165, 320-322`.

### Description
`pct` uses `possibleSoFar` (sum of marks for *already-marked* questions only): `pct = round(scored / possibleSoFar * 100)`. After marking one 2/2 question, `possibleSoFar = 2`, `scored = 2` → 100% → grade A*. Meanwhile the headline `{scored} / {maxMarks}` (159, 320) uses the *full* paper denominator. The prominent "Live grade" badge is therefore "grade among questions marked so far," not a paper grade.

### Expected Behavior
The live grade should be against the full paper, or be clearly labeled "grade on marked so far."

### Actual Behavior
A user marking their first correct question sees "Live grade A* · 100%" beside "2 / 75 marks" — internally contradictory.

### Evidence
`Marking.tsx:77` `const pct = possibleSoFar > 0 ? Math.round((scored / possibleSoFar) * 100) : 0;` vs `:159` `{scored}<span> / {maxMarks}</span>`.

### Impact
Strongly misleading grade feedback during marking; users may believe they are scoring A* when barely started.

### Recommended Fix
Compute the live grade against `maxMarks`, or relabel the badge to disclose the partial denominator.

### Confidence
High

---

## LOGIC-013

### Severity
**High**

### Location
`frontend/components/charts/index.tsx:238-244` (`ScatterChart`), used by `Analytics.tsx:134`.

### Description
The "Time vs score" scatter hardcodes `y: { min: 40, max: 100 }`. Any paper scored below 40% plots off the bottom and is invisible.

### Expected Behavior
All marked papers appear; the axis should start at 0 (or auto-scale).

### Actual Behavior
A student's weakest papers (<40%) — the most important to see — silently disappear.

### Evidence
`charts/index.tsx:240` `min: 40,`.

### Impact
Misleading visualization that omits low scores without indication.

### Recommended Fix
Set `min: 0` (or omit `min`).

### Confidence
High

---

## LOGIC-014

### Severity
**High**

### Location
`agents/infrastructure/curriculum_agent.py:17-21` (`_SR_INTERVALS`), `:239-273` (`schedule_review`).

### Description
The next interval is chosen solely from a static table indexed by stored `confidence` (1–5) and outcome: `interval_days = intervals[max(0, min(confidence - 1, 4))]`. It ignores `review_count` and uses no ease factor (there is no ease-factor column). A spec point reviewed correctly five times in a row at confidence 3 always gets the same interval — it never expands. `schedule_review` also never updates `confidence`. This is a fixed lookup, not SM-2.

### Expected Behavior
Real SM-2: expanding intervals (multiply previous interval by an ease factor adjusted per recall quality).

### Actual Behavior
Fixed per-outcome/confidence constant; no growth, no ease factor, confidence never changes. The Settings screen even advertises "Algorithm: SM-2 (modified)."

### Evidence
`curriculum_agent.py:260-263` selects from `_SR_INTERVALS[outcome][...]` and sets `next_review = today + interval_days`.

### Impact
Review scheduling does not actually space out; mastered items resurface as often as new ones. The core adaptive feature is broken.

### Recommended Fix
Implement real SM-2 (track `ease_factor`/`interval`/`repetition`, update EF from quality), or document the fixed ladder honestly and grow intervals by `review_count`.

### Confidence
High

---

## LOGIC-015

### Severity
**High**

### Location
`agents/infrastructure/curriculum_agent.py:33-89` (`advance_topic`), `:101-141` (`update_completion`), `:205-236` (`get_next_review_queue`).

### Description
Neither `advance_topic` nor `update_completion` ever sets `next_review`; only `schedule_review` does. `get_next_review_queue` requires `next_review IS NOT NULL`. So a spec point progressed to `taught`/`reviewed` through the normal path has `next_review = NULL` and never appears in the review queue — and nothing in the audited code calls `schedule_review` from the progression path.

### Expected Behavior
Reaching `taught` should schedule an initial review so the item enters the queue.

### Actual Behavior
Items taught via normal progression are never scheduled; the review queue stays empty even with the correct schema seeded.

### Evidence
`schedule_review` is the only writer of `next_review` (`:269`); `get_next_review_queue` filters `WHERE sc.next_review IS NOT NULL` (`:223`).

### Impact
Even after fixing LOGIC-001/009, the spaced-repetition queue would still be empty.

### Recommended Fix
Set an initial `next_review` when status reaches `taught`, or call `schedule_review` from the progression path.

### Confidence
High

---

## LOGIC-016

### Severity
**High**

### Location
`briefing/generator.py:285-288`.

### Description
The `--send-now` CLI path does `from agents.delivery.telegram_agent import TelegramAgent` then `TelegramAgent().send_message(text)`. `telegram_agent.py` defines **no `TelegramAgent` class** — only module-level `async def send_message(...)` / `send_daily_briefing(...)`. The import raises `ImportError`; even if it existed, `send_message` is a coroutine that must be awaited.

### Expected Behavior
`python -m briefing.generator --send-now` sends the briefing to Telegram.

### Actual Behavior
Immediate `ImportError`; the manual send path is dead.

### Evidence
`grep "^class\|^async def" telegram_agent.py` → only functions; `generator.py:286` imports `TelegramAgent`.

### Impact
The documented manual-send command never works.

### Recommended Fix
`import asyncio; from agents.delivery.telegram_agent import send_daily_briefing; asyncio.run(send_daily_briefing(text))`.

### Confidence
High

---

## LOGIC-017

### Severity
**High**

### Location
`agents/delivery/telegram_agent.py:11, 83-199` (`_cmd_*` handlers), content from `briefing/generator.py`.

### Description
All sends use legacy `parse_mode="Markdown"`. Briefing/quiz/revise inject raw extracted question text and misconception descriptions (e.g., `qod["raw_text"]`, `top['description']`) that contain unbalanced `_ * [ ` ` from OCR/LaTeX, causing Telegram HTTP 400 "can't parse entities." `format_for_telegram`'s docstring claims "MarkdownV2-safe" but it neither escapes nor uses V2. `send_message` has a plain-text retry, but the bot command handlers (`_cmd_quiz/_cmd_revise/_cmd_progress/_cmd_status/_cmd_coverage`) call `reply_text(..., parse_mode="Markdown")` with **no fallback** → they 400 outright on messy content.

### Expected Behavior
Dynamic content is escaped (or markup stripped); messages always render.

### Actual Behavior
Bot commands fail with HTTP 400 whenever extracted content contains stray markup.

### Evidence
`telegram_agent.py:11` default `parse_mode="Markdown"`; `:100-199` command handlers pass `parse_mode="Markdown"` directly.

### Impact
Interactive Telegram commands are unreliable/broken on real OCR'd content.

### Recommended Fix
Escape dynamic content or use HTML parse mode; add a plain-text fallback to the command handlers.

### Confidence
Medium-High

---

## LOGIC-018

### Severity
**High**

### Location
`backend/main.py:843-878` (`_update_mastery`, `UPDATE spaced_repetition_items`), plus all progress.db reads (98,101,432,529,539,564,605,645,1067).

### Description
CLAUDE.md / AGENTS.md designate the Curriculum Agent as the *sole* writer of progress.db syllabus/SR state. The FastAPI backend both reads and **writes** progress.db SR state directly (UPDATE at `:872`), bypassing the agent (and targeting the phantom table — LOGIC-001). Subject/analysis agents and scripts correctly stay in their own domains; the violation is isolated to the backend.

### Expected Behavior
All progress.db writes route through `curriculum_agent`.

### Actual Behavior
The backend writes progress.db directly, violating Agent Ownership.

### Evidence
`main.py:870-877` `UPDATE spaced_repetition_items SET mastery=?, ease_factor=?, ...`.

### Impact
Architectural-consistency / data-integrity risk: two writers of the same state with divergent models.

### Recommended Fix
Route mastery/review updates through the Curriculum Agent API.

### Confidence
High

---

## LOGIC-019

### Severity
**High**

### Location
`frontend/components/screens/Home.tsx:23-26, 51-58`; `backend/main.py:472` (`_recent_papers(limit=5)`); compare `Analytics.tsx:41-43`.

### Description
Home derives "Papers completed" and "Average score" from `recent_papers`, capped at **5** by the backend. Analytics derives "Average score" from `analytics.score_trend` (up to 30 completed sessions). Same labels, different populations.

### Expected Behavior
"Papers completed" reflects the true count; "Average score" is consistent across screens (or clearly scoped).

### Actual Behavior
"Papers completed" can never exceed 5; "Average score" on Home (≤5 papers) differs from Analytics (≤30 sessions) for the same user.

### Evidence
`Home.tsx:23` `completedPapers = d.recent_papers.filter(p => p.pct != null)`; `Analytics.tsx:42` averages `a.score_trend`.

### Impact
Headline KPIs are wrong/inconsistent — a student with 20 marked papers sees "5," and the same metric shows two values on two screens.

### Recommended Fix
Add a dedicated total-completed count and an all-papers average to the dashboard payload; compute both Home and Analytics from the same source.

### Confidence
High

---

## LOGIC-020

### Severity
**High**

### Location
`ingestion/extractor.py:11-19` (question-start regex, group 4).

### Description
The question-start pattern matches `\d{1,2}\s+[A-Z]`, so ordinary prose like "12 N force is applied…" or "5 March 2023" is treated as a new question boundary, over-splitting a single question into several.

### Expected Behavior
Only genuine question numbers start new questions.

### Actual Behavior
Fabricated/duplicate question records with wrong text and marks; combined with the duplicate-number skip (LOGIC-023 region) the first bogus block can win.

### Evidence
`extractor.py:11-19` question-start alternation includes `\d{1,2}\s+[A-Z]`.

### Impact
Corrupted question bank — wrong question counts, marks, and difficulty feed every downstream feature.

### Recommended Fix
Anchor question numbers to line starts with stricter context (e.g., require the number to be the first token of a line and followed by typical stems), and validate against expected counts.

### Confidence
Medium-High

---

## LOGIC-021

### Severity
**High**

### Location
`ingestion/extractor.py:30-32` (mark-scheme line regex); `:174-179` (`_normalise_mark_type`).

### Description
The mark-scheme line regex requires a trailing `[:\s]`, so bare/compact annotations (`B1`, `A1ft`, `A1cao`, `M1*`) at line end or without a space do not match and are silently dropped.

### Expected Behavior
All mark codes (`M1`, `A1`, `B1`, `dM1`, `A1ft`, `A1cao`, `B1*`, …) are captured.

### Actual Behavior
Whole mark entries are lost; markscheme totals understate the real scheme.

### Evidence
`extractor.py:30-32` pattern with mandatory trailing `[:\s]`.

### Impact
Incomplete mark schemes shown in Marking/QuestionReview ("No markscheme extracted"), and wrong mark totals.

### Recommended Fix
Broaden the regex to accept end-of-line codes and common follow-through/annotation suffixes; add a permissive second pass.

### Confidence
Medium

---

## LOGIC-022

### Severity
**High**

### Location
`ingestion/extractor.py:300-306`; `agents/analysis/examiner_report_agent.py:33, 96-97`.

### Description
Observation `topic`/`subtopic` are hardcoded to `None`. With `misconceptions UNIQUE(subject, module_code, topic, description)`, the topic dimension collapses — all misconceptions file under a null/"General" topic.

### Expected Behavior
Observations/misconceptions carry their real topic so topic-scoped retrieval works.

### Actual Behavior
Topic is lost; misconception/intervention retrieval by topic returns nothing (see LOGIC-045).

### Evidence
`extractor.py:300-306` builds observation dicts with `topic=None, subtopic=None`.

### Impact
The examiner-intelligence and misconception-driven practice features are effectively topic-blind.

### Recommended Fix
Classify observation topics (reuse `classifier.classify_topic`) before insert.

### Confidence
Medium-High

---

## LOGIC-023

### Severity
**High**

### Location
`agents/analysis/past_paper_agent.py:147, 149-163` (paper code/session/module detection); `question_bank.sql:20` (`UNIQUE(paper_code, session, paper_type)`).

### Description
`paper_code` is derived from the filename stem; module/session are taken from incidental text on the first two pages, with session falling back to a bare year. The dedup key `(paper_code, session, paper_type)` therefore keys on filename and a coarse session, so renaming a file creates a duplicate paper, and bare-year sessions fragment dedup. CS papers are always coded "CS".

### Expected Behavior
Papers are keyed on the official paper code + exact sitting; re-ingesting the same paper is idempotent.

### Actual Behavior
Duplicate papers on rename; wrong/fragmented sessions; module code = first match anywhere in the first pages.

### Evidence
`past_paper_agent.py:147` paper_code = filename stem; `:149-163` first-match module/session.

### Impact
Duplicate/misattributed papers pollute the bank, distorting coverage and recent-paper lists.

### Recommended Fix
Parse the official code/session from page content with validated patterns; key dedup on those.

### Confidence
Medium

---

## LOGIC-024

### Severity
**High**

### Location
`agents/analysis/markscheme_agent.py:72-82, 200-207` (`_find_question_id`).

### Description
Mark-scheme entries are linked to questions by exact `question_number` match. When the MS labels a part `1a` but the question bank stored `1` (or vice versa), no match is found and the entire mark scheme for that question is skipped silently.

### Expected Behavior
MS entries link via normalized question numbering tolerant of `1a`/`1(a)`/`1` variants.

### Actual Behavior
Whole mark schemes dropped on suffix mismatch.

### Evidence
`markscheme_agent.py:72-82` exact match on `question_number`.

### Impact
"No markscheme extracted" appears even when the MS PDF was ingested.

### Recommended Fix
Normalize question numbers on both sides before matching; fall back to part-prefix matching.

### Confidence
Medium

---

## LOGIC-025

### Severity
**High**

### Location
`agents/analysis/examiner_report_agent.py:53-62, 86-122, 146-157`.

### Description
On re-ingest, `reports` ON CONFLICT updates only `processed_at`; `observations` have no unique key and are always re-INSERTed; misconception `frequency` is incremented (`frequency = frequency + 1`) every run. Re-running the pipeline duplicates observations and inflates `frequency`.

### Expected Behavior
Re-ingestion is idempotent; `frequency` reflects distinct reports/mentions.

### Actual Behavior
Duplicated observations and ever-growing `frequency` on each re-run, skewing all frequency-ranked UI ("seen N×").

### Evidence
`examiner_report_agent.py:86-122` unconditional observation INSERT; `:146-157` `frequency+1`.

### Impact
Examiner-trap rankings and "seen N×" counts are unreliable and inflate over time.

### Recommended Fix
Add a unique key for observations; compute `frequency` from distinct source reports rather than incrementing per run.

### Confidence
Medium

---

## LOGIC-026

### Severity
**High**

### Location
`agents/analysis/diagram_agent.py:50-60` (`classify_diagram`), `:85-101, 119-161`.

### Description
`classify_diagram` keys on filename patterns the ingestion pipeline never actually produces, so every diagram falls through to "other." The docstring's pix2tex/CLIP classification is unimplemented (the classification is effectively faked). The `subject` argument is ignored; only full-page rasters are stored (no embedded-figure extraction).

### Expected Behavior
Diagrams are classified by content/type so type-filtered retrieval works.

### Actual Behavior
Every diagram is "other"; type-filtered diagram retrieval returns nothing.

### Evidence
`diagram_agent.py:50-60` filename-based switch with no matching producer.

### Impact
The diagram intelligence feature is non-functional; "Diagram Based" retrieval is empty.

### Recommended Fix
Implement real classification (or remove the type filter), and extract embedded figures rather than whole pages.

### Confidence
Medium

---

## LOGIC-027

### Severity
**High**

### Location
`scripts/extract_markschemes.py:98-112`; `scripts/extract_examiner.py:54-96`.

### Description
Mark scheme / examiner reports are matched to question papers within a **330-day** window, with an absolute-nearest fallback and a single-candidate last resort. Edexcel sittings are 4–6 months apart, so a 330-day window spans 2–3 sessions; the fallbacks match across sessions entirely. A mark scheme/examiner report can attach to the **wrong sitting's** paper.

### Expected Behavior
A mark scheme/examiner report matches the exact paper code + sitting it belongs to.

### Actual Behavior
Cross-session mis-association silently corrupts marking and observation data.

### Evidence
`extract_markschemes.py:98-112` 330-day window + absolute/single-candidate fallback (duplicated in `extract_examiner.py`).

### Impact
Wrong mark schemes shown for questions; observations filed against the wrong paper.

### Recommended Fix
Match on exact `(paper_code, session)`; drop the broad window and cross-session fallbacks (or gate them behind exact-code equality).

### Confidence
Medium

---

## LOGIC-028

### Severity
Medium

### Location
`backend/main.py:472-520` (`_recent_papers`).

### Description
`_recent_papers` selects sessions with no `ended_at IS NOT NULL` filter, ordered by `started_at DESC`. It then shows `score`/`grade` whenever `available > 0`. An in-progress session with a few logged attempts therefore appears in "Recent papers" with a partial score and a computed grade, indistinguishable (except for the `completed` flag) from a finished paper.

### Expected Behavior
Only completed sessions show a final score/grade; in-progress sessions are clearly marked or excluded.

### Actual Behavior
A partially-marked, still-running paper shows e.g. "12/75 · grade U" as if it were a completed result.

### Evidence
`main.py:480-481` no `ended_at` filter; `:511-514` score/grade emitted whenever `available`.

### Impact
Misleading recent-paper figures; partial scores misread as final.

### Recommended Fix
Only emit score/grade when `ended_at IS NOT NULL`, or label in-progress rows distinctly.

### Confidence
Medium

---

## LOGIC-029

### Severity
Medium

### Location
`backend/main.py:596, 634` (flat +0.10 prediction); `frontend/components/screens/Home.tsx:27-29, 42-45` ("best prediction").

### Description
"Predicted grade" = `_grade_from_mastery(min(1.0, mastery + 0.10))` — a uniform +10pp bump independent of trend, attempt count, or recency. Home then picks the headline "Predicted grade" as the subject with the **most attempts** (`reduce((a,b) => b.attempt_count > a.attempt_count ? b : a)`), not an overall or best/worst grade.

### Expected Behavior
A prediction reflects a defensible projection; the headline should be a meaningful single number.

### Actual Behavior
Predicted grade is essentially "current mastery + 10%" (often overstated), and the headline shows whichever subject the student has practised most — which may be their weakest.

### Evidence
`main.py:596` `"predicted_grade": _grade_from_mastery(min(1.0, mastery + 0.10))`; `Home.tsx:28`.

### Impact
Misleading core metric shown on Home and used by University Readiness for high-stakes framing.

### Recommended Fix
Replace the flat bump with a trend/coverage-based model (or relabel honestly); aggregate the headline across subjects or relabel it as "highest-confidence subject."

### Confidence
Medium

---

## LOGIC-030

### Severity
Medium

### Location
`backend/main.py:1136-1147` (`/api/briefing`); `frontend/lib/api.ts:117` (`getBriefing`, unused); `frontend/lib/types.ts:269-275` (`BriefingData`, unused); `frontend/components/screens/Briefing.tsx`.

### Description
The backend exposes `/api/briefing` (4-section generated briefing). The Briefing screen never calls it; it rebuilds a briefing from `getDashboard()` + `getCoverage()`. `getBriefing`/`BriefingData` are dead. Two divergent "briefing" definitions exist.

### Expected Behavior
One source of truth for the briefing.

### Actual Behavior
The richer generated briefing (per-subject misconceptions, curriculum %, revision packs) is never shown; a partial reconstruction is shown instead.

### Evidence
`Briefing.tsx:11-12` uses `getDashboard`/`getCoverage`; no `getBriefing` import.

### Impact
Contradictory sources of truth; maintenance hazard; the documented briefing content is invisible.

### Recommended Fix
Render `/api/briefing` in the Briefing screen, or remove the endpoint/types.

### Confidence
High

---

## LOGIC-031

### Severity
Medium

### Location
`frontend/components/screens/Marking.tsx:120` (`time_seconds: 0`); `Timer.tsx:179-185` (`logQuestionTime`); `backend/main.py` `question_times` vs `attempts`.

### Description
Timer records per-question time into `question_times`, but Marking submits each attempt with `time_seconds: 0`. The two are never reconciled, and `question_times` is never joined into anything user-facing.

### Expected Behavior
Attempt time reflects actual time spent and is visible (e.g., QuestionReview "last attempt").

### Actual Behavior
Every attempt stores 0 seconds; `question_times` data is orphaned.

### Evidence
`Marking.tsx:120` `time_seconds: 0,`; `Timer.tsx:182` `logQuestionTime(sid, qs[cur].id, { time_seconds: qTimes[cur], status })`.

### Impact
Time-on-question analytics impossible; a feature that appears to work produces no usable result.

### Recommended Fix
Carry per-question time from the timer session into the attempt, or derive attempt time from `question_times`.

### Confidence
High

---

## LOGIC-032

### Severity
Medium

### Location
`frontend/components/screens/Timer.tsx:14, 117-118`.

### Description
`OFFICIAL_DEFAULT = 90 * 60` is applied to every paper regardless of subject/unit; target = ⅔ of this. IAL papers vary (75/90/100/105 min).

### Expected Behavior
Official duration comes per-paper from the question bank.

### Actual Behavior
Pace warnings, "remaining," and the persisted `target_time_seconds` (which feeds the "vs target" deltas everywhere) are wrong for any non-90-min paper.

### Evidence
`Timer.tsx:14` `const OFFICIAL_DEFAULT = 90 * 60;`; `:117` `const official = OFFICIAL_DEFAULT;`.

### Impact
Inaccurate timing feedback and target deltas across Timer, Analytics, and Subjects.

### Recommended Fix
Store/serve official duration per paper and use it.

### Confidence
Medium

---

## LOGIC-033

### Severity
Medium

### Location
`frontend/components/screens/Timer.tsx:187-200, 270` (`finish`/`logCurrent`).

### Description
`finish()` (used by both "Finish — go to marking" and "Finished paper — go to marking") logs only the *current* question as "complete." If the user finishes early, all later questions get no `question_times` row.

### Expected Behavior
Unreached questions are explicitly logged (e.g., "skipped") on finish.

### Actual Behavior
Later questions have no timing rows → appear un-attempted / 0 in any timing view.

### Evidence
`Timer.tsx:187-194` `finish` calls `logCurrent("complete")` only.

### Impact
Incomplete per-question timing data feeding pace/weakness views.

### Recommended Fix
On finish, log all unreached questions as "skipped."

### Confidence
Medium

---

## LOGIC-034

### Severity
Medium

### Location
`frontend/components/screens/Analytics.tsx:145`.

### Description
Calibration bars are colored by `masteryBand(c.score)` — green if average score ≥80. Calibration is about agreement between confidence and score; a "Conf 1, 85%" (under-confident) shows green, while "Conf 5, 60%" (over-confident, the real problem) shows amber. Color encodes the wrong dimension.

### Expected Behavior
Color encodes confidence-vs-score deviation.

### Actual Behavior
The calibration chart's colors mislead about whether the student is well-calibrated.

### Evidence
`Analytics.tsx:145` `colors={calibration.map((c) => bandColor(masteryBand(c.score)))}`.

### Impact
The calibration insight is inverted/meaningless.

### Recommended Fix
Color by `|expected(conf) − score|` (deviation), not raw score.

### Confidence
Medium

---

## LOGIC-035

### Severity
Medium

### Location
`frontend/components/screens/Analytics.tsx:200-203, 221`.

### Description
The Paper library header shows `{papers.length} papers` (up to 500) but the table renders only `papers.slice(0, 50)`, with no "showing 50 of N" indicator and no pagination.

### Expected Behavior
The visible count matches the header, or a "showing 50 of N" note/pagination is present.

### Actual Behavior
Header claims e.g. "500 papers" but only 50 rows appear.

### Evidence
`Analytics.tsx:202` `{papers.length.toLocaleString()} papers`; `:221` `papers.slice(0, 50)`.

### Impact
Users believe the full library is shown; the rest is silently hidden.

### Recommended Fix
Show "Showing 50 of N" or paginate.

### Confidence
High

---

## LOGIC-036

### Severity
Medium

### Location
`frontend/components/screens/Subjects.tsx:11, 22, 41`.

### Description
`useState("physics")` assumes a physics subject always exists. If `subject_mastery` lacks physics, `s` is `undefined` and the screen shows "No syllabus data for this subject" even though other subjects have data and appear in the tab bar.

### Expected Behavior
Default to the first subject with data.

### Actual Behavior
Misleading empty state on first load whenever physics is absent.

### Evidence
`Subjects.tsx:11` `const [active, setActive] = useState("physics");` then `:22` `const s = subjectList.find(x => x.subject_id === active)`.

### Impact
Users with data but no physics see an empty screen and may assume the app has no data.

### Recommended Fix
Initialize `active` to `subjectList[0]?.subject_id` once data loads.

### Confidence
Medium

---

## LOGIC-037

### Severity
Medium

### Location
`agents/infrastructure/curriculum_agent.py:187-188, 287-309` (`get_specification_coverage`); consumed by briefing `_section2_curriculum_progress`.

### Description
"Coverage %" = `(mastered + reviewed) / total`, excluding `taught` and `in_progress`. A student taught the whole syllabus but not yet reviewed shows 0% coverage. The label conflates "taught coverage" with "mastery."

### Expected Behavior
Report taught-coverage and mastery separately, or include `taught` in coverage.

### Actual Behavior
Briefing/`/progress` understate real progress.

### Evidence
`curriculum_agent.py:187-188` `mastered = by_status.get("mastered",0) + by_status.get("reviewed",0)`.

### Impact
Demotivating, incorrect progress signal in the briefing.

### Recommended Fix
Expose two metrics, or redefine coverage to include taught/in-progress.

### Confidence
Medium

---

## LOGIC-038

### Severity
Medium

### Location
`schemas/progress.sql:65-72` (`review_history`); `agents/infrastructure/curriculum_agent.py:239-273` (`schedule_review`).

### Description
`review_history` is defined but never written — no `INSERT INTO review_history` exists anywhere. `schedule_review` updates counters on `syllabus_completion` but records no outcome row.

### Expected Behavior
Each review writes a `review_history` row (`strong/adequate/weak/failed`).

### Actual Behavior
No outcome audit trail; review-trend analysis impossible.

### Evidence
`grep "INSERT INTO review_history"` → no matches.

### Impact
Loss of historical review data; weakens analytics and any future trend features.

### Recommended Fix
Insert a `review_history` row inside `schedule_review`.

### Confidence
High

---

## LOGIC-039

### Severity
Medium

### Location
`agents/delivery/retrieval_agent.py:158-169` (`get_weak_topics`).

### Description
The function computes `cutoff = today - window_days` and filters `performance_trends` by `computed_at >= cutoff`, but `performance_trends` rows each carry their own `window_days`. It conflates "when the aggregate was computed" with "the window it covers," so a 90-day aggregate computed today is used for a 30-day request, and valid older aggregates are excluded.

### Expected Behavior
Filter on `window_days = requested` and take the most recent `computed_at` per topic.

### Actual Behavior
Weak-topic selection (driving revision packs and QotD priority) uses the wrong rows.

### Evidence
`retrieval_agent.py:158-169` filters on `computed_at`, not `window_days`.

### Impact
Adaptive revision targets the wrong topics.

### Recommended Fix
Filter by matching `window_days`; pick latest `computed_at` per topic.

### Confidence
Medium

---

## LOGIC-040

### Severity
Medium

### Location
`ingestion/ocr.py:89-117, 120-141`; `agents/analysis/examiner_report_agent.py:140-141`.

### Description
`ocr_page_with_fallback` re-runs `extract_text_pdfplumber(pdf_path)` for the whole PDF on every scanned page (O(n²)). The examiner agent OCRs the full text twice.

### Expected Behavior
Parse the PDF once; OCR each page once.

### Actual Behavior
Severe redundant work on large/scanned papers; slow ingestion.

### Evidence
`ocr.py:89-117` per-page full-PDF re-parse.

### Impact
Performance/cost; long ingestion runs.

### Recommended Fix
Extract all page texts once and index by page; OCR once.

### Confidence
Medium

---

## LOGIC-041

### Severity
Medium

### Location
`ingestion/extractor.py:174-179` (`_normalise_mark_type`), `:78-88` (`_extract_marks`).

### Description
`_normalise_mark_type` defaults unknown tokens to "M" (method mark), so OCR near-misses silently become method marks. `_extract_marks` returns the **last** bracketed number rather than the question total, mis-assigning marks for multi-part questions.

### Expected Behavior
Unknown mark types are flagged, not coerced; marks reflect the question total.

### Actual Behavior
Mislabeled mark types; wrong per-question marks → wrong difficulty (LOGIC-042).

### Evidence
`extractor.py:174-179` default `"M"`; `:78-88` returns last bracket.

### Impact
Mark scheme and difficulty data corrupted.

### Recommended Fix
Reject/flag unknown mark types; sum part marks or read the explicit total.

### Confidence
Medium

---

## LOGIC-042

### Severity
Medium

### Location
`ingestion/classifier.py:42-48` (`extract_command_word`), `:84-88` (`classify_difficulty`).

### Description
`classify_difficulty` averages a command-word weight with marks and rounds (`round((cw+marks)/2)`); a 4-mark proof can land at `round(2.5)=2` ("single-step"). `extract_command_word` matches command words mid-question via `\n{cw}`, so a later-line word (e.g., "given that") overrides the real leading command word.

### Expected Behavior
Difficulty reflects marks + cognitive demand sensibly; the leading command word wins.

### Actual Behavior
Mis-scored difficulty (drives revision ordering and QotD selection); wrong command word displayed.

### Evidence
`classifier.py:84-88` averaging+round; `:42-48` mid-question matching.

### Impact
Incorrect difficulty/command-word metadata across the bank.

### Recommended Fix
Use a non-averaging difficulty rule; match only the first command word.

### Confidence
Medium

---

## LOGIC-043

### Severity
Medium

### Location
`ingestion/classifier.py:197-212` (`classify_topic` fallback).

### Description
When no topic matches, the fallback writes the `module_code` (e.g., "P3") into `question_topics.topic`.

### Expected Behavior
Unknown topics are stored as "Unknown" (which the API already special-cases), not a module code.

### Actual Behavior
Module codes pollute topic retrieval; `get_questions(topic=...)` never matches a real topic name, and topic-based features misbehave.

### Evidence
`classifier.py:197-212` fallback assigns `module_code` to `topic`.

### Impact
Topic retrieval and weakness aggregation contaminated.

### Recommended Fix
Use "Unknown" for unmatched topics.

### Confidence
Medium

---

## LOGIC-044

### Severity
Medium

### Location
`agents/analysis/diagram_agent.py:85-101, 141-146` (`_write_diagram`).

### Description
`_write_diagram` trusts `cursor.lastrowid` even on the ON CONFLICT UPDATE path, where `lastrowid` does not reliably refer to the updated row. On re-ingest, diagram links can point to the wrong row (or rowid 0). Other agents deliberately re-query the id.

### Expected Behavior
Re-query the diagram id after upsert before creating links.

### Actual Behavior
Links to wrong/invalid diagrams on re-ingest.

### Evidence
`diagram_agent.py:85-101` uses `lastrowid` post-upsert.

### Impact
Broken diagram associations.

### Recommended Fix
SELECT the id by the unique key after upsert.

### Confidence
Medium

---

## LOGIC-045

### Severity
Medium

### Location
`agents/analysis/misconception_agent.py:165-202` (`_build_intervention`), `:199` (redundant fallback), `:203-204` (broad except).

### Description
Interventions call `get_questions(topic="General")` (because of LOGIC-022) → no practice questions returned. `code = q.get("paper_code") or q.get("paper_code", "?")` is a copy-paste no-op fallback. A broad `except Exception` at debug level hides retrieval failures.

### Expected Behavior
Interventions surface real practice questions for the misconception's topic; errors are visible.

### Actual Behavior
Empty intervention practice lists; silent failures.

### Evidence
`misconception_agent.py:165-202`.

### Impact
Misconception-driven remediation produces no questions.

### Recommended Fix
Fix LOGIC-022 so topics are real; correct the fallback; raise/log retrieval errors.

### Confidence
Medium

---

## LOGIC-046

### Severity
Medium

### Location
`backend/main.py:1176-1186` (`get_analytics` calibration), `:937-1053` (`get_weaknesses`).

### Description
Confidence calibration (`AVG(marks_awarded/marks_available*100)` grouped by confidence) and weakness aggregation (`SUM` over all attempts, `attempts += COUNT(*)`) both count duplicate attempts created by LOGIC-006, inflating `attempts`, `lost`, and skewing calibration.

### Expected Behavior
Aggregations use one attempt per `(session, question)`.

### Actual Behavior
Inflated/biased analytics whenever a question was re-marked.

### Evidence
`get_weaknesses` `entry["attempts"] += a["n"]` where `a["n"] = COUNT(*)`; calibration averages raw attempts.

### Impact
Analytics figures drift from reality after any re-marking.

### Recommended Fix
De-duplicate to the latest attempt per `(session, question)` in aggregations (or fix LOGIC-006).

### Confidence
Medium

---

## LOGIC-047

### Severity
Low

### Location
`backend/main.py:712-728` (`_streak`); `frontend/components/screens/Timer.tsx:121-132` (auto-create session).

### Description
`_streak` counts distinct days with any `sessions` row. A session is created the moment a paper loads in the Timer, not on completion. Opening (and abandoning) a paper counts the day.

### Expected Behavior
Streak counts days with genuine study (completed session or ≥1 marked attempt).

### Actual Behavior
Merely opening a paper inflates the streak.

### Evidence
`Timer.tsx:124` creates a session on data load; `_streak` counts any `started_at` day.

### Impact
Gameable/inflated streak; minor trust issue.

### Recommended Fix
Count completed sessions (`ended_at IS NOT NULL`) or attempt activity.

### Confidence
Medium

---

## LOGIC-048

### Severity
Low

### Location
`backend/main.py:166-178` (`days_ago`), `:712-728` (`_streak`), `:764` (UTC storage).

### Description
Sessions store UTC ISO timestamps (`datetime.now(timezone.utc)`), but `days_ago` compares against `date.today()` (server local) and `_streak`/queries use `DATE('now')` (SQLite UTC). Mixing UTC and local dates causes off-by-one near midnight.

### Expected Behavior
A single, consistent timezone (the student's) for all day-boundary math.

### Actual Behavior
"X days ago" and streak boundaries can be off by one.

### Evidence
`main.py:764` UTC store; `:175` `today = date.today()`.

### Impact
Minor relative-date/streak inaccuracy.

### Recommended Fix
Standardize on the user's timezone for day math.

### Confidence
Medium

---

## LOGIC-049

### Severity
Low

### Location
`backend/main.py:703` (`_question_of_day`); `frontend/components/screens/QuestionReview.tsx:55`.

### Description
`difficulty` is mapped via fixed-length array indexing `[...][qod["difficulty"]]`. If a row ever had `difficulty` NULL/0/>5, this raises `IndexError`/`TypeError` inside `get_dashboard` → 500. **Mitigated** by `question_bank.sql:29-30` (`NOT NULL DEFAULT 2 CHECK(difficulty BETWEEN 1 AND 5)`), so valid DBs cannot trigger it; the risk is only if data is inserted bypassing constraints.

### Expected Behavior
An unexpected difficulty degrades gracefully (blank label), never 500.

### Actual Behavior
Currently safe due to the CHECK constraint, but the index is unguarded.

### Evidence
`main.py:703` raw index; `QuestionReview.tsx:55` `DIFFICULTY[q.difficulty]`.

### Impact
Latent crash if the constraint is ever bypassed.

### Recommended Fix
Guard the index: `labels[d] if isinstance(d,int) and 0 <= d < len(labels) else ""`.

### Confidence
Medium

---

## LOGIC-050

### Severity
Low

### Location
`backend/main.py:534-543` (`weak_topics` unused), `:929` (`grade_contribution`); `frontend/lib/types.ts:50` (`ApiPaper.days_ago`, unrendered).

### Description
`_subject_mastery` computes `weak_topics` per unit but never returns it. `create_attempt` returns `grade_contribution` (mastery bands applied to a single question's percentage — semantically dubious) which the frontend never displays. `/api/papers` returns `days_ago`, never rendered.

### Expected Behavior
Either surface these values intentionally or remove them.

### Actual Behavior
Dead computation/fields; a misleading per-question "grade."

### Evidence
`main.py:538` computes `weak_topics`; `:929` returns `grade_contribution`; `types.ts:50` `days_ago`.

### Impact
Maintainability/clarity only.

### Recommended Fix
Remove or surface intentionally.

### Confidence
High

---

## LOGIC-051

### Severity
Low

### Location
`backend/main.py:884-919` (`create_attempt`).

### Description
`create_attempt` validates the question exists and (if provided) the session exists, but does not verify the question belongs to the session's paper. Combined with LOGIC-007, an attempt for one paper's question can be recorded against a different paper's session.

### Expected Behavior
An attempt's question belongs to its session's paper.

### Actual Behavior
Mismatched session/question pairs are accepted silently.

### Evidence
`main.py:895-898` checks session existence only.

### Impact
Potential cross-paper contamination of session scores (enabled by LOGIC-007).

### Recommended Fix
Verify the question's `paper_id` matches the session's `paper_id`; reject with 422 otherwise.

### Confidence
Medium

---

## LOGIC-052

### Severity
Low

### Location
`frontend/components/ClientLayout.tsx:47-101` (state-only routing).

### Description
Navigation is entirely client state (`useState<Route>`); there is no URL routing. Refresh or bookmark always returns to Home, and all cross-screen context (`paperId`, `sessionId`, `questionId`) is lost. Deep links are impossible.

### Expected Behavior
Routes map to URLs; refresh preserves location and (ideally) context.

### Actual Behavior
Any reload drops the user to Home and clears selection state.

### Evidence
`ClientLayout.tsx:48` `const [route, setRoute] = useState<Route>("home")`; no router.

### Impact
Frustrating navigation; lost work context on reload; no shareable links.

### Recommended Fix
Use Next.js routing (or sync route/state to the URL).

### Confidence
High

---

## LOGIC-053

### Severity
Low

### Location
`frontend/components/screens/University.tsx:22-26`; `Tutor.tsx`; `Booklet.tsx`; nav in `shell/Sidebar.tsx:25-44`.

### Description
University always shows "No target universities configured" (no universities table), while its heading promises "Predicted grades vs entry requirements." Tutor and Booklet are permanent stubs. All three occupy primary nav slots.

### Expected Behavior
Unimplemented features are hidden/marked "coming soon," not presented as working.

### Actual Behavior
Three nav items lead to perpetual empty states; University's subtitle overpromises.

### Evidence
`University.tsx:22-26` always-rendered EmptyState; `Tutor.tsx`/`Booklet.tsx` stubs.

### Impact
Dead ends that overstate capability.

### Recommended Fix
Disable/mark the nav items, or soften the headings.

### Confidence
High

---

## LOGIC-054

### Severity
Low

### Location
`frontend/components/screens/Timer.tsx:11`; `Weaknesses.tsx:173`.

### Description
Subject filter chip lists are hardcoded arrays (`["all","physics","maths","fmaths","chemistry","cs"]`). If the enrolled-subject set changes, filters drift from the data and a subject present in the data but absent from the list cannot be filtered.

### Expected Behavior
Derive chips from the data / `SUBJECT_LABELS`.

### Actual Behavior
Hardcoded chip lists can mismatch real subjects.

### Evidence
`Timer.tsx:11` `const SUBJECT_FILTERS = [...]`; `Weaknesses.tsx:173` inline array.

### Impact
Minor; potential filter/data mismatch.

### Recommended Fix
Build the chip list from data.

### Confidence
Medium

---

## LOGIC-055

### Severity
Low

### Location
`db/seed_syllabus.py:74, 94, 109, 124-136`.

### Description
`total_spec_points += 1` increments for every spec point regardless of whether `INSERT OR IGNORE` actually inserted, so re-runs report "N spec points seeded" even when zero new rows were written. In `--dry-run`, parent IDs are simulated as `-1`, so the counts are entirely simulated.

### Expected Behavior
Report real inserts (`rowcount`/`total_changes`); label dry-run as "would seed."

### Actual Behavior
Attempted-insert counts presented as actual; dry-run counts are fictional.

### Evidence
`seed_syllabus.py:124-136`.

### Impact
Misleading setup output (looks like work happened on idempotent re-runs).

### Recommended Fix
Use `cursor.rowcount`/`conn.total_changes`; clarify dry-run wording.

### Confidence
High

---

## LOGIC-056

### Severity
Low

### Location
`config/settings.py:15` (`DATA_DIR.mkdir(exist_ok=True)`); `:28-29` (Telegram defaults); `agents/delivery/telegram_agent.py:71` (`start_bot`).

### Description
`DATA_DIR.mkdir(exist_ok=True)` lacks `parents=True`, so a nested overridden `DATA_DIR` whose parent is missing raises `FileNotFoundError` (line 16 uses `parents=True` for the diagrams dir, but not for `DATA_DIR` itself). `TELEGRAM_BOT_TOKEN`/`CHAT_ID` default to `""` with no startup validation; `start_bot()` builds an `Application` with an empty token and only fails at runtime.

### Expected Behavior
Robust dir creation; explicit config validation at startup.

### Actual Behavior
Possible crash on nested `DATA_DIR`; opaque runtime failure on missing Telegram config.

### Evidence
`settings.py:15` `DATA_DIR.mkdir(exist_ok=True)`.

### Impact
Minor setup brittleness.

### Recommended Fix
`DATA_DIR.mkdir(parents=True, exist_ok=True)`; validate Telegram config before starting the bot.

### Confidence
Medium

---

## LOGIC-057

### Severity
Low

### Location
`frontend/components/screens/Timer.tsx:233-234`.

### Description
The progress bar fill width is `pct = elapsed/target*100`, but the "Official time" marker is hardcoded at `left: "66.6%"`. Since `target = official * 2/3`, the official time corresponds to `pct = 150%` (off the bar), so a marker at 66.6% does not represent official time.

### Expected Behavior
The marker sits at the official-time position on the bar's scale.

### Actual Behavior
The "Official time" marker is mispositioned/misleading.

### Evidence
`Timer.tsx:234` `<div className="aos-timer-mark" style={{ left: "66.6%" }} title="Official time" />`.

### Impact
Minor visual inaccuracy.

### Recommended Fix
Compute the marker position from the actual scale, or relabel it (it currently marks the ⅔ target, not official time).

### Confidence
Medium

---

## LOGIC-058

### Severity
Low

### Location
`frontend/components/screens/QuestionReview.tsx:10` vs `backend/main.py:703`.

### Description
QuestionReview maps difficulty 5 → "Examiner trap", while the backend QotD label array maps 5 → "Trap". Same concept, two labels.

### Expected Behavior
One shared difficulty-label source.

### Actual Behavior
Difficulty 5 reads "Examiner trap" on QuestionReview but "Trap" in the Question of the Day.

### Evidence
`QuestionReview.tsx:10` `const DIFFICULTY = ["", "Recall", "Standard", "Multi-step", "Advanced", "Examiner trap"]`; `main.py:703` `[..., "Trap"]`.

### Impact
Minor copy inconsistency.

### Recommended Fix
Centralize difficulty labels.

### Confidence
High

---

## Cross-Cutting Observations

- **Phantom-table schism (root cause #1).** The briefing and FastAPI backend were written against a flat `spaced_repetition_items` table that never existed, while the schema + Curriculum Agent implement a normalized tree. This single mismatch crashes the dashboard (LOGIC-001), the briefing (LOGIC-003), examiner traps (LOGIC-004), and mastery updates (LOGIC-018). RESTART.md documents the non-existent table — documentation drift.
- **Topic → "General" collapse (root cause #2).** Hardcoded `None` topics in extraction (LOGIC-022) destroy the topic dimension, which then guts misconception ranking (LOGIC-025), interventions (LOGIC-045), and topic-scoped retrieval (LOGIC-043).
- **Two grade systems / two briefing systems.** LOGIC-005 and LOGIC-030 are duplicated, divergent sources of truth between backend and frontend. Consolidate.
- **Silent-failure pattern.** `_query`/`_scalar` swallow all `sqlite3.Error`, converting infrastructure bugs into invisible "empty data" — except where a raw `conn.execute` leaks the error and 500s the dashboard (LOGIC-001). Distinguish "missing table/setup error" from "no rows."
- **Pervasive hardcoded identity/grades.** Name, grades, exam session, greeting are hardcoded (LOGIC-010, LOGIC-011), contradicting the project's Data-Integrity #1 principle and the app's own "every number from a real query" claim.

## Verification Performed
- Reproduced LOGIC-001 at runtime: `init_all_databases()` + `seed_all()` → `spaced_repetition_items` absent; `get_dashboard()` raises `OperationalError` (HTTP 500).
- Reproduced LOGIC-004 at runtime: `_examiner_traps()` returns keys `description/topic/subject/module_code/frequency`; frontend `t.text`/`t.freq` → `None`.
- Reproduced LOGIC-009 at runtime: post-`seed_all()`, `syllabus_completion` has 0 rows.
- Verified LOGIC-016/038 by grep: no `TelegramAgent` class; no `INSERT INTO review_history`.
- Statically traced every endpoint's output shape against `frontend/lib/types.ts` and each screen's consumption; cross-checked all backend SQL table/column names against `schemas/*.sql` (markscheme, examiner, attempts, question_bank match; **progress** does not — LOGIC-001).
