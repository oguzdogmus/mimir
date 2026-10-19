#!/usr/bin/env python3
"""Mimir release check: the live browser-open test, run by hand on each OS.

Dev only, standard library only, Python 3.11+. No skill uses this script; see
``RELEASE.md`` for when and how to run it. Run as::

    python3 scripts/release_check.py [--no-open]

It writes a self-contained ``mimir-release-check.html`` and
``mimir-release-check.svg`` (with ``<title>`` and ``<desc>``), both showing
"Mimir release check" and the detected platform, into a new temp folder whose
name contains a space. It then opens each one through
``visual.open_in_browser``, the opener the skills ship with (never a copy),
and prints one JSON object::

    {"platform": "linux", "html": "/tmp/mimir release check abc/mimir-release-check.html",
     "svg": "/tmp/mimir release check abc/mimir-release-check.svg",
     "opened_html": true, "opened_svg": true, "line": "Opened ... "}

Exit 0 when both opened, else 1. ``--no-open`` only builds the files (both
``opened_*`` false) and exits 0. A bad argument exits 2 with one stderr line.
The folder is left in place so the browser can still read the files.
"""

from __future__ import annotations

import html
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import visual  # noqa: E402
from workspace import _Parser  # noqa: E402

PROG = "release_check.py"
HEADING = "Mimir release check"
STEM = "mimir-release-check"


def render_html(platform: str) -> str:
    p = html.escape(platform)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">\n"
            f"<title>{HEADING}</title>\n"
            "<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;"
            "color:#1a1a1a;background:#fff}code{font-size:1.1em}</style>\n</head>\n<body>\n"
            f"<h1>{HEADING}</h1>\n<p>Platform: <code id=\"platform\">{p}</code></p>\n"
            "<p>If you can read this in a graphical browser, the HTML page opened.</p>\n"
            "</body>\n</html>\n")


def render_svg(platform: str) -> str:
    p = html.escape(platform)
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"480\" height=\"160\" viewBox=\"0 0 480 160\" "
            "role=\"img\" aria-labelledby=\"t d\">\n"
            f"<title id=\"t\">{HEADING}</title>\n"
            f"<desc id=\"d\">A test image from the Mimir release check. Platform: {p}.</desc>\n"
            "<rect x=\"1\" y=\"1\" width=\"478\" height=\"158\" fill=\"#ffffff\" stroke=\"#1a1a1a\" stroke-width=\"2\"/>\n"
            f"<text x=\"240\" y=\"70\" text-anchor=\"middle\" font-family=\"sans-serif\" font-size=\"28\" fill=\"#1a1a1a\">{HEADING}</text>\n"
            f"<text x=\"240\" y=\"115\" text-anchor=\"middle\" font-family=\"sans-serif\" font-size=\"22\" fill=\"#1a1a1a\">Platform: {p}</text>\n"
            "</svg>\n")


def build(platform: str) -> tuple[Path, Path]:
    folder = Path(tempfile.mkdtemp(prefix="mimir release check "))
    page, image = folder / f"{STEM}.html", folder / f"{STEM}.svg"
    page.write_text(render_html(platform), encoding="utf-8")
    image.write_text(render_svg(platform), encoding="utf-8")
    return page, image


class BuildError(Exception):
    """The temp folder or a test file could not be written."""


def run(open_files: bool) -> tuple[dict, int]:
    platform = visual._platform()
    try:
        page, image = build(platform)
    except OSError as exc:
        raise BuildError(f"cannot write the test files: {exc}") from None
    opened_html = bool(visual.open_in_browser(page)) if open_files else False
    opened_svg = bool(visual.open_in_browser(image)) if open_files else False
    if not open_files:
        line, code = f"Built `{page}` and `{image}` (not opened).", 0
    elif opened_html and opened_svg:
        line, code = (f"Opened `{page}` and `{image}` with the system's default apps. Confirm both render "
                      f"and show platform {platform}."), 0
    else:
        line, code = f"Could not open both: open `{page}` and `{image}` in your browser.", 1
    return {"platform": platform, "html": str(page), "svg": str(image),
            "opened_html": opened_html, "opened_svg": opened_svg, "line": line}, code


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog=PROG, description="Mimir release check: build two test files and open them in the browser.")
    parser.add_argument("--no-open", action="store_true", help="build the files only, do not open them")
    args = parser.parse_args(argv)
    try:
        result, code = run(not args.no_open)
    except BuildError as exc:
        sys.stderr.write(f"{PROG}: {exc}\n")
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
