# Errors — Issue Tracking & Remediation System

This directory drives the autonomous remediation cycle for AcademicOS.

## Files

| File          | Scope                                                        |
|---------------|-------------------------------------------------------------|
| `logic.md`    | Incorrect business rules, data flows, UI/data mismatches    |
| `security.md` | Vulnerabilities (injection, secrets, auth, unsafe IO)       |
| `syntax.md`   | Code/config that fails to compile, build, or parse          |
| `runtime.md`  | Crashes, leaks, race conditions, performance, instability   |
| `history/`    | Timestamped audit reports, one per remediation run          |

## Workflow

1. Open issues are logged under **Open Issues** in the relevant file using the
   commented entry template.
2. A remediation run reads all four files, fixes root causes, validates
   (syntax check + test suite + targeted security checks), and records what it
   did in `history/YYYY-MM-DD_HH-MM.md`.
3. Resolved issues are removed from the four files (which stay empty when there
   is no open work) and traced to their history entry.

## Target state

All four issue files contain no open entries, the project builds cleanly, the
full test suite passes, and `history/` holds the complete chronological audit
trail.
