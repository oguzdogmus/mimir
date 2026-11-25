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
    other than ``url(#...)``, ``@import``, ``image-set(`` or a backslash;
    ``<`` or ``&`` in ``<style>`` text; an outermost inline ``svg`` whose
    first two children are not a non-empty ``title`` then ``desc``, unless it
    has ``aria-hidden="true"``; elements inside an SVG ``title`` or ``desc``;
    a repeated id or one starting with ``mimir-`` or ``sk-``; a malformed or
    repeated attribute name; an end tag that does not close the open
    element, or an element left open; declarations, CDATA sections and
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
    animation. Without step markup the page carries no step script.
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
    TRACE_MAX_STACK symbols); other kinds refuse those fields. dfa and tree
    allow at most one move per (state, symbol). A tree's root has no incoming
    edge, every other node exactly one, and every node is reachable from the
    root. Limits: TRACE_MAX_STATES (60) states with names of at most
    STATE_NAME_MAX_CHARS (20), TRACE_MAX_TRANSITIONS (400) moves.
    ``example`` (optional) is the input the simulator starts with: at most
    TRACE_MAX_SYMBOLS (64) symbols (spaces ignored) and EXAMPLE_MAX_CHARS
    (4000) characters. The body needs an element ``id="state-<i>"`` inside an inline SVG for
    each state i (counting from 1). After the body the shell adds the
    simulator controls (``#mimir-sim``) and the machine as a table, the
    machine as JSON data and the simulator scripts (allowed by hash); current
    states get ``data-highlight-on`` (the teaching highlight), and the arrow
    keys act only while focus is in the simulator. The page simulates sets of
    configurations with ε-closure, at most TRACE_MAX_CONFIGS (256) at once
    and a PDA stack of at most TRACE_MAX_STACK, saying "Search limit reached"
    when it cuts; it accepts by final state after the whole input. A live
    region and an ordered history say each step in words, ending Accepted,
    Rejected or Stuck. The body's ``<style>`` is
    not scoped, since the builder writes the whole page. ``example`` without
    ``machine`` is refused; a page without ``machine`` has no simulator.

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
    other than ``url(#...)``; ``@import`` or ``image-set(``; a backslash in an
    attribute value or ``style`` text (CSS escapes would hide the checks).
    The document is written as given, with one ``<style>`` added as the root's
    last child: the Skald tokens, fonts inlined, in a CDATA section.

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
import hashlib
import html
import json
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
TRACE_MAX_STATES = 60
TRACE_MAX_TRANSITIONS = 400
STATE_NAME_MAX_CHARS = 20
TRACE_MAX_SYMBOLS = 64         # symbols in one fed input
EXAMPLE_MAX_CHARS = 4000       # the example input, spaces included
TRACE_MAX_CONFIGS = 256        # configurations followed at once (NFA/PDA)
TRACE_MAX_STACK = 64           # PDA stack depth

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_KATEX = _ASSETS / "vendor" / "katex"
_PAGE_TEMPLATE = _ASSETS / "page" / "page.html"
_PAGE_MATH_JS = _ASSETS / "page" / "math.js"
_MACHINE_JS = _ASSETS / "page" / "machine.js"       # the simulator engine (MimirSim)
_PAGE_SIM_JS = _ASSETS / "page" / "simulator.js"
_PAGE_STEPS_JS = _ASSETS / "page" / "steps.js"
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
_XML_DECL = re.compile(r"\ufeff?<\?xml\s[^>]*\?>")
_ENCODING = re.compile(r"""\bencoding\s*=\s*["']([^"']*)["']""")
_SVG_ALLOWED_CONTROL = {"\t", "\n", "\r"}
_XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", _XLINK_NS)
_TRACE_KINDS = ("dfa", "nfa", "pda", "tree")
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
    if "image-set(" in low:
        raise InputError(f"{field}: {where} contains image-set(")
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


def cmd_svg(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "svg"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    svg = data.get("svg")
    if not isinstance(svg, str) or not svg.strip():
        raise InputError("svg is required (the SVG document as a string)")
    if any(c not in _SVG_ALLOWED_CONTROL and unicodedata.category(c) in ("Cc", "Cs") for c in svg):
        raise InputError("svg contains control characters or lone surrogates")
    raw = svg.encode("utf-8")
    if len(raw) > SVG_MAX_BYTES:
        raise InputError(f"svg is {len(raw)} bytes; at most {SVG_MAX_BYTES}")
    course_dir = verify._course_dir(term, course)
    check_svg(raw)
    return _write_out(course_dir, name, "svg", _svg_with_tokens(svg).encode("utf-8"))


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
        f"At most {TRACE_MAX_SYMBOLS} symbols.</p>\n"
        '<p class="sim-buttons"><button type="button" id="mimir-sim-start">Start</button>'
        '<button type="button" id="mimir-sim-next">Next symbol</button>'
        '<button type="button" id="mimir-sim-back">Back</button></p>\n'
        '<p class="sim-hint">Enter in the input field starts; on the buttons, the right arrow reads the next '
        "symbol and the left arrow goes back. The current states are marked in the diagram.</p>\n"
        '<p id="mimir-sim-status" role="status" aria-live="polite"></p>\n'
        '<h3>Steps so far</h3>\n<ol id="mimir-sim-history"></ol>\n</div>\n'
        f'<details class="sim-machine"><summary>The machine</summary>\n{_machine_html(machine)}\n</details>\n'
        "</section>")


def render_free_page(title: str, body: str, math: bool, steps: bool = False,
                     machine: dict | None = None, example: str = "", motion: str = "none") -> str:
    katex = _katex() if math else None
    scripts = [katex["KATEX_JS"], katex["AUTO_RENDER_JS"],
               _check_raw(_PAGE_MATH_JS.read_text(encoding="utf-8"), "</script", "page math")] if katex else []
    if steps:
        scripts.append(_check_raw(_PAGE_STEPS_JS.read_text(encoding="utf-8"), "</script", "page steps"))
    data = ""
    if machine is not None:
        body += _simulator_html(machine, example)
        data = f'<script type="application/json" id="mimir-machine">{_json_script(_machine_data(machine))}</script>\n'
        scripts += [_check_raw(path.read_text(encoding="utf-8"), "</script", "simulator")
                    for path in (_MACHINE_JS, _PAGE_SIM_JS)]
    template = _PAGE_TEMPLATE.read_text(encoding="utf-8")
    return _fill(template, {
        "CSP": _csp([_csp_hash(s) for s in scripts]),
        "MOTION": motion if motion in workspace.MOTION_LEVELS else "none",
        "TITLE": html.escape(title),
        "KATEX_STYLE": f"<style>{katex['KATEX_CSS']}</style>\n" if katex else "",
        "TOKENS": _check_raw(skald_tokens(), "</style", "Skald tokens"),
        "BODY": body,
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
    if not isinstance(body, str) or not body.strip():
        raise InputError("body is required (the page body as an HTML string)")
    if any(c not in _SVG_ALLOWED_CONTROL and unicodedata.category(c) in ("Cc", "Cs") for c in body):
        raise InputError("body contains control characters or lone surrogates")
    size = len(body.encode("utf-8"))
    if size > PAGE_BODY_MAX_BYTES:
        raise InputError(f"body is {size} bytes; at most {PAGE_BODY_MAX_BYTES}")
    course_dir = verify._course_dir(term, course)
    index = course_dir / "INDEX.md"
    rows = {p: r for p, r in ingest.registry(index).items() if verify._inside(course_dir, p)}
    body_html, math, steps = check_page_body(
        body, lambda marker, k: _original(marker, f"body.original[{k}]", rows, course_dir, index),
        machine["states"] if machine else ())
    motion = workspace.read_motion(course_dir.parents[1]) or "none"  # course_dir is <root>/<term>/<course>
    page = render_free_page(title, body_html, math, steps, machine, example, motion)
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
    if kind not in _TRACE_KINDS:
        raise InputError(f"machine.kind must be one of {', '.join(_TRACE_KINDS)}: {_short(kind)}")
    pda = kind == "pda"
    raw_states = value.get("states")
    if not isinstance(raw_states, list) or not raw_states:
        raise InputError("machine.states is required (a non-empty list of state names)")
    if len(raw_states) > TRACE_MAX_STATES:
        raise InputError(f"machine.states has {len(raw_states)} states; at most {TRACE_MAX_STATES}")
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
    if len(raw_moves) > TRACE_MAX_TRANSITIONS:
        raise InputError(f"machine.transitions has {len(raw_moves)} moves; at most {TRACE_MAX_TRANSITIONS}")
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
            if not isinstance(push, str) or len(push) > TRACE_MAX_STACK:
                raise InputError(f"{where}.push must be a string of at most {TRACE_MAX_STACK} stack symbols")
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
    if symbols > TRACE_MAX_SYMBOLS:
        raise InputError(f"example has {symbols} symbols; at most {TRACE_MAX_SYMBOLS}")
    return example


def _machine_data(machine: dict) -> dict:
    """The simulator's JSON data: the machine and its limits."""
    return {**machine, "max_configs": TRACE_MAX_CONFIGS, "max_stack": TRACE_MAX_STACK,
            "max_symbols": TRACE_MAX_SYMBOLS}


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
