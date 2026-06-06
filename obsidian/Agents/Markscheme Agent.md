---
tags: [agent, analysis]
file: agents/analysis/markscheme_agent.py
---

# Markscheme Agent

## Functions

| Function | Purpose |
|----------|---------|
| `parse_markscheme(pdf_path)` | Returns `dict[question_number, list[MarkEntry]]` |
| `ingest_markscheme(pdf_path, paper_id)` | Parse + link to questions + write to markscheme.db |

## Mark Types

| Code | Meaning |
|------|---------|
| M | Method mark |
| A | Accuracy mark (depends on M) |
| B | Independent (free-standing) mark |
| E | Evaluation / explanation |
| Q | Quality of written communication |
| dM | Dependent method (requires preceding M) |
| ddM | Double-dependent method |
| ft | Follow-through |

## Related
- [[Schemas/markscheme.sql]]
- [[Agents/Past Paper Agent]]
