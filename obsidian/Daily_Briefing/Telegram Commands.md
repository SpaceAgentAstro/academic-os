---
tags: [telegram, commands]
---

# Telegram Bot Commands

The bot is started with `python -m agents.delivery.telegram_agent` (via scheduler).

## Available Commands

### /briefing
Generates and sends the full 4-section daily briefing immediately.

### /status
Returns Section 4 (System Status):
- Papers and questions count
- Reports and misconceptions count
- Data directory

### /coverage
Returns Section 2 (Curriculum Progress):
- Per-module coverage % for all subjects

## Configuration

Set in `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
BRIEFING_TIME=07:30
```

## Starting the Bot
```bash
cd academic-os
uv run python -c "
import asyncio
from agents.delivery.telegram_agent import start_bot
asyncio.run(start_bot())
"
```

## Related
- [[Daily_Briefing/Format]]
- [[Agents/Telegram Agent]]
