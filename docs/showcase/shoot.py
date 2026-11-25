#!/usr/bin/env python3
"""Rebuild the Skald showcase pages and take the README pictures (#95).

Dev-only, not part of CI. Each ``pieces/<name>.json`` is the exact ``visual.py page`` input
the visual builder wrote for one test piece of ``content.md`` (synthetic content, fixture
course ``2026-Fall/CS301 Automata``). Every fixture course is linked to its synthetic field
pack from ``tests/fixtures/`` first, because the shell builds nothing for a course without
one. This script builds every piece again through the
current ``scripts/visual.py`` in a throwaway workspace, so a change to the shell (tokens,
step controls, a mascot) shows up without rebuilding the bodies, then screenshots each
page with every step revealed, in light and dark::

    uv run --with playwright python docs/showcase/shoot.py      # writes assets/showcase/*.png
    python3 docs/showcase/shoot.py --html-only DIR               # only the pages, into DIR

The first form needs Playwright's Chromium (``uv run --with playwright playwright install
chromium`` once). Pictures are 1280 px wide at motion level none.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
PIECES = Path(__file__).resolve().parent / "pieces"
PICTURES = REPO / "assets" / "showcase"
WIDTH, HEIGHT = 1280, 1080
FIXTURE_PACKS = REPO / "tests" / "fixtures"
COURSE_FIELDS = {"CS301 Automata": "theory-of-computation", "BIO110 Microbiology": "microbiology"}


def run(script: str, cmd: str, data: dict, home: Path) -> dict:
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}  # Windows ignores HOME
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), cmd], input=json.dumps(data),
                          capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        sys.exit(f"shoot: {script} {cmd} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def build(out: Path, work: Path) -> list[Path]:
    """Build every piece in a fresh workspace under ``work``; copy the pages into ``out``."""
    home = work / "home"
    (home / ".config" / "mimir").mkdir(parents=True)
    (home / ".config" / "mimir" / "root").write_text(f"{work / 'learning'}\n", encoding="utf-8")
    run("workspace.py", "init", {}, home)  # its profile has no motion line: motion level none
    out.mkdir(parents=True, exist_ok=True)
    pages, saved = [], set()
    for path in sorted(PIECES.glob("*.json")):
        piece = json.loads(path.read_text(encoding="utf-8"))
        run("workspace.py", "course", {"term": piece["term"], "course": piece["course"]}, home)
        field = COURSE_FIELDS[piece["course"]]
        if field not in saved:
            pack = FIXTURE_PACKS / f"field-pack-{field}.json"
            run("fieldpack.py", "save", json.loads(pack.read_text(encoding="utf-8")), home)
            saved.add(field)
        run("fieldpack.py", "link", {"term": piece["term"], "course": piece["course"], "field": field}, home)
        built = Path(run("visual.py", "page", piece, home)["path"])
        pages.append(Path(shutil.copy2(built, out / built.name)))
    return pages


def shoot(pages: list[Path]) -> list[Path]:
    from playwright.sync_api import sync_playwright  # dev-only dependency

    PICTURES.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for page_path in pages:
            for theme in ("light", "dark"):
                page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, color_scheme=theme)
                page.goto(page_path.as_uri())
                page.wait_for_function("document.fonts.status === 'loaded'")
                total = int(page.get_attribute("html", "data-step-total") or 0)
                for _ in range(total):  # reveal every step, the last one marked
                    page.click("#mimir-next")
                page.evaluate("window.scrollTo(0, 0)")
                shot = PICTURES / f"{page_path.stem}-{theme}.png"
                page.screenshot(path=str(shot))
                shots.append(shot)
                page.close()
        browser.close()
    return shots


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--html-only", metavar="DIR", type=Path, help="only build the pages, into DIR")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        if args.html_only:
            for page in build(args.html_only, Path(tmp)):
                print(page)
            return
        for shot in shoot(build(Path(tmp) / "pages", Path(tmp))):
            print(shot.relative_to(REPO))


if __name__ == "__main__":
    main()
