from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


def start_scheduler() -> None:
    """Start APScheduler with all configured jobs and run until interrupted."""
    from config.settings import BRIEFING_TIME
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone="Europe/London")

    schedule_daily_briefing(scheduler, BRIEFING_TIME)
    schedule_paper_scan(scheduler, interval_minutes=60)

    logger.info("Academic OS scheduler starting — briefing at %s", BRIEFING_TIME)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


def _parse_briefing_time(time_str: str) -> tuple[int, int]:
    """Parse an HH:MM time, falling back to the documented default 07:30 on any
    malformed value rather than crashing the whole scheduler (RT-017)."""
    from datetime import datetime

    try:
        parsed = datetime.strptime(time_str.strip(), "%H:%M")
        return parsed.hour, parsed.minute
    except (ValueError, AttributeError):
        logger.warning("Invalid BRIEFING_TIME %r; falling back to 07:30", time_str)
        return 7, 30


def schedule_daily_briefing(scheduler: object, time_str: str) -> None:
    """Register the daily briefing job at time_str (HH:MM, 24h)."""
    hour, minute = _parse_briefing_time(time_str)

    def _job() -> None:
        from briefing.generator import generate_daily_briefing, format_for_telegram
        briefing = generate_daily_briefing()
        text = format_for_telegram(briefing)
        asyncio.run(_send(text))

    scheduler.add_job(  # type: ignore[union-attr]
        _job,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily_briefing",
        replace_existing=True,
    )
    logger.info("Daily briefing scheduled at %02d:%02d", hour, minute)


def schedule_paper_scan(scheduler: object, interval_minutes: int = 60) -> None:
    """Register a periodic job to scan papers/ for new PDFs and ingest them."""
    def _job() -> None:
        from agents.analysis.past_paper_agent import scan_papers_directory, ingest_paper
        unprocessed = scan_papers_directory()
        for pdf in unprocessed:
            try:
                ingest_paper(pdf)
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", pdf.name, exc)

    scheduler.add_job(  # type: ignore[union-attr]
        _job,
        trigger="interval",
        minutes=interval_minutes,
        id="paper_scan",
        replace_existing=True,
    )
    logger.info("Paper scan scheduled every %d minutes", interval_minutes)


async def _send(text: str) -> None:
    from agents.delivery.telegram_agent import send_daily_briefing
    await send_daily_briefing(text)
