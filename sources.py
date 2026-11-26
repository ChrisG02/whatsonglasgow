"""Fetchers for each kind of source. Each one takes a source dict from
config.yaml and returns a list of Item objects."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar

USER_AGENT = "Mozilla/5.0 (compatible; glasgow-digest/1.0; personal weekly digest)"
TIMEOUT = 20


@dataclass
class Item:
    source: str
    category: str
    title: str
    link: str
    summary: str = ""
    when: str = ""
    uid: str = ""
    highlight: bool = False

    def __post_init__(self):
        # Stable id used to remember what we've already sent.
        key = self.uid or self.link or f"{self.source}|{self.title}"
        self.uid = hashlib.sha1(key.encode("utf-8")).hexdigest()


def _fetch_text(url: str) -> str:
    # file:// lets you test against a saved copy of a page.
    if url.startswith("file://"):
        with open(url[len("file://"):], encoding="utf-8") as f:
            return f.read()
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _plain(html_text: str, limit: int = 280) -> str:
    text = BeautifulSoup(html_text or "", "html.parser").get_text(" ", strip=True)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fetch_rss(src: dict) -> list[Item]:
    feed = feedparser.parse(_fetch_text(src["url"]))
    if feed.bozo and not feed.entries:
        raise ValueError(f"couldn't parse feed ({feed.bozo_exception})")
    items = []
    for e in feed.entries:
        parsed = e.get("published_parsed") or e.get("updated_parsed")
        when = datetime(*parsed[:6]).strftime("%a %d %b") if parsed else ""
        items.append(Item(
            source=src["name"],
            category=src["category"],
            title=(e.get("title") or "(untitled)").strip(),
            link=e.get("link", ""),
            summary=_plain(e.get("summary", "")),
            when=when,
        ))
    return items


def fetch_ical(src: dict) -> list[Item]:
    cal = Calendar.from_ical(_fetch_text(src["url"]))
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=src.get("days_ahead", 90))
    items = []
    for ev in cal.walk("VEVENT"):
        start = ev.decoded("DTSTART", None)
        if start is None:
            continue
        if not isinstance(start, datetime):  # all-day event
            start = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
        elif start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if not (now - timedelta(days=1) <= start <= horizon):
            continue
        items.append(Item(
            source=src["name"],
            category=src["category"],
            title=str(ev.get("SUMMARY", "(untitled)")),
            link=str(ev.get("URL", "")),
            summary=str(ev.get("LOCATION", "")),
            when=start.strftime("%a %d %b"),
            uid=str(ev.get("UID", "")),
        ))
    return items


def fetch_html(src: dict) -> list[Item]:
    """Scrape a listings page using CSS selectors from config.yaml."""
    soup = BeautifulSoup(_fetch_text(src["url"]), "html.parser")
    nodes = soup.select(src["item_selector"])
    if not nodes:
        raise ValueError("item_selector matched nothing; the site layout may have changed")
    items = []
    for node in nodes:
        title_el = node.select_one(src["title_selector"]) if src.get("title_selector") else node
        if title_el is None:
            continue
        link_el = node if node.name == "a" else node.select_one(src.get("link_selector", "a[href]"))
        link = urljoin(src["url"], link_el["href"]) if link_el is not None and link_el.get("href") else src["url"]
        date_el = node.select_one(src["date_selector"]) if src.get("date_selector") else None
        items.append(Item(
            source=src["name"],
            category=src["category"],
            title=title_el.get_text(" ", strip=True),
            link=link,
            when=date_el.get_text(" ", strip=True) if date_el else "",
        ))
    return items


FETCHERS = {"rss": fetch_rss, "ical": fetch_ical, "html": fetch_html}
