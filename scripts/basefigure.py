#!/usr/bin/env python3
"""Mimir base figure store: save, check and find base figures by subject.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``fieldpack.py`` (same folder). Run as::

    python3 basefigure.py <save|save-course|find>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Every subcommand needs a
workspace at the learning root (see ``workspace.py``). On any error nothing
is written.

A base figure is one recurring subject of a field (a heart, a truss, a
neuron) drawn once, checked and saved as an SVG with stable part ids, so later
visuals of that subject start from it (``visual.py`` ``base``). A field
pack's base figures sit in its pack folder (``fieldpack.py``), and a course
may hold its own, from the professor's diagrams, that never leave the course
folder::

    <root>/.state/field-packs/<field>/base-figures/<subject>.svg
    <root>/<YYYY-Term>/<course>/.state/base-figures/<subject>.svg

The ``base-figures`` folder and a base figure may not be symlinks, nor may
anything ``fieldpack.py`` refuses as one. ``subject`` is named like a field,
at most SUBJECT_MAX_CHARS characters ("human-heart"). A base figure passes
every check of ``visual.py svg`` and the part check (``visual_base``): every
id is a stable part id (lowercase letters and digits joined by single
hyphens, starting with a letter, used once, not ``mimir-``/``sk-``), every
drawn shape (path, rect, circle, ellipse, line, polyline, polygon; not inside
defs, markers, clips or text) has one or sits in a group that has one, there
is at least one part, and there is no ``<use>``, so a reuse cannot change a
part by changing what it points at. A stored base figure is checked again
every time it is read; a damaged one exits 2 naming its file. A subject is
saved once per place: saving it again exits 2.

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
save -- save a base figure the figure checker passed to its field pack.
    in : {"field": "medicine", "subject": "human-heart", "figure":
          "anatomical section", "path": "/home/u/learning/2026-Fall/MED101
          Physiology/.state/out/base-human-heart.svg", "reply": "1 | pass |
          ...\\noverall | pass | ..."}
    out: {"field": "medicine", "subject": "human-heart", "path": "/home/u/
          learning/.state/field-packs/medicine/base-figures/human-heart.svg",
          "parts": ["aorta", "right-atrium", ...], "line": "Base figure saved:
          human-heart in the field pack medicine, 14 parts."}
    ``path`` is the candidate as ``visual.py svg`` built it (with today's
    Skald tokens, which are taken off again, so the stored file is the figure
    itself). ``reply`` is the figure checker's reply on that file, read as
    ``figurecheck.py read`` reads it for ``figure``; anything but an overall
    pass exits 2 and saves nothing, so the next need of the subject tries
    again.

save-course -- save a professor's diagram as one course's own base figure.
    in : {"term": "2026-Fall", "course": "MED101 Physiology", "subject":
          "human-heart", "path": "/home/u/learning/2026-Fall/MED101
          Physiology/slides/heart.svg"}
    out: {"course_dir": "...", "subject": "human-heart", "path": "/home/u/
          learning/2026-Fall/MED101 Physiology/.state/base-figures/human-heart.
          svg", "parts": [...], "line": "Base figure saved: human-heart for
          MED101 Physiology only, from the professor's diagram, 14 parts."}
    ``path`` is an ``.svg`` file inside the course folder; anything outside
    it exits 2. No checklist applies: the professor wins. The diagram is
    copied only within the course folder, never into the pack store.

find -- the base figure a course builds a subject from.
    in : {"term": "2026-Fall", "course": "MED101 Physiology", "subject":
          "human-heart"}
    out: {"course_dir": "...", "subject": "human-heart", "status": "found",
          "source": "pack", "field": "medicine", "path": "...", "parts":
          [...], "line": "Base figure human-heart for MED101 Physiology: the
          field pack medicine, 14 parts."}
    The course's own base figure comes first (``source`` "course", ``field``
    null), then the course's field packs in link order. With none, ``status``
    is "missing", ``source``, ``field`` and ``path`` are null and ``parts``
    is []. ``visual.py inputs`` reports the same lookup (``lookup``).

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``basefigure.py: <message>``) and
nothing on stdout. An unexpected internal error exits 1 with ``basefigure.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import fieldpack
import figurecheck
import ingest
import visual_base
import visual_render
import workspace
from workspace import InputError, check_keys, refuse_symlinks, short

BASE_DIR = "base-figures"
SUBJECT_MAX_CHARS = 40


def parse_subject(data: dict, key: str = "subject") -> str:
    return fieldpack.parse_name(data, key, SUBJECT_MAX_CHARS, "a recurring subject", "human-heart")


def _base_file(folder: Path, subject: str) -> Path:
    """``<folder>/<subject>.svg``; refuses a symlinked folder or file."""
    path = folder / f"{subject}.svg"
    refuse_symlinks(folder, path)
    return path


def pack_base_path(root: Path, field: str, subject: str) -> Path:
    """``<store>/<field>/base-figures/<subject>.svg``, beside the pack's ``pack.json``."""
    return _base_file(fieldpack.pack_path(root, field).parent / BASE_DIR, subject)


def course_base_path(course_dir: Path, subject: str) -> Path:
    """``<course>/.state/base-figures/<subject>.svg``: a professor's diagram, local to that course."""
    return _base_file(course_dir / ".state" / BASE_DIR, subject)


def _svg_file(data: dict) -> tuple[Path, str]:
    """The absolute ``path`` of an existing ``.svg`` file, not a symlink, and its text."""
    value = data.get("path")
    if not isinstance(value, str) or not value:
        raise InputError("path is required (the absolute path of an .svg file)")
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() != ".svg":
        raise InputError(f"path must be the absolute path of an .svg file: {short(value)}")
    refuse_symlinks(path, field="path")
    text = ingest.read_text(path)
    if text is None:
        raise InputError(f"path {path} is not a file")
    return path, text


def _base_parts(svg: str, where: str) -> list[str]:
    """The part ids of a base figure after every shell check (``visual_base.base_parts``)."""
    try:
        return list(visual_base.base_parts(svg))
    except InputError as exc:
        raise InputError(f"{where}: {exc}") from None


def _stored_base(path: Path) -> tuple[str, list[str]]:
    """A stored base figure and its part ids, checked again as on save; a damaged one is refused."""
    svg = ingest.read_text(path)
    try:
        if svg is None:
            raise InputError("it cannot be read")
        ids = _base_parts(svg, "it")
    except InputError as exc:
        raise InputError(f"base figure {path} is damaged ({exc}); fix or remove it") from None
    return svg, ids


def find(root: Path, course_dir: Path, subject: str) -> dict | None:
    """The base figure a course builds ``subject`` from, or None.

    The course's own (a professor's diagram) comes first, then the course's field packs in link order.
    ``{"source": "course" | "pack", "field": <pack field or None>, "path", "svg", "parts"}``.
    """
    places = [("course", None, course_base_path(course_dir, subject))]
    places += [("pack", p["field"], pack_base_path(root, p["field"], subject))
               for p in fieldpack.course_packs(root, course_dir)]
    for source, field, path in places:
        if path.exists():
            svg, ids = _stored_base(path)
            return {"source": source, "field": field, "path": str(path), "svg": svg, "parts": ids}
    return None


def lookup(root: Path, course_dir: Path, subject: str) -> dict:
    """The base figure lookup as ``find`` and ``visual.py inputs`` report it.

    ``{"subject", "status": "found" | "missing", "source", "field", "path", "parts"}``; with none, ``source``,
    ``field`` and ``path`` are None and ``parts`` is [].
    """
    base = find(root, course_dir, subject)
    if base is None:
        return {"subject": subject, "status": "missing", "source": None, "field": None, "path": None, "parts": []}
    return {"subject": subject, "status": "found", **{k: base[k] for k in ("source", "field", "path", "parts")}}


def origin(found: dict) -> str:
    """Where a found base figure comes from, for a ``line``: the course's own diagram or a field pack."""
    return "the course's own diagram" if found["source"] == "course" else f"the field pack {found['field']}"


# --- commands -------------------------------------------------------------------------

def cmd_save(data: dict) -> dict:
    check_keys(data, {"field", "subject", "figure", "path", "reply"})
    field, subject = fieldpack.parse_field(data), parse_subject(data)
    root = ingest._workspace_root()
    fieldpack.load_pack(root, field)
    path, text = _svg_file(data)
    svg = visual_render.svg_without_tokens(text)
    if svg is None:
        raise InputError(f"path {path} is not an SVG built by visual.py svg; build the base figure through the "
                         "shell first")
    ids = _base_parts(svg, f"base figure {path}")
    verdict = figurecheck.cmd_read({k: data.get(k) for k in ("field", "figure", "reply")})
    if verdict["overall"] != "pass":
        raise InputError(f"reply: {verdict['line'][:-1]}; the base figure {subject} is not saved")
    target = pack_base_path(root, field, subject)
    if target.exists():
        raise InputError(f"field pack {field} already has a base figure {subject} at {target}; reuse it")
    fieldpack.write_creating(target, svg, (target.parent,))
    return {"field": field, "subject": subject, "path": str(target), "parts": ids,
            "line": f"Base figure saved: {subject} in the field pack {field}, {len(ids)} parts."}


def cmd_save_course(data: dict) -> dict:
    check_keys(data, {"term", "course", "subject", "path"})
    subject = parse_subject(data)
    c = fieldpack.course_from(data)
    path, text = _svg_file(data)
    if not path.resolve().is_relative_to(c.course_dir.resolve()):
        raise InputError(f"path {path} must be inside the course folder {c.course_dir}: a professor's diagram "
                         "stays in its course")
    svg = visual_render.svg_without_tokens(text) or text
    ids = _base_parts(svg, f"diagram {path}")
    target = course_base_path(c.course_dir, subject)
    if target.exists():
        raise InputError(f"{c.name} already has its own base figure {subject} at {target}; remove it first to "
                         "replace it")
    workspace.build_course(c.root, c.term, c.name, [])  # restores a missing .state/
    fieldpack.write_creating(target, svg, (target.parent,))
    return {"course_dir": str(c.course_dir), "subject": subject, "path": str(target), "parts": ids,
            "line": f"Base figure saved: {subject} for {c.name} only, from the professor's diagram, "
                    f"{len(ids)} parts."}


def cmd_find(data: dict) -> dict:
    check_keys(data, {"term", "course", "subject"})
    subject = parse_subject(data)
    c = fieldpack.course_from(data)
    found = lookup(c.root, c.course_dir, subject)
    if found["status"] == "missing":
        line = f"No base figure {subject} for {c.name} yet; it grows on first use."
    else:
        line = f"Base figure {subject} for {c.name}: {origin(found)}, {len(found['parts'])} parts."
    return {"course_dir": str(c.course_dir), **found, "line": line}


COMMANDS = {
    "save": (cmd_save, "save a base figure the figure checker passed to its field pack"),
    "save-course": (cmd_save_course, "save a professor's diagram as one course's own base figure"),
    "find": (cmd_find, "the base figure a course builds a subject from: its own first, then its packs'"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("basefigure.py",
                             ("Mimir base figure store. Subcommands: save, save-course, find. Reads one JSON object "
                              "on stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
