from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 4096


async def send_message(text: str, parse_mode: str = "Markdown") -> None:
    """Send a message to the configured Telegram chat.

    Splits messages longer than 4096 characters into chunks.
    """
    from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    from telegram import Bot
    from telegram.error import TelegramError

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
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


async def start_bot() -> None:
    """Start the Telegram bot and register command handlers."""
    from config.settings import TELEGRAM_BOT_TOKEN
    from telegram.ext import Application, CommandHandler

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("briefing", _cmd_briefing))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("coverage", _cmd_coverage))

    logger.info("Starting Academic OS Telegram bot")
    await app.run_polling()


async def _cmd_briefing(update: Any, context: Any) -> None:
    from briefing.generator import generate_daily_briefing, format_for_telegram
    briefing = generate_daily_briefing()
    text = format_for_telegram(briefing)
    await update.message.reply_text(text, parse_mode="Markdown")


async def _cmd_status(update: Any, context: Any) -> None:
    from briefing.generator import _section4_system_status
    await update.message.reply_text(_section4_system_status(), parse_mode="Markdown")


async def _cmd_coverage(update: Any, context: Any) -> None:
    from briefing.generator import _section2_curriculum_progress
    await update.message.reply_text(_section2_curriculum_progress(), parse_mode="Markdown")
