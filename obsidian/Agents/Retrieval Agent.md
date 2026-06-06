---
tags: [agent, retrieval]
file: agents/delivery/retrieval_agent.py
---

# Retrieval Agent

**Read-only** — never writes to any database.

## Functions

| Function | Source DB | Filters |
|----------|-----------|---------|
| `get_questions(subject, module_code, topic, difficulty, tags, limit, exclude_ids)` | question_bank.db | All combinable |
| `get_questions_by_spec_point(spec_point_id, limit)` | question_bank.db | — |
| `get_misconceptions(subject, module_code, active_only)` | examiner_reports.db | active flag |
| `get_weak_topics(subject, window_days)` | analytics.db | rolling window |
| `get_diagrams(subject, diagram_type, limit)` | diagrams.db | type filter |

## SQL Pattern

All functions accept an optional `*_conn` parameter for in-memory SQLite (testability).
Dynamic WHERE clause built via `clauses: list[str]` + `params: list[Any]` — never f-string SQL.

## Related
- [[Agents/Revision Agent]]
- [[Architecture/Database Map]]
