---
tags: [agent, infrastructure, scheduler]
file: agents/infrastructure/scheduler_agent.py
---

# Scheduler Agent

## Functions

| Function | Trigger | Job |
|----------|---------|-----|
| `start_scheduler()` | Manual start | Registers all jobs and blocks |
| `schedule_daily_briefing(scheduler, time_str)` | cron (HH:MM) | generate + send briefing |
| `schedule_paper_scan(scheduler, interval_minutes)` | interval (60min) | scan papers/ and ingest |

## Starting

```bash
cd academic-os
PYTHONPATH=. .venv/bin/python -c "
from agents.infrastructure.scheduler_agent import start_scheduler
start_scheduler()
"
```

## Configuration
- `BRIEFING_TIME=07:30` in `.env`
- Scheduler timezone: `Europe/London`

## Related
- [[Agents/Telegram Agent]]
- [[Agents/Past Paper Agent]]
