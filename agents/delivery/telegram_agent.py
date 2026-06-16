from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 4096
_bot_singleton: Any = None


def _get_bot() -> Any:
    """Return a cached Bot instance (avoids churning the HTTPX pool per send)."""
    global _bot_singleton
    from config.settings import TELEGRAM_BOT_TOKEN

    if _bot_singleton is None:
        from telegram import Bot

        _bot_singleton = Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot_singleton


def _is_authorized(update: Any) -> bool:
    """True only when the message comes from the configured chat."""
    from config.settings import TELEGRAM_CHAT_ID

    if not TELEGRAM_CHAT_ID:
        return False
    chat = getattr(update, "effective_chat", None)
    return chat is not None and str(chat.id) == str(TELEGRAM_CHAT_ID)


async def _reply(update: Any, text: str, parse_mode: str | None = "Markdown") -> None:
    """Reply to a command, falling back to plain text if Markdown won't parse.

    Any send error (commonly a Telegram Markdown parse failure on content with
    `_`, `*`, `[`, `` ` ``) triggers a plain-text retry so the user always gets
    a readable reply. Catches broadly so this never depends on the optional
    `telegram` package being importable in the failure path.
    """
    try:
        await update.message.reply_text(text, parse_mode=parse_mode)
    except Exception:
        try:
            await update.message.reply_text(text)
        except Exception:
            logger.exception("Failed to reply to Telegram command")


async def send_message(text: str, parse_mode: str = "Markdown") -> None:
    """Send a message to the configured Telegram chat.

    Splits messages longer than 4096 characters into chunks.
    """
    from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    from telegram.error import TelegramError

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram bot token and chat ID must be configured in the environment.")

    bot = _get_bot()
    chunks = _split_message(text, _MAX_MESSAGE_LENGTH)
    for chunk in chunks:
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=chunk,
                parse_mode=parse_mode,
            )
        except TelegramError as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            # Retry without parse_mode (plain text fallback)
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk)
            except TelegramError:
                logger.exception("Telegram delivery failed completely")
                raise


def _split_message(text: str, max_len: int) -> list[str]:
    """Split long text into chunks respecting max_len."""
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


async def send_daily_briefing(briefing_text: str) -> None:
    """Format and send the daily briefing to Telegram."""
    logger.info("Sending daily briefing (%d chars)", len(briefing_text))
    await send_message(briefing_text, parse_mode="Markdown")


def start_bot() -> None:
    """Start the Telegram bot and register command handlers."""
    from config.settings import TELEGRAM_BOT_TOKEN
    from telegram.ext import Application, CommandHandler

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("briefing", _cmd_briefing))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("coverage", _cmd_coverage))
    app.add_handler(CommandHandler("quiz", _cmd_quiz))
    app.add_handler(CommandHandler("revise", _cmd_revise))
    app.add_handler(CommandHandler("progress", _cmd_progress))

    logger.info("Starting Academic OS Telegram bot")
    app.run_polling()


async def _cmd_briefing(update: Any, context: Any) -> None:
    if not _is_authorized(update):
        return
    from briefing.generator import generate_daily_briefing, format_for_telegram
    briefing = generate_daily_briefing()
    text = format_for_telegram(briefing)
    await _reply(update, text)


async def _cmd_status(update: Any, context: Any) -> None:
    if not _is_authorized(update):
        return
    from briefing.generator import _section4_system_status
    await _reply(update, _section4_system_status())


async def _cmd_coverage(update: Any, context: Any) -> None:
    if not _is_authorized(update):
        return
    from briefing.generator import _section2_curriculum_progress
    await _reply(update, _section2_curriculum_progress())


async def _cmd_quiz(update: Any, context: Any) -> None:
    """Return a single practice question from the question bank.

    Usage: /quiz [subject]
    Subject defaults to Mathematics when not specified.
    """
    if not _is_authorized(update):
        return
    from agents.delivery.retrieval_agent import get_questions

    args = context.args if context.args else []
    subject = " ".join(args).strip().title() if args else "Mathematics"

    questions = get_questions(subject=subject, limit=1)
    if not questions:
        await _reply(update, f"No questions found for *{subject}*. Ingest past papers first.")
        return

    q = questions[0]
    text = (
        f"*Quiz — {subject}*\n"
        f"_{q.get('paper_code', '?')} {q.get('session', '')} · "
        f"Q{q['question_number']} · {q.get('marks', '?')} marks · "
        f"Difficulty {q.get('difficulty', '?')}/5_\n\n"
        f"{q.get('raw_text') or q.get('latex_text') or '(No question text extracted)'}"
    )
    await _reply(update, text)


async def _cmd_revise(update: Any, context: Any) -> None:
    """Build and send a revision pack for a subject.

    Usage: /revise [subject]
    Subject defaults to Mathematics when not specified.
    """
    if not _is_authorized(update):
        return
    from agents.delivery.revision_agent import build_revision_pack

    args = context.args if context.args else []
    subject = " ".join(args).strip().title() if args else "Mathematics"

    pack = build_revision_pack(subject=subject, max_questions=10)

    if not pack.questions:
        await _reply(update, f"No questions available for *{subject}*. Ingest past papers first.")
        return

    marks = sum(q.get("marks", 0) for q in pack.questions)
    topics = ", ".join(pack.focus_topics[:3]) or "General"
    lines = [
        f"*Revision Pack — {subject}*",
        f"_{len(pack.questions)} questions · {marks} marks · "
        f"~{pack.estimated_duration_minutes} min_",
        f"Focus: {topics}",
    ]

    if pack.misconception_reminders:
        lines.append(f"\n⚠️ *Watch out:* {pack.misconception_reminders[0][:120]}")

    lines.append("\n*Questions:*")
    for q in pack.questions:
        code = q.get("paper_code", "?")
        session = q.get("session", "")
        lines.append(
            f"• Q{q['question_number']} · {code} {session} · "
            f"{q.get('marks', '?')} marks · diff {q.get('difficulty', '?')}/5"
        )

    await _reply(update, "\n".join(lines))


async def _cmd_progress(update: Any, context: Any) -> None:
    """Show specification coverage per module for all subjects."""
    if not _is_authorized(update):
        return
    from agents.infrastructure.curriculum_agent import get_specification_coverage

    subjects = [
        ("Mathematics", "MATH"),
        ("Further Mathematics", "FM"),
        ("Physics", "PHY"),
        ("Chemistry", "CHEM"),
        ("Computer Science", "CS"),
    ]

    lines = ["*Curriculum Progress*"]
    for subject, _code in subjects:
        try:
            coverage = get_specification_coverage(subject)
            if coverage:
                parts = [f"{mod}: {pct}%" for mod, pct in sorted(coverage.items())]
                avg = round(sum(coverage.values()) / len(coverage), 1)
                lines.append(f"• *{subject}* (avg {avg}%): {', '.join(parts)}")
            else:
                lines.append(f"• *{subject}*: No syllabus data — run seed_syllabus.py")
        except Exception:
            logger.exception("Coverage lookup failed for %s", subject)
            lines.append(f"• *{subject}*: Error retrieving coverage")

    await _reply(update, "\n".join(lines))


if __name__ == "__main__":
    start_bot()
