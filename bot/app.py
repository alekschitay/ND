"""Telegram-like bot runtime utilities."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib import error, parse, request

from .config import Settings

API_BASE = "https://api.telegram.org"


@dataclass(slots=True)
class BotApp:
    """Simple long-polling bot implementation."""

    settings: Settings

    def __post_init__(self) -> None:
        self._base_url = f"{API_BASE}/bot{self.settings.token}"
        self._logger = logging.getLogger("bot")

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------
    def _api_call(self, method: str, **params: Any) -> Dict[str, Any]:
        """Perform an API call against the Telegram HTTP interface."""

        query = parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self._base_url}/{method}"
        if query:
            url = f"{url}?{query}"

        req = request.Request(url)
        try:
            with request.urlopen(req, timeout=self.settings.request_timeout) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP error {exc.code} calling {method}: {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - defensive network guard
            raise RuntimeError(f"Failed to reach API for {method}: {exc.reason}") from exc

    # ------------------------------------------------------------------
    # High-level operations
    # ------------------------------------------------------------------
    def get_updates(self, offset: Optional[int] = None) -> Dict[str, Any]:
        """Fetch new updates from the Telegram API."""

        return self._api_call(
            "getUpdates",
            offset=offset,
            timeout=self.settings.request_timeout,
        )

    def send_message(self, chat_id: int, text: str) -> Dict[str, Any]:
        """Send a message to the given chat."""

        return self._api_call("sendMessage", chat_id=chat_id, text=text)

    # ------------------------------------------------------------------
    # Update processing
    # ------------------------------------------------------------------
    def handle_update(self, update: Dict[str, Any]) -> None:
        """Handle a single update payload."""

        message = update.get("message")
        if not message:
            return

        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            self._logger.debug("Skipping message without chat id: %s", update)
            return

        text = message.get("text")
        if text:
            reply = f"Echo: {text}"
        else:
            reply = "I can only echo text messages right now."

        self._logger.info("Replying to chat %s", chat_id)
        self.send_message(chat_id=chat_id, text=reply)

    def process_updates(self, updates: Iterable[Dict[str, Any]]) -> None:
        for update in updates:
            try:
                self.handle_update(update)
            except Exception as exc:  # pragma: no cover - defensive code
                self._logger.exception("Error while handling update: %s", exc)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the long-polling loop."""

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        self._logger.info("Bot is starting with polling interval %s seconds.", self.settings.check_interval)

        offset: Optional[int] = None
        while True:
            try:
                response = self.get_updates(offset)
            except Exception as exc:
                self._logger.error("Failed to fetch updates: %s", exc)
                time.sleep(self.settings.check_interval)
                continue

            if not response.get("ok", False):
                description = response.get("description", "unknown error")
                self._logger.error("API returned failure: %s", description)
                time.sleep(self.settings.check_interval)
                continue

            updates = response.get("result", [])
            if updates:
                offset = updates[-1]["update_id"] + 1
                self.process_updates(updates)
            else:
                self._logger.debug("No updates received.")

            time.sleep(self.settings.check_interval)


def main() -> None:
    """Entrypoint used by ``python -m bot``."""

    settings = Settings.from_env()
    BotApp(settings=settings).run()


if __name__ == "__main__":  # pragma: no cover - CLI hook
    main()
