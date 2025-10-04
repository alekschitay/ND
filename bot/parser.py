"""HTML parsing utilities for extracting events from venue pages."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag


MONTH_NAMES = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}
DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?\b", re.IGNORECASE
)
HUMAN_MONTH_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(%s)(?:\s+(\d{4}))?\b" % "|".join(MONTH_NAMES.keys()), re.IGNORECASE
)


@dataclass(slots=True)
class Event:
    """Structured information about an event on a venue page."""

    link: str
    title: str | None
    date_text: str | None
    image_url: str | None

    @property
    def event_id(self) -> str:
        """Deterministic identifier used to deduplicate events."""

        digest = hashlib.sha256()
        digest.update(self.link.encode("utf-8"))
        if self.title:
            digest.update(self.title.strip().lower().encode("utf-8"))
        if self.date_text:
            digest.update(self.date_text.strip().lower().encode("utf-8"))
        return digest.hexdigest()


async def fetch_html(url: str, timeout: float) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = " ".join(text.split())
    return cleaned or None


def _extract_date(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    if match:
        day, month, year = match.groups()
        if year is None:
            year = str(datetime.utcnow().year)
        if len(year) == 2:
            year = "20" + year
        return f"{day.zfill(2)}.{month.zfill(2)}.{year}"
    match = HUMAN_MONTH_PATTERN.search(text.lower())
    if match:
        day, month_name, year = match.groups()
        month = MONTH_NAMES[month_name]
        if year is None:
            year = str(datetime.utcnow().year)
        return f"{day.zfill(2)}.{month}.{year}"
    return None


def _choose_title(node: Tag) -> str | None:
    text = _normalize_text(node.get_text(" "))
    if text:
        return text
    heading = node.find(["h1", "h2", "h3", "h4"])
    if heading and heading.get_text(strip=True):
        return heading.get_text(strip=True)
    return None


def _find_image(node: Tag, base_url: str) -> str | None:
    img = node.find("img")
    if not img or not img.get("src"):
        return None
    return urljoin(base_url, img["src"])


def _walk_candidate_nodes(soup: BeautifulSoup) -> Iterable[Tag]:
    candidates = []
    for tag_name in ("article", "li", "div"):
        candidates.extend(soup.find_all(tag_name, class_=re.compile("event|afisha|poster", re.I)))
    if candidates:
        yield from candidates
        return
    for tag_name in ("article", "li"):
        candidates.extend(soup.find_all(tag_name))
    if candidates:
        yield from candidates
        return
    for container in soup.find_all("div"):
        if container.find("a"):
            yield container


def parse_events(url: str, html: str) -> list[Event]:
    soup = BeautifulSoup(html, "lxml")
    events: list[Event] = []

    for node in _walk_candidate_nodes(soup):
        link = node.find("a")
        if not link or not link.get("href"):
            continue
        href = urljoin(url, link["href"])
        title = _choose_title(node)
        date_text = None
        if title:
            date_text = _extract_date(title)
        if not date_text:
            date_text = _extract_date(node.get_text(" "))
        image_url = _find_image(node, url)
        if not title and not image_url:
            continue
        events.append(
            Event(
                link=href,
                title=title,
                date_text=date_text,
                image_url=image_url,
            )
        )

    # Deduplicate events by identifier preserving order
    seen: set[str] = set()
    unique_events: list[Event] = []
    for event in events:
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        unique_events.append(event)

    return unique_events
