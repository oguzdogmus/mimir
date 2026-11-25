"""Mimir visual builder, part 4: the page file around a checked body, the Skald tokens and the assets.

Standard library only, Python 3.11+. ``render_page`` fills the page shell (``assets/page/page.html``) with
the Skald tokens, KaTeX, the step script, the mascot and the simulator, each script allowed by its hash in
the Content-Security-Policy; ``svg_with_tokens`` adds the Skald tokens to a checked SVG document and
``svg_without_tokens`` takes them off again; ``original_html`` turns one ``<mimir-original>`` marker into the
image or link it stands for.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path

import verify
import visual_machine
import workspace
from workspace import InputError

ORIGINAL_EMBED_MAX_BYTES = 10 * 1024 * 1024

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_KATEX = _ASSETS / "vendor" / "katex"
_PAGE_TEMPLATE = _ASSETS / "page" / "page.html"
_PAGE_MATH_JS = _ASSETS / "page" / "math.js"
_MACHINE_JS = _ASSETS / "page" / "machine.js"       # the simulator engine (MimirSim)
_PAGE_SIM_JS = _ASSETS / "page" / "simulator.js"
_PAGE_STEPS_JS = _ASSETS / "page" / "steps.js"
_MASCOT_SVG = _ASSETS / "skald" / "mascot.svg"   # decorative art, no ids: inlined as it is
_SKALD = _ASSETS / "skald"
TOKENS_CSS = _SKALD / "tokens.css"            # also read by the label check (visual_labels)

_SLOT = re.compile(r"\{\{([A-Z_]+)\}\}")
_IMAGE_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
               "webp": "image/webp"}


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


def csp_hash(script: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"


def original_html(value, where: str, rows: dict, course_dir: Path, index: Path) -> str:
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
        raise InputError(f"{where}.path: {workspace.short(rel)} has no registry row inside the course in {index}")
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


_SKALD_FONT = re.compile(r'url\("fonts/([a-z0-9-]+\.woff2)"\)')


def skald_tokens() -> str:
    """The Skald stylesheet with its bundled fonts as data URIs (nothing left to load)."""
    def font(match: re.Match) -> str:
        payload = base64.b64encode((_SKALD / "fonts" / match.group(1)).read_bytes()).decode("ascii")
        return f"url(data:font/woff2;base64,{payload})"

    css = _SKALD_FONT.sub(font, TOKENS_CSS.read_text(encoding="utf-8"))
    if 'url("fonts/' in css or "url(fonts/" in css:
        raise RuntimeError("Skald tokens still reference a font file")
    return css


_SVG_ROOT_END = re.compile(r"</(?:([A-Za-z_][\w.-]*):)?svg\s*>((?:\s|<!--(?:(?!-->).)*-->)*)\Z", re.S)


def svg_with_tokens(svg: str) -> str:
    """Append the Skald tokens as the root's last ``<style>`` (CSS applies wherever it sits)."""
    css = skald_tokens()
    end = _SVG_ROOT_END.search(svg)
    if end is None or "]]>" in css:
        raise RuntimeError("cannot place the Skald tokens in the SVG")
    return svg[:end.start()] + _tokens_block(end, css) + svg[end.start():]


def _tokens_block(end: re.Match, css: str) -> str:
    tag = f"{end.group(1)}:style" if end.group(1) else "style"
    return f"<{tag}><![CDATA[\n{css}]]></{tag}>"


def svg_without_tokens(built: str) -> str | None:
    """The SVG document ``svg_with_tokens`` was given, or None when ``built`` does not end with today's tokens."""
    end = _SVG_ROOT_END.search(built)
    if end is None:
        return None
    block = _tokens_block(end, skald_tokens())
    head = built[:end.start()]
    if not head.endswith(block):
        return None
    return head[:-len(block)] + built[end.start():]


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
        body += visual_machine.simulator_html(machine, example)
        machine_json = _json_script(visual_machine.machine_data(machine))
        data = f'<script type="application/json" id="mimir-machine">{machine_json}</script>\n'
        scripts += [_check_raw(path.read_text(encoding="utf-8"), "</script", "simulator")
                    for path in (_MACHINE_JS, _PAGE_SIM_JS)]
    template = _PAGE_TEMPLATE.read_text(encoding="utf-8")
    return _fill(template, {
        "CSP": _csp([csp_hash(s) for s in scripts]),
        "MOTION": motion or "none",
        "TITLE": html.escape(title),
        "KATEX_STYLE": f"<style>{katex['KATEX_CSS']}</style>\n" if katex else "",
        "TOKENS": _check_raw(skald_tokens(), "</style", "Skald tokens"),
        "BODY": body,
        "MASCOT": mascot,
        "SCRIPTS": data + "".join(f"<script>{s}</script>\n" for s in scripts)})
