"""Configuration helpers for the Telegram bot."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    """Bot runtime settings."""

    bot_token: str
    database_path: str = "./bot.db"
    check_interval_seconds: int = 300
    request_timeout_seconds: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN environment variable must be set with the bot token"
            )

        database_path = os.getenv("BOT_DATABASE_PATH", cls.database_path)
        interval = int(os.getenv("BOT_CHECK_INTERVAL", cls.check_interval_seconds))
        timeout = int(os.getenv("BOT_REQUEST_TIMEOUT", cls.request_timeout_seconds))
        return cls(
            bot_token=token,
            database_path=database_path,
            check_interval_seconds=interval,
            request_timeout_seconds=timeout,
        )


settings = Settings.from_env()
