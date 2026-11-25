"""Mimir visual builder, part 6: base figures, their stable part ids and their reuse.

Standard library only, Python 3.11+. Works on the figure trees of ``visual_labels`` (a standalone SVG or
the inline SVGs of a page body). ``parts`` refuses a base figure whose drawn shapes do not all belong to a
part with a stable id and returns each part's signature; ``check_reuse`` refuses a later build of the subject
that changes, moves, hides or drops a part or adds anything but labels, leader lines and highlights (see the
docstring of ``visual.py``). The reuse check fails closed: it lists what may change and what may be added,
and refuses everything else.
"""

from __future__ import annotations

import functools
import re

import visual_check
import visual_labels
import visual_render
from workspace import InputError, short

# Elements that draw a shape. Each one in a base figure is a part or sits inside one.
SHAPES = ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "use")
# Attributes that place or shape a shape; an error names the first two to point at it.
GEOMETRY = ("d", "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "points",
            "transform", "href", "pathlength")
# Containers whose content is not drawn where it sits (definitions, markers, clips, text).
_NOT_DRAWN = {"defs", "marker", "clippath", "mask", "symbol", "lineargradient", "radialgradient", "style",
              "title", "desc", "text"}
# Definitions outside the parts: a reuse keeps them exactly as the base figure has them and adds none.
DEFINITIONS = ("defs", "marker", "clippath", "mask", "symbol", "lineargradient", "radialgradient")
# The only attributes a reuse may change on a part, on anything inside it or on a group round it.
PART_MAY_CHANGE = ("class", "data-step", "data-highlight")
# The classes a part, a group round it or the figure may take on: Skald figure classes that hide nothing.
PART_CLASSES = ("ink", "ink-fill", "soft", "soft-fill", "curve", "ghost", "wash")
# What a reuse may add outside the parts besides labels (<text>) and groups: a leader line (an open stroke;
# a content arrow is a leader whose head is part of the stroke), its end dot and a highlight mark.
LEADER = ("path", "line", "polyline")
MARKS = ("mark-loop", "mark-swipe")
ADDED_CLASSES = ("leader", "anchor") + MARKS
ANCHOR_MAX_SHARE = 0.01  # an anchor's largest radius, as a share of the viewBox's larger side
# Attributes an added shape or group may carry beside its own geometry (``aria-*`` too).
ADDED_ATTRS = ("class", "id", "data-step", "data-highlight")
_ADDED_GEOMETRY = {"path": ("d", "pathlength"), "line": ("x1", "y1", "x2", "y2", "pathlength"),
                   "polyline": ("points", "pathlength"), "circle": ("cx", "cy", "r")}
# CSS that reaches the figure's <svg> or an element round it may only lay it out and set its type.
FRAME_PROPERTIES = ("margin", "padding", "border", "outline", "background", "box-shadow", "width", "height",
                    "max-width", "max-height", "min-width", "min-height", "inline-size", "block-size",
                    "aspect-ratio", "float", "clear", "order", "gap", "row-gap", "column-gap", "text-align",
                    "line-height", "font", "font-family", "font-size", "font-weight", "font-style",
                    "letter-spacing", "word-spacing", "--sticky-fig")
_FRAME_PREFIXES = ("margin-", "padding-", "border-", "outline-", "background-", "grid", "flex", "justify-",
                   "align-", "place-", "break-", "page-break-")
# Skald classes an element round the figure may carry; any other token class could hide the figure.
FRAME_CLASSES = ("board", "work-first", "step", "body")
_PART_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_TOKEN_CLASS = re.compile(r"\.(-?[a-z_][\w-]*)", re.I)


def _drawn(node) -> bool:
    return node.tag not in _NOT_DRAWN and not any(a.tag in _NOT_DRAWN for a in visual_labels._ancestors(node))


def _kept(node) -> tuple:
    """What a reuse keeps on a node: its tag, its own text and every attribute it may not change."""
    attrs = tuple(sorted((k, " ".join(v.split())) for k, v in node.attrs.items() if k not in PART_MAY_CHANGE))
    text = " ".join("".join(k for k in node.kids if isinstance(k, str)).split())
    return node.tag, attrs, text


def _signature(figure, node) -> tuple:
    """Where a part sits and what it is: the groups round it, itself and everything inside it."""
    chain = tuple(_kept(a) for a in reversed(list(_below(figure, node))) if a.tag != "g" or _kept(a) != ("g", (), ""))
    return chain, _kept(node), tuple(_kept(n) for n in visual_labels._walk(node) if n is not node)


def parts(figure, field: str) -> dict[str, tuple]:
    """``{part id: signature}`` in document order; refuses a figure without stable part ids."""
    seen, found = set(), {}
    for node in visual_labels._walk(figure):
        value = node.attrs.get("id")
        if value is not None:
            if not _PART_ID.fullmatch(value):
                raise InputError(f"{field}: id {short(value)} on <{node.tag}> is not a stable part id (lowercase "
                                 "letters and digits joined by single hyphens, starting with a letter)")
            if visual_check._RESERVED_ID.match(value):
                raise InputError(f"{field}: id {short(value)} is reserved for the page (mimir-..., sk-...)")
            if value in seen:
                raise InputError(f"{field}: id {short(value)} is used twice")
            seen.add(value)
        if node.tag == "use":
            raise InputError(f"{field}: a base figure draws every part itself; <use> {_where(node)} is not "
                             "allowed, since a reuse could change what it points at")
        if node is figure or not _drawn(node):
            continue
        if node.tag in SHAPES or node.tag == "g":
            if value is not None:
                found[value] = _signature(figure, node)
            elif node.tag in SHAPES and not any("id" in a.attrs for a in _below(figure, node)):
                raise InputError(f"{field}: <{node.tag}> {_where(node)} belongs to no part: give it or its group "
                                 "a stable part id")
    if not found:
        raise InputError(f"{field}: the base figure has no parts (shapes or groups with a stable part id)")
    return found


def _below(figure, node):
    """The ancestors of ``node`` up to, not including, the figure's root."""
    for a in visual_labels._ancestors(node):
        if a is figure:
            return
        yield a


def _where(node) -> str:
    shown = [f'{k}="{short(node.attrs[k])}"' for k in GEOMETRY if k in node.attrs][:2]
    return f"({', '.join(shown)})" if shown else "(no geometry)"


def _viewbox(figure) -> str:
    return " ".join(figure.attrs.get("viewbox", "").replace(",", " ").split())


def _tree(node) -> tuple:
    return _kept(node), tuple(sorted(node.classes)), tuple(_tree(k) for k in node.kids if not isinstance(k, str))


def _outside_parts(figure, ids, tags) -> list:
    """The outermost nodes of ``tags`` in ``figure`` that sit in no part, in document order."""
    found, todo = [], [figure]
    while todo:
        node = todo.pop()
        if node.attrs.get("id") in ids and node is not figure:
            continue
        if node.tag in tags and node is not figure:
            found.append(node)
            continue
        todo.extend(reversed([k for k in node.kids if not isinstance(k, str)]))
    return found


def _check_classes(node, allowed: set, what: str, field: str) -> None:
    extra = sorted(node.classes - allowed - set(PART_CLASSES))
    if extra:
        raise InputError(f"{field}: class {short(extra[0])} on {what}; a base figure part may take on only the "
                         f"classes {', '.join(PART_CLASSES)}")


def check_reuse(base, figures: list, field: str) -> None:
    """Refuse a build of a subject that does not keep its base figure ``base`` exactly, as ``field``.

    ``figures`` are the build's outermost SVGs; the one holding the base figure's parts is checked, with
    every ``<style>`` and every element round it.
    """
    want = parts(base, "base figure")
    figure = next((f for f in figures if any(n.attrs.get("id") in want for n in visual_labels._walk(f))), None)
    if figure is None and len(figures) == 1 and figures[0].parent is None:
        figure = figures[0]  # a standalone SVG: name the parts it lacks
    if figure is None:
        raise InputError(f"{field}: no inline <svg> holds the base figure's parts; start from the base figure")
    if _viewbox(figure) != _viewbox(base):
        raise InputError(f"{field}: the viewBox {short(_viewbox(figure))} differs from the base figure's "
                         f"{short(_viewbox(base))}; keep the base figure's frame")
    _check_root(base, figure, field)
    base_styles = [visual_labels._text_of(n) for n in _outside_parts(base, want, {"style"})]
    figure_styles = [visual_labels._text_of(n) for n in _outside_parts(figure, want, {"style"})]
    if ([_tree(n) for n in _outside_parts(base, want, DEFINITIONS)]
            != [_tree(n) for n in _outside_parts(figure, want, DEFINITIONS)]
            or any(figure_styles.count(s) < base_styles.count(s) for s in base_styles)):
        raise InputError(f"{field}: the figure's definitions (defs, markers, clip paths, masks, gradients, its "
                         "<style>) differ from the base figure's; keep them exactly and add none")
    base_nodes = {n.attrs["id"]: n for n in visual_labels._walk(base) if "id" in n.attrs}
    nodes = {n.attrs["id"]: n for n in visual_labels._walk(figure) if "id" in n.attrs}
    for part, signature in want.items():
        if part not in nodes:
            raise InputError(f"{field}: base figure part {short(part)} is missing; keep every part of the base "
                             "figure")
        if _signature(figure, nodes[part]) != signature:
            raise InputError(f"{field}: base figure part {short(part)} changed (an attribute other than "
                             f"{', '.join(PART_MAY_CHANGE)}, a shape inside it or a group round it); start from "
                             "the base figure and never redraw, hide or restyle its parts")
        for was, now in zip(visual_labels._walk(base_nodes[part]), visual_labels._walk(nodes[part])):
            _check_classes(now, was.classes, f"base figure part {short(part)}", field)
        around = set().union(*(a.classes for a in _below(base, base_nodes[part])))
        for a in _below(figure, nodes[part]):
            _check_classes(a, around, f"a group round base figure part {short(part)}", field)
    _check_added(figure, set(want), field)
    _check_css(base_styles, figure, set(want), field)


def _check_root(base, figure, field: str) -> None:
    """The figure's own ``<svg>`` keeps the base figure's attributes; it may gain an id, a style and aria-*."""
    may_change = set(PART_MAY_CHANGE) | {"id", "style"}
    for name in sorted(set(base.attrs) | set(figure.attrs)):
        if name in may_change or name.startswith(("aria-", "xmlns")):
            continue
        if base.attrs.get(name) != figure.attrs.get(name):
            raise InputError(f"{field}: the <svg> attribute {name} differs from the base figure's; keep the base "
                             "figure's <svg> as it is")
    _check_classes(figure, base.classes, "the figure's <svg>", field)
    if figure.attrs.get("style", "") != base.attrs.get("style", ""):
        _check_frame(_properties(figure.attrs.get("style", "")), "the style attribute of the figure's <svg>", field)


def _check_added(figure, ids: set, field: str) -> None:
    """Outside the parts, only labels, leader lines, anchors, highlight marks and plain groups are added."""
    sides = [float(v) for v in _viewbox(figure).split()[2:4] if re.fullmatch(r"[0-9.eE+-]+", v)]
    anchor_max = max(sides, default=0.0) * ANCHOR_MAX_SHARE
    todo = [k for k in figure.kids if not isinstance(k, str)]
    while todo:
        node = todo.pop()
        if node.attrs.get("id") in ids or node.tag in DEFINITIONS + ("style", "title", "desc", "text"):
            continue  # a part, compared with the base figure; definitions; styles (``_check_css``); labels
        if node.tag == "g":
            if not any(n.attrs.get("id") in ids for n in visual_labels._walk(node)):
                _check_attrs(node, (), "a group added on a base figure", field)
                _check_classes(node, set(), "a group added on a base figure", field)
            todo.extend(k for k in node.kids if not isinstance(k, str))
            continue
        role = next(iter(node.classes)) if len(node.classes) == 1 else None
        if node.tag not in SHAPES or role not in ADDED_CLASSES:
            raise InputError(f"{field}: <{node.tag}> {_where(node)} is new; on a base figure add only labels, leader "
                             f"lines and highlights (shapes of one class: {', '.join(ADDED_CLASSES)})")
        if role == "leader" and node.tag not in LEADER:
            raise InputError(f"{field}: <{node.tag}> {_where(node)}: a leader is an open stroke, a <path> without "
                             "Z, a <line> or a <polyline>")
        if role == "anchor" and node.tag != "circle":
            raise InputError(f"{field}: <{node.tag}> {_where(node)}: an anchor is a <circle> of radius at most "
                             f"{anchor_max:g} ({ANCHOR_MAX_SHARE:.0%} of the viewBox's larger side)")
        if role in MARKS and node.tag != "path":
            raise InputError(f"{field}: <{node.tag}> {_where(node)}: a highlight mark is a <path>")
        _check_attrs(node, _ADDED_GEOMETRY[node.tag], f"an added {role}", field)
        if role == "leader" and "z" in node.attrs.get("d", "").lower():
            raise InputError(f"{field}: <path> {_where(node)}: a leader is an open stroke, a <path> without Z, a "
                             "<line> or a <polyline>")
        if role == "anchor":
            try:
                radius = float(node.attrs.get("r", ""))
            except ValueError:
                radius = anchor_max + 1
            if radius > anchor_max:
                raise InputError(f"{field}: <circle> {_where(node)}: an anchor is a <circle> of radius at most "
                                 f"{anchor_max:g} ({ANCHOR_MAX_SHARE:.0%} of the viewBox's larger side)")
        if role in MARKS and "data-highlight" not in node.attrs:
            raise InputError(f"{field}: <path> {_where(node)}: a highlight mark needs data-highlight, the step "
                             "it marks")


def _check_attrs(node, geometry: tuple, what: str, field: str) -> None:
    for name in sorted(node.attrs):
        if name not in ADDED_ATTRS + geometry and not name.startswith("aria-"):
            raise InputError(f"{field}: <{node.tag}> {_where(node)} has attribute {name}; {what} carries only "
                             f"{', '.join(ADDED_ATTRS + geometry)} and aria-*")


# --- CSS: what a <style> or a style attribute can reach --------------------------------

def _properties(declarations: str) -> list[str]:
    found = []
    for decl in visual_labels._split_top(declarations, ";"):
        name, colon, _ = decl.partition(":")
        if colon and name.strip():
            found.append(name.strip().lower())
    return found


def _rules(css: str):
    """``(selector, properties)`` for every style rule, inside @media, @supports and every other group too."""
    for prelude, body in visual_labels._css_blocks(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if prelude.startswith("@"):
            if (prelude[1:].split(None, 1) or [""])[0].lower() not in ("keyframes", "-webkit-keyframes", "font-face"):
                yield from _rules(body)
            continue
        if "{" in body:
            yield prelude, None  # nested CSS: refused, the shell does not follow it
            continue
        for selector in visual_labels._split_top(prelude, ","):
            yield selector.strip(), _properties(body)


def _frame_property(name: str) -> bool:
    return name in FRAME_PROPERTIES or name.startswith(_FRAME_PREFIXES)


def _check_frame(properties: list[str], where: str, field: str, tag: str = "") -> None:
    bad = next((p for p in properties if not _frame_property(p)), None)
    if bad is not None:
        on = f" on <{tag}>" if tag else ""
        raise InputError(f"{field}: {where} can reach the base figure: property {bad}{on} round it; there, set "
                         "only layout and type (margin, padding, border, background, size, grid, flex, font)")


def _is_label(node, figure, ids: set) -> bool:
    return node.tag in ("text", "tspan") and not any(
        n.attrs.get("id") in ids for n in [node, *_below(figure, node)])


@functools.lru_cache(maxsize=1)
def _token_classes() -> frozenset:
    return frozenset(_TOKEN_CLASS.findall(visual_render.TOKENS_CSS.read_text(encoding="utf-8")))


def _check_css(base_styles: list[str], figure, ids: set, field: str) -> None:
    """Refuse CSS that can reach a part, and anything round the figure that can hide or restyle it.

    A rule may style labels (``<text>`` outside the parts) and anything not round the figure freely; on the
    figure's ``<svg>`` and the elements round it, it may set only FRAME_PROPERTIES. A selector the shell does
    not follow (pseudo-classes, attributes, siblings, nesting) is refused.
    """
    top = figure
    while top.parent is not None:
        top = top.parent
    around = set(map(id, visual_labels._ancestors(figure)))
    for a in visual_labels._ancestors(figure):
        if "hidden" in a.attrs:
            raise InputError(f"{field}: <{a.tag}> round the base figure has attribute hidden; never hide the figure")
        tokens = sorted(a.classes & _token_classes() - set(FRAME_CLASSES))
        if tokens:
            raise InputError(f"{field}: class {short(tokens[0])} on <{a.tag}> round the base figure; there, use only "
                             f"the Skald classes {', '.join(FRAME_CLASSES)}")
        if "style" in a.attrs:
            _check_frame(_properties(a.attrs["style"]), f"the style attribute of <{a.tag}>", field)
    styles = list(base_styles)
    all_nodes = list(visual_labels._walk(top))
    for node in all_nodes:
        if node.tag != "style":
            continue
        css = visual_labels._text_of(node)
        if css in styles:
            styles.remove(css)  # the base figure's own
            continue
        for selector, properties in _rules(css):
            parsed = visual_labels._selector(selector) if properties is not None else None
            if parsed is None:
                raise InputError(f"{field}: CSS {short(selector)} can reach the base figure in ways the shell does "
                                 "not check; on a build from a base figure, select only by type, class and id, "
                                 "with descendant or child combinators, and write no nested rules")
            for hit in all_nodes:
                if not visual_labels._selector_matches(parsed, len(parsed) - 1, hit):
                    continue
                inside = hit is not figure and figure in visual_labels._ancestors(hit)
                if inside and not _is_label(hit, figure, ids):
                    raise InputError(f"{field}: CSS {short(selector)} can reach the base figure (<{hit.tag}> "
                                     f"{_where(hit)}); style only its labels, never its parts or shapes")
                if hit is figure or id(hit) in around:
                    _check_frame(properties, f"CSS {short(selector)}", field, hit.tag)
