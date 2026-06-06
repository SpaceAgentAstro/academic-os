---
tags: [briefing, telegram]
file: briefing/generator.py
---

# Daily Briefing Format

Delivered every day at 07:30 (configurable via `BRIEFING_TIME` env var) via Telegram.

## Four Sections

### Section 1: Academic Intelligence
- Top misconception per subject (frequency + description)
- Sourced from `examiner_reports.db → misconceptions`

### Section 2: Curriculum Progress
- Per-module coverage % for all 5 subjects
- Sourced from `progress.db → syllabus_completion`

### Section 3: Adaptive Revision
- Per-subject: question count, marks, estimated time, focus topics
- Weak topics first (from `analytics.db`), then hard questions
- Misconception warnings inline

### Section 4: System Status
- Papers indexed, questions in DB
- Examiner reports count, active misconceptions
- Data directory path, generation timestamp

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/briefing` | Full 4-section daily briefing on demand |
| `/status` | Section 4 only (system status) |
| `/coverage` | Section 2 only (curriculum progress) |

## Message Splitting
Messages >4096 chars are automatically split at newline boundaries.

## Related
- [[Agents/Telegram Agent]]
- [[Architecture/System Overview]]
