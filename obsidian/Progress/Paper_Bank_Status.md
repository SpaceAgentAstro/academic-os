# Paper Bank Status

## Summary

| Metric | Value |
|--------|-------|
| Question papers ingested | **331** |
| Questions extracted | **2,260** |
| Question tags | ~3,331 |
| Topic associations | ~2,497 |

*Last updated: 2026-06-07*

---

## Coverage by Subject

### Mathematics (2021–2026)
- **153 question papers** across P1–P4, M1–M2, S1–S3
- Source: `papers/maths/` — 651 PDFs (question papers + mark schemes + examiner reports)
- Module codes: WMA11–14 (2018 spec), WME03–04 (pre-2018), WME01–02 (Mechanics)

| Module | Description | Papers |
|--------|-------------|--------|
| P1 | Pure Mathematics 1 | 18 |
| P2 | Pure Mathematics 2 | 17 |
| P3 | Pure Mathematics 3 | 29 |
| P4 | Pure Mathematics 4 | 17 |
| M1 | Mechanics 1 | 16 |
| M2 | Mechanics 2 | 16 |
| S1 | Statistics 1 | 15 |
| S2 | Statistics 2 | 14 |
| S3 | Statistics 3 | 11 |

### Physics (2019–2026)
- **127 question papers** across Units 1–6
- Source: `papers/physics/` — 244 PDFs
- Module codes: WPH11–16 (2018 spec), WPH01–06 (pre-2018 spec)

| Unit | Papers |
|------|--------|
| Unit 1 | 23 |
| Unit 2 | 21 |
| Unit 3 | 23 |
| Unit 4 | 21 |
| Unit 5 | 19 |
| Unit 6 | 20 |

### Further Mathematics (2021–2026)
- **50 question papers** across FP1–FP3, D1
- Source: `papers/further_maths/` — 98 PDFs
- Module codes: WFM01–03 (FP1–3), WDM11 (Decision Maths)

| Module | Papers |
|--------|--------|
| FP1 | 12 |
| FP2 | 13 |
| FP3 | 13 |
| D1  | 12 |

---

## Known Gaps

None. All 993 PDFs are fully ingested. The 3 pre-2018 January 2019 Physics papers
(`WPH01_01_que_20190111.pdf`, `WPH05_01_que_20190117.pdf`, `WPH06_01_que_20190128.pdf`)
were scanned — resolved by installing poppler and fixing the extractor regex to handle
the pre-2018 MCQ format (`1 An object...` without punctuation).

---

## File Structure

```
papers/
├── maths/         651 PDFs  (question papers + mark schemes + examiner reports)
├── physics/       244 PDFs
└── further_maths/  98 PDFs
```

Total: **993 PDFs** copied from Downloads on 2026-06-07.

---

## Links

- [[Past_Paper_Agent]] — ingestion pipeline
- [[Question_Bank_Schema]] — database schema
- [[Markscheme_Agent]] — mark scheme processing (future)
- [[Examiner_Report_Agent]] — examiner report processing (future)
