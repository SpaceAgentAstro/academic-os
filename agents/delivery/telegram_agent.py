from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_message(text: str, parse_mode: str = "Markdown") -> None:
    """Send a message to the configured Telegram chat."""
    raise NotImplementedError


async def send_daily_briefing(briefing_text: str) -> None:
    """Format and send the daily briefing to Telegram."""
    raise NotImplementedError


async def start_bot() -> None:
    """Start the Telegram bot and register command handlers."""
    raise NotImplementedError
