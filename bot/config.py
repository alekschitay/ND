"""Configuration utilities for the bot service."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

DEFAULT_DATABASE_PATH: Path = Path("data/bot.sqlite3")
DEFAULT_CHECK_INTERVAL: int = 30
DEFAULT_REQUEST_TIMEOUT: int = 10

ENV_DATABASE_PATH = "BOT_DATABASE_PATH"
ENV_CHECK_INTERVAL = "BOT_CHECK_INTERVAL"
ENV_REQUEST_TIMEOUT = "BOT_REQUEST_TIMEOUT"
ENV_TOKEN = "BOT_TOKEN"


def _parse_int(name: str, raw_value: Optional[str], default: int) -> int:
    """Parse an integer environment variable with friendly errors.

    Parameters
    ----------
    name:
        The name of the environment variable.
    raw_value:
        The string value fetched from the environment, if any.
    default:
        The fallback value when ``raw_value`` is empty.

    Returns
    -------
    int
        The parsed integer or ``default`` when ``raw_value`` is not provided.

    Raises
    ------
    ValueError
        If ``raw_value`` is not a valid integer string.
    """

    if raw_value in (None, ""):
        return default

    try:
        return int(raw_value)
    except ValueError as exc:  # pragma: no cover - defensive code
        raise ValueError(f"{name} must be an integer, got {raw_value!r}") from exc


@dataclass(slots=True)
class Settings:
    """Runtime settings for the bot service."""

    token: str
    database_path: Path
    check_interval: int
    request_timeout: int

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "Settings":
        """Create a :class:`Settings` instance populated from the environment."""

        env = dict(os.environ if environ is None else environ)

        token = env.get(ENV_TOKEN, "").strip()
        if not token:
            raise RuntimeError(
                f"Missing bot token. Please set the {ENV_TOKEN} environment variable."
            )

        raw_database_path = env.get(ENV_DATABASE_PATH, "").strip()
        database_path = Path(raw_database_path) if raw_database_path else DEFAULT_DATABASE_PATH

        check_interval = _parse_int(
            ENV_CHECK_INTERVAL, env.get(ENV_CHECK_INTERVAL), DEFAULT_CHECK_INTERVAL
        )
        request_timeout = _parse_int(
            ENV_REQUEST_TIMEOUT, env.get(ENV_REQUEST_TIMEOUT), DEFAULT_REQUEST_TIMEOUT
        )

        return cls(
            token=token,
            database_path=database_path,
            check_interval=check_interval,
            request_timeout=request_timeout,
        )
