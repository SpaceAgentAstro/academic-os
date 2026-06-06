# AGENTS.md — Agent Definitions and Ownership

## Subject Agents

### Maths Agent
- **File**: `agents/subject/maths_agent.py`
- **Ownership**: IAL Mathematics (P1–P4, S1–S2, M1–M3)
- **Writes**: None (read-only from question_bank.db, progress.db, analytics.db)
- **Cannot**: Modify syllabus state

### Further Maths Agent
- **File**: `agents/subject/further_maths_agent.py`
- **Ownership**: IAL Further Mathematics (FP1–FP3, M1–M3)
- **Writes**: None
- **Cannot**: Modify syllabus state

### Physics Agent
- **File**: `agents/subject/physics_agent.py`
- **Ownership**: IAL Physics (Units 1–6)
- **Writes**: None
- **Cannot**: Modify syllabus state

### Chemistry Agent
- **File**: `agents/subject/chemistry_agent.py`
- **Ownership**: IAL Chemistry (Units 1–6)
- **Writes**: None
- **Cannot**: Modify syllabus state

### Computer Science Agent
- **File**: `agents/subject/cs_agent.py`
- **Ownership**: Cambridge AS & A Level CS
- **Writes**: None
- **Cannot**: Modify syllabus state

---

## Analysis Agents

### Past Paper Agent
- **File**: `agents/analysis/past_paper_agent.py`
- **Ownership**: Past paper ingestion pipeline
- **Writes**: `question_bank.db`
- **Inputs**: Raw PDF files in `papers/`
- **Outputs**: Structured questions in `question_bank.db`
- **Coordinates**: OCR Agent, Diagram Agent, Markscheme Agent

### OCR Agent
- **File**: `agents/analysis/ocr_agent.py`
- **Ownership**: PDF text and image extraction
- **Writes**: None (returns data to caller)
- **Tools**: pdfplumber, pytesseract, pdf2image, pix2tex

### Diagram Agent
- **File**: `agents/analysis/diagram_agent.py`
- **Ownership**: Diagram detection, classification, storage
- **Writes**: `diagrams.db`

### Markscheme Agent
- **File**: `agents/analysis/markscheme_agent.py`
- **Ownership**: Mark scheme extraction and structuring
- **Writes**: `markscheme.db`
- **Mark Types**: M (method), A (accuracy), B (independent), E (evaluation), Q (quality)

### Examiner Report Agent
- **File**: `agents/analysis/examiner_report_agent.py`
- **Ownership**: Examiner report processing
- **Writes**: `examiner_reports.db`

### Misconception Agent
- **File**: `agents/analysis/misconception_agent.py`
- **Ownership**: Misconception database construction
- **Writes**: `examiner_reports.db` (misconceptions table)
- **Reads**: `examiner_reports.db`, `question_bank.db`

---

## Delivery Agents

### Retrieval Agent
- **File**: `agents/delivery/retrieval_agent.py`
- **Ownership**: All database querying
- **Writes**: None (read-only across all databases)
- **Rule**: Always retrieve; never generate if retrieval is possible

### Revision Agent
- **File**: `agents/delivery/revision_agent.py`
- **Ownership**: Revision pack generation
- **Writes**: None (generates content, does not persist)
- **Reads**: `progress.db`, `analytics.db`, `question_bank.db`, `examiner_reports.db`
- **Prioritizes**: Weak topics → Difficult topics → Long-unreviewed → High-misconception → Examiner-emphasis

### Telegram Agent
- **File**: `agents/delivery/telegram_agent.py`
- **Ownership**: Telegram bot and message delivery
- **Writes**: None (delivery only)
- **Config**: Bot token in `.env`

---

## Infrastructure Agents

### Scheduler Agent
- **File**: `agents/infrastructure/scheduler_agent.py`
- **Ownership**: Scheduled task execution
- **Writes**: None (triggers other agents)
- **Triggers**: Daily briefing, paper processing, review intervals

### Analytics Agent
- **File**: `agents/infrastructure/analytics_agent.py`
- **Ownership**: Performance tracking and trend analysis
- **Writes**: `analytics.db`
- **Reads**: `question_bank.db`, `progress.db`

### Curriculum Agent
- **File**: `agents/infrastructure/curriculum_agent.py`
- **Ownership**: Syllabus state — SOLE AUTHORITY
- **Writes**: `progress.db` (syllabus progression only)
- **Authority**: No other agent may write syllabus progression state
- **Requires**: Student confirmation before advancing any topic

---

## Database Write Authority

| Database | Write Authority |
|----------|----------------|
| `progress.db` | Curriculum Agent ONLY |
| `question_bank.db` | Past Paper Agent |
| `markscheme.db` | Markscheme Agent |
| `examiner_reports.db` | Examiner Report Agent, Misconception Agent |
| `diagrams.db` | Diagram Agent |
| `analytics.db` | Analytics Agent |

## Communication Protocol

1. Shared databases with defined ownership (primary)
2. Direct Python function calls within same process
3. SQLite-backed task queue for async operations (Phase 6)
