# Release check

Mimir opens the pages it builds (math sheets, step pages and step-through pages) through `open_in_browser` in `scripts/visual.py`. The tests cover it with fake openers only, so before a release run the same live check by hand on each OS: Linux, macOS, Windows and WSL.

`scripts/release_check.py` is a dev-only script (standard library, Python 3.11+); no skill uses it. It writes `mimir-release-check.html` and `mimir-release-check.svg` into a new temp folder whose name contains a space, opens each one through the shipped `visual.open_in_browser`, and prints one JSON object: `platform`, `html`, `svg`, `opened_html`, `opened_svg`, `line`. It exits 0 when both files opened, else 1. `--no-open` only builds the files.

An Antigravity install (`agy plugin install`) is a snapshot of the repository: after every change, reinstall it (`agy plugin uninstall mimir`, then install again) before any live check on Antigravity.

## Run it

From a clone of this repository, in a graphical session:

| OS | Command | Opener used |
|---|---|---|
| Linux | `python3 scripts/release_check.py` | `xdg-open` (needs `DISPLAY` or `WAYLAND_DISPLAY`) |
| macOS | `python3 scripts/release_check.py` | `open` |
| Windows | `py scripts\release_check.py` (PowerShell or cmd) | `os.startfile` |
| WSL | `python3 scripts/release_check.py` inside the distro | `wslview`, else `explorer.exe` with a `wslpath -w` path |

## Confirm by eye

1. The command exits 0 and `opened_html` and `opened_svg` are both `true`.
2. The HTML page shows in a graphical browser (never a console browser such as `w3m` or `lynx`), with the heading "Mimir release check".
3. The SVG shows as a picture with "Mimir release check" in it. Mimir uses each OS's own default opener on purpose (the most portable choice), so the SVG opens in the system's default app for SVG: a browser or an image viewer both pass. Note which one.
4. Both show the right platform text: `linux`, `macos`, `windows` or `wsl`.
5. The folder path with a space in it did not break the open.

Then fill in that OS's row below, with the commit you ran (`git rev-parse --short HEAD`). A row is `passed` only after a real run on that OS. Exit 1 or a page that does not render is `failed`: note what happened, and it blocks the release until fixed and rerun. Each run leaves its temp folder (path in the JSON) for you to look at; delete it afterwards.

## Results

| OS | Date | Commit | Opened (exit code) | Rendered (by eye) | Tester | Notes |
|---|---|---|---|---|---|---|
| Linux | 2026-10-19 | 71ed3ae + story 15 | yes, both (exit 0) | passed: HTML in Firefox, SVG in Gwenview, platform text right | Claude Code run, eye check by the maintainer | CachyOS, KDE on Wayland, Python 3.14.8. SVG opens in the system SVG default (Gwenview), accepted by design. |
| macOS | not run | n/a | not run | not checked by hand | n/a | The by-eye check was not run by hand. The script tests pass in CI (`.github/workflows/tests.yml`). |
| Windows | not run | n/a | not run | not checked by hand | n/a | The by-eye check was not run by hand. The script tests pass in CI (`.github/workflows/tests.yml`). |
| WSL | not run | n/a | not run | not checked by hand | n/a | The by-eye check was not run by hand. |
