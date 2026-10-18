#!/usr/bin/env python3
"""Mimir visual builder: math sheets, safe SVG files and the browser open.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``verify.py`` (same folder). Run as::

    python3 visual.py <sheet|svg|open>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. All three need a workspace at
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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import ingest
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

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_TEMPLATE = _ASSETS / "math-sheet.html"
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


def _sheet_block(block, n: int, rows: dict, course_dir: Path, index: Path) -> str:
    where = f"blocks[{n}]"
    if not isinstance(block, dict) or len(block) != 1 or next(iter(block)) not in _BLOCK_KINDS:
        if isinstance(block, dict) and len(block) == 1:
            raise InputError(f"{where}: unknown field {_short(next(iter(block)))}; a block is one of "
                             f"{', '.join(_BLOCK_KINDS)}")
        raise InputError(f"{where} must be an object with exactly one of {', '.join(_BLOCK_KINDS)}")
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
        raise RuntimeError("math-sheet template slots do not match")
    return _SLOT.sub(lambda m: values[m.group(1)], template)


def render_sheet(title: str, blocks_html: list[str]) -> str:
    template = _TEMPLATE.read_text(encoding="utf-8")
    values = {
        "TITLE": html.escape(title),
        "BLOCKS": "\n".join(blocks_html),
        "KATEX_CSS": _check_raw(_inline_fonts(_vendor_text("katex.min.css")), "</style", "KaTeX CSS"),
        "KATEX_JS": _check_raw(_vendor_text("katex.min.js"), "</script", "KaTeX JS"),
        "AUTO_RENDER_JS": _check_raw(_vendor_text("contrib/auto-render.min.js"), "</script", "auto-render"),
    }
    hashes = []
    for body in _SCRIPT.findall(template):
        slot = _SLOT.fullmatch(body)
        if slot:
            hashes.append(_csp_hash(values[slot.group(1)]))
        elif "{{" in body:
            raise RuntimeError("math-sheet template script mixes code and a slot")
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
    parts = [_sheet_block(block, n, rows, course_dir, index) for n, block in enumerate(blocks, 1)]
    return _write_out(course_dir, name, "html", render_sheet(title, parts).encode("utf-8"))


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


def check_svg(raw: bytes) -> None:
    """Refuse an SVG document that could run script or load anything; see the docstring."""
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
    "open": (cmd_open, "open a built file in the default browser"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("visual.py",
                             ("Mimir visual builder. Subcommands: sheet, svg, open. Reads one JSON object on "
                              "stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
