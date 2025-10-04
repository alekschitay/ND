from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

DB_SCHEMA = r"""
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, url),
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    event_url TEXT NOT NULL,
    title TEXT,
    date_text TEXT,
    image_url TEXT,
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(url, event_url)
);
"""


@dataclass
class Event:
    event_url: str
    title: Optional[str]
    date_text: Optional[str]
    image_url: Optional[str]


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._conn() as conn:
            conn.executescript(DB_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add_user(self, user_id: int) -> None:
        with self._conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))

    def add_subscription(self, user_id: int, url: str) -> None:
        with self._conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            conn.execute(
                "INSERT OR IGNORE INTO subscriptions(user_id, url) VALUES (?, ?)",
                (user_id, url),
            )

    def remove_subscription(self, user_id: int, url: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND url = ?",
                (user_id, url),
            )
            return cur.rowcount

    def list_subscriptions(self, user_id: int) -> List[str]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT url FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            return [row[0] for row in cur.fetchall()]

    def list_all_subscription_urls(self) -> List[str]:
        with self._conn() as conn:
            cur = conn.execute("SELECT DISTINCT url FROM subscriptions ORDER BY url")
            return [row[0] for row in cur.fetchall()]

    def list_users_for_url(self, url: str) -> List[int]:
        with self._conn() as conn:
            cur = conn.execute("SELECT user_id FROM subscriptions WHERE url = ?", (url,))
            return [int(row[0]) for row in cur.fetchall()]

    def known_event_urls_for_page(self, page_url: str) -> set[str]:
        with self._conn() as conn:
            cur = conn.execute("SELECT event_url FROM events WHERE url = ?", (page_url,))
            return {row[0] for row in cur.fetchall()}

    def record_new_events(self, page_url: str, events: Iterable[Event]) -> List[Event]:
        new_events: List[Event] = []
        with self._conn() as conn:
            for ev in events:
                try:
                    conn.execute(
                        "INSERT INTO events(url, event_url, title, date_text, image_url) VALUES (?, ?, ?, ?, ?)",
                        (page_url, ev.event_url, ev.title, ev.date_text, ev.image_url),
                    )
                    new_events.append(ev)
                except sqlite3.IntegrityError:
                    pass
        return new_events
