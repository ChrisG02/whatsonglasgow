# Glasgow digest

A personal "what's on" page for Glasgow gigs, club nights, new openings and
tattoo news, built from sources you choose. It updates itself every
morning on GitHub and is hosted free on GitHub Pages: just bookmark it.

## How it works

1. `main.py` reads `config.yaml` and fetches each enabled source (RSS feed, calendar feed, or a scraped listings page).
2. Items are filtered by your `include` / `exclude` keywords.
3. Anything new is added to `state/items.json`, which the workflow commits back so it remembers between runs.
4. `render.py` builds `site/index.html`, which is published to GitHub Pages.

On the page:

- **For you** learns from the â™¡ hearts you tap, your `watch` list and your `interests`. **Everything** lists events by day. **Map** shows them by venue.
- Filter by category, by when (Tonight, Today, This weekend, Next 7 days, or pick dates), **Free only**, or search. Type words into **Hide** to drop things you never want.
- Cards show a photo, price and "Few left" / "Sold out" where the site gives them, plus **Add to calendar** and **Share** buttons.
- The address bar keeps your filters, so **Share this view** sends someone exactly what you're looking at.
- Anything found since you last opened it gets a **New** badge. If a source breaks (site redesign, dead feed), the rest still update, and the failure is listed at the bottom.

Also published next to the page:

- `weekend.xml`: RSS feed of this weekend's events matching your watch list or interests.
- `picks.ics`: the next 40 of those matches (up to 30 days ahead), as a calendar your phone can subscribe to.
- On a phone, Share â†’ **Add to Home Screen** installs it as an app (it opens offline with the last listings it saw).

## Setup

1. Push this folder to a GitHub repo, with the files (including `.github/`) at the top level.
2. The repo needs to be **public** for free GitHub Pages hosting.
3. Settings â†’ Pages â†’ Build and deployment â†’ Source: **GitHub Actions**.
4. Actions tab â†’ "Update Glasgow digest" â†’ Run workflow.
5. When it finishes, the page address is shown on the run (and under Settings â†’ Pages). Bookmark it.

After that it updates every morning, and also whenever you edit `config.yaml`.

## Working on it locally

```bash
pip install -r requirements.txt
python main.py --dry-run     # builds site/index.html without saving what it found
```

Open `site/index.html` in a browser to preview.

## Topping up from your computer

Eventbrite and Ticketmaster refuse GitHub's servers, so they're marked `local_only: true` in `config.yaml` and the daily run skips them. To include them, run this every week or so from a normal home or office connection:

```bash
python -m venv .venv                          # first time only
.venv\Scripts\pip install -r requirements.txt # first time only (Mac/Linux: .venv/bin/pip)
.venv\Scripts\python update_local.py          # Mac/Linux: .venv/bin/python update_local.py
```

It fetches every source, then commits and pushes `state/items.json`, which makes GitHub rebuild the page. Events stay listed until they've happened, so a weekly run keeps things full. The page footer says how long ago it last ran.

## Adding a source

- **Has an RSS feed?** Use `type: rss`. Try adding `/feed`, `/rss` or `?service=rss` to the URL.
- **Calendar feed?** Use `type: ical` (e.g. a Songkick calendar URL for tracked artists).
- **Ticket site or venue listings?** Try `type: jsonld` first. Most ticket sites (Skiddle, Eventbrite, Ticketmaster) and many venue sites embed event data that gives proper dates and venues. Use `categorise` to spread a broad source over several categories.
- **Neither?** Use `type: html`. Open the listings page, right-click an event â†’ Inspect, find the element wrapping each event, and put its CSS selector in `item_selector`. The photo is the first image in each listing unless you set `image_selector`.
- **Venue's own site blocked or unreadable?** Search for the venue on Ticketmaster or Skiddle and use its venue page with `type: jsonld` (Ticketmaster ones need `local_only: true`).
- **On the map:** sites that give coordinates appear automatically. For a single venue, add its `lat:` and `lon:` (right-click the spot on openstreetmap.org â†’ "Show address").
