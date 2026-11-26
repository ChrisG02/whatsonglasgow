"""Extra files published next to the page:

  weekend.xml  RSS feed: this weekend's events matching your watch list or interests
  picks.ics    calendar you can subscribe to: the next 40 of those matches (30 days ahead)
"""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape


def _matches(it: dict, words: list[str]) -> bool:
    text = f"{it.get('title', '')} {it.get('summary', '')} {it.get('venue', '')}".lower()
    return any(w.lower() in text for w in words)


def _start(it: dict):
    return datetime.fromisoformat(it["starts"]) if it.get("starts") else None


def picks(items: list[dict], words: list[str]) -> list[dict]:
    """Upcoming one-off events (not long-running exhibitions) matching any word, soonest first."""
    out = [it for it in items if it.get("starts") and not it.get("ends") and _matches(it, words)]
    return sorted(out, key=_start)


def weekend_window(now: datetime) -> tuple[datetime, datetime]:
    """Friday 00:00 to Monday 05:00 (UK time is close enough to UTC for this); from today if it's already the weekend."""
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    dow = today.weekday()  # Mon=0
    start = today if dow >= 4 else today + timedelta(days=4 - dow)
    end = start + timedelta(days=7 - start.weekday(), hours=5)
    return start, end


def weekend_rss(items: list[dict], words: list[str], page_url: str, now: datetime) -> str:
    start, end = weekend_window(now)
    chosen = [it for it in picks(items, words) if start <= _start(it) < end]
    entries = []
    for it in chosen:
        when = _start(it).strftime("%a %d %b") + ("" if _start(it).strftime("%H:%M") == "00:00" else _start(it).strftime(", %H:%M"))
        desc = " Â· ".join(x for x in [when, it.get("venue", ""), it.get("price", ""), it.get("summary", "")] if x)
        entries.append(f"""  <item>
    <title>{escape(it['title'])}</title>
    <link>{escape(it.get('link') or page_url)}</link>
    <guid isPermaLink="false">{it['uid']}</guid>
    <pubDate>{format_datetime(datetime.fromisoformat(it['first_seen']))}</pubDate>
    <description>{escape(desc)}</description>
  </item>""")
    title = f"This weekend for you ({start.strftime('%a %d %b')})"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
  <title>{escape(title)}</title>
  <link>{escape(page_url)}</link>
  <description>Glasgow events this weekend matching your watch list and interests</description>
  <lastBuildDate>{format_datetime(now)}</lastBuildDate>
{chr(10).join(entries)}
</channel>
</rss>
"""


def _ics_text(s: str) -> str:
    return str(s or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _fold(line: str) -> str:
    out = []
    while len(line) > 73:
        out.append(line[:73])
        line = " " + line[73:]
    out.append(line)
    return "\r\n".join(out)


MAX_CAL = 40   # keeps a subscribed calendar readable when a busy venue is on the watch list


def picks_ics(items: list[dict], words: list[str], now: datetime) -> str:
    horizon = now + timedelta(days=30)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//glasgow-digest//EN", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:Glasgow picks", "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    upcoming = [it for it in picks(items, words) if now - timedelta(hours=12) <= _start(it) <= horizon]
    for it in upcoming[:MAX_CAL]:
        start = _start(it).astimezone(timezone.utc)
        lines += ["BEGIN:VEVENT", f"UID:{it['uid']}@glasgow-digest", f"DTSTAMP:{stamp}"]
        if start.strftime("%H%M") == "0000":   # date only
            lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{start + timedelta(days=1):%Y%m%d}"]
        else:
            lines += [f"DTSTART:{start:%Y%m%dT%H%M%SZ}", f"DTEND:{start + timedelta(hours=3):%Y%m%dT%H%M%SZ}"]
        lines.append("SUMMARY:" + _ics_text(it["title"]))
        if it.get("venue"):
            lines.append("LOCATION:" + _ics_text(it["venue"]))
        if (it.get("link") or "").startswith("http"):
            lines.append("URL:" + it["link"])
        lines.append("DESCRIPTION:" + _ics_text("\n".join(x for x in [it.get("price", ""), it.get("link", "")] if x)))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
