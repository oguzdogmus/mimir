"""Mimir visual builder, part 2: the label overlap check for every SVG figure.

Standard library only, Python 3.11+. ``check_svg_labels`` checks a standalone SVG (its root as
``visual_check.check_svg`` returns it) and ``check_body_labels`` every outermost ``<svg>`` of a checked page
body; both refuse a ``<text>`` whose estimated box touches a stroke or leaves the viewBox (see the docstring
of ``visual.py``).
"""

from __future__ import annotations

import functools
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import visual_check
import visual_render
from workspace import InputError

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
        attrs = {visual_check.split_tag(k)[1].lower(): v for k, v in el.attrib.items()}
        return _Node(visual_check.split_tag(el.tag)[1], attrs, parent)
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
    return tuple(_css_rules(visual_render.TOKENS_CSS.read_text(encoding="utf-8")))


def check_labels(svgs: list[_Node], styles: list[str], field: str, root_font: float) -> None:
    """Refuse figures whose labels touch a stroke or leave the viewBox (see the docstring of ``visual.py``)."""
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


def check_svg_labels(root: ET.Element) -> None:
    """The label check of ``visual.py svg``: one standalone figure at the browser's default font size."""
    figure = _tree_from_svg(root)
    check_labels([figure], _style_texts(figure), "svg", _SVG_FONT_PX)


def check_body_labels(body: str) -> None:
    """The label check of ``visual.py page``: every outermost ``<svg>`` of a checked body, inside the page."""
    main = _body_tree(body)
    check_labels(_outermost_svgs(main), _style_texts(main), "body", _PAGE_FONT_PX)


def body_figures(body: str) -> list[_Node]:
    """Every outermost ``<svg>`` of a checked page body, in order, in the tree the page places it in."""
    return _outermost_svgs(_body_tree(body))


def _body_tree(body: str) -> _Node:
    tree = _BodyTree()
    tree.feed(body)
    tree.close()
    return tree.root


def _outermost_svgs(main: _Node) -> list[_Node]:
    return [n for n in _walk(main) if n.tag == "svg" and not any(a.tag == "svg" for a in _ancestors(n))]
