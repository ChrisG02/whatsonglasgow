"""Glasgow digest: pulls new items from your sources, filters them, and
emails anything you haven't seen before.

    python main.py --dry-run      # write digest.html locally, send nothing
    python main.py                # fetch, email, remember what was sent
"""

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from render import render_html, render_text
from sources import FETCHERS

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state" / "seen.json"
log = logging.getLogger("digest")


def load_seen() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_seen(seen: dict, keep_days: int) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
    pruned = {uid: ts for uid, ts in seen.items() if ts >= cutoff}
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(pruned, indent=0, sort_keys=True), encoding="utf-8")


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
    ap.add_argument("--dry-run", action="store_true", help="write the digest to a file instead of emailing it")
    ap.add_argument("--all", action="store_true", help="ignore the seen list (handy when testing a new source)")
    ap.add_argument("--out", default="digest.html")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    settings = cfg.get("settings", {})
    categories = cfg.get("categories", {})
    watch = settings.get("watch", [])
    global_exclude = settings.get("exclude", [])
    cap = settings.get("max_items_per_source", 15)

    seen = {} if args.all else load_seen()
    now_iso = datetime.now(timezone.utc).isoformat()
    by_cat: dict[str, list] = {}
    errors: list[tuple[str, str]] = []

    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        try:
            items = FETCHERS[src["type"]](src)
        except Exception as exc:  # one broken site shouldn't stop the digest
            log.warning("%s failed: %s", src["name"], exc)
            errors.append((src["name"], str(exc)[:200]))
            continue
        kept = 0
        for item in items:
            if item.uid in seen or not wanted(item, src, global_exclude):
                continue
            seen[item.uid] = now_iso  # anything over the cap is skipped, not saved for later
            if kept < cap:
                item.highlight = _contains_any(f"{item.title} {item.summary}".lower(), watch)
                by_cat.setdefault(src["category"], []).append(item)
                kept += 1
        log.info("%s: %d fetched, %d new", src["name"], len(items), kept)

    total = sum(len(v) for v in by_cat.values())
    if total == 0 and not errors and not settings.get("send_when_empty", False):
        log.info("Nothing new this time; not sending.")
        if not args.dry_run:
            save_seen(seen, settings.get("remember_days", 180))
        return

    title = f"Glasgow digest · {datetime.now():%a %d %b} · {total} new"
    html = render_html(title, categories, by_cat, errors)
    text = render_text(title, categories, by_cat, errors)

    if args.dry_run:
        Path(args.out).write_text(html, encoding="utf-8")
        print(text)
        log.info("Dry run: wrote %s, nothing sent, seen list unchanged.", args.out)
        return

    from mailer import send
    send(title, html, text)
    save_seen(seen, settings.get("remember_days", 180))  # only after a successful send
    log.info("Sent digest with %d items.", total)


if __name__ == "__main__":
    main()
