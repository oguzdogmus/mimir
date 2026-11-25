#!/usr/bin/env python3
"""Mimir visual builder: Skald pages, safe SVG files and the browser open.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``verify.py`` (same folder). Run as::

    python3 visual.py <page|svg|open>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Every subcommand needs a workspace at
the learning root (see ``workspace.py``) and an existing course folder; the
term and course folders and the course ``.state/`` must not be symlinks.

This script is the trust boundary for generated pages: the model supplies
content, this script escapes it, checks it and places the file. Output goes
only to ``<course>/.state/out/<name>.<ext>``: ``out/`` is created when
missing, neither ``out/`` nor the target may be a symlink, and the file is
written atomically (a rebuild replaces it). ``name`` matches
``[a-z0-9]+(-[a-z0-9]+)*``, at most NAME_MAX_CHARS (60) characters. Errors
name the field, e.g. ``body.original[2].page`` (lists are numbered from 1).

page -- an offline page in the Skald house style from a body the builder wrote.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "name": "even-zeros",
          "title": "Even number of 0s", "body": "<header class=\\"head\\"><h1>...</h1></header>
           <p>Let \\(p\\) be ...</p><mimir-original path=\\"past-papers/q.jpg\\" page=\\"1\\"></mimir-original>"}
    out: {"course_dir": "/home/u/learning/2026-Fall/CS201 Theory",
          "path": "/home/u/learning/2026-Fall/CS201 Theory/.state/out/even-zeros.html",
          "line": "Built /home/u/learning/2026-Fall/CS201 Theory/.state/out/even-zeros.html."}
    ``title`` (required, one line, at most TITLE_MAX_CHARS) is the ``<title>``.
    ``body`` (required, at most PAGE_BODY_MAX_BYTES (1 MiB) as UTF-8, no
    control characters other than tab, newline and carriage return) is HTML
    that may hold inline SVG. It is parsed and checked against an allowlist,
    then written out again from what was checked (comments dropped, text and
    attribute values re-escaped, SVG names in their camelCase spelling), so
    the browser sees exactly the markup that passed. Allowed HTML elements:
    div, span, p, h1-h6, header, footer, section, article, aside, figure,
    figcaption, ul, ol, li, dl, dt, dd, table, thead, tbody, tfoot, tr, th,
    td, caption, colgroup, col, strong, em, b, i, u, s, small, sub, sup, mark,
    code, pre, kbd, var, samp, abbr, cite, q, blockquote, br, hr, wbr,
    details, summary, time, a, style, svg. Allowed HTML attributes: id,
    class, style, title, lang, dir, role, hidden, tabindex, ``aria-*``,
    ``data-*``, plus a href, th and td colspan/rowspan/headers (th also
    scope, abbr), col and colgroup span, ol start/reversed/type, li value,
    time datetime and details open. Inside an ``svg`` only the ``svg`` kind's
    elements, with any attribute except ``on*``. Refused: any other element
    (script, forms, buttons, inputs, img, iframe, object, embed, link, meta,
    base, math, template, foreignObject, ...); an ``on*`` attribute; an
    ``href`` (any namespace) not starting with ``#``; in a ``style``
    attribute, a ``<style>`` or any SVG attribute, ``javascript:``, ``url(``
    other than ``url(#...)``, ``@import``, another CSS function that loads
    something (``image(``, ``image-set(``, ``cross-fade(``, ``element(``,
    ``src(``, ``paint(``) or a backslash; ``<`` or ``&`` in ``<style>`` text;
    ``<style>`` text naming the shell's ``mimir-``/``sk-`` ids or classes
    (it could restyle or hide the controls); an outermost inline ``svg`` whose
    first two children are not a non-empty ``title`` then ``desc``, unless it
    has ``aria-hidden="true"``; elements inside an SVG ``title`` or ``desc``;
    a repeated id or one starting with ``mimir-`` or ``sk-``; a malformed or
    repeated attribute name; an end tag that does not close the open
    element, or an element left open; a body that ends inside an unfinished
    tag, comment or declaration; declarations, CDATA sections and
    processing instructions. Errors start ``body:``.
    Steps are markup: ``data-step="N"`` on any element, HTML or SVG (a text
    block, an SVG group), hides it until step N is revealed;
    ``data-highlight="N"`` marks a target of the teaching highlight while step
    N is the latest. N is a whole number from 1 to STEPS_MAX (50); the steps
    run 1 to n without gaps, a highlight names one of them, and an element
    never sits inside one with a higher step. With step markup the page gets
    the shell's step script (``assets/page/steps.js``, after any KaTeX): Back
    and Next controls (Enter and Space on them), the arrow keys anywhere
    outside fields and focusable areas, and a polite live region saying
    "Step k of n." Unrevealed steps are hidden on screen only, so with
    JavaScript off or on paper every step shows; a step back replays no
    animation. It also shows the shell's mascot (``assets/skald/mascot.svg``,
    inlined after ``<main>``, decorative and hidden in print and with
    JavaScript off) at the bottom right, his mood following the steps:
    curious before step 1, proud on the last, explaining, thinking,
    surprised and pleased in turn between. Without step markup the page
    carries no step script and no mascot.
    An original is placed with ``<mimir-original path="..." page="N">`` (empty,
    closed by ``</mimir-original>`` or ``/>``, not inside an SVG); ``path`` and
    ``page`` name the original of an ``ocr`` transcription, and errors name
    ``body.original[k]`` (markers numbered from 1). ``path`` is a registry
    path of this course's INDEX.md that resolves inside the course folder,
    ``page`` a whole number >= 1 within the row's pages when known. A png,
    jpg, jpeg, gif or webp file of at most ORIGINAL_EMBED_MAX_BYTES (10 MiB)
    is embedded as an image with alt text "Original: <path>, p.<page>";
    anything else becomes a ``file://`` link with that text (the whole page
    stands in for the crop). The page carries the Skald
    tokens (``assets/skald/tokens.css`` with its fonts as data URIs), the
    shell's chalk and marker filters (``#sk-chalk``, ``#sk-marker``) and
    ``data-motion`` on its root: the profile's ``motion:`` line (none, gentle
    or full) read at build time, none when it is missing or malformed; the
    system's reduced-motion setting is not consulted. When the body's text
    (outside SVG and ``<style>``) holds ``\\(`` or ``\\[``, KaTeX (``assets/vendor/katex``) is inlined:
    its JS, auto-render and CSS, with the woff2 fonts as data URIs and other
    font formats dropped. It renders ``\\(...\\)`` and ``\\[...\\]`` in
    ``<main>``, skipping SVG, with ``throwOnError: false`` and
    ``trust: false``.
    A Content-Security-Policy meta allows only ``data:`` fonts and images,
    inline styles and the page's own scripts by sha256 hash: nothing loads
    from the network. A page with no math, no steps and no machine has no
    script at all (``script-src 'none'``).
    ``machine`` (optional) attaches the automata simulator to the body's
    inline diagram:
    {"kind": "dfa", "states": ["q0", "q1"], "start": "q0", "accept": ["q0"],
     "transitions": [{"from": "q0", "read": "0", "to": "q1"}, ...]}.
    ``kind`` is dfa, nfa, pda or tree. Symbols (``read``, ``pop``, the
    characters of ``push``, ``stack_start``) are single characters that are
    not spaces, from the Basic Multilingual Plane; ``read`` "" is ε, allowed
    in nfa and pda only. A pda needs ``stack_start``; its moves take ``pop``
    ("" or one symbol) and ``push`` (the new top first; at most
    MACHINE_MAX_STACK symbols); other kinds refuse those fields. dfa and tree
    allow at most one move per (state, symbol). A tree's root has no incoming
    edge, every other node exactly one, and every node is reachable from the
    root. Limits: MACHINE_MAX_STATES (60) states with names of at most
    STATE_NAME_MAX_CHARS (20), MACHINE_MAX_TRANSITIONS (400) moves.
    ``example`` (optional) is the input the simulator starts with: at most
    MACHINE_MAX_SYMBOLS (64) symbols (spaces ignored) and EXAMPLE_MAX_CHARS
    (4000) characters. The body needs an element ``id="state-<i>"`` inside an inline SVG for
    each state i (counting from 1). After the body the shell adds the
    simulator controls (``#mimir-sim``) and the machine as a table, the
    machine as JSON data and the simulator scripts (allowed by hash); current
    states get ``data-highlight-on`` (the teaching highlight), and the arrow
    keys act only while focus is in the simulator. The page simulates sets of
    configurations with ε-closure, at most MACHINE_MAX_CONFIGS (256) at once
    and a PDA stack of at most MACHINE_MAX_STACK, saying "Search limit reached"
    when it cuts; it accepts by final state after the whole input. A live
    region and an ordered history say each step in words, ending Accepted,
    Rejected or Stuck. The body's ``<style>`` is
    not scoped, since the builder writes the whole page. ``example`` without
    ``machine`` is refused; a page without ``machine`` has no simulator.
    Every ``<svg>`` in the body passes the label check of ``svg`` (errors name
    ``svg k`` when the body holds more than one), with the page's ``<style>``
    rules and a 17 px inherited font size.

svg -- check one SVG document and write it with the Skald tokens.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "name": "dfa-even-zeros",
          "svg": "<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 200 80\\">
                  <title>DFA for an even number of 0s</title><desc>...</desc>...</svg>"}
    out: {"course_dir": "...", "path": "/home/u/learning/2026-Fall/CS201 Theory/.state/out/dfa-even-zeros.svg",
          "line": "Built /home/u/learning/2026-Fall/CS201 Theory/.state/out/dfa-even-zeros.svg."}
    Refused: more than SVG_MAX_BYTES (1 MiB) as UTF-8; control characters
    other than tab, newline and carriage return; a DOCTYPE or ENTITY; an
    XML declaration whose ``encoding`` is not UTF-8 (the bytes are written
    as UTF-8);
    processing instructions (``<?xml ...?>`` itself is fine); XML that does
    not parse; a root that is not the SVG-namespace ``svg``; first two child
    elements other than a non-empty ``title`` then a non-empty ``desc``; any
    element outside the SVG namespace or the allowlist (svg, g, defs, symbol,
    use, title, desc, style, path, rect, circle, ellipse, line, polyline,
    polygon, text, tspan, marker, linearGradient, radialGradient, stop,
    clipPath, mask); an ``on*`` attribute; an ``href`` (any namespace) not
    starting with ``#``; ``javascript:`` in an attribute or style; ``url(``
    other than ``url(#...)``; ``@import`` or another CSS function that loads
    something (``image(``, ``image-set(``, ``src(``, ...); a backslash in an
    attribute value or ``style`` text (CSS escapes would hide the checks).
    The document is written as given, with one ``<style>`` added as the root's
    last child: the Skald tokens, fonts inlined, in a CDATA section.
    Labels are checked too (as in every SVG of a ``page``): a ``<text>`` whose
    estimated box touches a stroked line, polyline, polygon, path, rect,
    circle or ellipse, or leaves the viewBox, is refused with the label, its
    position and what it touched. The box comes from the text's position,
    anchor, font size and character count (LABEL_WIDTH_FACTOR em a character,
    LABEL_ASCENT and LABEL_DESCENT em around the baseline, LABEL_MARGIN units
    of clearance), through every transform; font sizes and strokes follow the
    Skald tokens and the figure's CSS (type, class and id selectors), once
    without and once with its ``@media`` rules (the phone sizes).

open -- open a built file in the default browser.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "file": "pumping-lemma.html"}
    out: {"path": "/home/u/learning/2026-Fall/CS201 Theory/.state/out/pumping-lemma.html",
          "opened": true,
          "line": "Opened `/home/u/.../pumping-lemma.html` in your browser."}
    ``file`` is an existing ``<name>.html`` or ``<name>.svg`` in ``out/``
    (a regular file, not a symlink). macOS: ``open``; Windows:
    ``os.startfile``; WSL: ``wslview``, else ``explorer.exe`` with the
    ``wslpath -w`` path; other Linux: ``xdg-open`` only when DISPLAY or
    WAYLAND_DISPLAY is set. A console browser is never used. The launcher is
    waited on for at most OPEN_WAIT_SECONDS (5); one still running then counts
    as opened. A non-zero exit (except explorer.exe, which exits 1 on
    success) or a launcher that cannot start counts as not opened, and
    ``line`` is then "Open `<path>` in your browser." (the path is the
    fallback).

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``visual.py: <message>``) and nothing
on stdout. An unexpected internal error exits 1 with ``visual.py: internal
error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import ingest
import verify
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

NAME_MAX_CHARS = 60
TITLE_MAX_CHARS = 120
ORIGINAL_EMBED_MAX_BYTES = 10 * 1024 * 1024
SVG_MAX_BYTES = 1024 * 1024
PAGE_BODY_MAX_BYTES = 1024 * 1024
OPEN_WAIT_SECONDS = 5
STEPS_MAX = 50                 # data-step numbers on one page
MACHINE_MAX_STATES = 60
MACHINE_MAX_TRANSITIONS = 400
STATE_NAME_MAX_CHARS = 20
MACHINE_MAX_SYMBOLS = 64         # symbols in one fed input
EXAMPLE_MAX_CHARS = 4000       # the example input, spaces included
MACHINE_MAX_CONFIGS = 256        # configurations followed at once (NFA/PDA)
MACHINE_MAX_STACK = 64           # PDA stack depth

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_KATEX = _ASSETS / "vendor" / "katex"
_PAGE_TEMPLATE = _ASSETS / "page" / "page.html"
_PAGE_MATH_JS = _ASSETS / "page" / "math.js"
_MACHINE_JS = _ASSETS / "page" / "machine.js"       # the simulator engine (MimirSim)
_PAGE_SIM_JS = _ASSETS / "page" / "simulator.js"
_PAGE_STEPS_JS = _ASSETS / "page" / "steps.js"
_MASCOT_SVG = _ASSETS / "skald" / "mascot.svg"   # decorative art, no ids: inlined as it is
_SKALD = _ASSETS / "skald"

_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_FILE = re.compile(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.(html|svg)")
_SLOT = re.compile(r"\{\{([A-Z_]+)\}\}")
_IMAGE_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
               "webp": "image/webp"}

_SVG_NS = "http://www.w3.org/2000/svg"
_SVG_ELEMENTS = {"svg", "g", "defs", "symbol", "use", "title", "desc", "style", "path", "rect", "circle",
                 "ellipse", "line", "polyline", "polygon", "text", "tspan", "marker", "linearGradient",
                 "radialGradient", "stop", "clipPath", "mask"}
_URL = re.compile(r"url\(", re.I)
_URL_LOCAL = re.compile(r"url\(\s*['\"]?#", re.I)
# CSS functions besides url() that can load an image or a resource: all refused
_CSS_FETCH = re.compile(r"(?<![\w-])(-webkit-image-set|image-set|-webkit-cross-fade|cross-fade|-moz-element|element"
                        r"|image|src|paint)\(", re.I)
_XML_DECL = re.compile(r"\ufeff?<\?xml\s[^>]*\?>")
_ENCODING = re.compile(r"""\bencoding\s*=\s*["']([^"']*)["']""")
_ALLOWED_CONTROL = {"\t", "\n", "\r"}
_XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", _XLINK_NS)
_MACHINE_KINDS = ("dfa", "nfa", "pda", "tree")
_KIND_TEXT = {"dfa": "DFA", "nfa": "NFA", "pda": "PDA, accepting by final state",
              "tree": "tree: the input walks the labelled edges from the root"}


# --- Shared ------------------------------------------------------------------------

def _name(data: dict) -> str:
    value = data.get("name")
    if not isinstance(value, str) or not value:
        raise InputError("name is required (lowercase letters, digits and single hyphens)")
    if len(value) > NAME_MAX_CHARS or not _NAME.fullmatch(value):
        raise InputError(f"name must match [a-z0-9]+(-[a-z0-9]+)* and be at most {NAME_MAX_CHARS} "
                         f"characters: {_short(value)}")
    return value


def _out_dir(course_dir: Path, create: bool) -> Path:
    out = course_dir / ".state" / "out"
    if out.is_symlink():
        raise InputError(f"output folder {out} is a symlink; refusing to write through it")
    if out.exists() and not out.is_dir():
        raise InputError(f"output folder {out} exists and is not a folder")
    if not out.exists():
        if not create:
            raise InputError(f"no output folder at {out}; build a page or an SVG first")
        out.mkdir()
    return out


def _write_new_or_replace(target: Path, data: bytes) -> None:
    """Write ``data`` to ``target`` atomically (temp file in the same folder, then replace)."""
    if target.is_symlink():
        raise InputError(f"{target} is a symlink; refusing to replace it")
    if target.exists() and not target.is_file():
        raise InputError(f"{target} exists and is not a regular file")
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_out(course_dir: Path, name: str, ext: str, content: bytes) -> dict:
    out = _out_dir(course_dir, create=True)
    target = out / f"{name}.{ext}"
    _write_new_or_replace(target, content)
    return {"course_dir": str(course_dir), "path": str(target), "line": f"Built {target}."}


# --- shared page parts -------------------------------------------------------------------------

def _vendor_text(rel: str) -> str:
    return (_KATEX / rel).read_text(encoding="utf-8")


def _inline_fonts(css: str) -> str:
    """Rewrite each @font-face ``src`` to its woff2 file as a data URI; drop other formats."""
    def font_face(match: re.Match) -> str:
        body = match.group(1)
        src = re.search(r"src:([^;}]*)", body)
        if src is None:
            raise RuntimeError("KaTeX @font-face without src")
        woff2 = re.search(r"url\(fonts/([A-Za-z0-9_-]+\.woff2)\)\s*format\([\"']woff2[\"']\)", src.group(1))
        if woff2 is None:
            raise RuntimeError("KaTeX @font-face without a woff2 source")
        payload = base64.b64encode((_KATEX / "fonts" / woff2.group(1)).read_bytes()).decode("ascii")
        new_src = f'src:url(data:font/woff2;base64,{payload}) format("woff2")'
        return "@font-face{" + body[:src.start()] + new_src + body[src.end():] + "}"

    out = re.sub(r"@font-face\{([^}]*)\}", font_face, css)
    if any(not m.startswith("url(data:") for m in re.findall(r"url\([^)]{0,5}", out)):
        raise RuntimeError("KaTeX CSS still references a file")
    return out


def _check_raw(value: str, closer: str, what: str) -> str:
    """Vendored code inlined into a raw-text element must not be able to close it."""
    low = value.lower()
    if closer in low or "<!--" in low or "<script" in low:
        raise RuntimeError(f"vendored {what} cannot be inlined safely")
    return value


def _csp_hash(script: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"


def _original(value, where: str, rows: dict, course_dir: Path, index: Path) -> str:
    if not isinstance(value, dict):
        raise InputError(f"{where} must be an object {{path, page}}")
    verify._keys(value, {"path", "page"}, where)
    if "path" not in value:
        raise InputError(f"{where}.path is required")
    if "page" not in value:
        raise InputError(f"{where}.page is required")
    rel = verify._text(value["path"], f"{where}.path", None)
    page = verify._page(value["page"], f"{where}.page")
    row = rows.get(rel)
    if row is None:
        raise InputError(f"{where}.path: {_short(rel)} has no registry row inside the course in {index}")
    pages = row[1]
    if pages is not None and page > pages:
        raise InputError(f"{where}.page: page {page} is past the last page of {rel} ({pages})")
    path = course_dir / rel
    if not path.is_file():
        raise InputError(f"{where}.path: {path} is not an existing file")
    text = f"Original: {rel}, p.{page}"
    ext = path.suffix.lower().lstrip(".")
    if ext in _IMAGE_MIME and path.stat().st_size <= ORIGINAL_EMBED_MAX_BYTES:
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return (f'<figure class="original"><img src="data:{_IMAGE_MIME[ext]};base64,{payload}" '
                f'alt="{html.escape(text)}"><figcaption aria-hidden="true">{html.escape(text)}</figcaption>'
                "</figure>")
    uri = path.resolve().as_uri() + (f"#page={page}" if ext == "pdf" else "")
    return (f'<p class="original original-link"><a href="{html.escape(uri)}">{html.escape(text)}</a></p>')


def _fill(template: str, values: dict[str, str]) -> str:
    """Replace every ``{{SLOT}}`` in one pass; inserted values are never re-scanned."""
    found = set(_SLOT.findall(template))
    if found != set(values):
        raise RuntimeError("page template slots do not match")
    return _SLOT.sub(lambda m: values[m.group(1)], template)


def _katex() -> dict[str, str]:
    """KaTeX's CSS (woff2 fonts as data URIs), its JS and auto-render, checked for inlining."""
    return {
        "KATEX_CSS": _check_raw(_inline_fonts(_vendor_text("katex.min.css")), "</style", "KaTeX CSS"),
        "KATEX_JS": _check_raw(_vendor_text("katex.min.js"), "</script", "KaTeX JS"),
        "AUTO_RENDER_JS": _check_raw(_vendor_text("contrib/auto-render.min.js"), "</script", "auto-render"),
    }


def _json_script(value) -> str:
    """JSON for a ``<script type="application/json">`` body: ``<``, ``>`` and ``&`` are escaped."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _csp(hashes: list[str]) -> str:
    """The page's Content-Security-Policy: nothing from the network, only these scripts by hash."""
    return html.escape("default-src 'none'; script-src " + (" ".join(hashes) or "'none'") + "; "
                       "style-src 'unsafe-inline'; font-src data:; img-src data:; "
                       "base-uri 'none'; form-action 'none'", quote=False)


# --- svg ---------------------------------------------------------------------------

def _local(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        ns, _, local = tag[1:].partition("}")
        return ns, local
    return "", tag


def _check_css_text(value: str, where: str, field: str = "svg") -> None:
    low = value.lower()
    if "\\" in value:
        raise InputError(f"{field}: {where} contains a backslash (CSS escapes are not allowed)")
    if "javascript:" in re.sub(r"[\s\x00-\x1f]", "", low):
        raise InputError(f"{field}: {where} contains javascript:")
    if "@import" in low:
        raise InputError(f"{field}: {where} contains @import")
    fetch = _CSS_FETCH.search(value)
    if fetch:
        raise InputError(f"{field}: {where} contains {fetch.group(1).lower()}( (only url(#...) may point at anything)")
    if len(_URL.findall(value)) != len(_URL_LOCAL.findall(value)):
        raise InputError(f"{field}: {where} has url( that is not url(#...)")


def check_svg(raw: bytes) -> ET.Element:
    """Refuse an SVG document that could run script or load anything (see the docstring); return its root."""
    text = raw.decode("utf-8")
    low = text.lower()
    if "<!doctype" in low:
        raise InputError("svg: a DOCTYPE is not allowed")
    if "<!entity" in low:
        raise InputError("svg: an ENTITY declaration is not allowed")
    decl = _XML_DECL.match(text)
    encoding = _ENCODING.search(decl.group(0)) if decl else None
    if encoding and encoding.group(1).lower() not in ("utf-8", "utf8"):
        raise InputError(f"svg: the XML declaration's encoding must be UTF-8 (the file is written as UTF-8), "
                         f"not {_short(encoding.group(1))}")
    if encoding:  # expat knows only the "utf-8" spelling; browsers read "utf8" the same way
        start = decl.start() + encoding.start(1)
        text = text[:start] + "utf-8" + text[decl.start() + encoding.end(1):]
        raw = text.encode("utf-8")
    parser = ET.XMLPullParser(events=("start", "pi"))
    try:
        parser.feed(raw)
        parser.close()
    except ET.ParseError as exc:
        raise InputError(f"svg: not well-formed XML ({exc})") from None
    root = None
    for event, item in parser.read_events():
        if event == "pi":
            raise InputError("svg: processing instructions are not allowed")
        if root is None:
            root = item
    if root is None or _local(root.tag) != (_SVG_NS, "svg"):
        raise InputError(f"svg: the root element must be svg in the namespace {_SVG_NS}")
    kids = list(root)
    for k, want in ((0, "title"), (1, "desc")):
        if len(kids) <= k or _local(kids[k].tag) != (_SVG_NS, want):
            raise InputError(f"svg: child element {k + 1} of the root must be <{want}>")
        if not "".join(kids[k].itertext()).strip():
            raise InputError(f"svg: <{want}> must not be empty")
    for element in root.iter():
        ns, local = _local(element.tag)
        if ns != _SVG_NS or local not in _SVG_ELEMENTS:
            shown = local if ns in ("", _SVG_NS) else f"{{{ns}}}{local}"
            raise InputError(f"svg: element <{shown}> is not allowed")
        for attr, value in element.attrib.items():
            _, name = _local(attr)
            where = f"<{local}> attribute {name}"
            if name.lower().startswith("on"):
                raise InputError(f"svg: event attribute {name} on <{local}> is not allowed")
            if name.lower() == "href" and not value.startswith("#"):
                raise InputError(f"svg: {where} must start with # (no external links): {_short(value)}")
            _check_css_text(value, where)
        if local == "style":
            _check_css_text("".join(element.itertext()), "<style>")
    return root


def _markup_field(value, field: str, what: str, max_bytes: int) -> bytes:
    """A builder-written markup field (``svg``, ``body``) as UTF-8: non-empty, no control characters, not too big."""
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} is required ({what})")
    if any(c not in _ALLOWED_CONTROL and unicodedata.category(c) in ("Cc", "Cs") for c in value):
        raise InputError(f"{field} contains control characters or lone surrogates")
    raw = value.encode("utf-8")
    if len(raw) > max_bytes:
        raise InputError(f"{field} is {len(raw)} bytes; at most {max_bytes}")
    return raw


def build_svg(svg) -> str:
    """The standalone SVG file for ``svg``: every check of ``visual.py svg``, then the Skald tokens added."""
    figure = _tree_from_svg(check_svg(_markup_field(svg, "svg", "the SVG document as a string", SVG_MAX_BYTES)))
    check_labels([figure], _style_texts(figure), "svg", _SVG_FONT_PX)
    return _svg_with_tokens(svg)


def cmd_svg(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "svg"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    course_dir = verify._course_dir(term, course)
    return _write_out(course_dir, name, "svg", build_svg(data.get("svg")).encode("utf-8"))


# --- Skald tokens --------------------------------------------------------------------

_SKALD_FONT = re.compile(r'url\("fonts/([a-z0-9-]+\.woff2)"\)')


def skald_tokens() -> str:
    """The Skald stylesheet with its bundled fonts as data URIs (nothing left to load)."""
    def font(match: re.Match) -> str:
        payload = base64.b64encode((_SKALD / "fonts" / match.group(1)).read_bytes()).decode("ascii")
        return f"url(data:font/woff2;base64,{payload})"

    css = _SKALD_FONT.sub(font, (_SKALD / "tokens.css").read_text(encoding="utf-8"))
    if 'url("fonts/' in css or "url(fonts/" in css:
        raise RuntimeError("Skald tokens still reference a font file")
    return css


_SVG_ROOT_END = re.compile(r"</(?:([A-Za-z_][\w.-]*):)?svg\s*>((?:\s|<!--(?:(?!-->).)*-->)*)\Z", re.S)


def _svg_with_tokens(svg: str) -> str:
    """Append the Skald tokens as the root's last ``<style>`` (CSS applies wherever it sits)."""
    css = skald_tokens()
    end = _SVG_ROOT_END.search(svg)
    if end is None or "]]>" in css:
        raise RuntimeError("cannot place the Skald tokens in the SVG")
    tag = f"{end.group(1)}:style" if end.group(1) else "style"
    return svg[:end.start()] + f"<{tag}><![CDATA[\n{css}]]></{tag}>" + svg[end.start():]


# --- label overlap check -------------------------------------------------------------
# The shell cannot render fonts, so each label's box is estimated from its position,
# anchor, font size and character count. Font sizes, strokes and visibility follow a small
# CSS cascade over the Skald tokens and the figure's own <style> rules: type, class and id
# selectors with descendant and child combinators; rules with pseudo-classes or attribute
# selectors (states such as a highlight) are skipped. The check runs twice, once without
# and once with the rules inside @media and @supports, so a figure is checked at its
# phone font sizes too.

LABEL_WIDTH_FACTOR = 0.58      # estimated advance of one character, in em
LABEL_ASCENT = 0.7             # box top above the baseline, in em
LABEL_DESCENT = 0.22           # box bottom below the baseline, in em
LABEL_MARGIN = 1.5             # clearance between a label's box and a stroke, in the label's units
LABEL_PROBLEMS_SHOWN = 5
_PAGE_FONT_PX = 17.0           # the page's body font (tokens.css --fs-body, 1.0625rem), inherited by inline SVG
_SVG_FONT_PX = 16.0            # a standalone SVG's root font: the browser default

_CSS_PROPS = ("font-size", "stroke", "stroke-width", "stroke-linecap", "display", "visibility", "text-anchor",
              "dominant-baseline")
_INHERITED = set(_CSS_PROPS) - {"display"}
_NOT_DRAWN = {"defs", "symbol", "marker", "clippath", "mask", "lineargradient", "radialgradient", "title", "desc",
              "style", "pattern", "metadata"}
_SHAPES = {"line", "polyline", "polygon", "path", "rect", "circle", "ellipse"}
_HTML_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_DIMENSION = re.compile(r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(px|rem|em|pt|ex|ch|%)?(?![\w%])", re.I)
_FONT_KEYWORDS = {"xx-small": 9, "x-small": 10, "small": 13, "medium": 16, "large": 18, "x-large": 24,
                  "xx-large": 32, "xxx-large": 48}
_COMPOUND = re.compile(r"(\*|[a-z][\w-]*)?((?:[.#][\w-]+)*)", re.I)
_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate|skewx|skewy)\s*\(([^)]*)\)", re.I)


class _Node:
    """One element of a figure (SVG or the page's HTML around it), names lowercased."""
    __slots__ = ("tag", "attrs", "kids", "parent", "classes")

    def __init__(self, tag: str, attrs: dict, parent: "_Node | None"):
        self.tag, self.attrs, self.parent, self.kids = tag.lower(), attrs, parent, []
        self.classes = set(attrs.get("class", "").split())


def _tree_from_svg(root: ET.Element) -> _Node:
    def convert(el, parent):
        return _Node(_local(el.tag)[1], {_local(k)[1].lower(): v for k, v in el.attrib.items()}, parent)
    top = convert(root, None)
    todo = [(root, top)]
    while todo:
        el, node = todo.pop()
        if el.text:
            node.kids.append(el.text)
        for child in el:
            kid = convert(child, node)
            node.kids.append(kid)
            todo.append((child, kid))
            if child.tail:
                node.kids.append(child.tail)
    return top


class _BodyTree(HTMLParser):
    """The checked page body as a tree inside html > body > main, as the shell places it."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        html_node = _Node("html", {}, None)
        body = _Node("body", {}, html_node)
        self.root = _Node("main", {}, body)
        self.cur = self.root

    def _in_svg(self) -> bool:
        node = self.cur
        while node is not None and node.tag != "svg":
            node = node.parent
        return node is not None

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, {k.lower(): v or "" for k, v in attrs}, self.cur)
        self.cur.kids.append(node)
        if self._in_svg() or tag not in _HTML_VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(_Node(tag, {k.lower(): v or "" for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        if self.cur.parent is not None:
            self.cur = self.cur.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def _ancestors(node: _Node):
    while node.parent is not None:
        node = node.parent
        yield node


def _walk(node: _Node):
    todo = [node]
    while todo:
        node = todo.pop()
        yield node
        todo.extend(reversed([k for k in node.kids if isinstance(k, _Node)]))


def _text_of(node: _Node) -> str:
    return "".join(k if isinstance(k, str) else _text_of(k) for k in node.kids)


# -- CSS

def _css_blocks(css: str):
    depth, start, body = 0, 0, 0
    for i, c in enumerate(css):
        if c == "{":
            if depth == 0:
                prelude, body = css[start:i], i + 1
            depth += 1
        elif c == "}" and depth:
            depth -= 1
            if depth == 0:
                yield prelude.rsplit(";", 1)[-1].strip(), css[body:i]
                start = i + 1


def _split_top(text: str, sep: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        depth += c == "("
        depth -= c == ")"
        if c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    return parts + [text[start:]]


def _declarations(body: str) -> dict[str, tuple[str, bool]]:
    out = {}
    for decl in _split_top(body, ";"):
        prop, colon, value = decl.partition(":")
        prop, value = prop.strip().lower(), value.strip()
        if not colon or not value:
            continue
        important = value.lower().endswith("!important")
        if important:
            value = value[:-len("!important")].strip()
        if prop == "font":  # the shorthand's size is the token with a unit, before an optional "/line-height"
            sizes = (t.split("/")[0] for t in value.split())
            size = next((t for t in sizes if (m := _DIMENSION.fullmatch(t)) and m.group(2)
                         or t.lower() in _FONT_KEYWORDS), None)
            if size is not None:
                out["font-size"] = (size, important)
        elif prop in _CSS_PROPS:
            out[prop] = (value, important)
    return out


def _selector(text: str):
    """Compounds left to right as (tag, classes, id, combinator to the left), or None when unsupported."""
    if any(c in text for c in ":[+~"):
        return None
    parts, comb = [], " "
    for token in text.replace(">", " > ").split():
        if token == ">":
            comb = ">"
            continue
        m = _COMPOUND.fullmatch(token)
        if not m or not token:
            return None
        tag = (m.group(1) or "*").lower()
        names = re.findall(r"([.#])([\w-]+)", m.group(2))
        ids = [n for kind, n in names if kind == "#"]
        parts.append((tag, frozenset(n for kind, n in names if kind == "."), ids[0] if ids else None, comb))
        comb = " "
    return parts or None


def _css_rules(css: str, conditional: bool = False, rules: list | None = None) -> list:
    rules = [] if rules is None else rules
    for prelude, body in _css_blocks(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if prelude.startswith("@"):
            if prelude[1:].split(None, 1)[0].lower() in ("media", "supports", "layer", "container"):
                _css_rules(body, True, rules)
            continue
        decls = _declarations(body)
        if not decls:
            continue
        for text in _split_top(prelude, ","):
            parts = _selector(text.strip())
            if parts:
                spec = (sum(p[2] is not None for p in parts), sum(len(p[1]) for p in parts),
                        sum(p[0] != "*" for p in parts))
                rules.append((parts, spec, len(rules), decls, conditional))
    return rules


def _compound_matches(part, node: _Node) -> bool:
    tag, classes, ident, _ = part
    return (tag == "*" or tag == node.tag) and classes <= node.classes and (ident is None or
                                                                            node.attrs.get("id") == ident)


def _selector_matches(parts, i: int, node: _Node) -> bool:
    if not _compound_matches(parts[i], node):
        return False
    if i == 0:
        return True
    up = node.parent
    if parts[i][3] == ">":
        return up is not None and _selector_matches(parts, i - 1, up)
    while up is not None:
        if _selector_matches(parts, i - 1, up):
            return True
        up = up.parent
    return False


class _Cascade:
    """Computed font size, stroke, visibility, anchor and baseline per element."""

    def __init__(self, rules: list, conditional: bool, root_font: float):
        self.root_font = root_font
        self.index: dict[tuple, list] = {}
        for rule in rules:
            if rule[4] and not conditional:
                continue
            tag, classes, ident, _ = rule[0][-1]
            key = ("#", ident) if ident else (".", min(classes)) if classes else ("t", tag)
            self.index.setdefault(key, []).append(rule)

    def initial(self) -> dict:
        return {"font-size": self.root_font, "stroke": False, "stroke-width": 1.0, "stroke-linecap": "butt",
                "visibility": True, "text-anchor": "start", "dominant-baseline": "auto", "display": True}

    def style(self, node: _Node, parent: dict) -> dict:
        found: dict[str, list] = {}
        for prop in _CSS_PROPS:
            if prop in node.attrs:
                found.setdefault(prop, []).append(((False, 0, (-1, 0, 0), 0), node.attrs[prop]))
        keys = [("#", node.attrs.get("id")), ("t", node.tag), ("t", "*")] + [(".", c) for c in node.classes]
        for key in keys:
            for parts, spec, order, decls, _ in self.index.get(key, ()):
                if _selector_matches(parts, len(parts) - 1, node):
                    for prop, (value, important) in decls.items():
                        found.setdefault(prop, []).append(((important, 0, spec, order), value))
        if "style" in node.attrs:
            for prop, (value, important) in _declarations(node.attrs["style"]).items():
                found.setdefault(prop, []).append(((important, 1, (0, 0, 0), 0), value))
        out = {p: v for p, v in parent.items() if p in _INHERITED}
        out["display"] = True
        for prop in (p for p in _CSS_PROPS if p in found):  # font-size first: em lengths need it
            for _, value in sorted(found[prop], key=lambda c: c[0], reverse=True):
                value = self._value(prop, value.strip(), parent, out)
                if value is not None:
                    out[prop] = value
                    break
        return out

    def _value(self, prop: str, value: str, parent: dict, out: dict):
        low = value.lower()
        if low in ("inherit", "unset"):
            return parent.get(prop, self.initial()[prop])
        if low == "initial":
            return self.initial()[prop]
        if prop == "font-size":
            return self._font_size(low, parent["font-size"])
        if prop == "stroke":
            return low not in ("none", "transparent")
        if prop == "stroke-width":
            m = _DIMENSION.fullmatch(low)
            if not m or m.group(2) == "%":
                return None
            return _length(m, out["font-size"])
        if prop == "display":
            return low != "none"
        if prop == "visibility":
            return low not in ("hidden", "collapse")
        return low

    def _font_size(self, value: str, parent: float):
        if value in _FONT_KEYWORDS:
            return float(_FONT_KEYWORDS[value])
        if value in ("smaller", "larger"):
            return parent / 1.2 if value == "smaller" else parent * 1.2
        if "(" in value:  # clamp(), min(), max(), calc(), var(--x, 14px): the largest length inside
            sizes = [_length(m, parent) for m in _DIMENSION.finditer(value) if m.group(2)]
        else:
            m = _DIMENSION.fullmatch(value)
            sizes = [_length(m, parent)] if m else []
        return max(sizes) if sizes and max(sizes) > 0 else None


def _length(m: re.Match, font: float) -> float:
    unit = (m.group(2) or "").lower()
    return float(m.group(1)) * {"": 1, "px": 1, "rem": 16, "pt": 4 / 3, "em": font, "ex": font / 2,
                                "ch": font / 2, "%": font / 100}[unit]


def _offset(node: "_Node", name: str, font: float) -> float:
    m = _DIMENSION.match((node.attrs.get(name) or "").strip())
    return _length(m, font) if m and (m.group(2) or "").lower() != "%" else 0.0


# -- geometry

def _mul(m, n):
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + c * q, b * p + d * q, a * r + c * s, b * r + d * s, a * t + c * u + e, b * t + d * u + f)


def _apply(m, x: float, y: float) -> tuple[float, float]:
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def _inverse(m):
    a, b, c, d, e, f = m
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    return (d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det)


def _scale(m) -> float:
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))


_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _transform(value: str):
    m = _IDENTITY
    for name, args in _TRANSFORM.findall(value or ""):
        v = [float(x) for x in _NUMBER.findall(args)]
        name = name.lower()
        if name == "matrix" and len(v) == 6:
            step = tuple(v)
        elif name == "translate" and v:
            step = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale" and v:
            step = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate" and v:
            r = math.radians(v[0])
            step = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                step = _mul(_mul((1, 0, 0, 1, v[1], v[2]), step), (1, 0, 0, 1, -v[1], -v[2]))
        elif name in ("skewx", "skewy") and v:
            t = math.tan(math.radians(v[0]))
            step = (1, 0, t, 1, 0, 0) if name == "skewx" else (1, t, 0, 1, 0, 0)
        else:
            return _IDENTITY  # an invalid transform list is ignored, as browsers do
        m = _mul(m, step)
    return m


def _number(node: _Node, name: str, default: float | None = 0.0):
    m = _NUMBER.match((node.attrs.get(name) or "").strip())
    return float(m.group(0)) if m else default


def _ellipse(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]


def _arc(x0, y0, rx, ry, phi, large, sweep, x1, y1):
    """Points along an SVG elliptical arc (endpoint form), after x0, y0."""
    if (x0, y0) == (x1, y1):
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [(x1, y1)]
    cos, sin = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    xp, yp = cos * dx + sin * dy, -sin * dx + cos * dy
    grow = xp * xp / (rx * rx) + yp * yp / (ry * ry)
    if grow > 1:
        rx, ry = rx * math.sqrt(grow), ry * math.sqrt(grow)
    num = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp
    k = math.sqrt(max(0.0, num / (rx * rx * yp * yp + ry * ry * xp * xp)))
    k = -k if large == sweep else k
    cxp, cyp = k * rx * yp / ry, -k * ry * xp / rx
    cx, cy = cos * cxp - sin * cyp + (x0 + x1) / 2, sin * cxp + cos * cyp + (y0 + y1) / 2
    t0 = math.atan2((yp - cyp) / ry, (xp - cxp) / rx)
    t1 = math.atan2((-yp - cyp) / ry, (-xp - cxp) / rx)
    dt = t1 - t0
    if sweep and dt < 0:
        dt += 2 * math.pi
    elif not sweep and dt > 0:
        dt -= 2 * math.pi
    n = max(4, int(abs(dt) / (math.pi / 18)) + 1)
    return [(cx + rx * math.cos(t0 + dt * i / n) * cos - ry * math.sin(t0 + dt * i / n) * sin,
             cy + rx * math.cos(t0 + dt * i / n) * sin + ry * math.sin(t0 + dt * i / n) * cos)
            for i in range(1, n + 1)]


def _path(d: str) -> list[list[tuple[float, float]]]:
    """Subpaths of an SVG path as polylines; parsing stops at the first error, as rendering does."""
    tokens = re.findall(r"[MmZzLlHhVvCcSsQqTtAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    out, cur, i = [], [], 0
    x = y = sx = sy = 0.0
    cmd, last_ctrl, last_cmd = None, None, ""

    def nums(k):
        nonlocal i
        if i + k > len(tokens) or any(t.isalpha() for t in tokens[i:i + k]):
            raise ValueError
        i += k
        return [float(t) for t in tokens[i - k:i]]

    def curve(points, steps=16):
        n = len(points) - 1
        res = []
        for s in range(1, steps + 1):
            t = s / steps
            if n == 2:
                res.append(tuple((1 - t) ** 2 * points[0][j] + 2 * (1 - t) * t * points[1][j] + t * t * points[2][j]
                                 for j in (0, 1)))
            else:
                res.append(tuple((1 - t) ** 3 * points[0][j] + 3 * (1 - t) ** 2 * t * points[1][j]
                                 + 3 * (1 - t) * t * t * points[2][j] + t ** 3 * points[3][j] for j in (0, 1)))
        return res

    try:
        while i < len(tokens):
            if tokens[i].isalpha():
                cmd = tokens[i]
                i += 1
            elif cmd is None:
                break
            rel, up = cmd.islower(), cmd.upper()
            ox, oy = (x, y) if rel else (0.0, 0.0)
            if up == "Z":
                if cur:
                    cur.append((sx, sy))
                x, y = sx, sy
                last_ctrl, last_cmd = None, "Z"
                cmd = None if i >= len(tokens) or tokens[i].isalpha() else cmd
                continue
            if up == "M":
                px, py = nums(2)
                if len(cur) > 1:
                    out.append(cur)
                x, y = px + ox, py + oy
                sx, sy, cur = x, y, [(x, y)]
                cmd = "l" if rel else "L"
                last_ctrl = None
                continue
            if not cur:
                cur = [(x, y)]
            if up == "L":
                px, py = nums(2)
                x, y = px + ox, py + oy
                cur.append((x, y))
                last_ctrl = None
            elif up == "H":
                x = nums(1)[0] + ox
                cur.append((x, y))
                last_ctrl = None
            elif up == "V":
                y = nums(1)[0] + oy
                cur.append((x, y))
                last_ctrl = None
            elif up in "CS":
                if up == "C":
                    v = nums(6)
                    c1 = (v[0] + ox, v[1] + oy)
                    c2, end = (v[2] + ox, v[3] + oy), (v[4] + ox, v[5] + oy)
                else:
                    v = nums(4)
                    c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl and last_cmd in "CS" else (x, y)
                    c2, end = (v[0] + ox, v[1] + oy), (v[2] + ox, v[3] + oy)
                cur.extend(curve([(x, y), c1, c2, end]))
                x, y = end
                last_ctrl = c2
            elif up in "QT":
                if up == "Q":
                    v = nums(4)
                    c1, end = (v[0] + ox, v[1] + oy), (v[2] + ox, v[3] + oy)
                else:
                    v = nums(2)
                    c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl and last_cmd in "QT" else (x, y)
                    end = (v[0] + ox, v[1] + oy)
                cur.extend(curve([(x, y), c1, end]))
                x, y = end
                last_ctrl = c1
            elif up == "A":
                rx, ry, phi = nums(3)
                flags = []
                while len(flags) < 2:  # flags may be written without separators ("0110 10")
                    if i >= len(tokens) or tokens[i][:1] not in "01":
                        raise ValueError
                    flags.append(tokens[i][0] == "1")
                    tokens[i] = tokens[i][1:]
                    if not tokens[i]:
                        i += 1
                px, py = nums(2)
                end = (px + ox, py + oy)
                cur.extend(_arc(x, y, rx, ry, phi, flags[0], flags[1], *end))
                x, y = end
                last_ctrl = None
            last_cmd = up
    except ValueError:
        pass
    if len(cur) > 1:
        out.append(cur)
    return out


def _shape_lines(node: _Node) -> list[list[tuple[float, float]]]:
    tag, n = node.tag, (lambda name: _number(node, name))
    if tag == "line":
        return [[(n("x1"), n("y1")), (n("x2"), n("y2"))]]
    if tag == "rect":
        x, y, w, h = n("x"), n("y"), n("width"), n("height")
        return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]] if w > 0 and h > 0 else []
    if tag == "circle":
        r = n("r")
        return [_ellipse(n("cx"), n("cy"), r, r)] if r > 0 else []
    if tag == "ellipse":
        rx, ry = n("rx"), n("ry")
        return [_ellipse(n("cx"), n("cy"), rx, ry)] if rx > 0 and ry > 0 else []
    if tag in ("polyline", "polygon"):
        v = [float(t) for t in _NUMBER.findall(node.attrs.get("points", ""))]
        pts = list(zip(v[0::2], v[1::2]))
        if tag == "polygon" and pts:
            pts.append(pts[0])
        return [pts] if len(pts) > 1 else []
    return _path(node.attrs.get("d", ""))


def _describe(node: _Node) -> str:
    """The shape as the builder wrote it, shortened to one line: tag, id, class and geometry attributes."""
    geometry = {"line": ("x1", "y1", "x2", "y2"), "rect": ("x", "y", "width", "height"), "circle": ("cx", "cy", "r"),
                "ellipse": ("cx", "cy", "rx", "ry"), "polyline": ("points",), "polygon": ("points",),
                "path": ("d",)}.get(node.tag, ())
    shown = []
    for name in ("id", "class") + geometry:
        value = re.sub(r"\s+", " ", node.attrs.get(name) or "").strip()
        if value:
            shown.append(f' {name}="{value if len(value) <= 40 else value[:37] + "..."}"')
    return f"<{node.tag}{''.join(shown)}>"


# -- labels

def _label_boxes(text: _Node, state: dict, cascade: _Cascade) -> list[tuple[str, tuple, tuple]]:
    """(text, start point, estimated box) of each chunk of a <text> (a chunk starts at an absolute x), in its units."""
    events = []

    def visit(node, st):
        events.append(("pos", _number(node, "x", None), _number(node, "y", None),
                       _offset(node, "dx", st["font-size"]), _offset(node, "dy", st["font-size"]), st["text-anchor"]))
        for kid in node.kids:
            if isinstance(kid, str):
                events.append(("text", kid, st["font-size"]))
            elif kid.tag == "tspan":
                kst = cascade.style(kid, st)
                if kst["display"]:
                    visit(kid, kst)

    visit(text, state)
    # whitespace as SVG lays it out: runs collapse to one space, the ends are trimmed
    texts = [k for k, e in enumerate(events) if e[0] == "text"]
    prev_space = True
    for k in texts:
        s = re.sub(r"\s+", " ", events[k][1])
        if prev_space:
            s = s.lstrip(" ")
        if s:
            prev_space = s.endswith(" ")
        events[k] = ("text", s, events[k][2])
    for k in reversed(texts):
        s = events[k][1].rstrip(" ")
        events[k] = ("text", s, events[k][2])
        if s:
            break
    base = state["dominant-baseline"]
    up, down = LABEL_ASCENT, LABEL_DESCENT
    if base in ("middle", "central", "mathematical"):
        up = down = (LABEL_ASCENT + LABEL_DESCENT) / 2
    elif base in ("hanging", "text-before-edge", "text-top"):
        up, down = 0.0, LABEL_ASCENT + LABEL_DESCENT
    elif base in ("text-after-edge", "ideographic", "text-bottom"):
        up, down = LABEL_ASCENT + LABEL_DESCENT, 0.0
    chunks, x, y = [], 0.0, 0.0
    for event in events:
        if event[0] == "pos":
            _, ax, ay, dx, dy, anchor = event
            if ax is not None or not chunks:
                chunks.append({"x": ax if ax is not None else x, "y": y, "anchor": anchor, "end": 0.0, "runs": [],
                               "text": ""})
                x = chunks[-1]["x"]
            y = (ay if ay is not None else y) + dy
            if not chunks[-1]["runs"]:
                chunks[-1]["y"] = y
            x += dx
            continue
        _, s, size = event
        chars = [c for c in s if not unicodedata.combining(c) and unicodedata.category(c) != "Cf"]
        width = sum(size * (1.0 if unicodedata.east_asian_width(c) in "WF" else LABEL_WIDTH_FACTOR) for c in chars)
        if chars:
            chunks[-1]["runs"].append((x - chunks[-1]["x"], x - chunks[-1]["x"] + width,
                                       y - up * size, y + down * size))
        x += width
        chunks[-1]["end"] = x - chunks[-1]["x"]
        chunks[-1]["text"] += s
    boxes = []
    for chunk in chunks:
        if not chunk["runs"]:
            continue
        shift = {"middle": -chunk["end"] / 2, "end": -chunk["end"]}.get(chunk["anchor"], 0.0)
        x0 = chunk["x"] + shift
        boxes.append((chunk["text"].strip(), (chunk["x"], chunk["y"]),
                      (x0 + min(r[0] for r in chunk["runs"]), min(r[2] for r in chunk["runs"]),
                       x0 + max(r[1] for r in chunk["runs"]), max(r[3] for r in chunk["runs"]))))
    return boxes


def _stroke_meets(line: list, half: float, cap: str, box: tuple) -> bool:
    """Whether the stroke along a polyline (half width ``half``) meets an axis-aligned box.

    Joins count as round; the ends of an open line follow its cap (butt, round or square).
    """
    closed = len(line) > 2 and math.dist(line[0], line[-1]) < 1e-9
    last = len(line) - 1
    for k, p in enumerate(line):
        if closed or 0 < k < last or cap == "round":
            if math.hypot(max(box[0] - p[0], 0.0, p[0] - box[2]), max(box[1] - p[1], 0.0, p[1] - box[3])) <= half:
                return True
    corners = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
    for k in range(last):
        p, q = line[k], line[k + 1]
        length = math.dist(p, q)
        if length == 0:
            continue
        u = ((q[0] - p[0]) / length, (q[1] - p[1]) / length)
        n = (-u[1], u[0])
        a = half if cap == "square" and not closed and k == 0 else 0.0
        b = half if cap == "square" and not closed and k == last - 1 else 0.0
        p = (p[0] - u[0] * a, p[1] - u[1] * a)
        q = (q[0] + u[0] * b, q[1] + u[1] * b)
        quad = [(p[0] + n[0] * half, p[1] + n[1] * half), (q[0] + n[0] * half, q[1] + n[1] * half),
                (q[0] - n[0] * half, q[1] - n[1] * half), (p[0] - n[0] * half, p[1] - n[1] * half)]
        for axis in ((1.0, 0.0), (0.0, 1.0), u, n):  # separating axis test
            mine = [c[0] * axis[0] + c[1] * axis[1] for c in quad]
            theirs = [c[0] * axis[0] + c[1] * axis[1] for c in corners]
            if max(mine) < min(theirs) or max(theirs) < min(mine):
                break
        else:
            return True
    return False


class _ShapeGrid:
    """Which shapes' bounds (stroke included) may meet a box: a uniform grid, so big figures stay fast."""

    def __init__(self, bounds: list[tuple]):
        self.bounds, self.cells, self.wide = bounds, {}, []
        if not bounds:
            return
        span = max(max(b[2] for b in bounds) - min(b[0] for b in bounds),
                   max(b[3] for b in bounds) - min(b[1] for b in bounds))
        self.size = max(span / 64, 1e-6)
        for k, b in enumerate(bounds):
            cells = self._cells(b)
            if cells is None:
                self.wide.append(k)
            else:
                for cell in cells:
                    self.cells.setdefault(cell, []).append(k)

    def _cells(self, b: tuple):
        x0, y0, x1, y1 = (math.floor(v / self.size) for v in b)
        if (x1 - x0 + 1) * (y1 - y0 + 1) > 256:
            return None
        return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]

    def near(self, box: tuple) -> list[int]:
        if not self.bounds:
            return []
        cells = self._cells(box)
        found = set(self.wide) if cells is not None else set(range(len(self.bounds)))
        for cell in cells or ():
            found.update(self.cells.get(cell, ()))
        return [k for k in sorted(found) if not (self.bounds[k][0] > box[2] or self.bounds[k][2] < box[0]
                                                 or self.bounds[k][1] > box[3] or self.bounds[k][3] < box[1])]


def _figure_problems(root: _Node, cascade: _Cascade) -> list[tuple[tuple, str]]:
    """(key, message) for each label of one figure that touches a stroke or leaves the viewBox."""
    ids = {}
    for node in _walk(root):
        ids.setdefault(node.attrs.get("id"), node)
    start = cascade.initial()
    for node in reversed(list(_ancestors(root))):  # a page figure inherits from the HTML around it
        start = cascade.style(node, start)
    labels, shapes = [], []
    todo = [(root, start, _IDENTITY, 0)]
    while todo:
        node, parent, ctm, depth = todo.pop()
        if node.tag in _NOT_DRAWN:
            continue
        state = cascade.style(node, parent)
        if not state["display"]:
            continue
        ctm = _mul(ctm, _transform(node.attrs.get("transform", "")))
        if node.tag == "svg" and node is not root:
            ctm = _mul(ctm, (1, 0, 0, 1, _number(node, "x"), _number(node, "y")))
        if node.tag == "use":
            ref = node.attrs.get("href") or node.attrs.get("xlink:href") or ""
            target = ids.get(ref[1:]) if ref.startswith("#") else None
            if target is not None and depth < 4 and target.tag not in _NOT_DRAWN - {"symbol"}:
                ctm = _mul(ctm, (1, 0, 0, 1, _number(node, "x"), _number(node, "y")))
                items = [k for k in target.kids if isinstance(k, _Node)] if target.tag == "symbol" else [target]
                todo.extend((k, state, ctm, depth + 1) for k in reversed(items))
            continue
        if node.tag == "text":
            if state["visibility"]:
                for k, (words, at, box) in enumerate(_label_boxes(node, state, cascade)):
                    labels.append(((id(node), k), words, at, box, ctm))
            continue
        if node.tag in _SHAPES and state["visibility"] and state["stroke"] and state["stroke-width"] > 0:
            lines = [[_apply(ctm, *p) for p in line] for line in _shape_lines(node)]
            if lines:
                xs = [p[0] for line in lines for p in line]
                ys = [p[1] for line in lines for p in line]
                half = state["stroke-width"] * _scale(ctm) / 2
                shapes.append((node, lines, (min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half), half,
                               state["stroke-linecap"]))
        todo.extend((k, state, ctm, depth) for k in reversed([k for k in node.kids if isinstance(k, _Node)]))
    view = [float(v) for v in _NUMBER.findall(root.attrs.get("viewbox", ""))]
    if len(view) != 4 or view[2] <= 0 or view[3] <= 0:
        w, h = _number(root, "width", None), _number(root, "height", None)
        view = [0.0, 0.0, w, h] if w and h and "%" not in root.attrs.get("width", "") + root.attrs.get("height", "") \
            else None
    nearby = _ShapeGrid([s[2] for s in shapes])
    problems = []
    for key, words, at, box, ctm in labels:
        name = f'label "{words if len(words) <= 30 else words[:27] + "..."}" at ({at[0]:g}, {at[1]:g})'
        corners = [_apply(ctm, x, y) for x in (box[0], box[2]) for y in (box[1], box[3])]
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        if view is not None:
            sides = [side for side, out in (
                ("left", min(xs) < view[0]), ("right", max(xs) > view[0] + view[2]),
                ("top", min(ys) < view[1]), ("bottom", max(ys) > view[1] + view[3])) if out]
            if sides:
                problems.append(((key, "frame"), f"{name} leaves the viewBox at the {' and '.join(sides)}"))
        inverse = _inverse(ctm)
        if inverse is None:
            continue
        scale, touched = _scale(ctm), []
        reach = LABEL_MARGIN * scale
        for k in nearby.near((min(xs) - reach, min(ys) - reach, max(xs) + reach, max(ys) + reach)):
            shape, lines, _, half, cap = shapes[k]
            grown = (box[0] - LABEL_MARGIN, box[1] - LABEL_MARGIN, box[2] + LABEL_MARGIN, box[3] + LABEL_MARGIN)
            if any(_stroke_meets([_apply(inverse, *p) for p in line], half / scale, cap, grown) for line in lines):
                touched.append(shape)
        if touched:
            more = f" and {len(touched) - 1} more" if len(touched) > 1 else ""
            problems.append(((key, "lines"), f"{name} touches {_describe(touched[0])}{more}"))
    return problems


@functools.lru_cache(maxsize=1)
def _token_rules() -> tuple:
    return tuple(_css_rules((_SKALD / "tokens.css").read_text(encoding="utf-8")))


def check_labels(svgs: list[_Node], styles: list[str], field: str, root_font: float) -> None:
    """Refuse figures whose labels touch a stroke or leave the viewBox (see the module docstring)."""
    rules = list(_token_rules())
    for css in styles:
        _css_rules(css, rules=rules)
    rules = [(parts, spec, order, decls, cond) for order, (parts, spec, _, decls, cond) in enumerate(rules)]
    found: dict[tuple, str] = {}
    for conditional in (False, True):
        cascade = _Cascade(rules, conditional, root_font)
        for k, root in enumerate(svgs, 1):
            prefix = f"svg {k}: " if len(svgs) > 1 else ""
            for key, message in _figure_problems(root, cascade):
                found.setdefault((k,) + key, prefix + message + (" (at the @media font sizes)" if conditional else ""))
    if found:
        shown = list(found.values())
        more = f"; and {len(shown) - LABEL_PROBLEMS_SHOWN} more" if len(shown) > LABEL_PROBLEMS_SHOWN else ""
        raise InputError(f"{field}: " + "; ".join(shown[:LABEL_PROBLEMS_SHOWN]) + more
                         + f". Move each label clear (text boxes are estimated at {LABEL_WIDTH_FACTOR} em a "
                         f"character, with {LABEL_MARGIN:g} units of clearance) and build again")


def _style_texts(root: _Node) -> list[str]:
    return [_text_of(node) for node in _walk(root) if node.tag == "style"]


# --- page ----------------------------------------------------------------------------

_PAGE_HTML_ELEMENTS = {
    "div", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer", "section", "article", "aside",
    "figure", "figcaption", "ul", "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody", "tfoot", "tr", "th",
    "td", "caption", "colgroup", "col", "strong", "em", "b", "i", "u", "s", "small", "sub", "sup", "mark",
    "code", "pre", "kbd", "var", "samp", "abbr", "cite", "q", "blockquote", "br", "hr", "wbr", "details",
    "summary", "time", "a", "style", "svg", "mimir-original"}
_PAGE_VOID = {"br", "hr", "wbr", "col"}
_PAGE_GLOBAL_ATTRS = {"id", "class", "style", "title", "lang", "dir", "role", "hidden", "tabindex"}
_PAGE_ELEMENT_ATTRS = {
    "a": {"href"}, "th": {"colspan", "rowspan", "scope", "headers", "abbr"}, "td": {"colspan", "rowspan", "headers"},
    "col": {"span"}, "colgroup": {"span"}, "ol": {"start", "reversed", "type"}, "li": {"value"},
    "time": {"datetime"}, "details": {"open"}}
_PAGE_ATTR_NAME = re.compile(r"[a-z][a-z0-9_.:-]*")
# html.parser lowercases names; inline SVG gets the camelCase spelling back
_SVG_CASE = {name.lower(): name for name in _SVG_ELEMENTS | {
    "viewBox", "preserveAspectRatio", "pathLength", "gradientUnits", "gradientTransform", "spreadMethod",
    "markerWidth", "markerHeight", "markerUnits", "refX", "refY", "clipPathUnits", "maskUnits",
    "maskContentUnits", "textLength", "lengthAdjust", "startOffset"}}
_RESERVED_ID = re.compile(r"(?:mimir|sk)-")
# in a builder's <style>: a shell id or class (#mimir-controls, .mimir-js, .sk-defs, ...) or an attribute selector
# on id or class that names one; url(#sk-chalk) and the like are fine (taken out before the search)
_SHELL_NAME = re.compile(r"(?<![\w-])(?:mimir|sk)-|\[\s*(?:id|class)\b[^\]]*(?:mimir|sk)", re.I)
_STEP_NUMBER = re.compile(r"[1-9][0-9]*")


class _PageBody(HTMLParser):
    """Check a builder-written page body against the allowlist and write it out again from what was checked.

    The output is rebuilt from the parsed tokens (names, escaped text and attribute values), so the
    browser sees exactly the markup that passed. ``original(attrs, k)`` turns the k-th
    ``<mimir-original>`` marker into the shell's markup.
    """

    def __init__(self, original):
        super().__init__(convert_charrefs=True)
        self.original = original
        self.out: list[str] = []
        self.stack: list[dict] = []      # open elements: {"name", "svg", "kids", "text"}
        self.ids: set[str] = set()
        self.svg_ids: set[str] = set()
        self.markers = 0
        self.math = False
        self.steps: set[int] = set()     # every data-step number
        self.highlights: dict[int, str] = {}  # data-highlight number -> the first element with it

    # -- helpers
    def _fail(self, message: str):
        raise InputError(f"body: {message}")

    def _in_svg(self) -> bool:
        return bool(self.stack) and self.stack[-1]["svg"]

    def _attrs(self, tag: str, attrs: list, svg: bool) -> str:
        seen, parts = set(), []
        for name, value in attrs:
            if not _PAGE_ATTR_NAME.fullmatch(name):
                self._fail(f"<{tag}> has a malformed attribute name {_short(name)}")
            if name in seen:
                self._fail(f"<{tag}> has the attribute {name} twice")
            seen.add(name)
            value = "" if value is None else value
            if name.startswith("on"):
                self._fail(f"event attribute {name} on <{tag}> is not allowed")
            where = f"<{tag}> attribute {name}"
            if svg:
                if name.endswith("href") and not value.startswith("#"):
                    self._fail(f"{where} must start with # (no external links): {_short(value)}")
                _check_css_text(value, where, "body")
                name = _SVG_CASE.get(name, name)
            else:
                allowed = name in _PAGE_GLOBAL_ATTRS or name in _PAGE_ELEMENT_ATTRS.get(tag, ())
                if not (allowed or name.startswith(("aria-", "data-"))):
                    self._fail(f"attribute {name} on <{tag}> is not allowed")
                if name == "href" and not value.startswith("#"):
                    self._fail(f"{where} must start with # (no links out of the page): {_short(value)}")
                if name == "style":
                    _check_css_text(value, where, "body")
            if name == "id":
                if value in self.ids:
                    self._fail(f"id {_short(value)} is used twice")
                if _RESERVED_ID.match(value):
                    self._fail(f"id {_short(value)} is reserved for the page (mimir-..., sk-...)")
                self.ids.add(value)
                if svg:
                    self.svg_ids.add(value)
            parts.append(f' {name}="{html.escape(value)}"')
        return "".join(parts)

    def _step(self, tag: str, attrs: list) -> int:
        """Check the step markup of one element; return the step it shows at (0: always shown)."""
        values = dict(attrs)
        numbers = {}
        for name in ("data-step", "data-highlight"):
            if name in values:
                value = values[name] or ""
                if not (_STEP_NUMBER.fullmatch(value) and int(value) <= STEPS_MAX):
                    self._fail(f"<{tag}> attribute {name} must be a whole number from 1 to {STEPS_MAX}: "
                               f"{_short(value)}")
                numbers[name] = int(value)
        if "data-highlight" in numbers:
            self.highlights.setdefault(numbers["data-highlight"], tag)
        outer = max((entry.get("step", 0) for entry in self.stack), default=0)
        step = numbers.get("data-step", 0)
        if step:
            self.steps.add(step)
            if step < outer:
                self._fail(f'<{tag}> has data-step="{step}" inside a data-step="{outer}" element, '
                           f"so it could not show before step {outer}")
        return max(step, outer)

    def _open(self, tag: str, attrs: list, closed: bool) -> None:
        parent = self.stack[-1] if self.stack else None
        if parent is not None and parent["name"] in ("mimir-original", "title", "desc"):
            self._fail(f"<{parent['name']}> must not contain elements")
        svg = self._in_svg() or tag == "svg"
        if parent is not None and parent["root"]:
            parent["kids"].append(tag)
        if self._in_svg():
            if _SVG_CASE.get(tag) not in _SVG_ELEMENTS:
                self._fail(f"element <{tag}> is not allowed in an SVG")
        elif tag not in _PAGE_HTML_ELEMENTS:
            self._fail(f"element <{tag}> is not allowed")
        if tag == "mimir-original":
            self.markers += 1
            marker = {}
            for name, value in attrs:
                if name in marker:
                    self._fail(f"<mimir-original> has the attribute {name} twice")
                marker[name] = int(value) if name == "page" and value and value.isascii() and value.isdigit() \
                    else value
            self.out.append(self.original(marker, self.markers))
            if not closed:
                self.stack.append({"name": tag, "svg": False, "root": False})
            return
        name = _SVG_CASE.get(tag, tag) if svg else tag
        text = f"<{name}{self._attrs(tag, attrs, svg)}"
        step = self._step(tag, attrs)
        if svg and closed:
            self.out.append(text + "/>")
            return
        self.out.append(text + ">")
        if not svg and tag in _PAGE_VOID:
            return
        root = tag == "svg" and not self._in_svg()
        hidden = root and dict(attrs).get("aria-hidden") == "true"
        self.stack.append({"name": tag, "svg": svg, "root": root and not hidden, "kids": [], "text": {},
                           "step": step})
        if closed:
            self.handle_endtag(tag)

    # -- parser events
    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, closed=False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, closed=True)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1]["name"] != tag:
            if tag in _PAGE_VOID:
                self._fail(f"</{tag}> closes nothing (<{tag}> has no end tag)")
            open_ = f"<{self.stack[-1]['name']}>" if self.stack else "no open element"
            self._fail(f"</{tag}> does not close {open_}")
        top = self.stack.pop()
        if tag == "mimir-original":
            return
        if top.get("root"):
            for k, want in enumerate(("title", "desc")):
                if len(top["kids"]) <= k or top["kids"][k] != want:
                    self._fail(f'<svg>: child element {k + 1} must be <{want}> (or mark the svg aria-hidden="true")')
                if not top["text"].get(want, "").strip():
                    self._fail(f"<svg>: <{want}> must not be empty")
        self.out.append(f"</{_SVG_CASE.get(tag, tag) if top['svg'] else tag}>")

    def handle_data(self, data):
        parent = self.stack[-1] if self.stack else None
        if parent is not None and parent["name"] == "style":
            if "<" in data or "&" in data:
                self._fail("<style> must not contain < or &")
            _check_css_text(data, "<style>", "body")
            if _SHELL_NAME.search(re.sub(r"url\([^)]*\)", "", data)):
                self._fail("<style> must not name the page's own mimir-... or sk-... ids and classes "
                           "(the step controls, the simulator and the mascot belong to the shell)")
            self.out.append(data)
            return
        if parent is not None and parent["name"] == "mimir-original" and data.strip():
            self._fail("<mimir-original> must be empty")
        if parent is not None and parent["name"] in ("title", "desc") and len(self.stack) > 1 \
                and self.stack[-2].get("root"):
            self.stack[-2]["text"][parent["name"]] = self.stack[-2]["text"].get(parent["name"], "") + data
        if not self._in_svg() and ("\\(" in data or "\\[" in data):
            self.math = True
        self.out.append(html.escape(data, quote=False))

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        self._fail("declarations (<!...>) are not allowed")

    def unknown_decl(self, data):
        self._fail("declarations and CDATA sections (<![...]>) are not allowed")

    def handle_pi(self, data):
        self._fail("processing instructions (<?...>) are not allowed")

    def finish(self) -> str:
        if "<" in self.rawdata:  # close() would drop it silently (an unclosed quote, tag or comment)
            self._fail(f"the body ends inside an unfinished tag, comment or declaration: {_short(self.rawdata)}")
        self.close()
        if self.stack:
            self._fail(f"<{self.stack[-1]['name']}> is not closed")
        total = max(self.steps, default=0)
        missing = sorted(set(range(1, total + 1)) - self.steps)
        if missing:
            self._fail(f"data-step must number the steps 1 to {total} without gaps; "
                       f'no element has data-step="{missing[0]}"')
        for number, tag in sorted(self.highlights.items()):
            if number > total:
                self._fail(f'<{tag}> has data-highlight="{number}", but '
                           + (f"the steps run 1 to {total}" if total else "the page has no data-step markup"))
        return "".join(self.out)


def check_page_body(body: str, original, states: list[str] = ()) -> tuple[str, bool, bool]:
    """Check a page body (see the docstring); return it rebuilt, whether it holds math and whether it has steps.

    ``states`` are a machine's states: each needs an element ``id="state-<i>"`` inside an inline SVG.
    """
    parser = _PageBody(original)
    parser.feed(body)
    out = parser.finish()
    for i, name in enumerate(states, 1):
        if f"state-{i}" not in parser.svg_ids:
            raise InputError(f'body: no element with id "state-{i}" for machine.states[{i}] {_short(name)} '
                             "inside an inline <svg>")
    return out, parser.math, bool(parser.steps)


def _simulator_html(machine: dict, example: str) -> str:
    """The shell's simulator controls and the machine as a table, placed after the builder's body."""
    return (
        '\n<section class="sim" id="mimir-sim">\n<div id="mimir-sim-controls" hidden>\n'
        "<h2>Feed an input</h2>\n"
        f'<p><label for="mimir-sim-input">Input</label> <input type="text" id="mimir-sim-input" '
        f'value="{html.escape(example)}" autocomplete="off" spellcheck="false" '
        'aria-describedby="mimir-sim-hint"></p>\n'
        f'<p class="sim-hint" id="mimir-sim-hint">One symbol per character; spaces are ignored. '
        f"At most {MACHINE_MAX_SYMBOLS} symbols.</p>\n"
        '<p class="sim-buttons"><button type="button" id="mimir-sim-start">Start</button>'
        '<button type="button" id="mimir-sim-next">Next symbol</button>'
        '<button type="button" id="mimir-sim-back">Back</button></p>\n'
        '<p class="sim-hint">Enter in the input field starts; on the buttons, the right arrow reads the next '
        "symbol and the left arrow goes back. The current states are marked in the diagram.</p>\n"
        '<p id="mimir-sim-status" role="status" aria-live="polite"></p>\n'
        '<h3>Steps so far</h3>\n<ol id="mimir-sim-history"></ol>\n</div>\n'
        f'<details class="sim-machine"><summary>The machine</summary>\n{_machine_html(machine)}\n</details>\n'
        "</section>")


def _mascot_html() -> str:
    """The shell's mascot, hidden until the step script shows him (so never with JavaScript off)."""
    art = _MASCOT_SVG.read_text(encoding="utf-8")
    if re.search(r"<script|<style|<!--|\son\w+\s*=|\sid\s*=|href|url\(", art, re.I):
        raise RuntimeError("the mascot art must be plain decorative SVG (no script, style, ids or links)")
    return f'<div id="mimir-mascot" class="mimir-mascot" aria-hidden="true" hidden>\n{art}</div>\n'


def render_page(title: str, body: str, math: bool, steps: bool = False,
                machine: dict | None = None, example: str = "", motion: str | None = None) -> str:
    """The page file around a checked body. ``motion`` is ``workspace.read_motion``'s level; None builds as none."""
    katex = _katex() if math else None
    scripts = [katex["KATEX_JS"], katex["AUTO_RENDER_JS"],
               _check_raw(_PAGE_MATH_JS.read_text(encoding="utf-8"), "</script", "page math")] if katex else []
    mascot = ""
    if steps:  # the mascot's moods follow the steps; the step script shows him
        scripts.append(_check_raw(_PAGE_STEPS_JS.read_text(encoding="utf-8"), "</script", "page steps"))
        mascot = _mascot_html()
    data = ""
    if machine is not None:
        body += _simulator_html(machine, example)
        data = f'<script type="application/json" id="mimir-machine">{_json_script(_machine_data(machine))}</script>\n'
        scripts += [_check_raw(path.read_text(encoding="utf-8"), "</script", "simulator")
                    for path in (_MACHINE_JS, _PAGE_SIM_JS)]
    template = _PAGE_TEMPLATE.read_text(encoding="utf-8")
    return _fill(template, {
        "CSP": _csp([_csp_hash(s) for s in scripts]),
        "MOTION": motion or "none",
        "TITLE": html.escape(title),
        "KATEX_STYLE": f"<style>{katex['KATEX_CSS']}</style>\n" if katex else "",
        "TOKENS": _check_raw(skald_tokens(), "</style", "Skald tokens"),
        "BODY": body,
        "MASCOT": mascot,
        "SCRIPTS": data + "".join(f"<script>{s}</script>\n" for s in scripts)})


def cmd_page(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "title", "body", "machine", "example"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    if "title" not in data:
        raise InputError("title is required")
    title = verify._text(data["title"], "title", TITLE_MAX_CHARS)
    machine = _machine(data["machine"]) if "machine" in data else None
    if machine is None and "example" in data:
        raise InputError("example is only for a page with a machine")
    example = _example(data)
    body = data.get("body")
    _markup_field(body, "body", "the page body as an HTML string", PAGE_BODY_MAX_BYTES)
    course_dir = verify._course_dir(term, course)
    index = course_dir / "INDEX.md"
    rows = {p: r for p, r in ingest.registry(index).items() if verify._inside(course_dir, p)}
    body_html, math, steps = check_page_body(
        body, lambda marker, k: _original(marker, f"body.original[{k}]", rows, course_dir, index),
        machine["states"] if machine else ())
    tree = _BodyTree()
    tree.feed(body_html)
    tree.close()
    figures = [n for n in _walk(tree.root) if n.tag == "svg" and not any(a.tag == "svg" for a in _ancestors(n))]
    check_labels(figures, _style_texts(tree.root), "body", _PAGE_FONT_PX)
    page = render_page(title, body_html, math, steps, machine, example,
                       workspace.read_motion(ingest._workspace_root()))
    return _write_out(course_dir, name, "html", page.encode("utf-8"))


# --- machine ---------------------------------------------------------------------------

def _symbol(value, where: str, epsilon: bool) -> str:
    """One input or stack symbol: a single character that is not a space; "" is ε when allowed."""
    if isinstance(value, str) and value == "" and epsilon:
        return value
    if (not isinstance(value, str) or len(value) != 1 or value.isspace() or _has_control(value)
            or ord(value) > 0xFFFF):
        also = ' or "" for ε' if epsilon else ""
        raise InputError(f"{where} must be one character that is not a space and not outside the Basic "
                         f"Multilingual Plane (e.g. not an emoji){also}: {_short(value)}")
    return value


def _state(value, where: str, states: list[str]) -> str:
    name = verify._text(value, where, STATE_NAME_MAX_CHARS)
    if name not in states:
        raise InputError(f"{where}: {_short(name)} is not one of machine.states")
    return name


def _machine(value) -> dict:
    """Check a machine and return it normalized (see the docstring)."""
    if not isinstance(value, dict):
        raise InputError("machine must be an object")
    verify._keys(value, {"kind", "states", "start", "accept", "transitions", "stack_start"}, "machine")
    kind = value.get("kind")
    if kind not in _MACHINE_KINDS:
        raise InputError(f"machine.kind must be one of {', '.join(_MACHINE_KINDS)}: {_short(kind)}")
    pda = kind == "pda"
    raw_states = value.get("states")
    if not isinstance(raw_states, list) or not raw_states:
        raise InputError("machine.states is required (a non-empty list of state names)")
    if len(raw_states) > MACHINE_MAX_STATES:
        raise InputError(f"machine.states has {len(raw_states)} states; at most {MACHINE_MAX_STATES}")
    states: list[str] = []
    for i, item in enumerate(raw_states, 1):
        name = verify._text(item, f"machine.states[{i}]", STATE_NAME_MAX_CHARS)
        if name in states:
            raise InputError(f"machine.states[{i}]: {_short(name)} is listed twice")
        states.append(name)
    if "start" not in value:
        raise InputError("machine.start is required")
    start = _state(value["start"], "machine.start", states)
    raw_accept = value.get("accept", [])
    if not isinstance(raw_accept, list):
        raise InputError("machine.accept must be a list of state names")
    accept: list[str] = []
    for i, item in enumerate(raw_accept, 1):
        name = _state(item, f"machine.accept[{i}]", states)
        if name in accept:
            raise InputError(f"machine.accept[{i}]: {_short(name)} is listed twice")
        accept.append(name)
    if pda:
        if "stack_start" not in value:
            raise InputError("machine.stack_start is required for a pda (one stack symbol)")
        stack_start = _symbol(value["stack_start"], "machine.stack_start", epsilon=False)
    elif "stack_start" in value:
        raise InputError(f"machine.stack_start is only for a pda, not a {kind}")
    raw_moves = value.get("transitions")
    if not isinstance(raw_moves, list):
        raise InputError("machine.transitions is required (a list of moves)")
    if len(raw_moves) > MACHINE_MAX_TRANSITIONS:
        raise InputError(f"machine.transitions has {len(raw_moves)} moves; at most {MACHINE_MAX_TRANSITIONS}")
    moves, seen = [], set()
    for i, item in enumerate(raw_moves, 1):
        where = f"machine.transitions[{i}]"
        if not isinstance(item, dict):
            raise InputError(f"{where} must be an object {{from, read, to}}")
        for extra in ("pop", "push"):
            if extra in item and not pda:
                raise InputError(f"{where}.{extra} is only for a pda, not a {kind}")
        verify._keys(item, {"from", "read", "to", "pop", "push"}, where)
        for field in ("from", "read", "to"):
            if field not in item:
                raise InputError(f"{where}.{field} is required")
        move = {"from": _state(item["from"], f"{where}.from", states),
                "read": _symbol(item["read"], f"{where}.read", epsilon=kind in ("nfa", "pda")),
                "to": _state(item["to"], f"{where}.to", states)}
        if pda:
            move["pop"] = _symbol(item.get("pop", ""), f"{where}.pop", epsilon=True)
            push = item.get("push", "")
            if not isinstance(push, str) or len(push) > MACHINE_MAX_STACK:
                raise InputError(f"{where}.push must be a string of at most {MACHINE_MAX_STACK} stack symbols")
            for c in push:
                _symbol(c, f"{where}.push", epsilon=False)
            move["push"] = push
        if kind in ("dfa", "tree"):
            if (move["from"], move["read"]) in seen:
                raise InputError(f"{where}: a second move from {_short(move['from'])} on "
                                 f"{_short(move['read'])} (a {kind} has at most one)")
            seen.add((move["from"], move["read"]))
        moves.append(move)
    if kind == "tree":
        parents = {name: [m["from"] for m in moves if m["to"] == name] for name in states}
        if parents[start]:
            raise InputError(f"machine.transitions: the root {_short(start)} of a tree has an incoming edge")
        for name in states:
            if name != start and len(parents[name]) != 1:
                raise InputError(f"machine.transitions: tree node {_short(name)} has {len(parents[name])} "
                                 "incoming edges; every node but the root has exactly one")
        reached, queue = {start}, [start]
        while queue:
            here = queue.pop()
            for m in moves:
                if m["from"] == here and m["to"] not in reached:
                    reached.add(m["to"])
                    queue.append(m["to"])
        lost = [name for name in states if name not in reached]
        if lost:
            raise InputError(f"machine.transitions: tree node {_short(lost[0])} cannot be reached from the root")
    out = {"kind": kind, "states": states, "start": start, "accept": accept, "transitions": moves}
    if pda:
        out["stack_start"] = stack_start
    return out


def _machine_html(machine: dict) -> str:
    def cell(text: str) -> str:
        return f"<td>{html.escape(text) if text else 'ε'}</td>"

    pda = machine["kind"] == "pda"
    accept = ", ".join(machine["accept"]) or "none"
    facts = (f"Kind: {_KIND_TEXT[machine['kind']]}. Start state: {machine['start']}. "
             f"Accepting states: {accept}.")
    if pda:
        facts += f" Stack start symbol: {machine['stack_start']}; the first pushed symbol becomes the top."
    head = "<th scope=\"col\">From</th><th scope=\"col\">Read</th>"
    if pda:
        head += "<th scope=\"col\">Pop</th><th scope=\"col\">Push</th>"
    head += "<th scope=\"col\">To</th>"
    body = []
    for m in machine["transitions"]:
        cells = cell(m["from"]) + cell(m["read"])
        if pda:
            cells += cell(m["pop"]) + cell(m["push"])
        body.append(f"<tr>{cells}{cell(m['to'])}</tr>")
    if not body:
        body.append(f"<tr><td colspan=\"{5 if pda else 3}\">No moves.</td></tr>")
    return (f"<p>{html.escape(facts)}</p>\n<div class=\"table-wrap\"><table>\n<thead><tr>{head}</tr></thead>\n"
            "<tbody>\n" + "\n".join(body) + "\n</tbody>\n</table></div>")


def _example(data: dict) -> str:
    """The optional input the simulator starts with."""
    if data.get("example") is None:
        return ""
    example = verify._text(data["example"], "example", EXAMPLE_MAX_CHARS, required=False)
    symbols = sum(1 for c in example if not c.isspace())
    if symbols > MACHINE_MAX_SYMBOLS:
        raise InputError(f"example has {symbols} symbols; at most {MACHINE_MAX_SYMBOLS}")
    return example


def _machine_data(machine: dict) -> dict:
    """The simulator's JSON data: the machine and its limits."""
    return {**machine, "max_configs": MACHINE_MAX_CONFIGS, "max_stack": MACHINE_MAX_STACK,
            "max_symbols": MACHINE_MAX_SYMBOLS}


# --- open --------------------------------------------------------------------------

def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _launch(argv: list[str], ignore_exit: bool) -> bool:
    env = {k: v for k, v in os.environ.items() if k != "BROWSER"}
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=env, start_new_session=True)
    except OSError:
        return False
    try:
        code = proc.wait(timeout=OPEN_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        return True  # still running: the browser is starting in the foreground
    return ignore_exit or code == 0


def _platform() -> str:
    """Return macos, windows, wsl, linux or other."""
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "wsl" if _is_wsl() else "linux"
    return "other"


def open_in_browser(path: Path) -> bool:
    """Try the platform's own opener (never a console browser); True when it reports success."""
    platform = _platform()
    if platform == "macos":
        return _launch(["open", str(path)], ignore_exit=False)
    if platform == "windows":
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except (OSError, AttributeError):
            return False
        return True
    if platform == "wsl":
        if shutil.which("wslview"):
            return _launch(["wslview", str(path)], ignore_exit=False)
        explorer, wslpath = shutil.which("explorer.exe"), shutil.which("wslpath")
        if not explorer or not wslpath:
            return False
        try:
            win = subprocess.run([wslpath, "-w", str(path)], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, timeout=OPEN_WAIT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if win.returncode != 0 or not win.stdout.strip():
            return False
        return _launch([explorer, win.stdout.strip()], ignore_exit=True)
    if platform == "linux" and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        opener = shutil.which("xdg-open")
        return bool(opener) and _launch([opener, str(path)], ignore_exit=False)
    return False


def cmd_open(data: dict) -> dict:
    _check_keys(data, {"term", "course", "file"})
    term, course = parse_term(data), parse_segment(data, "course")
    value = data.get("file")
    if not isinstance(value, str) or not value:
        raise InputError("file is required (<name>.html or <name>.svg)")
    if _has_control(value) or not _FILE.fullmatch(value) or len(value.rsplit(".", 1)[0]) > NAME_MAX_CHARS:
        raise InputError(f"file must be <name>.html or <name>.svg with a valid name: {_short(value)}")
    course_dir = verify._course_dir(term, course)
    out = _out_dir(course_dir, create=False)
    path = out / value
    if path.is_symlink() or not path.is_file():
        raise InputError(f"file: {path} is not an existing file in {out}")
    opened = open_in_browser(path)
    line = f"Opened `{path}` in your browser." if opened else f"Open `{path}` in your browser."
    return {"path": str(path), "opened": opened, "line": line}


COMMANDS = {
    "page": (cmd_page, "build an offline Skald page from a checked page body in <course>/.state/out/"),
    "svg": (cmd_svg, "check an SVG document and write it to <course>/.state/out/"),
    "open": (cmd_open, "open a built file in the default browser"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("visual.py",
                             ("Mimir visual builder. Subcommands: page, svg, open. Reads one JSON object on "
                              "stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
