---
tags: [principles, rules]
---

# Governing Principles

## Priority Order (highest to lowest)

1. **Data Integrity** — never delete or corrupt stored data
2. **Educational Accuracy** — all content must be educationally correct
3. **Retrieval Before Generation** — query databases first; generate only as last resort
4. **Architectural Consistency** — follow established patterns and agent ownership
5. **Maintainability** — code must be readable and testable
6. **Scalability** — design for years of exam data accumulation
7. **Automation** — reduce manual effort over time

## Hard Rules

| Rule | Rationale |
|------|-----------|
| Never delete user data | Past papers and answers are irreplaceable |
| Never overwrite DB without backup | SQLite rollback protects against corruption |
| Never move root files without approval | Breaks imports and git history |
| Never reorganise repo without approval | Architecture is intentional |
| Architecture before implementation | Prevents tech debt |
| Documentation before implementation | Ensures thinking precedes coding |
| Retrieval before generation | LLM hallucinations are an exam risk |

## Why SQLite over PostgreSQL
- No server process required (local machine, offline capable)
- Separate files per domain → clean ownership boundaries
- WAL mode → safe concurrent reads during briefing generation
- Cross-platform → runs on Lenovo Legion (Windows) and macOS

## Related
- [[Architecture/Agent Ownership]]
- [[Dashboard]]
