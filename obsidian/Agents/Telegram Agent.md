---
tags: [agent, delivery, telegram]
file: agents/delivery/telegram_agent.py
---

# Telegram Agent

## Functions

| Function | Description |
|----------|------------|
| `send_message(text, parse_mode)` | Send with auto-split for >4096 chars |
| `send_daily_briefing(briefing_text)` | Calls send_message with Markdown |
| `start_bot()` | Register handlers and start polling |

## Bot Commands
- `/briefing` → `generate_daily_briefing()` → formatted and sent
- `/status` → Section 4 only
- `/coverage` → Section 2 only

## Message Splitting
`_split_message(text, 4096)` splits at newline boundaries.
Fallback to plain text if Markdown parse fails.

## Related
- [[Daily_Briefing/Format]]
- [[Agents/Scheduler Agent]]
