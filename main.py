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


def wanted(item, src: dict, global_exclude: list[str]) -> bool:
    text = f"{item.title} {item.summary}".lower()
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
        for item in fetched:
            if added >= cap or item.uid in store or not wanted(item, src, global_exclude):
                continue
            record = asdict(item)
            record.pop("highlight", None)
            record["first_seen"] = now_iso
            store[item.uid] = record
            added += 1
        log.info("%s: %d fetched, %d new", src["name"], len(fetched), added)

    # Only show what's still in the config's window; older items stay remembered so they're never re-added.
    show_cutoff = (datetime.now(timezone.utc) - timedelta(days=settings.get("show_days", 45))).isoformat()
    visible = sorted((it for it in store.values() if it["first_seen"] >= show_cutoff),
                     key=lambda it: it["first_seen"], reverse=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_page(visible, cfg.get("categories", {}), settings.get("watch", []), errors, now_iso),
                   encoding="utf-8")
    log.info("Wrote %s with %d items.", out, len(visible))

    if not args.dry_run:
        save_items(store, settings.get("remember_days", 180))


if __name__ == "__main__":
    main()
