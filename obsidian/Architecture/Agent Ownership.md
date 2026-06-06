---
tags: [architecture, agents]
---

# Agent Ownership

## Database Write Authority

| Database | Write Authority | Notes |
|----------|----------------|-------|
| `progress.db` | **Curriculum Agent ONLY** | No other agent may write syllabus state |
| `question_bank.db` | Past Paper Agent | Questions, papers, topics, tags |
| `markscheme.db` | Markscheme Agent | Mark entries, alternatives |
| `examiner_reports.db` | Examiner Report Agent + Misconception Agent | Observations, misconceptions |
| `diagrams.db` | Diagram Agent | Extracted and classified images |
| `analytics.db` | Analytics Agent | Sessions, mastery, trends |

## 15 Agents

### Analysis
- **Past Paper Agent** — detect type, extract metadata, extract questions, ingest to DB
- **Markscheme Agent** — parse mark scheme, link to questions, write to markscheme.db
- **Examiner Report Agent** — extract observations, upsert misconceptions
- **Diagram Agent** — classify images, store to diagrams.db
- **Misconception Agent** — aggregate and prioritise recurring misconceptions

### Delivery
- **Retrieval Agent** — cross-DB query interface (no writes)
- **Revision Agent** — build revision packs, mock exams, spaced repetition queue
- **Telegram Agent** — message delivery, bot command handlers

### Infrastructure
- **Curriculum Agent** — sole write authority for progress.db
- **Analytics Agent** — mastery scores, performance trends
- **Scheduler Agent** — APScheduler cron/interval jobs

### Subject Specialists
- Maths Agent, Further Maths Agent, Physics Agent, Chemistry Agent, CS Agent

## Related Notes
- [[System Overview]]
- [[Database Map]]
