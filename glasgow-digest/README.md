# Glasgow digest

A weekly email of new gigs, club nights, openings and tattoo news from
sources you choose. It runs free on GitHub Actions and remembers what
it's already sent, so you only ever see new things.

## How it works

1. `main.py` reads `config.yaml` and fetches each enabled source (RSS feed, calendar feed, or a scraped listings page).
2. Items are filtered by your `include` / `exclude` keywords; anything matching `watch` gets a ★.
3. Items already in `state/seen.json` are skipped.
4. New items are emailed, grouped by category, and the seen list is committed back to the repo.

If a source breaks (site redesign, dead feed), the rest still go out, and the failure is listed at the bottom of the email.

## Setup

1. **Create a private GitHub repo** and push this folder to it.
2. **Make a Gmail app password**: turn on 2-step verification on the Google account, then create an app password (Google Account → Security → App passwords). Don't use your normal password.
3. **Add repo secrets** (Settings → Secrets and variables → Actions):
   - `SMTP_USER`: the Gmail address
   - `SMTP_PASSWORD`: the app password
   - `DIGEST_TO`: where to send it (optional; defaults to SMTP_USER)
   - `SMTP_HOST` / `SMTP_PORT`: only if not using Gmail
4. **Test it**: Actions tab → "Weekly Glasgow digest" → Run workflow.

After that it runs every Friday morning on its own.

## Working on it locally

```bash
pip install -r requirements.txt
python main.py --dry-run          # writes digest.html, sends nothing
python main.py --dry-run --all    # ignore the seen list, e.g. to test a new source
```

## Adding a source

- **Has an RSS feed?** Use `type: rss`. Many news sites and blogs have one; try adding `/feed`, `/rss` or `?service=rss` to the URL.
- **Calendar feed?** Use `type: ical` (e.g. Songkick can give you a calendar URL for tracked artists).
- **Neither?** Use `type: html`. Open the listings page, right-click an event → Inspect, find the element wrapping each event, and put its CSS selector in `item_selector`. Test with `--dry-run --all`.
