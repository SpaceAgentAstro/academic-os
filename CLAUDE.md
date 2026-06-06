# CLAUDE.md — Academic OS

## Project Identity

Autonomous educational intelligence platform for:
- Pearson Edexcel IAL Mathematics (P1–P4, S1–S2, M1–M3)
- Pearson Edexcel IAL Further Mathematics (FP1–FP3, M1–M3)
- Pearson Edexcel IAL Physics (Units 1–6)
- Pearson Edexcel IAL Chemistry (Units 1–6)
- Cambridge International AS & A Level Computer Science

## Document Loading Order

Always consult in this order before acting:
1. CLAUDE.md (this file)
2. AGENTS.md
3. MEMORY.md
4. RESTART.md
5. BACKLOG.md
6. context.md
7. systemArchitecture.md
8. conventions.md
9. testing.md
10. roadmaps.md

## Governing Principles (Priority Order)

1. Data Integrity
2. Educational Accuracy
3. Retrieval Before Generation
4. Architectural Consistency
5. Maintainability
6. Scalability
7. Automation

## Hard Rules

- Never delete user data
- Never overwrite a database without backup
- Never move root files without approval
- Never reorganize the repository without approval
- Never duplicate existing functionality
- Architecture precedes implementation
- Documentation precedes implementation
- Data model precedes implementation
- Always retrieve before generating; generation is last resort

## Agent Ownership

Every agent owns its domain exclusively. The Curriculum Agent is the sole authority for syllabus progression. No other agent may write to `progress.db` syllabus state.

## Development Phases

| Phase | Focus |
|-------|-------|
| 1 | Architecture, documentation, schemas |
| 2 | Ingestion, OCR, extraction |
| 3 | Classification, markschemes, examiner reports, diagrams |
| 4 | Retrieval, adaptive revision |
| 5 | Curriculum agents |
| 6 | Daily briefing, Telegram delivery, scheduler |

## Python Environment

- Python 3.11+
- SQLite (separate .db file per domain)
- `uv` for package management
- Virtual environment at `.venv/`
