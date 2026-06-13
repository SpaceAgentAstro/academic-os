# context.md — Project Context

## What This Is

An autonomous educational intelligence platform built for a single student. It processes past papers, mark schemes, and examiner reports to build a searchable knowledge base, detect misconceptions, construct adaptive revision, generate daily briefings, and deliver content via Telegram.

## Target Student

Studying concurrently:
- Pearson Edexcel IAL Mathematics (P1, P2, P3, P4, S1, S2, M1, M2, M3)
- Pearson Edexcel IAL Further Mathematics (FP1, FP2, FP3, M1, M2, M3)
- Pearson Edexcel IAL Physics (Units 1–6)
- Pearson Edexcel IAL Chemistry (Units 1–6)
- Cambridge International AS & A Level Computer Science

## Hardware

- Lenovo Legion Laptop
- Dedicated NVIDIA GPU (available for local inference if needed)
- Modern multicore CPU
- Large local storage

## Design Philosophy

This is an academic operating system meant to outlast a single exam season. It is designed to be used across years of study, preserving all progress data, processed content, and analytical intelligence across sessions and machines.

Every question ever processed remains retrievable.
Every misconception detected informs future revision.
Every examiner observation shapes what gets prioritized.

## What the System Does NOT Do

- Does not replace active study
- Does not generate exam questions from nothing (retrieval-first policy)
- Does not advance progression autonomously (Curriculum Agent requires student confirmation)

## Key Constraints

- All student data stays local (no cloud sync)
- Telegram is the sole delivery channel
- Databases use SQLite (no external database server)
- OCR must handle mathematical notation (LaTeX conversion required)

## Session Continuity

The system is fully resumable after any interruption. RESTART.md always contains the current state. A new session picks up exactly where the last one left off.

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11+), uvicorn |
| Databases | SQLite — separate `.db` file per domain |
| Package manager | `uv` (Python), `npm` (frontend) |
| Delivery | Telegram Bot API |
| OCR | pdfplumber + pytesseract + pix2tex (optional) |
| Scheduling | APScheduler |

Database files:
- `question_bank.db` — questions, papers
- `markscheme.db` — mark scheme points
- `examiner_reports.db` — observations, misconceptions
- `progress.db` — syllabus topics, mastery, spaced repetition
- `attempts.db` — sessions, attempts, per-question times

Backend entry point: `backend/main.py` (FastAPI app)
Frontend entry point: `frontend/app/page.tsx`
Start script: `./start-backend.sh`

---

## THE GOAL — Build the fully operational AcademicOS

Real data, real pipelines, real functionality.
Zero dummy data. Zero placeholder logic.
If a screen cannot show real data yet, it shows an empty state — never fabricated numbers.

**THIS IS NOT A DEMO. THIS IS THE REAL PRODUCT.**

Every number on every screen must come from a real database query.
Every interaction must write to a real database.
Every API call must hit the real FastAPI backend.
If the data does not exist yet, the screen says so honestly — it does not invent it.

---

## Before Writing Any Code

### Step 1 — Read all docs
CLAUDE.md → AGENTS.md → MEMORY.md → RESTART.md → BACKLOG.md → systemArchitecture.md

### Step 2 — Audit the databases

Run these queries and report results before continuing:

```sql
-- question_bank.db
SELECT COUNT(*) FROM questions;
SELECT COUNT(*) FROM papers;
SELECT DISTINCT subject FROM papers;
SELECT DISTINCT unit FROM questions LIMIT 20;

-- markscheme.db
SELECT COUNT(*) FROM markscheme_points;
-- if zero: extraction pipeline has not run

-- examiner_reports.db
SELECT COUNT(*) FROM observations;
SELECT COUNT(*) FROM misconceptions;
-- if zero: extraction pipeline has not run

-- progress.db
SELECT COUNT(*) FROM syllabus_topics;
SELECT COUNT(*) FROM spaced_repetition_items;
-- if zero: not seeded yet

-- attempts.db
SELECT COUNT(*) FROM attempts;
SELECT COUNT(*) FROM sessions;
```

Do not proceed past this step until you have real numbers from every database.

### Step 3 — Run extraction pipelines if needed

If `markscheme.db` is empty: run MarkschemeAgent against all `_msc_` files, confirm row count after.
If `examiner_reports.db` is empty: run ExaminerReportAgent against all `_pef_` files, confirm row count after.
If `progress.db` is empty: seed with Physics syllabus JSON first, confirm row count after.

Do not build any API endpoint that depends on empty tables. Fill the tables first.

### Step 4 — Read briefing/generator.py

Understand the current question selection logic. If it is random or sequential, fix it before the dashboard goes live.

---

## API Contract

All endpoints live in `backend/main.py`. Every endpoint queries a real SQLite database. No hardcoded returns. No mock data. Zero rows → empty array, never fabricated data.

### GET /api/dashboard
1. `progress.db` — spaced repetition due items (today's priorities by urgency)
2. `attempts.db` — last 5 sessions (real scores and times)
3. `progress.db` — mastery per subject/unit (real percentages)
4. `examiner_reports.db` — misconceptions matching weakest topics
5. `question_bank.db` — question of the day: topic = today's #1 priority, not previously attempted, difficulty 3–4, examiner trap preferred
6. `progress.db` — predicted grades (calculated from mastery)
7. `attempts.db` — streak (consecutive days with ≥1 attempt)

### GET /api/papers
```sql
SELECT id, title, subject, unit, session, year, total_marks, time_minutes
FROM papers ORDER BY subject, year DESC
```

### GET /api/papers/:id/questions
```sql
SELECT id, question_number, question_text, marks, topic, subtopic, difficulty, has_diagram
FROM questions WHERE paper_id = :id ORDER BY question_number
```

### GET /api/questions/:id
Full question intelligence: question row + grouped markscheme points + examiner observations for this topic.

### POST /api/sessions
```sql
INSERT INTO sessions (paper_id, started_at, official_time_seconds, target_time_seconds)
VALUES (...) RETURNING id
```

### PATCH /api/sessions/:id/questions/:q_id
```sql
INSERT OR REPLACE INTO question_times (session_id, question_id, time_seconds, status) VALUES (...)
```

### POST /api/sessions/:id/complete
```sql
UPDATE sessions SET ended_at = ?, total_time_seconds = ? WHERE id = :id
```

### POST /api/attempts
1. INSERT into `attempts` + `attempt_mistakes`
2. UPDATE mastery in `progress.db`:
   - `new_mastery = previous_mastery * 0.7 + attempt_score_pct * 0.3`
3. UPDATE spaced repetition interval:
   - ≥80%: increase interval
   - 60–79%: keep interval
   - <60%: reset interval, flag for review
4. Returns `attempt_id` + updated mastery score

### GET /api/subjects/:subject
Aggregated mastery, question counts, recent papers, weak topics across `attempts.db` and `progress.db`.

### GET /api/weaknesses
```sql
SELECT topic, subtopic,
  COUNT(*) as attempts,
  AVG(marks_awarded * 1.0 / marks_available) as avg_score,
  SUM(marks_available - marks_awarded) as marks_lost
FROM attempts
GROUP BY topic, subtopic ORDER BY marks_lost DESC
```
Joined with `attempt_mistakes` for failure modes and `examiner_reports` for trap flags.

---

## Design System

Visual language: dark background, crystal teal accent, honest messaging.

**Loading states:** skeleton in the exact shape of real content. CSS animation `opacity: 0.4 → 0.8 → 0.4`. Never a spinner.

**Empty states:** honest message matching the design language.
- No papers: "No sessions yet. Start your first paper to see your performance here."
- No spaced repetition: "Syllabus not yet seeded. Run the setup to begin tracking your progress."
- No examiner data: "Examiner reports not yet extracted. Run the extraction pipeline to unlock this intelligence."

**Error states:** show the error clearly. Never fall back to dummy data. Log full detail to console.

**Data freshness:** dashboard refetches every 60 seconds; all other screens refetch on navigation; timer never refetches mid-session; marking refetches on question change.

---

## Timer Behaviour

- Mount → POST /api/sessions → store session_id → start interval
- "Done with Q[n]" → PATCH session/questions, advance question, reset question timer
- "Finished paper" → POST sessions/:id/complete → navigate to marking with session_id (do not reset timer until navigation completes)
- Tab close → `beforeunload` calls complete endpoint

---

## Marking Behaviour

- Mount → load session_id from navigation state or URL → fetch questions → fetch markscheme + examiner data per question
- Mark tap → update local state immediately (zero latency), recalculate score/grade locally, do not wait for API
- "Save & next" → POST /api/attempts → wait for 200 → advance (on failure: show error, do not advance)
- Final question saved → navigate to session summary with real totals (score, grade, time, marks lost breakdown, top mistakes)

---

## Quality Gate (per screen before marking complete)

- [ ] Every number from a real DB query
- [ ] No hardcoded values in the component
- [ ] Loading state renders correctly
- [ ] Empty state renders correctly
- [ ] Error state renders correctly
- [ ] All API calls through `/lib/api.ts`
- [ ] TypeScript zero errors
- [ ] Design matches reference HTML exactly
- [ ] No console errors in normal operation
- [ ] Tested with real data from `question_bank.db`

---

## Order of Operations

Do these in exact order. Do not skip ahead. Confirm working with real data before proceeding to N+1.

1. Audit all databases — report row counts
2. Run extraction pipelines if tables empty
3. Seed `progress.db` with Physics syllabus
4. Build `/lib/api.ts` client
5. Build `GET /api/papers` + test it
6. Build timer screen wired to real papers
7. Build `POST /api/sessions` + PATCH endpoint
8. Build `GET /api/questions/:id`
9. Build marking screen wired to real questions
10. Build `POST /api/attempts` with mastery update
11. Build `GET /api/dashboard`
12. Build home dashboard wired to real data
13. Build remaining screens in priority order
14. Wire Telegram briefing + test live send
15. End-to-end test: start paper → mark → dashboard updates → Telegram reflects it

---

## The Standard

When this is done, Mouad should be able to:

1. Open the app.
2. Select WPH14 June 2024 from real papers.
3. Start the timer — a real session is created.
4. Complete questions — real times are logged.
5. Go to marking — real markscheme appears.
6. Award marks — real attempt is saved.
7. See the dashboard update — real mastery changes.
8. Receive a Telegram briefing tomorrow morning that reflects what was practiced today.

That is the bar. Build to that bar. Nothing less is complete.
