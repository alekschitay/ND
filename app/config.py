from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_path: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "events.db")
    check_interval_minutes: int = 10


def get_settings() -> Settings:
    # Load variables from .env if present
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    return Settings(telegram_bot_token=token)
