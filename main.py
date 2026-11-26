"""Glasgow digest: pulls new items from your sources, filters them, and
builds a web page (site/index.html) showing everything recent.

    python main.py --dry-run      # build the page locally, don't update the saved items
    python main.py                # build the page and remember what was found
"""

import argparse
import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from render import build_page
from sources import FETCHERS

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state" / "items.json"
log = logging.getLogger("digest")


def load_items() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_items(items: dict, keep_days: int) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
    kept = {uid: it for uid, it in items.items() if it["first_seen"] >= cutoff}
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(kept, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _contains_any(text: str, words: list[str]) -> bool:
    return any(w.lower() in text for w in words)


def _item_text(item) -> str:
    return f"{item.title} {item.summary} {item.venue}".lower()


def sort_into_category(item, src: dict) -> None:
    """Broad sources can spread items over categories: the first `categorise`
    entry whose keywords match wins, otherwise the source's own category.
    Matches on title, venue and event type only: long descriptions mention
    food, DJs etc. in passing and send things to the wrong place."""
    text = f"{item.title} {item.venue} {item.kind}".lower()
    for cat, words in (src.get("categorise") or {}).items():
        if _contains_any(text, words):
            item.category = cat
            return


def wanted(item, src: dict, global_exclude: list[str]) -> bool:
    text = _item_text(item)
    include = src.get("include", [])
    if include and not _contains_any(text, include):
        return False
    return not _contains_any(text, src.get("exclude", []) + global_exclude)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--dry-run", action="store_true", help="build the page but don't save what was found")
    ap.add_argument("--out", default=str(ROOT / "site" / "index.html"))
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    settings = cfg.get("settings", {})
    global_exclude = settings.get("exclude", [])
    cap = settings.get("max_items_per_source", 15)

    store = load_items()
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    errors: list[dict] = []

    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        try:
            fetched = FETCHERS[src["type"]](src)
        except Exception as exc:  # one broken site shouldn't stop the rest
            log.warning("%s failed: %s", src["name"], exc)
            errors.append({"source": src["name"], "message": str(exc)[:200]})
            continue
        added = 0
        src_cap = src.get("max_items", cap)
        for item in fetched:
            if added >= src_cap or item.uid in store or not wanted(item, src, global_exclude):
                continue
            sort_into_category(item, src)
            record = asdict(item)
            record.pop("highlight", None)
            record["first_seen"] = now_iso
            store[item.uid] = record
            added += 1
        log.info("%s: %d fetched, %d new", src["name"], len(fetched), added)

    # Events stay on the page until they've happened; news items for show_days after they were found.
    # Older items stay remembered so they're never re-added.
    now = datetime.now(timezone.utc)
    show_cutoff = (now - timedelta(days=settings.get("show_days", 45))).isoformat()
    event_cutoff = now - timedelta(hours=12)

    def visible_now(it: dict) -> bool:
        if it.get("starts"):
            return datetime.fromisoformat(it.get("ends") or it["starts"]) >= event_cutoff
        return it["first_seen"] >= show_cutoff

    visible = sorted(filter(visible_now, store.values()), key=lambda it: it["first_seen"], reverse=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_page(visible, cfg.get("categories", {}), settings.get("watch", []), errors, now_iso,
                              settings.get("interests") or []),
                   encoding="utf-8")
    log.info("Wrote %s with %d items.", out, len(visible))

    if not args.dry_run:
        save_items(store, settings.get("remember_days", 180))


if __name__ == "__main__":
    main()
