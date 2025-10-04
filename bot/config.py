"""Configuration helpers for the demo concierge bot."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the bot application.

    The settings are intentionally small. They are kept flexible enough so the
    bot can be personalised via environment variables without having to touch
    the source code. The two knobs we expose are the bot's name and the greeting
    that is presented to a new user when the application starts.
    """

    bot_name: str
    greeting: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Create a :class:`Settings` instance from environment variables."""

        bot_name = os.getenv("BOT_NAME", "ConciergeBot")
        greeting = os.getenv(
            "BOT_GREETING", "Hello! I'm here to help. Ask me anything."
        )
        return cls(bot_name=bot_name, greeting=greeting)


__all__ = ["Settings"]

