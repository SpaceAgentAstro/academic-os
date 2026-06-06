from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def start_scheduler() -> None:
    """Start APScheduler with all configured jobs."""
    raise NotImplementedError


def schedule_daily_briefing(time_str: str) -> None:
    """Schedule daily briefing generation and Telegram delivery at time_str (HH:MM)."""
    raise NotImplementedError


def schedule_paper_scan(interval_minutes: int = 60) -> None:
    """Schedule periodic scan of papers/ directory for new PDFs."""
    raise NotImplementedError
