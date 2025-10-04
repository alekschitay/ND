from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


@dataclass
class ScrapedEvent:
    event_url: str
    title: Optional[str]
    date_text: Optional[str]
    image_url: Optional[str]


async def fetch_html(url: str, timeout: float = 15.0) -> str:
    async with httpx.AsyncClient(timeout=timeout, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127 Safari/537.36"
    }) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.text


def extract_events_from_html(base_url: str, html: str) -> List[ScrapedEvent]:
    # Use built-in parser to avoid external lxml dependency
    soup = BeautifulSoup(html, "html.parser")

    candidates = []

    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue
        full_url = urljoin(base_url, href)
        title = a.get_text(strip=True) or None

        parent = a.parent
        date_text: Optional[str] = None
        image_url: Optional[str] = None

        def class_has_date(val) -> bool:
            if not val:
                return False
            if isinstance(val, str):
                return "date" in val.lower()
            if isinstance(val, (list, tuple, set)):
                return any("date" in str(item).lower() for item in val)
            return "date" in str(val).lower()

        if parent:
            time_el = parent.find(["time", "span", "div"], attrs={"class": class_has_date})
            if time_el and time_el.get_text(strip=True):
                date_text = time_el.get_text(strip=True)

            img_el = parent.find("img")
            if img_el and (src := (img_el.get("src") or img_el.get("data-src") or img_el.get("srcset"))):
                # If srcset is present, take the first URL
                src = str(src).split()[0]
                image_url = urljoin(base_url, src)

        candidates.append(ScrapedEvent(event_url=full_url, title=title, date_text=date_text, image_url=image_url))

    filtered: List[ScrapedEvent] = []
    seen_urls: set[str] = set()
    for ev in candidates:
        if ev.event_url in seen_urls:
            continue
        seen_urls.add(ev.event_url)

        if not ev.title:
            continue
        if not ev.title or len(ev.title) < 3:
            continue

        filtered.append(ev)

    return filtered


async def scrape_events(url: str) -> List[ScrapedEvent]:
    html = await fetch_html(url)
    return extract_events_from_html(url, html)
