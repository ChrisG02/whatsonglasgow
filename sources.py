"""Fetchers for each kind of source. Each one takes a source dict from
config.yaml and returns a list of Item objects."""

import hashlib
import json
import re
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from icalendar import Calendar

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)  # short descriptions that look like URLs

try:  # use the OS certificate store, so local runs work behind networks that inspect HTTPS
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

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
    starts: str = ""     # ISO start time, for events (lets the page filter by date)
    ends: str = ""       # ISO end date, for things that run a while (exhibitions)
    venue: str = ""
    kind: str = ""       # event type if the site gives one, e.g. MusicEvent, "Exhibition, Visual Arts"
    image: str = ""      # photo URL
    price: str = ""      # e.g. "£8", "£8–£15", "Free"
    free: bool = False
    soldout: str = ""    # "" | "few" | "out"
    lat: float | None = None
    lon: float | None = None
    highlight: bool = False

    def __post_init__(self):
        # Stable id used to remember what we've already sent.
        key = self.uid or self.link or f"{self.source}|{self.title}"
        self.uid = hashlib.sha1(key.encode("utf-8")).hexdigest()


HOST_GAP = 4.0        # seconds between requests to the same site (Eventbrite rate-limits bursts)
HOST_GAPS = {"www.skiddle.com": 12.0}   # Skiddle starts refusing after a handful of quick page loads
_last_hit: dict[str, float] = {}


def _polite_get(url: str) -> requests.Response:
    """GET with a pause between requests to the same host, and one retry if told to slow down."""
    host = urlparse(url).netloc
    for attempt in range(2):
        wait = _last_hit.get(host, 0) + HOST_GAPS.get(host, HOST_GAP) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        _last_hit[host] = time.monotonic()
        # 429 = slow down; an empty 202 is Skiddle's way of saying the same thing
        busy = r.status_code == 429 or (r.status_code == 202 and not r.content)
        if not busy or attempt:
            if r.status_code == 202 and not r.content:
                raise ValueError("site asked us to come back later (empty 202)")
            return r
        retry_after = r.headers.get("Retry-After", "")
        time.sleep(min(int(retry_after), 60) if retry_after.isdigit() else 30)
    return r


def _fetch_text(url: str) -> str:
    # file:// lets you test against a saved copy of a page.
    if url.startswith("file://"):
        with open(url[len("file://"):], encoding="utf-8") as f:
            return f.read()
    r = _polite_get(url)
    r.raise_for_status()
    if "charset" not in r.headers.get("content-type", "").lower():
        r.encoding = "utf-8"  # requests would otherwise assume Latin-1 and garble é, ’ etc.
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
            starts=start.isoformat(),
            venue=str(ev.get("LOCATION", "")).split(",")[0],
        ))
    return items


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


_DATE_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})[a-z]*\.?(?:,?\s+'?(\d{4}|\d{2})\b)?")
_DATE_MF_RE = re.compile(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4})\b)?")   # "Nov 26, 2026"
_LEAD_DAY_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:-|–|to)\s*(?:[A-Za-z]+,?\s+)?$")          # "Sat 28th - Sun 29th Nov"


def _guess_dates(text: str) -> tuple[str, str]:
    """Turn listing dates into ISO (start, end). Handles "Thu 26 Nov", "Fri 04 Dec '26",
    "Thu, Nov 26", "28th - 29th Nov 2026" and ranges like "6 November - 23 December 2026".
    A single date with no year is taken as the next time it comes round. Returns ""
    for anything it can't read."""
    text = text or ""
    hits = []  # (position, [day, month, year])
    for m in _DATE_RE.finditer(text):
        if m.group(2).lower() in _MONTHS:
            year = m.group(3)
            year = (int(year) + (2000 if len(year) == 2 else 0)) if year else None
            hits.append((m.start(), m.end(), [int(m.group(1)), _MONTHS[m.group(2).lower()], year]))
    for m in _DATE_MF_RE.finditer(text):
        if m.group(1).lower() in _MONTHS and not any(s <= m.start() < e for s, e, _ in hits):
            hits.append((m.start(), m.end(), [int(m.group(2)), _MONTHS[m.group(1).lower()], int(m.group(3)) if m.group(3) else None]))
    hits.sort(key=lambda h: h[0])
    found = [h[2] for h in hits[:2]]
    if len(found) == 1:
        lead = _LEAD_DAY_RE.search(text[:hits[0][0]])
        if lead and int(lead.group(1)) < found[0][0]:   # "28th - 29th Nov": the 28th is the same month
            found = [[int(lead.group(1)), found[0][1], found[0][2]], found[0]]
    if not found:
        return "", ""
    today = datetime.now(timezone.utc).date()
    start, end = found[0], (found[1] if len(found) > 1 else None)
    if end is not None:
        if end[2] is None:
            end[2] = start[2] or today.year
            if start[2] is None and (end[1], end[0]) < (today.month, today.day):
                end[2] += 1
        if start[2] is None:
            start[2] = end[2] if (start[1], start[0]) <= (end[1], end[0]) else end[2] - 1
    elif start[2] is None:
        start[2] = today.year if (start[1], start[0]) >= (today.month, today.day - 1) else today.year + 1

    def iso(d):
        try:
            return datetime(d[2], d[1], d[0], tzinfo=timezone.utc).isoformat()
        except ValueError:
            return ""
    return iso(start), (iso(end) if end else "")


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
        when = date_el.get_text(" ", strip=True) if date_el else ""
        kind_el = node.select_one(src["kind_selector"]) if src.get("kind_selector") else None
        starts, ends = _guess_dates(when)
        stamp = date_el if date_el is not None and date_el.get("datetime") else (date_el.select_one("[datetime]") if date_el is not None else None)
        if stamp is not None:   # <time datetime="2026-11-28"> is more reliable than the visible text
            try:
                d = datetime.fromisoformat(stamp["datetime"][:10])
                starts, ends = d.replace(tzinfo=timezone.utc).isoformat(), ""
            except ValueError:
                pass
        title = title_el.get_text(" ", strip=True)
        if date_el is not None and date_el is not title_el and title and title in when:
            when = when.replace(title, "").strip(" -–:")  # date text that repeats the title
        items.append(Item(
            source=src["name"],
            category=src["category"],
            title=title,
            link=link,
            when=when,
            starts=starts,
            ends=ends,
            venue=src.get("venue", src["name"]),
            kind=kind_el.get_text(" ", strip=True) if kind_el else "",
            image=_img_from(node, src),
        ))
    return items


def _pick_srcset(srcset: str) -> str:
    """From "a.jpg 160w, b.jpg 480w, c.jpg 1200w" pick the one nearest 480px wide."""
    best, best_gap = "", 1e9
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        w = int(bits[1][:-1]) if len(bits) > 1 and bits[1].endswith("w") and bits[1][:-1].isdigit() else 480
        if abs(w - 480) < best_gap:
            best, best_gap = bits[0], abs(w - 480)
    return best


def _img_from(node, src: dict) -> str:
    """Photo for a scraped listing: image_selector if given, else the first <img> in it."""
    sel = src.get("image_selector", "img")
    if not sel:
        return ""
    img = node if node.name == "img" else node.select_one(sel)
    if img is None:
        return ""
    url = ""
    for attr in ("data-srcset", "srcset"):
        if img.get(attr):
            url = _pick_srcset(img[attr])
            break
    url = url or img.get("data-src") or img.get("data-image") or img.get("src") or ""
    if not url or url.startswith("data:"):
        return ""
    return urljoin(src["url"], url)


def _image(v) -> str:
    if isinstance(v, list):
        v = next((x for x in v if x), "")
    if isinstance(v, dict):
        v = v.get("url") or v.get("contentUrl") or ""
    v = str(v or "")
    if "/venue/maps/" in v:   # Ticketmaster's seating plan, not a photo
        return ""
    return v if v.startswith("http") and not v.lower().endswith(".pdf") else ""


def _price_info(ev: dict) -> tuple[str, bool, str]:
    """(price label, is free, "" / "few" / "out") from schema.org offers."""
    offers = ev.get("offers") or []
    offers = offers if isinstance(offers, list) else [offers]
    prices, avail = [], []
    for o in offers:
        if not isinstance(o, dict):
            continue
        avail.append(str(o.get("availability", "")).rsplit("/", 1)[-1].lower())
        for k in ("price", "lowPrice", "highPrice"):
            try:
                if o.get(k) not in (None, ""):
                    prices.append(float(str(o[k]).replace("£", "").replace(",", "")))
            except ValueError:
                pass
    free = ev.get("isAccessibleForFree") in (True, "true", "True") or (bool(prices) and max(prices) == 0)
    paid = [p for p in prices if p > 0]
    fmt = lambda p: f"£{p:.0f}" if p == int(p) else f"£{p:.2f}"
    label = "Free" if free else (fmt(min(paid)) + (f"–{fmt(max(paid))}" if max(paid) > min(paid) else "") if paid else "")
    status = "out" if avail and all(a in ("soldout", "outofstock") for a in avail) else \
             "few" if any(a == "limitedavailability" for a in avail) else ""
    return label, free, status


def _geo(loc) -> tuple[float | None, float | None]:
    geo = loc.get("geo") if isinstance(loc, dict) else None
    if not isinstance(geo, dict):
        return None, None
    try:
        lat, lon = float(geo.get("latitude")), float(geo.get("longitude"))
    except (TypeError, ValueError):
        return None, None
    return (lat, lon) if (lat, lon) != (0.0, 0.0) else (None, None)


def _walk_events(data):
    """Yield every schema.org *Event object inside a JSON-LD blob."""
    stack = [data]
    while stack:
        d = stack.pop()
        if isinstance(d, list):
            stack.extend(reversed(d))
            continue
        if not isinstance(d, dict):
            continue
        types = d.get("@type")
        types = types if isinstance(types, list) else [types]
        if any(isinstance(t, str) and t.endswith("Event") for t in types):
            yield d
            continue
        for key in ("@graph", "itemListElement", "item", "mainEntity"):
            if key in d:
                stack.append(d[key])


def _text(v) -> str:
    if isinstance(v, list):
        v = v[0] if v else ""
    if isinstance(v, dict):
        v = v.get("name", "")
    return str(v or "").strip()


def fetch_jsonld(src: dict) -> list[Item]:
    """Read schema.org Event data embedded in a page. Most ticket sites
    (Skiddle, Eventbrite, Ticketmaster) and many venue sites publish it."""
    soup = BeautifulSoup(_fetch_text(src["url"]), "html.parser")
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=src.get("days_ahead", 90))
    items, seen = [], set()
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue
        for ev in _walk_events(data):
            name = _text(ev.get("name"))
            start_raw = _text(ev.get("startDate"))
            if not name or not start_raw:
                continue
            try:
                start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            end = None
            try:
                end = datetime.fromisoformat(_text(ev.get("endDate")).replace("Z", "+00:00"))
                end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
            if end is not None and end - start < timedelta(days=1):
                end = None  # an ordinary evening event, not a run
            if start > horizon or (end or start) < now - timedelta(hours=12):
                continue
            link = urljoin(src["url"], _text(ev.get("url"))) if ev.get("url") else src["url"]
            link_key = link.split("?")[0]  # same event, different tracking codes per search page
            if (link_key, start_raw) in seen:
                continue
            seen.add((link_key, start_raw))
            venue = _text(ev.get("location"))
            loc = ev.get("location")
            loc = loc[0] if isinstance(loc, list) and loc else loc
            town = (loc.get("address") or {}) if isinstance(loc, dict) else {}
            town = str(town.get("addressLocality", "")) if isinstance(town, dict) else str(town)
            if any(p.lower() in town.lower() for p in src.get("exclude_places", [])):
                continue  # search pages leak in events from other cities
            if "cancelled" in str(ev.get("eventStatus", "")).lower():
                continue
            price, free, soldout = _price_info(ev)
            lat, lon = _geo(loc)
            items.append(Item(
                source=src["name"],
                category=src["category"],
                title=_plain(name, 160),
                link=link,
                summary=_plain(_text(ev.get("description"))),
                when=start.strftime("%a %d %b, %H:%M") if (start.hour or start.minute) else start.strftime("%a %d %b"),
                uid=f"{link_key}|{start_raw}",
                starts=start.isoformat(),
                ends=end.isoformat() if end else "",
                venue=venue or src.get("venue", ""),
                kind=_text(ev.get("@type")),
                image=_image(ev.get("image")),
                price=price,
                free=free,
                soldout=soldout,
                lat=lat,
                lon=lon,
            ))
    if not items and not soup.select('script[type="application/ld+json"]'):
        raise ValueError("no event data (JSON-LD) on the page; try type: html instead")
    return items


FETCHERS = {"rss": fetch_rss, "ical": fetch_ical, "html": fetch_html, "jsonld": fetch_jsonld}
