"""Mimir visual builder, part 1: the allowlist checkers for SVG documents and page bodies.

Standard library only, Python 3.11+. ``check_svg`` refuses an SVG document that could run script or load
anything; ``check_page_body`` checks a builder-written page body and writes it out again from what was
checked. What each refuses is the contract of ``visual.py svg`` and ``visual.py page`` (see the docstring of
``visual.py``); errors start ``svg:`` or ``body:``.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import workspace
from workspace import InputError

STEPS_MAX = 50                 # data-step numbers on one page

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
_XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", _XLINK_NS)


def split_tag(tag: str) -> tuple[str, str]:
    """An ElementTree tag as (namespace, local name); the namespace is "" when there is none."""
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
                         f"not {workspace.short(encoding.group(1))}")
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
    if root is None or split_tag(root.tag) != (_SVG_NS, "svg"):
        raise InputError(f"svg: the root element must be svg in the namespace {_SVG_NS}")
    kids = list(root)
    for k, want in ((0, "title"), (1, "desc")):
        if len(kids) <= k or split_tag(kids[k].tag) != (_SVG_NS, want):
            raise InputError(f"svg: child element {k + 1} of the root must be <{want}>")
        if not "".join(kids[k].itertext()).strip():
            raise InputError(f"svg: <{want}> must not be empty")
    for element in root.iter():
        ns, local = split_tag(element.tag)
        if ns != _SVG_NS or local not in _SVG_ELEMENTS:
            shown = local if ns in ("", _SVG_NS) else f"{{{ns}}}{local}"
            raise InputError(f"svg: element <{shown}> is not allowed")
        for attr, value in element.attrib.items():
            _, name = split_tag(attr)
            where = f"<{local}> attribute {name}"
            if name.lower().startswith("on"):
                raise InputError(f"svg: event attribute {name} on <{local}> is not allowed")
            if name.lower() == "href" and not value.startswith("#"):
                raise InputError(f"svg: {where} must start with # (no external links): {workspace.short(value)}")
            _check_css_text(value, where)
        if local == "style":
            _check_css_text("".join(element.itertext()), "<style>")
    return root


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
                self._fail(f"<{tag}> has a malformed attribute name {workspace.short(name)}")
            if name in seen:
                self._fail(f"<{tag}> has the attribute {name} twice")
            seen.add(name)
            value = "" if value is None else value
            if name.startswith("on"):
                self._fail(f"event attribute {name} on <{tag}> is not allowed")
            where = f"<{tag}> attribute {name}"
            if svg:
                if name.endswith("href") and not value.startswith("#"):
                    self._fail(f"{where} must start with # (no external links): {workspace.short(value)}")
                _check_css_text(value, where, "body")
                name = _SVG_CASE.get(name, name)
            else:
                allowed = name in _PAGE_GLOBAL_ATTRS or name in _PAGE_ELEMENT_ATTRS.get(tag, ())
                if not (allowed or name.startswith(("aria-", "data-"))):
                    self._fail(f"attribute {name} on <{tag}> is not allowed")
                if name == "href" and not value.startswith("#"):
                    self._fail(f"{where} must start with # (no links out of the page): {workspace.short(value)}")
                if name == "style":
                    _check_css_text(value, where, "body")
            if name == "id":
                if value in self.ids:
                    self._fail(f"id {workspace.short(value)} is used twice")
                if _RESERVED_ID.match(value):
                    self._fail(f"id {workspace.short(value)} is reserved for the page (mimir-..., sk-...)")
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
                               f"{workspace.short(value)}")
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
            self._fail("the body ends inside an unfinished tag, comment or declaration: "
                       f"{workspace.short(self.rawdata)}")
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
            raise InputError(f'body: no element with id "state-{i}" for machine.states[{i}] {workspace.short(name)} '
                             "inside an inline <svg>")
    return out, parser.math, bool(parser.steps)
