#!/usr/bin/env python3
"""Mimir field pack store: save, check and list field packs, link courses to them.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py`` and ``ingest.py`` (same folder). Run as::

    python3 fieldpack.py <save|list|link|match|report|save-base|save-course-base|find-base>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Every subcommand needs a
workspace at the learning root (see ``workspace.py``). On any error nothing
is written. This script researches nothing: it is the store research and the
visual shell build on, and it refuses a bad pack.

Store
-----
One pack per field, shared by all of the student's courses in that field,
and one link record per course::

    <root>/.state/field-packs/<field>/pack.json
    <root>/<YYYY-Term>/<course>/.state/field-packs.json   {"packs": [...]}

The pack folder is the pack's home: its base figures sit beside ``pack.json``,
and a course may hold its own, from the professor's diagrams, that never leave
the course folder::

    <root>/.state/field-packs/<field>/base-figures/<subject>.svg
    <root>/<YYYY-Term>/<course>/.state/base-figures/<subject>.svg

``.state``, the store, a pack folder, ``pack.json``
and a link record may not be symlinks; neither may the term, course or course
``.state`` folder (``workspace.course_folder``). A stored pack is checked
again, exactly as on save, every time it is read; a damaged pack or link
record exits 2 naming its file.

Pack
----
``field`` is the stable field name: lowercase letters and digits joined by
single hyphens, at most FIELD_MAX_CHARS characters ("medicine",
"civil-engineering"). Text values are one line without control characters,
at most TEXT_MAX_CHARS characters, stored stripped::

    {"field": "medicine", "title": "Medicine",
     "figure_kinds": [{"name": "anatomical section", "kind": "depiction"}],
     "conventions": [{"rule": "...", "source": "..."}],
     "recipes": [{"figure": "anatomical section", "rule": "...",
                  "source": "..."}],
     "checklists": [{"figure": "anatomical section",
                     "rules": [{"rule": "...", "source": "..."}]}],
     "test_page": {"figure": "anatomical section", "content": "..."}}

* ``figure_kinds``: at least one; names distinct ignoring case; ``kind`` is
  one of FIGURE_KINDS, the four figure kinds of the house style.
* ``conventions`` and ``recipes`` may be empty; every rule has a ``source``.
  A recipe's ``figure`` names one of the pack's figure kinds.
* ``checklists``: exactly one accuracy checklist per figure kind, each with
  at least one sourced rule.
* ``test_page``: the fixed synthetic content of the pack's blind test page,
  for one of its figure kinds; ``content`` may span lines, at most
  CONTENT_MAX_CHARS characters.
* The stored file (indented JSON) is at most MAX_PACK_CHARS characters, so
  every builder can read the pack in full beside the core guide.

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
save -- check one field pack and write it once.
    in : the pack (see ``Pack``)
    out: {"field": "medicine", "title": "Medicine", "path": "/home/u/
          learning/.state/field-packs/medicine/pack.json", "line": "Field
          pack saved: Medicine (medicine)."}
    A field that already has a pack folder exits 2: a pack is written once
    per field and reused. The pack is checked before anything is created.

list -- the packs already in the workspace, sorted by field.
    in : {}
    out: {"packs": [{"field": "medicine", "title": "Medicine", "path":
          "...", "figure_kinds": ["anatomical section", "ECG trace"]}],
          "line": "1 field pack: medicine."}
    Names starting with ``.`` and ``__MACOSX`` are skipped; any other store entry that is not
    a folder named as a field exits 2.

link -- record that a course uses a field pack.
    in : {"term": "2026-Fall", "course": "MED101 Physiology",
          "field": "medicine"}
    out: {"course_dir": "...", "path": "/home/u/learning/2026-Fall/MED101
          Physiology/.state/field-packs.json", "field": "medicine",
          "packs": ["medicine"], "added": true, "line": "MED101 Physiology
          now uses the field pack medicine."}
    The pack must exist and the course folder too. A course uses at most
    MAX_LINKS packs, in link order; linking a pack it already uses changes
    nothing (``added`` false).

match -- link a course to the pack of its field, or name the research it needs.
    in : {"term": "2026-Fall", "course": "ANAT101 Human Anatomy",
          "field": "human-anatomy", "topics": ["Cardiac cycle"]}
    out: {"course_dir": "...", "path": "...", "field": "human-anatomy",
          "packs": [], "added": false, "status": "research", "brief":
          {"field": "human-anatomy", "topics": ["Cardiac cycle"]}, "line":
          "No field pack human-anatomy yet; researching it in the
          background."}
    When the field already has a pack, ``match`` links it exactly as
    ``link`` does and returns ``status`` "linked" with no ``brief``. With
    no pack it writes nothing and returns ``status`` "research" and the
    ``brief``: the field researcher's whole input, built only from the field
    name and the topic names, so no course text, name or path reaches it.
    ``topics`` (optional, default []) holds at most MAX_TOPICS public topic
    names, one line each, at most ``ingest.TOPIC_MAX_CHARS`` characters,
    stored stripped. A course that already uses MAX_LINKS packs exits 2.
    Matching again after the research saved the pack links the course.

report -- the field packs one course uses.
    in : {"term": "2026-Fall", "course": "MED101 Physiology"}
    out: {"course_dir": "...", "status": "linked", "packs": [{"field":
          "medicine", "title": "Medicine", "path": "..."}], "line":
          "MED101 Physiology uses the field pack medicine."}
    A course with no link record (or an empty one) exits 0 with ``status``
    "none", ``packs`` [] and the line "<course> has no field pack yet.". A
    linked pack that is missing or damaged exits 2.

Base figures
------------
A base figure is one recurring subject of a field (a heart, a truss, a
neuron) drawn once, checked and saved as an SVG with stable part ids, so later
visuals of that subject start from it (``visual.py`` ``base``). ``subject``
is named like a field, at most SUBJECT_MAX_CHARS characters ("human-heart").
A base figure passes every check of ``visual.py svg`` and the part check: every
id is a stable part id (lowercase letters and digits joined by single hyphens,
starting with a letter, used once, not ``mimir-``/``sk-``), every drawn shape
(path, rect, circle, ellipse, line, polyline, polygon; not inside defs,
markers, clips or text) has one or sits in a group that has one, there is at
least one part, and there is no ``<use>``, so a reuse cannot change a part by
changing what it points at. A stored base figure is checked again every time it is
read; a damaged one exits 2 naming its file. A subject is saved once per
place: saving it again exits 2.

save-base -- save a base figure the figure checker passed to its field pack.
    in : {"field": "medicine", "subject": "human-heart", "figure":
          "anatomical section", "path": "/home/u/learning/2026-Fall/MED101
          Physiology/.state/out/base-human-heart.svg", "reply": "1 | pass |
          ...\noverall | pass | ..."}
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

save-course-base -- save a professor's diagram as one course's own base figure.
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

find-base -- the base figure a course builds a subject from.
    in : {"term": "2026-Fall", "course": "MED101 Physiology", "subject":
          "human-heart"}
    out: {"course_dir": "...", "subject": "human-heart", "status": "found",
          "source": "pack", "field": "medicine", "path": "...", "parts":
          [...], "line": "Base figure human-heart for MED101 Physiology: the
          field pack medicine, 14 parts."}
    The course's own base figure comes first (``source`` "course", ``field``
    null), then the course's field packs in link order. With none, ``status``
    is "missing", ``source``, ``field`` and ``path`` are null and ``parts``
    is [].

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``fieldpack.py: <message>``) and
nothing on stdout. An unexpected internal error exits 1 with ``fieldpack.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ingest
import visual_render
import workspace
from workspace import InputError, check_keys, has_control, parse_segment, parse_term, short

PACK_FILE = "pack.json"
LINK_FILE = "field-packs.json"
MAX_LINKS = 2
FIGURE_KINDS = ("depiction", "formal notation", "plot", "own sketch")
MAX_PACK_CHARS = 16000
FIELD_MAX_CHARS = 40
TEXT_MAX_CHARS = 300
CONTENT_MAX_CHARS = 2000
MAX_TOPICS = 20
BASE_DIR = "base-figures"
SUBJECT_MAX_CHARS = 40

_FIELD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def store_dir(root: Path) -> Path:
    """``<root>/.state/field-packs``; refuses a symlinked ``.state`` or store folder."""
    store = root / ".state" / "field-packs"
    for folder in (root / ".state", store):
        if folder.is_symlink():
            raise InputError(f"{folder} is a symlink; refusing to work through it")
    return store


def pack_path(root: Path, field: str) -> Path:
    """``<store>/<field>/pack.json``; refuses a symlinked pack folder or file."""
    folder = store_dir(root) / field
    path = folder / PACK_FILE
    for item in (folder, path):
        if item.is_symlink():
            raise InputError(f"{item} is a symlink; refusing to work through it")
    return path


def _dump(pack: dict) -> str:
    return json.dumps(pack, ensure_ascii=False, indent=1) + "\n"


# --- checks ---------------------------------------------------------------------------

def parse_field(data: dict, key: str = "field") -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise InputError(f"{key} is required (a field name such as civil-engineering)")
    if len(value) > FIELD_MAX_CHARS or not _FIELD.fullmatch(value):
        raise InputError(f"{key} must be lowercase letters and digits joined by single hyphens, at most "
                         f"{FIELD_MAX_CHARS} characters, e.g. civil-engineering: {short(value)}")
    return value


def _text(value, where: str, limit: int = TEXT_MAX_CHARS, lines: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where} is required (non-empty text)")
    if has_control(value.replace("\n", "") if lines else value):
        raise InputError(f"{where} must be {'text' if lines else 'one line'} without control characters")
    if len(value) > limit:
        raise InputError(f"{where} has {len(value)} characters, over the {limit}-character limit")
    return value.strip()


def _list(data: dict, key: str, required: bool) -> list:
    value = data.get(key)
    if not isinstance(value, list) or (required and not value):
        raise InputError(f"{key} is required (a list{' of at least one entry' if required else ''})")
    return value


def _object(value, where: str, keys: set[str]) -> dict:
    if not isinstance(value, dict):
        raise InputError(f"{where} must be an object")
    try:
        check_keys(value, keys)
    except InputError as exc:
        raise InputError(f"{where}: {exc}") from None
    return value


def _sourced(value, where: str, keys: set[str] = frozenset()) -> dict:
    entry = _object(value, where, {"rule", "source", *keys})
    return {"rule": _text(entry.get("rule"), f"{where}.rule"),
            "source": _text(entry.get("source"), f"{where}.source")}


def _figure(entry: dict, where: str, names: dict[str, str]) -> str:
    name = _text(entry.get("figure"), f"{where}.figure")
    if name.casefold() not in names:
        raise InputError(f"{where}.figure {short(name)} is not one of the pack's figure_kinds")
    return names[name.casefold()]


def check_pack(data: dict) -> dict:
    """The pack as it is stored; refuses anything the store does not know."""
    check_keys(data, {"field", "title", "figure_kinds", "conventions", "recipes", "checklists", "test_page"})
    field = parse_field(data)
    title = _text(data.get("title"), "title", FIELD_MAX_CHARS * 2)
    kinds, names = [], {}
    for n, value in enumerate(_list(data, "figure_kinds", True), 1):
        where = f"figure_kinds[{n}]"
        entry = _object(value, where, {"name", "kind"})
        name = _text(entry.get("name"), f"{where}.name", FIELD_MAX_CHARS * 2)
        if entry.get("kind") not in FIGURE_KINDS:
            raise InputError(f"{where}.kind must be one of {', '.join(FIGURE_KINDS)}: {short(entry.get('kind'))}")
        if name.casefold() in names:
            raise InputError(f"{where}.name {short(name)} repeats an earlier figure kind (names are distinct "
                             "ignoring case)")
        names[name.casefold()] = name
        kinds.append({"name": name, "kind": entry["kind"]})
    conventions = [_sourced(v, f"conventions[{n}]") for n, v in enumerate(_list(data, "conventions", False), 1)]
    recipes = []
    for n, value in enumerate(_list(data, "recipes", False), 1):
        where = f"recipes[{n}]"
        rule = _sourced(value, where, {"figure"})
        recipes.append({"figure": _figure(value, where, names), **rule})
    checklists, checked = [], set()
    for n, value in enumerate(_list(data, "checklists", True), 1):
        where = f"checklists[{n}]"
        entry = _object(value, where, {"figure", "rules"})
        figure = _figure(entry, where, names)
        if figure in checked:
            raise InputError(f"{where}.figure {short(figure)} already has a checklist")
        checked.add(figure)
        rules = entry.get("rules")
        if not isinstance(rules, list) or not rules:
            raise InputError(f"{where}.rules is required (a list of at least one rule)")
        checklists.append({"figure": figure,
                           "rules": [_sourced(v, f"{where}.rules[{m}]") for m, v in enumerate(rules, 1)]})
    for n, kind in enumerate(kinds, 1):
        if kind["name"] not in checked:
            raise InputError(f"figure_kinds[{n}] {short(kind['name'])} has no accuracy checklist")
    page = _object(data.get("test_page"), "test_page", {"figure", "content"})
    test_page = {"figure": _figure(page, "test_page", names),
                 "content": _text(page.get("content"), "test_page.content", CONTENT_MAX_CHARS, lines=True)}
    pack = {"field": field, "title": title, "figure_kinds": kinds, "conventions": conventions, "recipes": recipes,
            "checklists": checklists, "test_page": test_page}
    size = len(_dump(pack))
    if size > MAX_PACK_CHARS:
        raise InputError(f"the pack has {size} characters, over the {MAX_PACK_CHARS}-character cap; keep it "
                         "compact enough for every builder to read in full")
    return pack


def load_pack(root: Path, field: str) -> tuple[Path, dict]:
    """The stored pack of ``field``, checked again as on save; a missing or damaged pack is refused."""
    path = pack_path(root, field)
    text = ingest.read_text(path)
    if text is None:
        raise InputError(f"no field pack {short(field)}: {path} is missing")
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise InputError("it must hold one JSON object")
        pack = check_pack(data)
    except (ValueError, RecursionError, InputError) as exc:
        detail = exc if isinstance(exc, InputError) else "it is not valid JSON"
        raise InputError(f"field pack {path} is damaged ({detail}); fix or remove it") from None
    if pack["field"] != field:
        raise InputError(f"field pack {path} is damaged (its field {short(pack['field'])} does not match its "
                         "folder); fix or remove it")
    return path, pack


def stored_fields(root: Path) -> list[str]:
    """The field names of every pack folder in the store, sorted; a folder that is not a field name is refused."""
    store = store_dir(root)
    if not store.exists():
        return []
    fields = []
    for item in sorted(store.iterdir()):
        if ingest._ignored(item.name):
            continue
        if not item.is_dir() or item.is_symlink() or not _FIELD.fullmatch(item.name):
            raise InputError(f"{item} is not a field pack folder; remove it from {store}")
        fields.append(item.name)
    return fields


# --- save -----------------------------------------------------------------------------

def cmd_save(data: dict) -> dict:
    data = check_pack(data)
    root = ingest._workspace_root()
    field, title = data["field"], data["title"]
    path = pack_path(root, field)
    if path.parent.exists():
        raise InputError(f"field pack {short(field)} already exists at {path}; a pack is written once per field, "
                         "reuse it")
    created = [d for d in (path.parent.parent, path.parent) if not d.exists()]
    for folder in created:
        folder.mkdir()
    try:
        ingest._write_atomic(path, _dump(data))
    except BaseException:
        for folder in reversed(created):
            try:
                folder.rmdir()
            except OSError:
                pass  # the original failure is what gets reported
        raise
    return {"field": field, "title": title, "path": str(path), "line": f"Field pack saved: {title} ({field})."}


def cmd_list(data: dict) -> dict:
    check_keys(data, set())
    root = ingest._workspace_root()
    packs = []
    for field in stored_fields(root):
        path, p = load_pack(root, field)
        packs.append({"field": p["field"], "title": p["title"], "path": str(path),
                      "figure_kinds": [k["name"] for k in p["figure_kinds"]]})
    names = ", ".join(p["field"] for p in packs)
    line = f"{len(packs)} field pack{'' if len(packs) == 1 else 's'}: {names}." if packs else "No field packs yet."
    return {"packs": packs, "line": line}


# --- link -----------------------------------------------------------------------------

def _course(data: dict) -> tuple[Path, Path, Path, str, str]:
    term, course = parse_term(data), parse_segment(data, "course")
    root = ingest._workspace_root()
    course_dir = workspace.course_folder(root, term, course)
    if not course_dir.is_dir():
        raise InputError(f"no course folder at {course_dir}")
    return root, course_dir, link_record(course_dir), term, course


def link_record(course_dir: Path) -> Path:
    """``<course>/.state/field-packs.json``; refuses a symlinked record."""
    record = course_dir / ".state" / LINK_FILE
    if record.is_symlink():
        raise InputError(f"{record} is a symlink; refusing to work through it")
    return record


def linked_fields(record: Path) -> list[str]:
    """The fields a course's link record names, in link order; [] when the course has no record."""
    text = ingest.read_text(record)
    if text is None:
        return []
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or set(data) != {"packs"} or not isinstance(data["packs"], list):
            raise ValueError
        fields = [parse_field({"field": f}) for f in data["packs"]]
    except (ValueError, RecursionError, InputError):
        fields = None
    if fields is None or len(fields) > MAX_LINKS or len(set(fields)) != len(fields):
        raise InputError(f"{record} is damaged (it must hold {{\"packs\": [...]}} with at most {MAX_LINKS} "
                         "distinct field names); fix or remove it")
    return fields


def _check_room(course: str, fields: list[str]) -> None:
    if len(fields) >= MAX_LINKS:
        raise InputError(f"{course} already uses {len(fields)} field packs ({', '.join(fields)}); a course uses "
                         f"at most {MAX_LINKS}")


def cmd_link(data: dict) -> dict:
    check_keys(data, {"term", "course", "field"})
    field = parse_field(data)
    root, course_dir, record, term, course = _course(data)
    load_pack(root, field)
    fields = linked_fields(record)
    added = field not in fields
    if added:
        _check_room(course, fields)
    if added:
        fields.append(field)
        workspace.build_course(root, term, course, [])  # after every check: restores a missing .state/
        ingest._write_atomic(record, json.dumps({"packs": fields}, ensure_ascii=False) + "\n")
    line = (f"{course} now uses the field pack {field}." if added
            else f"{course} already uses the field pack {field}.")
    return {"course_dir": str(course_dir), "path": str(record), "field": field, "packs": fields, "added": added,
            "line": line}


# --- match ----------------------------------------------------------------------------

def _topics(data: dict) -> list[str]:
    value = data.get("topics", [])
    if not isinstance(value, list) or len(value) > MAX_TOPICS:
        raise InputError(f"topics must be a list of at most {MAX_TOPICS} topic names")
    return [_text(v, f"topics[{n}]", ingest.TOPIC_MAX_CHARS) for n, v in enumerate(value, 1)]


def cmd_match(data: dict) -> dict:
    check_keys(data, {"term", "course", "field", "topics"})
    field, topics = parse_field(data), _topics(data)
    root, course_dir, record, _, course = _course(data)
    if pack_path(root, field).parent.exists():
        out = cmd_link({k: data[k] for k in ("term", "course", "field")})
        return {**out, "status": "linked"}
    fields = linked_fields(record)
    _check_room(course, fields)
    return {"course_dir": str(course_dir), "path": str(record), "field": field, "packs": fields,
            "added": False, "status": "research", "brief": {"field": field, "topics": topics},
            "line": f"No field pack {field} yet; researching it in the background."}


# --- base figures ---------------------------------------------------------------------

def parse_subject(data: dict, key: str = "subject") -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise InputError(f"{key} is required (a recurring subject such as human-heart)")
    if len(value) > SUBJECT_MAX_CHARS or not _FIELD.fullmatch(value):
        raise InputError(f"{key} must be lowercase letters and digits joined by single hyphens, at most "
                         f"{SUBJECT_MAX_CHARS} characters, e.g. human-heart: {short(value)}")
    return value


def _base_file(folder: Path, subject: str) -> Path:
    """``<folder>/<subject>.svg``; refuses a symlinked folder or file."""
    path = folder / f"{subject}.svg"
    for item in (folder, path):
        if item.is_symlink():
            raise InputError(f"{item} is a symlink; refusing to work through it")
    return path


def pack_base_path(root: Path, field: str, subject: str) -> Path:
    """``<store>/<field>/base-figures/<subject>.svg``, beside the pack's ``pack.json``."""
    return _base_file(pack_path(root, field).parent / BASE_DIR, subject)


def _svg_file(data: dict) -> tuple[Path, str]:
    """The absolute ``path`` of an existing ``.svg`` file, not a symlink, and its text."""
    value = data.get("path")
    if not isinstance(value, str) or not value:
        raise InputError("path is required (the absolute path of an .svg file)")
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() != ".svg":
        raise InputError(f"path must be the absolute path of an .svg file: {short(value)}")
    if path.is_symlink():
        raise InputError(f"path {path} is a symlink; refusing to work through it")
    text = ingest.read_text(path)
    if text is None:
        raise InputError(f"path {path} is not a file")
    return path, text


def _base_parts(svg: str, where: str) -> list[str]:
    """The part ids of a base figure after every shell check (``visual.base_parts``)."""
    import visual  # here, not at the top: visual.py imports this module
    try:
        return list(visual.base_parts(svg))
    except InputError as exc:
        raise InputError(f"{where}: {exc}") from None


def _write_base(target: Path, svg: str) -> None:
    created = not target.parent.exists()
    if created:
        target.parent.mkdir()
    try:
        ingest._write_atomic(target, svg)
    except BaseException:
        if created:
            try:
                target.parent.rmdir()
            except OSError:
                pass  # the original failure is what gets reported
        raise


def cmd_save_base(data: dict) -> dict:
    import figurecheck  # here, not at the top: figurecheck.py imports this module
    check_keys(data, {"field", "subject", "figure", "path", "reply"})
    field, subject = parse_field(data), parse_subject(data)
    root = ingest._workspace_root()
    load_pack(root, field)
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
    _write_base(target, svg)
    return {"field": field, "subject": subject, "path": str(target), "parts": ids,
            "line": f"Base figure saved: {subject} in the field pack {field}, {len(ids)} parts."}


def course_base_path(course_dir: Path, subject: str) -> Path:
    """``<course>/.state/base-figures/<subject>.svg``: a professor's diagram, local to that course."""
    return _base_file(course_dir / ".state" / BASE_DIR, subject)


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


def find_base(root: Path, course_dir: Path, subject: str) -> dict | None:
    """The base figure a course builds ``subject`` from, or None.

    The course's own (a professor's diagram) comes first, then the course's field packs in link order.
    ``{"source": "course" | "pack", "field": <pack field or None>, "path", "svg", "parts"}``.
    """
    places = [("course", None, course_base_path(course_dir, subject))]
    places += [("pack", p["field"], pack_base_path(root, p["field"], subject)) for p in course_packs(root, course_dir)]
    for source, field, path in places:
        if path.exists():
            svg, ids = _stored_base(path)
            return {"source": source, "field": field, "path": str(path), "svg": svg, "parts": ids}
    return None


def cmd_find_base(data: dict) -> dict:
    check_keys(data, {"term", "course", "subject"})
    subject = parse_subject(data)
    root, course_dir, _, _, course = _course(data)
    base = find_base(root, course_dir, subject)
    if base is None:
        return {"course_dir": str(course_dir), "subject": subject, "status": "missing", "source": None,
                "field": None, "path": None, "parts": [],
                "line": f"No base figure {subject} for {course} yet; it grows on first use."}
    origin = "the course's own diagram" if base["source"] == "course" else f"the field pack {base['field']}"
    return {"course_dir": str(course_dir), "subject": subject, "status": "found",
            **{k: base[k] for k in ("source", "field", "path", "parts")},
            "line": f"Base figure {subject} for {course}: {origin}, {len(base['parts'])} parts."}


def cmd_save_course_base(data: dict) -> dict:
    check_keys(data, {"term", "course", "subject", "path"})
    subject = parse_subject(data)
    _, course_dir, _, term, course = _course(data)
    path, text = _svg_file(data)
    if not path.resolve().is_relative_to(course_dir.resolve()):
        raise InputError(f"path {path} must be inside the course folder {course_dir}: a professor's diagram "
                         "stays in its course")
    svg = visual_render.svg_without_tokens(text) or text
    ids = _base_parts(svg, f"diagram {path}")
    target = course_base_path(course_dir, subject)
    if target.exists():
        raise InputError(f"{course} already has its own base figure {subject} at {target}; remove it first to "
                         "replace it")
    workspace.build_course(ingest._workspace_root(), term, course, [])  # restores a missing .state/
    _write_base(target, svg)
    return {"course_dir": str(course_dir), "subject": subject, "path": str(target), "parts": ids,
            "line": f"Base figure saved: {subject} for {course} only, from the professor's diagram, "
                    f"{len(ids)} parts."}


# --- report ---------------------------------------------------------------------------

def course_packs(root: Path, course_dir: Path) -> list[dict]:
    """The packs a course uses, in link order, each checked as on save: ``{field, title, path}``.

    [] when the course has no link record; a damaged record or a missing or damaged pack is refused.
    """
    packs = []
    for field in linked_fields(link_record(course_dir)):
        path, p = load_pack(root, field)
        packs.append({"field": field, "title": p["title"], "path": str(path)})
    return packs


def cmd_report(data: dict) -> dict:
    check_keys(data, {"term", "course"})
    root, course_dir, _, _, course = _course(data)
    packs = course_packs(root, course_dir)
    if packs:
        line = f"{course} uses the field pack{'s' if len(packs) > 1 else ''} {', '.join(p['field'] for p in packs)}."
    else:
        line = f"{course} has no field pack yet."
    return {"course_dir": str(course_dir), "status": "linked" if packs else "none", "packs": packs, "line": line}


COMMANDS = {
    "save": (cmd_save, "check one field pack and write it once"),
    "list": (cmd_list, "list the field packs in the workspace"),
    "link": (cmd_link, "record that a course uses a field pack (at most two)"),
    "match": (cmd_match, "link a course to the pack of its field, or name the research it needs"),
    "report": (cmd_report, "the field packs one course uses"),
    "save-base": (cmd_save_base, "save a base figure the figure checker passed to its field pack"),
    "save-course-base": (cmd_save_course_base, "save a professor's diagram as one course's own base figure"),
    "find-base": (cmd_find_base, "the base figure a course builds a subject from: its own first, then its packs'"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("fieldpack.py",
                             ("Mimir field pack store. Subcommands: save, list, link, match, report, save-base, "
                              "save-course-base, find-base. Reads one JSON object on stdin and prints one JSON object "
                              "on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
