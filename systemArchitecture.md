# systemArchitecture.md — System Architecture

## Overview

```
papers/ (raw PDFs)
    │
    ▼
[Past Paper Agent]
    │ triggers
    ├──▶ [OCR Agent]          → text + images
    ├──▶ [Diagram Agent]      → diagrams.db
    └──▶ [Markscheme Agent]   → markscheme.db
    │
    ▼
question_bank.db
    │
    ├──▶ [Examiner Report Agent] → examiner_reports.db
    │         │
    │         └──▶ [Misconception Agent] → examiner_reports.db
    │
    ├──▶ [Retrieval Agent]    (read-only, serves all delivery)
    │         │
    │         ├──▶ [Revision Agent]   → revision packs
    │         └──▶ [Subject Agents]   → topic queries
    │
    ├──▶ [Analytics Agent]    → analytics.db
    │
    └──▶ [Curriculum Agent]   → progress.db (SOLE WRITE AUTHORITY)
              │
              └──▶ [Scheduler Agent]
                        │
                        └──▶ [Telegram Agent] → Telegram
```

## Database Layer

### progress.db
Tracks syllabus completion and review scheduling.

Tables: `subjects`, `modules`, `topics`, `subtopics`, `specification_points`, `syllabus_completion`, `review_history`

### question_bank.db
Stores all extracted questions with full metadata.

Tables: `papers`, `questions`, `question_spec_links`, `question_topics`, `question_tags`

### markscheme.db
Stores structured marking logic.

Tables: `markscheme_entries`, `mark_alternatives`, `required_terms`

### examiner_reports.db
Stores examiner observations and derived misconceptions.

Tables: `reports`, `observations`, `misconceptions`, `corrective_interventions`

### diagrams.db
Stores extracted and classified diagrams.

Tables: `diagrams`, `diagram_question_links`

### analytics.db
Stores performance data and computed trends.

Tables: `mastery_scores`, `revision_sessions`, `performance_trends`, `topic_difficulty_ratings`

## Ingestion Pipeline

```
1. New PDF detected in papers/<subject>/
2. Past Paper Agent identifies paper type (question paper, mark scheme, examiner report)
3. For question papers:
   a. OCR Agent extracts text with layout (pdfplumber)
   b. OCR Agent extracts images (pdf2image)
   c. OCR Agent converts math images to LaTeX (pix2tex)
   d. Past Paper Agent parses question boundaries
   e. Past Paper Agent classifies each question to spec point
   f. Diagram Agent classifies extracted images
   g. Writes to question_bank.db and diagrams.db
4. For mark schemes:
   a. OCR Agent extracts text
   b. Markscheme Agent parses M/A/B/E/Q marks
   c. Links to questions in question_bank.db
   d. Writes to markscheme.db
5. For examiner reports:
   a. OCR Agent extracts text
   b. Examiner Report Agent extracts observations by question
   c. Misconception Agent derives and stores misconceptions
   d. Writes to examiner_reports.db
```

## Delivery Pipeline

```
1. Scheduler Agent triggers daily briefing at configured time
2. Briefing Generator queries:
   a. Curriculum Agent → current progression state
   b. Analytics Agent → weak topics and trends
   c. Retrieval Agent → questions for weak topics
   d. Misconception Agent → active misconceptions
   e. Past Paper Agent → newly processed papers
3. Briefing Generator assembles 4-section report
4. Telegram Agent formats and sends to student
```

## Question Classification Taxonomy

```
Subject
└── Module (e.g., P1, S2, FP3, Unit 4, Unit 2 Chemistry)
    └── Topic (e.g., Differentiation, Normal Distribution)
        └── Subtopic (e.g., Chain Rule, Z-score calculation)
            └── Specification Point (e.g., Spec ref. 3.2.1)
```

## Difficulty Scale

| Level | Description |
|-------|-------------|
| 1 | Recall |
| 2 | Standard Application |
| 3 | Multi-Step Application |
| 4 | Advanced Synthesis |
| 5 | Examiner Trap |

## Question Tags

`Proof`, `Modelling`, `Calculation`, `Interpretation`, `Evaluation`, `Data Analysis`, `Diagram Based`, `Multi Topic`

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Databases | SQLite 3 (separate files per domain) |
| PDF Extraction | pdfplumber |
| OCR (scanned) | pytesseract + Tesseract |
| Math OCR | pix2tex |
| PDF-to-image | pdf2image + poppler |
| Telegram | python-telegram-bot |
| Scheduling | APScheduler |
| Config | python-dotenv |
| Package manager | uv |
| Testing | pytest |
