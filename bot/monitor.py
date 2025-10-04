"""Background watcher tasks for venue pages."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from aiogram.exceptions import TelegramBadRequest

from .config import settings
from .db import Database, Watcher
from .parser import Event, fetch_html, parse_events

logger = logging.getLogger(__name__)


SendEventCallback = Callable[[Watcher, Event], Awaitable[None]]


class WatcherMonitor:
    """Schedules background checks for watcher subscriptions."""

    def __init__(self, db: Database, send_callback: SendEventCallback) -> None:
        self._db = db
        self._send_callback = send_callback
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        watchers = await self._db.list_watchers()
        for watcher in watchers:
            await self._seed_known_events(watcher)
            self._ensure_task(watcher)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    def _ensure_task(self, watcher: Watcher) -> None:
        if watcher.id in self._tasks:
            return
        task = asyncio.create_task(self._run_watcher(watcher))
        self._tasks[watcher.id] = task

    async def add_watcher(self, watcher: Watcher) -> None:
        await self._seed_known_events(watcher)
        self._ensure_task(watcher)

    async def remove_watcher(self, watcher_id: int) -> None:
        task = self._tasks.pop(watcher_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _run_watcher(self, watcher: Watcher) -> None:
        logger.info("Starting watcher task for %s", watcher)
        interval = settings.check_interval_seconds
        timeout = settings.request_timeout_seconds

        while self._running:
            try:
                html = await fetch_html(watcher.url, timeout=timeout)
                events = parse_events(watcher.url, html)
                await self._process_events(watcher, events)
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.exception("Failed to update watcher %s: %s", watcher.id, exc)
            await asyncio.sleep(interval)

    async def _process_events(self, watcher: Watcher, events: list[Event]) -> None:
        event_ids = [event.event_id for event in events]
        new_ids = await self._db.filter_new_events(watcher.id, event_ids)
        if not new_ids:
            return
        id_to_event = {event.event_id: event for event in events}
        for event_id in new_ids:
            event = id_to_event[event_id]
            try:
                await self._send_callback(watcher, event)
            except TelegramBadRequest:
                logger.warning("Failed to send event %s to user %s", event.link, watcher.user_id)
        await self._db.add_known_events(watcher.id, new_ids)

    async def _seed_known_events(self, watcher: Watcher) -> None:
        try:
            html = await fetch_html(watcher.url, timeout=settings.request_timeout_seconds)
        except Exception:  # pragma: no cover - best effort logging
            logger.exception("Failed to seed watcher %s", watcher.id)
            return
        events = parse_events(watcher.url, html)
        await self._db.add_known_events(watcher.id, (event.event_id for event in events))
