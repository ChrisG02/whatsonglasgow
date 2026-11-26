# Glasgow digest

A personal "what's on" page for Glasgow gigs, club nights, new openings and
tattoo news, built from sources you choose. It updates itself every
morning on GitHub and is hosted free on GitHub Pages: just bookmark it.

## How it works

1. `main.py` reads `config.yaml` and fetches each enabled source (RSS feed, calendar feed, or a scraped listings page).
2. Items are filtered by your `include` / `exclude` keywords.
3. Anything new is added to `state/items.json`, which the workflow commits back so it remembers between runs.
4. `render.py` builds `site/index.html`, which is published to GitHub Pages.

On the page, items are grouped by when they were found and can be filtered by category or searched. Anything found since you last opened it gets a **New** badge, and anything matching your `watch` list gets a ★ and goes to the top. If a source breaks (site redesign, dead feed), the rest still update, and the failure is listed at the bottom.

## Setup

1. Push this folder to a GitHub repo, with the files (including `.github/`) at the top level.
2. The repo needs to be **public** for free GitHub Pages hosting.
3. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
4. Actions tab → "Update Glasgow digest" → Run workflow.
5. When it finishes, the page address is shown on the run (and under Settings → Pages). Bookmark it.

After that it updates every morning, and also whenever you edit `config.yaml`.

## Working on it locally

```bash
pip install -r requirements.txt
python main.py --dry-run     # builds site/index.html without saving what it found
```

Open `site/index.html` in a browser to preview.

## Adding a source

- **Has an RSS feed?** Use `type: rss`. Try adding `/feed`, `/rss` or `?service=rss` to the URL.
- **Calendar feed?** Use `type: ical` (e.g. a Songkick calendar URL for tracked artists).
- **Ticket site or venue listings?** Try `type: jsonld` first. Most ticket sites (Skiddle, Eventbrite, Ticketmaster) and many venue sites embed event data that gives proper dates and venues. Use `categorise` to spread a broad source over several categories.
- **Neither?** Use `type: html`. Open the listings page, right-click an event → Inspect, find the element wrapping each event, and put its CSS selector in `item_selector`.
