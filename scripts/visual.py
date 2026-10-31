#!/usr/bin/env python3
"""Mimir visual builder: math sheets, safe SVG files, interactive pages and the browser open.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``verify.py`` (same folder). Run as::

    python3 visual.py <sheet|svg|steps|trace|delay|open>  < input.json

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
name the field, e.g. ``blocks[3].math`` (blocks are numbered from 1).

sheet -- an offline HTML math sheet from ``assets/math-sheet.html``.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "name": "pumping-lemma",
          "title": "Pumping lemma, worked answer", "blocks": [
            {"heading": "Setup"},
            {"text": "Let \\(p\\) be the pumping length."},
            {"math": "\\frac{a}{b} = \\sum_{i=0}^{n} x_i"},
            {"original": {"path": "past-papers/q.jpg", "page": 1}}]}
    out: {"course_dir": "/home/u/learning/2026-Fall/CS201 Theory",
          "path": "/home/u/learning/2026-Fall/CS201 Theory/.state/out/pumping-lemma.html",
          "line": "Built /home/u/learning/2026-Fall/CS201 Theory/.state/out/pumping-lemma.html."}
    Each block is an object with exactly one of:
    * ``heading``: a section heading (``<h2>``), at most HEADING_MAX_CHARS (120).
    * ``text``: a paragraph; inline math only as ``\\(...\\)``.
    * ``math``: one display formula, LaTeX without delimiters, in a
      keyboard-focusable (``tabindex="0"``) block so a wide formula can scroll.
    * ``original``: ``{path, page}``, the original of an ``ocr`` transcription.
      ``path`` is a registry path of this course's INDEX.md that resolves
      inside the course folder, ``page`` an integer >= 1 within the row's
      pages when known. A png, jpg, jpeg, gif or webp file of at most
      ORIGINAL_EMBED_MAX_BYTES (10 MiB) is embedded as an image with alt text
      "Original: <path>, p.<page>"; anything else becomes a ``file://`` link
      with that text (the whole page stands in for the crop).
    ``\\[`` and ``\\]`` are refused in ``title``, ``heading`` and ``text``
    (auto-render scans the whole page body; display math is a ``math`` block).
    ``title`` (required) is at most TITLE_MAX_CHARS (120); ``text`` and
    ``math`` at most BLOCK_MAX_CHARS (4000); at most SHEET_MAX_BLOCKS (200)
    blocks. Strings have no control characters (one line each). The template
    is filled in one pass, so inserted values are never re-scanned, and every
    string is HTML-escaped. KaTeX (``assets/vendor/katex``) is inlined: its
    JS, auto-render and CSS, with the woff2 fonts as data URIs and other font
    formats dropped. KaTeX runs with ``output: "htmlAndMathml"``,
    ``throwOnError: false``, ``trust: false`` and the delimiters ``\\(\\)``
    and ``\\[\\]`` only. A Content-Security-Policy meta allows only ``data:``
    fonts and images, inline styles and the page's own scripts by sha256
    hash: nothing loads from the network.

svg -- check one SVG document and write it byte-for-byte.
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

steps -- a step-reveal worked answer from ``assets/interactive/step-reveal.html``.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "name": "q2-steps",
          "title": "Q2, worked", "blocks": [{"text": "[practice, not from a real paper]"},
          {"text": "Show that L is not regular."}],
          "steps": [[{"text": "Assume \\(L\\) is regular."}], [{"math": "s = a^p b^p"}]]}
    out: as ``sheet``.
    ``blocks`` are sheet blocks, always shown (label, question, ``original``).
    ``steps``: 1 to STEPS_MAX (50) steps, each 1 to STEP_MAX_BLOCKS (20)
    ``text`` or ``math`` blocks with the sheet's rules. Each step is an
    ``<li class="step">`` the page script hides at load (without JavaScript
    every step stays visible); a button reveals the next one (Enter, Space),
    ArrowRight/ArrowDown reveal, ArrowLeft/ArrowUp hide the last, and a
    polite live region says "Step k of n". KaTeX and the CSP are as in ``sheet``.

trace -- a structure step-through from ``assets/interactive/step-through.html``.
    in : {"term": ..., "course": ..., "name": "dfa-even-zeros", "title": "...",
          "example": "0101", "svg": "<svg ...>...</svg>",
          "machine": {"kind": "dfa", "states": ["q0", "q1"], "start": "q0",
            "accept": ["q0"], "transitions": [{"from": "q0", "read": "0", "to": "q1"}, ...]}}
    out: as ``sheet``.
    ``kind`` is dfa, nfa, pda or tree. Symbols (``read``, ``pop``, the
    characters of ``push``, ``stack_start``) are single characters that are
    not spaces, from the Basic Multilingual Plane; ``read`` "" is ε, allowed in nfa and pda only. A pda needs
    ``stack_start``; its moves take ``pop`` ("" or one symbol) and ``push``
    (the new top first; at most TRACE_MAX_STACK symbols); other kinds refuse
    those fields. dfa and tree allow at most one move per (state, symbol). A
    tree's root has no incoming edge, every other node exactly one, and every
    node is reachable from the root. Limits: TRACE_MAX_STATES (60) states
    with names of at most STATE_NAME_MAX_CHARS (20), TRACE_MAX_TRANSITIONS
    (400) moves, ``example`` at most TRACE_MAX_SYMBOLS (64) symbols (spaces
    ignored). ``svg`` passes the ``svg`` checks below, has an element with
    ``id="state-<i>"`` for each state i (counting from 1), no repeated id and
    no id starting with ``mimir-``; it is re-serialized (no comments, CDATA or
    declarations) before it is inlined, and every selector in its ``<style>``
    is prefixed with ``#mimir-diagram`` (only top-level ``@media`` at-rules
    are allowed) so it cannot restyle the page. The machine goes in as JSON data
    (``<script type="application/json">``, with ``<``, ``>`` and ``&``
    escaped); the page simulates sets of configurations with ε-closure, at
    most TRACE_MAX_CONFIGS (256) at once and a PDA stack of at most
    TRACE_MAX_STACK, saying "Search limit reached" when it cuts; it accepts by
    final state after the whole input. Current states get the class
    ``mimir-current`` (a thick outline); a live region and an ordered history
    say each step in words, ending Accepted, Rejected or Stuck.

delay -- the cost-of-delay slider page and chart, from ``assets/interactive/slider.html``.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "name": "cost-of-delay",
          "now": "2026-10-17T09:00:00+03:00"}
    out: {"course_dir": "...", "html": ".../cost-of-delay.html", "svg":
          ".../cost-of-delay.svg", "delay_line": "Start today: 19 days × ...",
          "line": "Built .../cost-of-delay.html and .../cost-of-delay.svg."}
    The route and the exam come from ``session.py start`` for that course
    and the rows from ``plan.py``: ``delay_line`` is the same line as
    ``start``'s in a Standard session (``start`` gives none when Urgent; this
    still computes it, so ``mimir-plan`` works in either class). No
    arithmetic happens in the page. The page: a native range
    input "Start day" over every row, an ``<output>`` with that row's line,
    the confidence line and a table of every row. The SVG chart is generated
    here (solid bars to the low end, outlined bars to the high end, day labels,
    a ``<desc>`` saying the trend in words) and passes the ``svg`` checks. An
    exam that is null or a route with no topics left exits 2.

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
from fractions import Fraction
from pathlib import Path

import ingest
import plan
import session
import verify
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

NAME_MAX_CHARS = 60
TITLE_MAX_CHARS = 120
HEADING_MAX_CHARS = 120
BLOCK_MAX_CHARS = 4000
SHEET_MAX_BLOCKS = 200
ORIGINAL_EMBED_MAX_BYTES = 10 * 1024 * 1024
SVG_MAX_BYTES = 1024 * 1024
OPEN_WAIT_SECONDS = 5
STEPS_MAX = 50                 # steps in a step-reveal page
STEP_MAX_BLOCKS = 20           # blocks in one step
TRACE_MAX_STATES = 60
TRACE_MAX_TRANSITIONS = 400
STATE_NAME_MAX_CHARS = 20
TRACE_MAX_SYMBOLS = 64         # symbols in one fed input
TRACE_MAX_CONFIGS = 256        # configurations followed at once (NFA/PDA)
TRACE_MAX_STACK = 64           # PDA stack depth

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_TEMPLATE = _ASSETS / "math-sheet.html"
_STEPS_TEMPLATE = _ASSETS / "interactive" / "step-reveal.html"
_TRACE_TEMPLATE = _ASSETS / "interactive" / "step-through.html"
_SLIDER_TEMPLATE = _ASSETS / "interactive" / "slider.html"
_KATEX = _ASSETS / "vendor" / "katex"

_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_FILE = re.compile(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.(html|svg)")
_SLOT = re.compile(r"\{\{([A-Z_]+)\}\}")
_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
_BLOCK_KINDS = ("heading", "text", "math", "original")
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
_STEP_KINDS = ("text", "math")
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
            raise InputError(f"no output folder at {out}; build a sheet or an SVG first")
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


# --- sheet -------------------------------------------------------------------------

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


def _inline_only(value, where: str, limit: int) -> str:
    """A title, heading or text string: auto-render scans all of <main>, so no display delimiters."""
    text = verify._text(value, where, limit)
    if "\\[" in text or "\\]" in text:
        raise InputError(f"{where}: inline math only as \\(...\\); display math goes in a math block")
    return text


def _sheet_block(block, where: str, rows: dict, course_dir: Path, index: Path,
                 kinds: tuple[str, ...] = _BLOCK_KINDS) -> str:
    if not isinstance(block, dict) or len(block) != 1 or next(iter(block)) not in kinds:
        if isinstance(block, dict) and len(block) == 1:
            raise InputError(f"{where}: unknown field {_short(next(iter(block)))}; a block is one of "
                             f"{', '.join(kinds)}")
        raise InputError(f"{where} must be an object with exactly one of {', '.join(kinds)}")
    kind, value = next(iter(block.items()))
    if kind == "heading":
        return f"<h2>{html.escape(_inline_only(value, f'{where}.heading', HEADING_MAX_CHARS))}</h2>"
    if kind == "text":
        return f"<p>{html.escape(_inline_only(value, f'{where}.text', BLOCK_MAX_CHARS))}</p>"
    if kind == "math":
        return f'<div class="mimir-display" tabindex="0">{html.escape(verify._text(value, f"{where}.math", BLOCK_MAX_CHARS))}</div>'
    return _original(value, f"{where}.original", rows, course_dir, index)


def _fill(template: str, values: dict[str, str]) -> str:
    """Replace every ``{{SLOT}}`` in one pass; inserted values are never re-scanned."""
    found = set(_SLOT.findall(template))
    if found != set(values):
        raise RuntimeError("page template slots do not match")
    return _SLOT.sub(lambda m: values[m.group(1)], template)


def _katex_values() -> dict[str, str]:
    return {
        "KATEX_CSS": _check_raw(_inline_fonts(_vendor_text("katex.min.css")), "</style", "KaTeX CSS"),
        "KATEX_JS": _check_raw(_vendor_text("katex.min.js"), "</script", "KaTeX JS"),
        "AUTO_RENDER_JS": _check_raw(_vendor_text("contrib/auto-render.min.js"), "</script", "auto-render"),
    }


def _json_script(value) -> str:
    """JSON for a ``<script type="application/json">`` body: ``<``, ``>`` and ``&`` are escaped."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_sheet(title: str, blocks_html: list[str]) -> str:
    return render_page(_TEMPLATE, {"TITLE": html.escape(title), "BLOCKS": "\n".join(blocks_html),
                                   **_katex_values()})


def render_page(template_path: Path, values: dict[str, str]) -> str:
    """Fill a page template; the CSP allows exactly its plain ``<script>`` bodies by hash."""
    template = template_path.read_text(encoding="utf-8")
    values = dict(values)
    hashes = []
    for body in _SCRIPT.findall(template):
        slot = _SLOT.fullmatch(body)
        if slot:
            hashes.append(_csp_hash(values[slot.group(1)]))
        elif "{{" in body:
            raise RuntimeError("page template script mixes code and a slot")
        else:
            hashes.append(_csp_hash(body))
    values["CSP"] = html.escape("default-src 'none'; script-src " + " ".join(hashes) + "; "
                                "style-src 'unsafe-inline'; font-src data:; img-src data:; "
                                "base-uri 'none'; form-action 'none'", quote=False)
    return _fill(template, values)


def cmd_sheet(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "title", "blocks"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    if "title" not in data:
        raise InputError("title is required")
    title = _inline_only(data["title"], "title", TITLE_MAX_CHARS)
    blocks = data.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise InputError("blocks is required (a non-empty list)")
    if len(blocks) > SHEET_MAX_BLOCKS:
        raise InputError(f"blocks has {len(blocks)} blocks; at most {SHEET_MAX_BLOCKS}")
    course_dir = verify._course_dir(term, course)
    index = course_dir / "INDEX.md"
    rows = {p: r for p, r in ingest.registry(index).items() if verify._inside(course_dir, p)}
    parts = [_sheet_block(block, f"blocks[{n}]", rows, course_dir, index) for n, block in enumerate(blocks, 1)]
    return _write_out(course_dir, name, "html", render_sheet(title, parts).encode("utf-8"))


# --- steps ---------------------------------------------------------------------------

def _title(data: dict) -> str:
    if "title" not in data:
        raise InputError("title is required")
    return _inline_only(data["title"], "title", TITLE_MAX_CHARS)


def cmd_steps(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "title", "blocks", "steps"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    title = _title(data)
    blocks, steps = data.get("blocks"), data.get("steps")
    if not isinstance(blocks, list) or not blocks:
        raise InputError("blocks is required (a non-empty list: the label, the question, any original)")
    if len(blocks) > SHEET_MAX_BLOCKS:
        raise InputError(f"blocks has {len(blocks)} blocks; at most {SHEET_MAX_BLOCKS}")
    if not isinstance(steps, list) or not steps:
        raise InputError("steps is required (a non-empty list of steps, each a list of text and math blocks)")
    if len(steps) > STEPS_MAX:
        raise InputError(f"steps has {len(steps)} steps; at most {STEPS_MAX}")
    for k, step in enumerate(steps, 1):
        if not isinstance(step, list) or not step:
            raise InputError(f"steps[{k}] must be a non-empty list of text and math blocks")
        if len(step) > STEP_MAX_BLOCKS:
            raise InputError(f"steps[{k}] has {len(step)} blocks; at most {STEP_MAX_BLOCKS}")
    course_dir = verify._course_dir(term, course)
    index = course_dir / "INDEX.md"
    rows = {p: r for p, r in ingest.registry(index).items() if verify._inside(course_dir, p)}
    intro = [_sheet_block(block, f"blocks[{n}]", rows, course_dir, index) for n, block in enumerate(blocks, 1)]
    items = []
    for k, step in enumerate(steps, 1):
        parts = [_sheet_block(block, f"steps[{k}][{n}]", rows, course_dir, index, _STEP_KINDS)
                 for n, block in enumerate(step, 1)]
        items.append(f'<li class="step" id="mimir-step-{k}"><h2>Step {k}</h2>\n' + "\n".join(parts) + "</li>")
    page = render_page(_STEPS_TEMPLATE, {"TITLE": html.escape(title), "BLOCKS": "\n".join(intro),
                                         "STEPS": "\n".join(items), **_katex_values()})
    return _write_out(course_dir, name, "html", page.encode("utf-8"))


# --- svg ---------------------------------------------------------------------------

def _local(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        ns, _, local = tag[1:].partition("}")
        return ns, local
    return "", tag


def _check_css_text(value: str, where: str) -> None:
    low = value.lower()
    if "\\" in value:
        raise InputError(f"svg: {where} contains a backslash (CSS escapes are not allowed)")
    if "javascript:" in re.sub(r"[\s\x00-\x1f]", "", low):
        raise InputError(f"svg: {where} contains javascript:")
    if "@import" in low:
        raise InputError(f"svg: {where} contains @import")
    if "image-set(" in low:
        raise InputError(f"svg: {where} contains image-set(")
    if len(_URL.findall(value)) != len(_URL_LOCAL.findall(value)):
        raise InputError(f"svg: {where} has url( that is not url(#...)")


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
    return _write_out(course_dir, name, "svg", raw)


# --- trace ---------------------------------------------------------------------------

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


_BRACE = re.compile(r"[{}]")


def _scope_css(css: str) -> str:
    """Prefix every selector with ``#mimir-diagram`` so an inlined diagram's CSS styles only the diagram."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, stack, pos = [], [], 0
    while True:
        match = _BRACE.search(css, pos)
        if match is None:
            if css[pos:].strip() or stack:
                raise InputError("svg: <style> has an unbalanced block")
            return "".join(out)
        prelude = css[pos:match.start()]
        if match.group() == "{":
            head = prelude.strip()
            if stack and stack[-1] == "rule":
                raise InputError("svg: <style> has a block nested in a rule")
            if head.startswith("@"):
                if stack or not head.lower().startswith("@media"):
                    raise InputError("svg: <style> in a step-through diagram allows only top-level @media at-rules")
                out.append(head + "{")
                stack.append("media")
            else:
                selectors = [part.strip() for part in head.split(",")]
                if not all(selectors):
                    raise InputError("svg: <style> has a rule without a selector")
                out.append(",".join(f"#mimir-diagram {sel}" for sel in selectors) + "{")
                stack.append("rule")
        else:
            if not stack or (stack[-1] == "media" and prelude.strip()):
                raise InputError("svg: <style> has an unbalanced block")
            out.append((prelude if stack.pop() == "rule" else "") + "}")
        pos = match.end()


def _inline_svg(value, states: list[str]) -> str:
    """Check the diagram, require one ``state-<i>`` element per state, and re-serialize it."""
    if not isinstance(value, str) or not value.strip():
        raise InputError("svg is required (the SVG document as a string)")
    if any(c not in _SVG_ALLOWED_CONTROL and unicodedata.category(c) in ("Cc", "Cs") for c in value):
        raise InputError("svg contains control characters or lone surrogates")
    raw = value.encode("utf-8")
    if len(raw) > SVG_MAX_BYTES:
        raise InputError(f"svg is {len(raw)} bytes; at most {SVG_MAX_BYTES}")
    root = check_svg(raw)
    ids: set[str] = set()
    for element in root.iter():
        ident = element.get("id")
        if ident is None:
            continue
        if ident in ids:
            raise InputError(f"svg: id {_short(ident)} is used twice")
        if ident.startswith("mimir-"):
            raise InputError(f"svg: id {_short(ident)} is reserved for the page (mimir-...)")
        ids.add(ident)
    for i, name in enumerate(states, 1):
        if f"state-{i}" not in ids:
            raise InputError(f'svg: no element with id "state-{i}" for machine.states[{i}] {_short(name)}')
    for element in root.iter(f"{{{_SVG_NS}}}style"):
        css = "".join(element.itertext())
        for child in list(element):
            element.remove(child)
        element.text = _scope_css(css)
    return ET.tostring(root, encoding="unicode")


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
    return (f"<p>{html.escape(facts)}</p>\n<table>\n<thead><tr>{head}</tr></thead>\n<tbody>\n"
            + "\n".join(body) + "\n</tbody>\n</table>")


def cmd_trace(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "title", "machine", "svg", "example"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    title = _title(data)
    machine = _machine(data.get("machine"))
    example = ""
    if data.get("example") is not None:
        example = verify._text(data["example"], "example", BLOCK_MAX_CHARS, required=False)
        symbols = sum(1 for c in example if not c.isspace())
        if symbols > TRACE_MAX_SYMBOLS:
            raise InputError(f"example has {symbols} symbols; at most {TRACE_MAX_SYMBOLS}")
    diagram = _inline_svg(data.get("svg"), machine["states"])
    course_dir = verify._course_dir(term, course)
    payload = {**machine, "max_configs": TRACE_MAX_CONFIGS, "max_stack": TRACE_MAX_STACK,
               "max_symbols": TRACE_MAX_SYMBOLS}
    page = render_page(_TRACE_TEMPLATE, {"TITLE": html.escape(title), "SVG": diagram,
                                         "EXAMPLE": html.escape(example), "MAX_SYMBOLS": str(TRACE_MAX_SYMBOLS),
                                         "MACHINE": _machine_html(machine), "DATA": _json_script(payload)})
    return _write_out(course_dir, name, "html", page.encode("utf-8"))


# --- delay ---------------------------------------------------------------------------

_CHART_W, _CHART_H = 640, 320
_PLOT_X, _PLOT_Y, _PLOT_W, _PLOT_H = 60, 50, 560, 190


def _f(value) -> str:
    return f"{float(value):.2f}"


def _delay_chart(course: str, rows: list[dict], texts: list[str], confidence: str) -> bytes:
    """A bar chart of study a day by start day: solid to the low end, outlined to the high end."""
    picks = sorted({0, len(rows) // 2, len(rows) - 1})
    top = max(r["high"] for r in rows)
    width = Fraction(_PLOT_W) / len(rows)
    gap = width / 5 if width >= 4 else Fraction(0)
    desc = (f"Study needed a day for each start day from today to the exam eve. "
            + " ".join(texts[i] for i in picks)
            + f" Solid bars show the low estimate, outlined bars the high estimate. Confidence: {confidence}.")
    esc = html.escape
    parts = [f'<svg xmlns="{_SVG_NS}" viewBox="0 0 {_CHART_W} {_CHART_H}" role="img">',
             f"<title>{esc(f'Cost of delay: {course}')}</title>",
             f"<desc>{esc(desc)}</desc>",
             "<style>.bg{fill:#ffffff}.low{fill:#1b1b1b}.high{fill:none;stroke:#1b1b1b;stroke-width:1}"
             ".axis{stroke:#1b1b1b;stroke-width:1}text{fill:#1b1b1b;font:14px system-ui,sans-serif}"
             "@media (prefers-color-scheme: dark){.bg{fill:#121212}.low{fill:#ececec}.high{stroke:#ececec}"
             ".axis{stroke:#ececec}text{fill:#ececec}}</style>",
             f'<rect class="bg" x="0" y="0" width="{_CHART_W}" height="{_CHART_H}"/>',
             f'<text x="{_PLOT_X}" y="28">{esc(f"Study a day by start day (scale top: {plan.fmt_duration(top)})")}</text>',
             f'<line class="axis" x1="{_PLOT_X}" y1="{_PLOT_Y + _PLOT_H}" x2="{_PLOT_X + _PLOT_W}" '
             f'y2="{_PLOT_Y + _PLOT_H}"/>',
             f'<line class="axis" x1="{_PLOT_X}" y1="{_PLOT_Y}" x2="{_PLOT_X}" y2="{_PLOT_Y + _PLOT_H}"/>']
    for i, row in enumerate(rows):
        x = _PLOT_X + width * i + gap / 2
        for cls, value in (("high", row["high"]), ("low", row["low"])):
            h = Fraction(_PLOT_H) * value / top
            parts.append(f'<rect class="{cls}" x="{_f(x)}" y="{_f(_PLOT_Y + _PLOT_H - h)}" '
                         f'width="{_f(width - gap)}" height="{_f(h)}"/>')
    for i in picks:
        label = "Today" if i == 0 else plan.day_label(rows[i]["start"])
        anchor = "start" if i == 0 else ("end" if i == len(rows) - 1 else "middle")
        x = (_PLOT_X if i == 0 else _PLOT_X + _PLOT_W if i == len(rows) - 1
             else _PLOT_X + width * i + width / 2)
        parts.append(f'<text x="{_f(x)}" y="{_PLOT_Y + _PLOT_H + 24}" text-anchor="{anchor}">{esc(label)}</text>')
    parts.append(f'<text x="{_PLOT_X}" y="{_CHART_H - 20}">Solid: low estimate. Outline: high estimate.</text>')
    parts.append("</svg>")
    raw = ("\n".join(parts) + "\n").encode("utf-8")
    check_svg(raw)
    return raw


def cmd_delay(data: dict) -> dict:
    _check_keys(data, {"term", "course", "name", "now"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    course_dir = verify._course_dir(term, course)
    start = session.cmd_start({"now": data.get("now"), "term": term, "course": course})
    if start["exam"] is None:
        raise InputError(f"no exam date for {course}: the cost of delay needs one")
    if not start["remaining"]:
        raise InputError(f"no topics left on the route of {course}: nothing to plan")
    payload = session.plan_payload(data["now"], start["exam"], start["remaining"])
    rows, est, _ = session._plan(plan.delay_rows, payload)
    delay_line = session._plan(plan.cost_of_delay, payload)["line"]
    texts = [plan.delay_phrase(row, i == 0) for i, row in enumerate(rows)]
    table = []
    for i, row in enumerate(rows):
        day = plan.day_label(row["start"]) + (" (today)" if i == 0 else "")
        table.append(f"<tr><td>{html.escape(day)}</td><td>{html.escape(plan.count(row['days'], 'day'))}</td>"
                     f"<td>{html.escape(plan.fmt_range(row['low'], row['high']))}</td></tr>")
    page = render_page(_SLIDER_TEMPLATE, {
        "TITLE": html.escape(f"Cost of delay: {course}"), "MAX": str(len(rows) - 1),
        "FIRST": html.escape(texts[0]), "CONFIDENCE": html.escape(f"Confidence: {est['confidence']}."),
        "ROWS": "\n".join(table), "DATA": _json_script(texts)})
    chart = _delay_chart(course, rows, texts, est["confidence"])
    built = _write_out(course_dir, name, "html", page.encode("utf-8"))
    svg_out = _write_out(course_dir, name, "svg", chart)
    return {"course_dir": str(course_dir), "html": built["path"], "svg": svg_out["path"],
            "delay_line": delay_line, "line": f"Built {built['path']} and {svg_out['path']}."}


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
    "sheet": (cmd_sheet, "build an offline HTML math sheet in <course>/.state/out/"),
    "svg": (cmd_svg, "check an SVG document and write it to <course>/.state/out/"),
    "steps": (cmd_steps, "build a step-reveal worked answer page in <course>/.state/out/"),
    "trace": (cmd_trace, "build a structure step-through page in <course>/.state/out/"),
    "delay": (cmd_delay, "build the cost-of-delay slider page and chart in <course>/.state/out/"),
    "open": (cmd_open, "open a built file in the default browser"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("visual.py",
                             ("Mimir visual builder. Subcommands: sheet, svg, steps, trace, delay, open. Reads one JSON object on "
                              "stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
