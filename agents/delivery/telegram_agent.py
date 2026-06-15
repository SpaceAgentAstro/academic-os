from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 4096


@lru_cache(maxsize=1)
def _get_bot(token: str):
    """Return a cached Bot. python-telegram-bot Bot objects own an HTTPX pool;
    reconstructing one per send churns connections (RT-016), so reuse a single
    instance keyed on the token."""
    from telegram import Bot

    return Bot(token=token)


def _authorized(update: Any) -> bool:
    """True only if the message comes from the configured chat. Interactive bot
    commands must not answer arbitrary Telegram users (AOS-005)."""
    from config.settings import TELEGRAM_CHAT_ID

    chat = getattr(update, "effective_chat", None)
    if chat is None or not TELEGRAM_CHAT_ID:
        return False
    return str(chat.id) == str(TELEGRAM_CHAT_ID)


async def _safe_reply(update: Any, text: str) -> None:
    """Reply with Markdown, falling back to plain text if Telegram rejects the
    entities (question/topic text routinely contains _ * [ ` — RT-005)."""
    from telegram.error import TelegramError

    try:
        await update.message.reply_text(text, parse_mode="Markdown")
    except TelegramError as exc:
        logger.warning("Markdown reply rejected, retrying as plain text: %s", exc)
        await update.message.reply_text(text)


async def send_message(text: str, parse_mode: str = "Markdown") -> None:
    """Send a message to the configured Telegram chat.

    Splits messages longer than 4096 characters into chunks.
    """
    from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    from telegram.error import TelegramError

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram bot token and chat ID must be configured in the environment.")

    bot = _get_bot(TELEGRAM_BOT_TOKEN)
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
    """Start the Telegram bot and register command handlers.

    Every handler is restricted to the configured TELEGRAM_CHAT_ID via a
    per-handler chat filter, so only the owner can invoke commands (AOS-005).
    """
    from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    from telegram.ext import Application, CommandHandler, filters

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    chat_filter = filters.Chat(chat_id=int(TELEGRAM_CHAT_ID)) if TELEGRAM_CHAT_ID else None
    for name, handler in (
        ("briefing", _cmd_briefing), ("status", _cmd_status),
        ("coverage", _cmd_coverage), ("quiz", _cmd_quiz),
        ("revise", _cmd_revise), ("progress", _cmd_progress),
    ):
        app.add_handler(CommandHandler(name, handler, filters=chat_filter))

    logger.info("Starting Academic OS Telegram bot")
    app.run_polling()


async def _cmd_briefing(update: Any, context: Any) -> None:
    if not _authorized(update):
        return
    from briefing.generator import generate_daily_briefing, format_for_telegram
    briefing = generate_daily_briefing()
    text = format_for_telegram(briefing)
    await _safe_reply(update, text)


async def _cmd_status(update: Any, context: Any) -> None:
    if not _authorized(update):
        return
    from briefing.generator import _section4_system_status
    await _safe_reply(update, _section4_system_status())


async def _cmd_coverage(update: Any, context: Any) -> None:
    if not _authorized(update):
        return
    from briefing.generator import _section2_curriculum_progress
    await _safe_reply(update, _section2_curriculum_progress())


async def _cmd_quiz(update: Any, context: Any) -> None:
    """Return a single practice question from the question bank.

    Usage: /quiz [subject]
    Subject defaults to Mathematics when not specified.
    """
    if not _authorized(update):
        return
    from agents.delivery.retrieval_agent import get_questions

    args = context.args if context.args else []
    subject = " ".join(args).strip().title() if args else "Mathematics"

    questions = get_questions(subject=subject, limit=1)
    if not questions:
        await _safe_reply(update, f"No questions found for *{subject}*. Ingest past papers first.")
        return

    q = questions[0]
    text = (
        f"*Quiz — {subject}*\n"
        f"_{q.get('paper_code', '?')} {q.get('session', '')} · "
        f"Q{q['question_number']} · {q.get('marks', '?')} marks · "
        f"Difficulty {q.get('difficulty', '?')}/5_\n\n"
        f"{q.get('raw_text') or q.get('latex_text') or '(No question text extracted)'}"
    )
    await _safe_reply(update, text)


async def _cmd_revise(update: Any, context: Any) -> None:
    """Build and send a revision pack for a subject.

    Usage: /revise [subject]
    Subject defaults to Mathematics when not specified.
    """
    if not _authorized(update):
        return
    from agents.delivery.revision_agent import build_revision_pack

    args = context.args if context.args else []
    subject = " ".join(args).strip().title() if args else "Mathematics"

    pack = build_revision_pack(subject=subject, max_questions=10)

    if not pack.questions:
        await _safe_reply(update, f"No questions available for *{subject}*. Ingest past papers first.")
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

    await _safe_reply(update, "\n".join(lines))


async def _cmd_progress(update: Any, context: Any) -> None:
    """Show specification coverage per module for all subjects."""
    if not _authorized(update):
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
            lines.append(f"• *{subject}*: coverage unavailable")

    await _safe_reply(update, "\n".join(lines))


if __name__ == "__main__":
    start_bot()
