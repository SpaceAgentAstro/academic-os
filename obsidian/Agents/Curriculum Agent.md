---
tags: [agent, progress, critical]
file: agents/infrastructure/curriculum_agent.py
---

# Curriculum Agent

> ⚠️ **SOLE WRITE AUTHORITY** for `progress.db` syllabus state.
> No other agent may call `advance_topic`, `update_completion`, or `schedule_review`.

## Functions

| Function | Purpose |
|----------|---------|
| `advance_topic(spec_point_id, new_status, confidence)` | Move spec point forward (blocks backwards moves) |
| `update_completion(spec_point_id, status, confidence, notes)` | Update any completion field |
| `get_current_progression(subject, module_code)` | Coverage dict: {total, by_status, coverage_pct} |
| `get_next_review_queue(limit)` | Spec points due for review today |
| `schedule_review(spec_point_id, outcome)` | Set next_review via spaced repetition |
| `get_specification_coverage(subject)` | Per-module coverage % |

## Status Progression

```
not_started → in_progress → taught → reviewed → mastered
```
Backwards moves are silently ignored.

## Spaced Repetition Intervals

| Outcome | Confidence 1 | 2 | 3 | 4 | 5 |
|---------|-------------|---|---|---|---|
| correct | 1d | 3d | 7d | 14d | 30d |
| partial | 1d | 1d | 3d | 7d | 14d |
| incorrect | 1d | 1d | 1d | 1d | 3d |

## Related
- [[Schemas/progress.sql]]
- [[Architecture/Agent Ownership]]
