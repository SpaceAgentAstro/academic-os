---
tags: [agent, revision]
file: agents/delivery/revision_agent.py
---

# Revision Agent

## Functions

| Function | Purpose |
|----------|---------|
| `build_revision_pack(subject, module_code, max_questions)` | Priority: weak topics → hard questions → misconceptions |
| `build_mock_exam(subject, module_code, total_marks)` | Difficulty-proportional exam assembly |
| `get_spaced_repetition_queue(limit)` | Spec points due for review (from progress.db) |

## Revision Pack Priority

1. **Weak topics** from analytics.performance_trends (low avg_score, last 30 days)
2. **High-difficulty questions** (difficulty 4–5) not yet attempted
3. **Misconception reminders** from top 5 active misconceptions

## Mock Exam Distribution

| Difficulty | Target % |
|-----------|---------|
| 2 | 30% |
| 3 | 40% |
| 4 | 20% |
| 5 | 10% |

## Related
- [[Agents/Retrieval Agent]]
- [[Schemas/analytics.sql]]
