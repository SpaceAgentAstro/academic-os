from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DailyBriefing:
    date: str
    section1_academic: str = ""       # Academic Intelligence
    section2_curriculum: str = ""     # Curriculum Progress
    section3_revision: str = ""       # Adaptive Revision
    section4_status: str = ""         # System Status


def _section1_academic_intelligence() -> str:
    """Retrieval-first: pull latest misconceptions and examiner findings."""
    from agents.delivery.retrieval_agent import get_misconceptions

    lines = ["*Academic Intelligence*"]
    subjects = ["Mathematics", "Further Mathematics", "Physics", "Chemistry", "Computer Science"]
    total_misconceptions = 0
    for subj in subjects:
        misconceptions = get_misconceptions(subject=subj, active_only=True)
        if misconceptions:
            top = misconceptions[0]
            lines.append(
                f"• *{subj}* — Top misconception ({top['frequency']}x seen): "
                f"{top['description'][:120]}"
            )
            total_misconceptions += len(misconceptions)

    if total_misconceptions == 0:
        lines.append("• No active misconceptions flagged. Ingest examiner reports to populate.")

    lines.append(f"\n_Total active misconceptions tracked: {total_misconceptions}_")
    return "\n".join(lines)


def _section2_curriculum_progress() -> str:
    """Retrieval-first: pull per-subject coverage from progress.db."""
    from agents.infrastructure.curriculum_agent import get_specification_coverage

    lines = ["*Curriculum Progress*"]
    subjects = [
        ("Mathematics", "MATH"),
        ("Further Mathematics", "FM"),
        ("Physics", "PHY"),
        ("Chemistry", "CHEM"),
        ("Computer Science", "CS"),
    ]

    for subject, _code in subjects:
        try:
            coverage = get_specification_coverage(subject)
            if coverage:
                parts = [f"{mod}: {pct}%" for mod, pct in sorted(coverage.items())]
                lines.append(f"• *{subject}*: {', '.join(parts)}")
            else:
                lines.append(f"• *{subject}*: No syllabus data yet — seed progress.db")
        except Exception as exc:
            lines.append(f"• *{subject}*: Error — {exc}")

    return "\n".join(lines)


def _section3_adaptive_revision() -> str:
    """Retrieval-first: build revision priorities from analytics + question bank."""
    from agents.delivery.revision_agent import build_revision_pack

    lines = ["*Adaptive Revision*"]
    subjects = ["Mathematics", "Physics", "Chemistry", "Computer Science"]

    for subject in subjects:
        try:
            pack = build_revision_pack(subject=subject, max_questions=5)
            if pack.questions:
                q_count = len(pack.questions)
                marks = sum(q.get("marks", 0) for q in pack.questions)
                topics = ", ".join(pack.focus_topics[:3]) or "General"
                lines.append(
                    f"• *{subject}* — {q_count} questions, {marks} marks, "
                    f"~{pack.estimated_duration_minutes}min | Topics: {topics}"
                )
                if pack.misconception_reminders:
                    lines.append(f"  ⚠️ Watch: {pack.misconception_reminders[0][:100]}")
            else:
                lines.append(f"• *{subject}*: No questions available — ingest past papers first")
        except Exception as exc:
            lines.append(f"• *{subject}*: Error — {exc}")

    return "\n".join(lines)


def _section4_system_status() -> str:
    """Pull paper counts and database health metrics."""
    from config.settings import DB_QUESTION_BANK, DB_EXAMINER, DATA_DIR
    from db.models import get_db

    lines = ["*System Status*"]
    try:
        with get_db(DB_QUESTION_BANK) as conn:
            paper_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            q_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        lines.append(f"• Papers indexed: {paper_count} | Questions: {q_count}")
    except Exception:
        lines.append("• question_bank.db: not yet initialized")

    try:
        with get_db(DB_EXAMINER) as conn:
            report_count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
            misc_count   = conn.execute("SELECT COUNT(*) FROM misconceptions WHERE is_active=1").fetchone()[0]
        lines.append(f"• Examiner reports: {report_count} | Active misconceptions: {misc_count}")
    except Exception:
        lines.append("• examiner_reports.db: not yet initialized")

    lines.append(f"• Data directory: {DATA_DIR}")
    lines.append(f"• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def generate_daily_briefing() -> DailyBriefing:
    """Assemble the 4-section daily briefing from live database state.

    Always retrieves before generating — databases are the source of truth.
    """
    today = date.today().isoformat()
    briefing = DailyBriefing(date=today)

    briefing.section1_academic  = _section1_academic_intelligence()
    briefing.section2_curriculum = _section2_curriculum_progress()
    briefing.section3_revision  = _section3_adaptive_revision()
    briefing.section4_status    = _section4_system_status()

    logger.info("Daily briefing generated for %s", today)
    return briefing


def format_for_telegram(briefing: DailyBriefing) -> str:
    """Format a DailyBriefing into Telegram-compatible Markdown (MarkdownV2-safe)."""
    header = f"📚 *Academic OS — Daily Briefing*\n_{briefing.date}_\n"
    separator = "\n" + "─" * 30 + "\n"
    sections = [
        briefing.section1_academic,
        briefing.section2_curriculum,
        briefing.section3_revision,
        briefing.section4_status,
    ]
    body = separator.join(s for s in sections if s)
    return header + separator + body
