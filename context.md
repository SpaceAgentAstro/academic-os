# context.md — Project Context

## Available Skills & Commands

```
/superpowers
/frontend-design
/stop-slop
/codereview
/context-engineering
/mem get project
/mem get design
/mem get api
/mem get stack
/mem get rules
/mem get progress
```

## Goal

**Make AcademicOS fully operational with real live data end to end.**

No dummy data. No demo mode. No placeholder numbers.
If it cannot show real data it shows nothing.

---

## What This Is

An autonomous educational intelligence platform built for a single student. It processes past papers, mark schemes, and examiner reports to build a searchable knowledge base, detect misconceptions, construct adaptive revision, generate daily briefings, and deliver content via Telegram.

## Target Student

Studying concurrently:
- Pearson Edexcel IAL Mathematics (P1, P2, P3, P4, S1, S2, M1, M2, M3)
- Pearson Edexcel IAL Further Mathematics (FP1, FP2, FP3, M1, M2, M3)
- Pearson Edexcel IAL Physics (Units 1–6)
- Pearson Edexcel IAL Chemistry (Units 1–6)
- Cambridge International AS & A Level Computer Science

## Hardware

- Lenovo Legion Laptop
- Dedicated NVIDIA GPU (available for local inference if needed)
- Modern multicore CPU
- Large local storage

## Design Philosophy

This is an academic operating system meant to outlast a single exam season. It is designed to be used across years of study, preserving all progress data, processed content, and analytical intelligence across sessions and machines.

Every question ever processed remains retrievable.
Every misconception detected informs future revision.
Every examiner observation shapes what gets prioritized.

## What the System Does NOT Do

- Does not replace active study
- Does not generate exam questions from nothing (retrieval-first policy)
- Does not advance progression autonomously (Curriculum Agent requires student confirmation)

## Key Constraints

- All student data stays local (no cloud sync)
- Telegram is the sole delivery channel
- Databases use SQLite (no external database server)
- OCR must handle mathematical notation (LaTeX conversion required)

## Session Continuity

The system is fully resumable after any interruption. RESTART.md always contains the current state. A new session picks up exactly where the last one left off.
