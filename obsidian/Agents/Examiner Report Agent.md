---
tags: [agent, analysis]
file: agents/analysis/examiner_report_agent.py
---

# Examiner Report Agent

## Functions

| Function | Purpose |
|----------|---------|
| `extract_observations(pdf_path)` | Returns `list[Observation]` |
| `ingest_report(pdf_path, paper_id, year, session, subject, module_code)` | Full pipeline to examiner_reports.db |

## Observation Types

| Type | Trigger Keywords |
|------|----------------|
| `misconception` | "misconception", "misunderstand", "confused" |
| `common_error` | "error", "mistake", "incorrect", "wrong" |
| `weak_area` | "weak", "struggle", "difficult", "poor" |
| `command_word_failure` | "command word", "did not read", "failed to" |
| `positive_note` | "well", "good", "correct", "excellent" |
| `emphasis` | Default for anything else |

## Emphasis Levels

- **3** (High): "many", "most", "majority", "frequently"
- **2** (Medium): "some", "several", "number of"
- **1** (Low): Mentioned without frequency qualifier

## Related
- [[Schemas/examiner_reports.sql]]
- [[Agents/Curriculum Agent]]
