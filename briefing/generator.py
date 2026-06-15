from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Legacy-Markdown metacharacters that break Telegram parsing when they appear in
# interpolated database content (topic names, question text, descriptions).
_MD_SPECIALS = re.compile(r"([_*\[\]`])")


def _md(value: Any) -> str:
    """Escape Telegram Markdown metacharacters in dynamic content so the briefing
    keeps its *bold* structure without tripping the parser (RT-018)."""
    return _MD_SPECIALS.sub(r"\\\1", str(value))


@dataclass
class DailyBriefing:
    date: str
    section1_academic: str = ""       # Academic Intelligence
    section2_curriculum: str = ""     # Curriculum Progress
    section3_revision: str = ""       # Adaptive Revision
    section4_status: str = ""         # System Status


def get_due_review_items(limit: int = 10) -> list[dict[str, Any]]:
    """Spaced-repetition items due today, overdue first, weakest first.

    Falls back to the lowest-mastery topics when nothing is due yet —
    never returns an empty list while spaced_repetition_items has rows.
    """
    from config.settings import DB_PROGRESS
    from db.models import get_db

    with get_db(DB_PROGRESS) as conn:
        rows = conn.execute(
            """
            SELECT topic, subtopic, unit, subject, due_date, mastery,
                   ease_factor, interval_days,
                   CAST(JULIANDAY('now') - JULIANDAY(due_date) AS INTEGER) AS days_overdue
            FROM spaced_repetition_items
            WHERE due_date <= DATE('now')
            ORDER BY
                CASE WHEN due_date < DATE('now') THEN 0 ELSE 1 END,
                mastery ASC,
                due_date ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                """
                SELECT topic, subtopic, unit, subject, due_date, mastery,
                       ease_factor, interval_days, 0 AS days_overdue
                FROM spaced_repetition_items
                ORDER BY mastery ASC
                LIMIT 5
                """,
            ).fetchall()
        return [dict(r) for r in rows]


def select_question_of_the_day() -> dict[str, Any] | None:
    """Pick today's question from the #1 priority topic.

    Fallback chain (never silently None while questions exist):
    1. Unattempted difficulty-3/4 question on the priority topic
    2. Any difficulty-3/4 question on the priority topic
    3. Any unattempted difficulty-3/4 question
    4. Most recently ingested question
    """
    from config.settings import DB_QUESTION_BANK, DB_ATTEMPTS
    from db.models import get_db

    due = get_due_review_items(limit=1)
    priority_topic = due[0]["topic"] if due else None

    base = """
        SELECT q.id, q.question_number, q.marks, q.difficulty, q.raw_text,
               q.command_word, p.subject, p.module_code, p.paper_code, p.session
        FROM questions q
        JOIN papers p ON p.id = q.paper_id
    """

    with get_db(DB_QUESTION_BANK) as conn:
        conn.execute("ATTACH DATABASE ? AS att", (str(DB_ATTEMPTS),))
        attempted = "q.id NOT IN (SELECT question_id FROM att.attempts)"
        text_ok = "q.raw_text IS NOT NULL AND LENGTH(TRIM(q.raw_text)) > 40"

        candidates: list[tuple[str, tuple]] = []
        if priority_topic:
            topic_join = (
                "JOIN question_topics qt ON qt.question_id = q.id "
                "AND qt.topic LIKE '%' || ? || '%'"
            )
            candidates.append((
                f"{base} {topic_join} WHERE q.difficulty IN (3,4) AND {attempted} AND {text_ok} "
                "ORDER BY RANDOM() LIMIT 1",
                (priority_topic,),
            ))
            candidates.append((
                f"{base} {topic_join} WHERE q.difficulty IN (3,4) AND {text_ok} "
                "ORDER BY RANDOM() LIMIT 1",
                (priority_topic,),
            ))
        candidates.append((
            f"{base} WHERE q.difficulty IN (3,4) AND {attempted} AND {text_ok} "
            "ORDER BY RANDOM() LIMIT 1",
            (),
        ))
        candidates.append((
            f"{base} WHERE {text_ok} ORDER BY q.id DESC LIMIT 1",
            (),
        ))

        for sql, params in candidates:
            row = conn.execute(sql, params).fetchone()
            if row:
                result = dict(row)
                result["priority_topic"] = priority_topic
                return result

    return None


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
                f"{_md(top['description'][:120])}"
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
                parts = [f"{_md(mod)}: {pct}%" for mod, pct in sorted(coverage.items())]
                lines.append(f"• *{subject}*: {', '.join(parts)}")
            else:
                lines.append(f"• *{subject}*: No syllabus data yet — seed progress.db")
        except Exception:
            logger.exception("Coverage lookup failed for %s", subject)
            lines.append(f"• *{subject}*: coverage unavailable")

    return "\n".join(lines)


def _section3_adaptive_revision() -> str:
    """Retrieval-first: due reviews, question of the day, then revision packs."""
    from agents.delivery.revision_agent import build_revision_pack

    lines = ["*Adaptive Revision*"]

    due = get_due_review_items(limit=5)
    if due:
        lines.append("_Due for review:_")
        for item in due:
            overdue = item.get("days_overdue") or 0
            flag = f" (overdue {overdue}d)" if overdue > 0 else ""
            lines.append(
                f"• {_md(item['subject'])} {_md(item['unit'])} — {_md(item['topic'])} "
                f"(mastery {item['mastery']:.0%}){flag}"
            )

    qod = select_question_of_the_day()
    if qod:
        lines.append(
            f"\n_Question of the day_ — {_md(qod['subject'])} {_md(qod['module_code'])} "
            f"Q{_md(qod['question_number'])} ({qod['marks']} marks, difficulty {qod['difficulty']}):"
        )
        lines.append(_md((qod["raw_text"] or "").strip()[:280]))

    subjects = ["Mathematics", "Physics", "Chemistry", "Computer Science"]

    for subject in subjects:
        try:
            pack = build_revision_pack(subject=subject, max_questions=5)
            if pack.questions:
                q_count = len(pack.questions)
                marks = sum(q.get("marks", 0) for q in pack.questions)
                topics = _md(", ".join(pack.focus_topics[:3]) or "General")
                lines.append(
                    f"• *{subject}* — {q_count} questions, {marks} marks, "
                    f"~{pack.estimated_duration_minutes}min | Topics: {topics}"
                )
                if pack.misconception_reminders:
                    lines.append(f"  ⚠️ Watch: {_md(pack.misconception_reminders[0][:100])}")
            else:
                lines.append(f"• *{subject}*: No questions available — ingest past papers first")
        except Exception:
            logger.exception("Revision pack build failed for %s", subject)
            lines.append(f"• *{subject}*: revision pack unavailable")

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


if __name__ == "__main__":
    import sys

    briefing = generate_daily_briefing()
    text = format_for_telegram(briefing)
    print(text)

    if "--send-now" in sys.argv:
        import asyncio

        from agents.delivery.telegram_agent import send_daily_briefing

        asyncio.run(send_daily_briefing(text))
        print("\n[sent to Telegram]")
