"""Generate today's briefing and send it to Telegram immediately.

One-command verification of the delivery pipeline and the manual-send entry point.
The APScheduler morning job (agents/infrastructure/scheduler_agent.py) runs the same
generate -> format -> send path at BRIEFING_TIME.

Usage:
    DATA_DIR=<repo>/data python scripts/send_briefing.py          # send
    DATA_DIR=<repo>/data python scripts/send_briefing.py --dry    # print only, no send

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env (from @BotFather).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from briefing.generator import generate_daily_briefing, format_for_telegram
    from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    briefing = generate_daily_briefing()
    text = format_for_telegram(briefing)

    if "--dry" in sys.argv:
        print(text)
        return 0

    token_ok = TELEGRAM_BOT_TOKEN and ":" in TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN.split(":")[0].isdigit()
    if not token_ok or not TELEGRAM_CHAT_ID or "placeholder" in TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured in .env.")
        print("Get a token from @BotFather, then set both in .env. Run again to send.")
        print("\n--- Briefing that WOULD be sent ---\n")
        print(text)
        return 1

    from agents.delivery.telegram_agent import send_daily_briefing
    asyncio.run(send_daily_briefing(text))
    print(f"Sent daily briefing ({len(text)} chars) to chat {TELEGRAM_CHAT_ID}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
