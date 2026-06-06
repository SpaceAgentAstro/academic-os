---
tags: [architecture, databases]
---

# Database Map

## Six SQLite Databases

### progress.db
- Owner: **Curriculum Agent**
- Tables: `subjects`, `modules`, `topics`, `subtopics`, `specification_points`, `syllabus_completion`, `review_history`
- Key: Spaced repetition state, status progression, confidence scores
- [[Schemas/progress.sql]]

### question_bank.db
- Owner: Past Paper Agent
- Tables: `papers`, `questions`, `question_spec_links`, `question_topics`, `question_tags`
- Key: All extracted questions with difficulty 1–5, command word, tags
- [[Schemas/question_bank.sql]]

### markscheme.db
- Owner: Markscheme Agent
- Tables: `markscheme_entries`, `mark_alternatives`, `required_terms`, `follow_through_rules`
- Mark types: M, A, B, E, Q, dM, ddM, ft
- [[Schemas/markscheme.sql]]

### examiner_reports.db
- Owner: Examiner Report Agent (reports, observations) + Misconception Agent (misconceptions)
- Tables: `reports`, `observations`, `misconceptions`, `misconception_sources`, `corrective_interventions`
- [[Schemas/examiner_reports.sql]]

### diagrams.db
- Owner: Diagram Agent
- Tables: `diagrams`, `diagram_question_links`
- 20+ diagram types across all subjects
- [[Schemas/diagrams.sql]]

### analytics.db
- Owner: Analytics Agent
- Tables: `mastery_scores`, `revision_sessions`, `session_questions`, `performance_trends`, `topic_difficulty_ratings`
- [[Schemas/analytics.sql]]
