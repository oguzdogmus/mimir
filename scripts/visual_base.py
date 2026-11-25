"""Mimir visual builder, part 6: base figures, their stable part ids and their reuse.

Standard library only, Python 3.11+. Works on the figure trees of ``visual_labels`` (a standalone SVG or
the inline SVGs of a page body). ``parts`` refuses a base figure whose drawn shapes do not all belong to a
part with a stable id and returns each part's geometry; ``check_reuse`` refuses a later build of the subject
that changes, moves or drops a part or adds anything but labels, leader lines and highlights (see the
docstring of ``visual.py``).
"""

from __future__ import annotations

import re

import visual_check
import visual_labels
from workspace import InputError, short

# Elements that draw a shape. Each one in a base figure is a part or sits inside one.
SHAPES = ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "use")
# Attributes that place or shape a part. A reuse keeps every one of them on every part.
GEOMETRY = ("d", "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "points",
            "transform", "href", "pathlength")
# Containers whose content is not drawn where it sits (definitions, markers, clips, text).
_NOT_DRAWN = {"defs", "marker", "clippath", "mask", "symbol", "lineargradient", "radialgradient", "style",
              "title", "desc", "text"}
# The classes a shape added on top of a base figure may carry: a leader line, its end dot, a highlight.
ADDED_CLASSES = ("leader", "anchor", "mark-loop", "mark-swipe")
_PART_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def _drawn(node) -> bool:
    return node.tag not in _NOT_DRAWN and not any(a.tag in _NOT_DRAWN for a in visual_labels._ancestors(node))


def _geometry(node) -> tuple:
    return (node.tag,) + tuple((k, " ".join(node.attrs[k].split())) for k in GEOMETRY if k in node.attrs)


def _signature(figure, node) -> tuple:
    """Where a part sits and what it draws: its ancestors' transforms, its own geometry and every shape in it."""
    chain = []
    for a in visual_labels._ancestors(node):
        if "transform" in a.attrs:
            chain.append(" ".join(a.attrs["transform"].split()))
        if a is figure:
            break
    inner = tuple(_geometry(n) for n in visual_labels._walk(node)
                  if n is not node and n.tag in SHAPES and _drawn(n))
    return tuple(reversed(chain)), _geometry(node), inner


def parts(figure, field: str) -> dict[str, tuple]:
    """``{part id: geometry}`` in document order; refuses a figure without stable part ids."""
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


def check_reuse(base, figures: list, field: str) -> None:
    """Refuse a build of a subject that does not keep its base figure ``base`` exactly, as ``field``.

    ``figures`` are the build's outermost SVGs; the one holding the base figure's parts is checked.
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
    nodes = {n.attrs["id"]: n for n in visual_labels._walk(figure) if "id" in n.attrs}
    for part, signature in want.items():
        if part not in nodes:
            raise InputError(f"{field}: base figure part {short(part)} is missing; keep every part of the base "
                             "figure")
        if _signature(figure, nodes[part]) != signature:
            raise InputError(f"{field}: base figure part {short(part)} changed (its geometry, a shape inside it or "
                             "a transform around it); start from the base figure and never redraw its parts")
    for node in visual_labels._walk(figure):
        if node.tag not in SHAPES or not _drawn(node) or node.attrs.get("id") in want:
            continue
        if any(a.attrs.get("id") in want for a in _below(figure, node)):
            continue  # inside a part, already compared with it
        if not node.classes & set(ADDED_CLASSES):
            raise InputError(f"{field}: <{node.tag}> {_where(node)} is new; on a base figure add only labels, leader "
                             f"lines and highlights (shapes of class {', '.join(ADDED_CLASSES)})")
