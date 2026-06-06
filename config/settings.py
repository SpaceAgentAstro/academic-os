from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PAPERS_DIR = BASE_DIR / "papers"
DIAGRAMS_DIR = BASE_DIR / "data" / "diagrams"

DATA_DIR.mkdir(exist_ok=True)
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

# Database paths
DB_PROGRESS       = DATA_DIR / "progress.db"
DB_QUESTION_BANK  = DATA_DIR / "question_bank.db"
DB_MARKSCHEME     = DATA_DIR / "markscheme.db"
DB_EXAMINER       = DATA_DIR / "examiner_reports.db"
DB_DIAGRAMS       = DATA_DIR / "diagrams.db"
DB_ANALYTICS      = DATA_DIR / "analytics.db"

# Telegram
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str   = os.environ["TELEGRAM_CHAT_ID"]

# Briefing schedule (24h time, local timezone)
BRIEFING_TIME: str = os.getenv("BRIEFING_TIME", "07:30")

# OCR settings
TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
PIX2TEX_ENABLED: bool = os.getenv("PIX2TEX_ENABLED", "true").lower() == "true"

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
