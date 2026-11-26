"""Top up the site from your own computer.

Some sites (Eventbrite, Ticketmaster) refuse GitHub's servers, so the daily
GitHub run skips them (they're marked local_only in config.yaml). Run this
every week or so from a normal home or office connection:

    .venv\\Scripts\\python update_local.py      (Windows)
    .venv/bin/python update_local.py          (Mac/Linux)

It pulls the latest saved items, fetches every source, then commits and
pushes state/items.json. The push makes GitHub rebuild the page.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, check=check)


def main() -> None:
    print("Getting the latest saved items from GitHub…")
    git("pull", "--rebase", "--autostash")

    for attempt in range(3):
        print("Fetching every source (this takes a few minutes)…")
        subprocess.run([sys.executable, str(ROOT / "main.py")], cwd=ROOT, check=True)

        git("add", "state/items.json", "state/local_run.json")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("Nothing new to save.")
            return
        git("commit", "-m", "Local top-up of found items")
        if git("push", check=False).returncode == 0:
            print("Done. GitHub is rebuilding the page now; it updates in a couple of minutes.")
            return
        # GitHub's daily run saved items while this was fetching: drop this attempt
        # and redo it on top of theirs, rather than merging two versions of the file.
        print("GitHub saved new items in the meantime; redoing on top of them…")
        git("reset", "--soft", "HEAD~1")                       # undo only our commit…
        for f in ("state/items.json", "state/local_run.json"):  # …and our state files
            if git("restore", "--staged", "--worktree", f, check=False).returncode != 0:
                git("rm", "--cached", "--quiet", f, check=False)  # file is new: not on GitHub yet
                (ROOT / f).unlink(missing_ok=True)
        git("pull", "--rebase", "--autostash")                 # any other edits you have are kept
    sys.exit("Couldn't push after 3 tries. Run it again later.")


if __name__ == "__main__":
    main()
