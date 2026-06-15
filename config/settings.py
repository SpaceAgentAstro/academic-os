from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
PAPERS_DIR = BASE_DIR / "papers"
DIAGRAMS_DIR = DATA_DIR / "diagrams"

DATA_DIR.mkdir(exist_ok=True)
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

# Database paths
DB_PROGRESS       = DATA_DIR / "progress.db"
DB_QUESTION_BANK  = DATA_DIR / "question_bank.db"
DB_MARKSCHEME     = DATA_DIR / "markscheme.db"
DB_EXAMINER       = DATA_DIR / "examiner_reports.db"
DB_DIAGRAMS       = DATA_DIR / "diagrams.db"
DB_ANALYTICS      = DATA_DIR / "analytics.db"
DB_ATTEMPTS       = DATA_DIR / "attempts.db"

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str   = os.getenv("TELEGRAM_CHAT_ID", "")

# --- API security / deployment ---------------------------------------------
# Optional shared secret. When set, every non-health API route requires a
# matching `X-API-Key` (or `Authorization: Bearer <key>`) header. Left empty
# for local development, in which case a startup warning is emitted.
API_KEY: str = os.getenv("API_KEY", "")

# Comma-separated list of allowed CORS origins for the deployed frontend.
# Defaults to local dev origins; set ALLOWED_ORIGINS in production to the
# real frontend origin(s) (e.g. "https://academic-os.vercel.app").
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    ).split(",")
    if o.strip()
]

# Per-client request budget (sliding 60s window) for basic abuse protection.
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

# Briefing schedule (24h time, local timezone)
BRIEFING_TIME: str = os.getenv("BRIEFING_TIME", "07:30")

# OCR settings
TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
PIX2TEX_ENABLED: bool = os.getenv("PIX2TEX_ENABLED", "true").lower() == "true"

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
