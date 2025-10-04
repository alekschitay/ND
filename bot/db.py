"""SQLite storage for watcher subscriptions and known events."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterable, Sequence

import aiosqlite


@dataclass(slots=True)
class Watcher:
    id: int
    user_id: int
    url: str


@dataclass(slots=True)
class KnownEvent:
    watcher_id: int
    event_id: str


class Database:
    """Thin async wrapper around aiosqlite."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        # Ensure directory exists
        if self._path.parent != Path(""):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            async with aiosqlite.connect(self._path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watchers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        url TEXT NOT NULL,
                        UNIQUE(user_id, url)
                    )
                    """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS known_events (
                        watcher_id INTEGER NOT NULL,
                        event_id TEXT NOT NULL,
                        PRIMARY KEY (watcher_id, event_id),
                        FOREIGN KEY (watcher_id) REFERENCES watchers(id) ON DELETE CASCADE
                    )
                    """
                )
                await db.commit()

    @asynccontextmanager
    async def _acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._lock:
            async with aiosqlite.connect(self._path) as connection:
                connection.row_factory = aiosqlite.Row
                yield connection

    async def add_watcher(self, user_id: int, url: str) -> Watcher:
        async with self._acquire() as db:
            await db.execute(
                "INSERT OR IGNORE INTO watchers(user_id, url) VALUES (?, ?)",
                (user_id, url),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT id, user_id, url FROM watchers WHERE user_id = ? AND url = ?",
                (user_id, url),
            )
            row = await cursor.fetchone()
            assert row, "Watcher must exist after insertion"
            return Watcher(id=row["id"], user_id=row["user_id"], url=row["url"])

    async def remove_watcher(self, user_id: int, url: str) -> Watcher | None:
        async with self._acquire() as db:
            cursor = await db.execute(
                "SELECT id, user_id, url FROM watchers WHERE user_id = ? AND url = ?",
                (user_id, url),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            await db.execute(
                "DELETE FROM watchers WHERE id = ?",
                (row["id"],),
            )
            await db.commit()
            return Watcher(id=row["id"], user_id=row["user_id"], url=row["url"])

    async def list_watchers(self, user_id: int | None = None) -> Sequence[Watcher]:
        query = "SELECT id, user_id, url FROM watchers"
        params: tuple[object, ...] = ()
        if user_id is not None:
            query += " WHERE user_id = ?"
            params = (user_id,)
        async with self._acquire() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [Watcher(id=row["id"], user_id=row["user_id"], url=row["url"]) for row in rows]

    async def add_known_events(self, watcher_id: int, event_ids: Iterable[str]) -> None:
        async with self._acquire() as db:
            await db.executemany(
                "INSERT OR IGNORE INTO known_events(watcher_id, event_id) VALUES (?, ?)",
                ((watcher_id, event_id) for event_id in event_ids),
            )
            await db.commit()

    async def filter_new_events(
        self, watcher_id: int, event_ids: Iterable[str]
    ) -> list[str]:
        ids = list(event_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        query = (
            "SELECT event_id FROM known_events WHERE watcher_id = ? AND event_id IN ("
            + placeholders
            + ")"
        )
        async with self._acquire() as db:
            cursor = await db.execute(query, (watcher_id, *ids))
            existing = {row["event_id"] for row in await cursor.fetchall()}
        return [event_id for event_id in ids if event_id not in existing]
