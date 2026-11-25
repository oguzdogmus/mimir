#!/usr/bin/env python3
"""Mimir visual builder: Skald pages, safe SVG files and the browser open.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``verify.py`` (same folder). Run as::

    python3 visual.py <inputs|page|svg|open>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Every subcommand needs a workspace at
the learning root (see ``workspace.py``) and an existing course folder; the
term and course folders and the course ``.state/`` must not be symlinks.

No builder draws without its field's guidance: ``inputs``, ``page`` and
``svg`` refuse a course that uses no field pack (``fieldpack.py``), right
after the course folder is found and before anything is checked or written,
with "field pack missing for course <term>/<course>: run field research for
its field first, then build again". A linked pack that is missing or damaged
is refused too. ``open`` only opens a file already built.

This script is the command line and owns the contract below; the work is
split by job into sibling modules: ``visual_check.py`` (the SVG and page body
allowlist checkers), ``visual_labels.py`` (the label overlap check),
``visual_machine.py`` (the simulator's machine), ``visual_render.py`` (the
page file, the Skald tokens and the assets), ``visual_base.py`` (base figures:
stable part ids and their reuse) and ``visual_open.py`` (the browser open). The limits named below live with the module that applies them.

This script is the trust boundary for generated pages: the model supplies
content, this script escapes it, checks it and places the file. Output goes
only to ``<course>/.state/out/<name>.<ext>``: ``out/`` is created when
missing, neither ``out/`` nor the target may be a symlink, and the file is
written atomically (a rebuild replaces it). ``name`` matches
``[a-z0-9]+(-[a-z0-9]+)*``, at most NAME_MAX_CHARS (60) characters. Errors
name the field, e.g. ``body.original[2].page`` (lists are numbered from 1).

inputs -- what the builder reads beside the core house style guide.
    in : {"term": "2026-Fall", "course": "CS201 Theory"}
    out: {"course_dir": "/home/u/learning/2026-Fall/CS201 Theory",
          "packs": [{"field": "theory-of-computation", "title": "Theory of
          computation", "path": "/home/u/learning/.state/field-packs/
          theory-of-computation/pack.json"}],
          "notation": "- Writes the transition function as delta(q, a) ...",
          "line": "CS201 Theory: field pack theory-of-computation; notation
          section included."}
    ``packs`` are the course's field packs in link order, each checked as
    ``fieldpack.py`` checks it on save. ``notation`` is the ``## Notation``
    section of the course's ``.state/fingerprint.md``, or "" when there is
    none ("no notation section." in ``line``). Writes nothing.
    With ``subject`` (optional, a base figure subject as ``fieldpack.py``
    names it), ``base`` is the base figure the course builds that subject
    from, ``{"subject", "status", "source", "field", "path", "parts"}``
    exactly as ``fieldpack.py find-base`` reports it (the course's own
    first; ``status`` "missing" when it has none yet); ``line`` ends "; base
    figure <subject> from the field pack <field>." (or "the course's own
    diagram", or "; no base figure <subject> yet.").

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
    other than ``url(#...)``, ``@import``, another CSS function that loads
    something (``image(``, ``image-set(``, ``cross-fade(``, ``element(``,
    ``src(``, ``paint(``) or a backslash; ``<`` or ``&`` in ``<style>`` text;
    ``<style>`` text naming the shell's ``mimir-``/``sk-`` ids or classes
    (it could restyle or hide the controls); an outermost inline ``svg`` whose
    first two children are not a non-empty ``title`` then ``desc``, unless it
    has ``aria-hidden="true"``; elements inside an SVG ``title`` or ``desc``;
    a repeated id or one starting with ``mimir-`` or ``sk-``; a malformed or
    repeated attribute name; an end tag that does not close the open
    element, or an element left open; a body that ends inside an unfinished
    tag, comment or declaration; declarations, CDATA sections and
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
    animation. It also shows the shell's mascot (``assets/skald/mascot.svg``,
    inlined after ``<main>``, decorative and hidden in print and with
    JavaScript off) at the bottom right, his mood following the steps:
    curious before step 1, proud on the last, explaining, thinking,
    surprised and pleased in turn between. Without step markup the page
    carries no step script and no mascot.
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
    MACHINE_MAX_STACK symbols); other kinds refuse those fields. dfa and tree
    allow at most one move per (state, symbol). A tree's root has no incoming
    edge, every other node exactly one, and every node is reachable from the
    root. Limits: MACHINE_MAX_STATES (60) states with names of at most
    STATE_NAME_MAX_CHARS (20), MACHINE_MAX_TRANSITIONS (400) moves.
    ``example`` (optional) is the input the simulator starts with: at most
    MACHINE_MAX_SYMBOLS (64) symbols (spaces ignored) and EXAMPLE_MAX_CHARS
    (4000) characters. The body needs an element ``id="state-<i>"`` inside an inline SVG for
    each state i (counting from 1). After the body the shell adds the
    simulator controls (``#mimir-sim``) and the machine as a table, the
    machine as JSON data and the simulator scripts (allowed by hash); current
    states get ``data-highlight-on`` (the teaching highlight), and the arrow
    keys act only while focus is in the simulator. The page simulates sets of
    configurations with ε-closure, at most MACHINE_MAX_CONFIGS (256) at once
    and a PDA stack of at most MACHINE_MAX_STACK, saying "Search limit reached"
    when it cuts; it accepts by final state after the whole input. A live
    region and an ordered history say each step in words, ending Accepted,
    Rejected or Stuck. The body's ``<style>`` is
    not scoped, since the builder writes the whole page. ``example`` without
    ``machine`` is refused; a page without ``machine`` has no simulator.
    Every ``<svg>`` in the body passes the label check of ``svg`` (errors name
    ``svg k`` when the body holds more than one), with the page's ``<style>``
    rules and a 17 px inherited font size.

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
    other than ``url(#...)``; ``@import`` or another CSS function that loads
    something (``image(``, ``image-set(``, ``src(``, ...); a backslash in an
    attribute value or ``style`` text (CSS escapes would hide the checks).
    The document is written as given, with one ``<style>`` added as the root's
    last child: the Skald tokens, fonts inlined, in a CDATA section.
    Labels are checked too (as in every SVG of a ``page``): a ``<text>`` whose
    estimated box touches a stroked line, polyline, polygon, path, rect,
    circle or ellipse, or leaves the viewBox, is refused with the label, its
    position and what it touched. The box comes from the text's position,
    anchor, font size and character count (LABEL_WIDTH_FACTOR em a character,
    LABEL_ASCENT and LABEL_DESCENT em around the baseline, LABEL_MARGIN units
    of clearance), through every transform; font sizes and strokes follow the
    Skald tokens and the figure's CSS (type, class and id selectors), once
    without and once with its ``@media`` rules (the phone sizes).

Base figures (``page`` and ``svg``)
    With ``base`` (optional, a subject), the build starts from the subject's
    base figure, the one ``inputs`` names for the course, and must keep it
    exactly. The check fails closed (``visual_base``): it lists what may
    change and what may be added, and refuses everything else.
    - The SVG that holds its parts (for ``page``, the first outermost inline
      ``<svg>`` with one of its part ids) has the base figure's viewBox and
      ``<svg>`` attributes; it may gain an id, aria-* and a style attribute
      of FRAME_PROPERTIES only.
    - Every part, by id, keeps its tag, every attribute and everything inside
      it; only class, ``data-step`` and ``data-highlight``
      (``visual_base.PART_MAY_CHANGE``) may change, and a new class is one
      of ink, ink-fill, soft, soft-fill, curve, ghost or wash
      (``PART_CLASSES``). A group round a part keeps every attribute but
      those, so a step group ``<g data-step="N">`` is fine and a transform,
      opacity, clip or mask round a part is refused.
    - Definitions outside the parts (defs, markers, clip paths, masks,
      gradients) stay exactly as the base figure has them, and so does its
      own ``<style>``: none is added, dropped or changed.
    - Outside the parts, the build may add labels (``<text>``), groups that
      carry only class, id, ``data-step``, ``data-highlight`` and aria-*, and
      shapes of exactly one class (``ADDED_CLASSES``), with only their own
      geometry and those attributes, never a fill or a style: a leader is an
      open stroke (a ``<path>`` without Z, a ``<line>`` or a ``<polyline>``;
      a content arrow is a leader whose head is part of the stroke), an
      anchor a ``<circle>`` of radius at most ANCHOR_MAX_SHARE (1%) of the
      viewBox's larger side, a highlight mark (mark-loop, mark-swipe) a
      ``<path>`` with ``data-highlight``.
    - CSS: every ``<style>`` rule but the base figure's own selects only by
      type, class and id with descendant or child combinators (no
      pseudo-class, attribute or sibling selector, no nested rule), reaches
      no part or shape of the figure (labels are fine), and sets on the
      figure's ``<svg>`` and the elements round it only FRAME_PROPERTIES
      (layout and type). An element round the figure carries no ``hidden``,
      no Skald class but board, work-first, step and body, and a style
      attribute of FRAME_PROPERTIES only.
    Anything else, or a subject with no base figure, exits 2 with ``base:
    ...`` and nothing is written.

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

import os
import re
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import fieldpack
import ingest
import verify
import visual_base
import visual_check
import visual_labels
import visual_machine
import visual_open
import visual_render
import workspace
from workspace import InputError, check_keys, has_control, parse_segment, parse_term, short

NAME_MAX_CHARS = 60
TITLE_MAX_CHARS = 120
SVG_MAX_BYTES = 1024 * 1024
PAGE_BODY_MAX_BYTES = 1024 * 1024

_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_FILE = re.compile(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.(html|svg)")
_ALLOWED_CONTROL = {"\t", "\n", "\r"}


# --- Shared ------------------------------------------------------------------------

def _name(data: dict) -> str:
    value = data.get("name")
    if not isinstance(value, str) or not value:
        raise InputError("name is required (lowercase letters, digits and single hyphens)")
    if len(value) > NAME_MAX_CHARS or not _NAME.fullmatch(value):
        raise InputError(f"name must match [a-z0-9]+(-[a-z0-9]+)* and be at most {NAME_MAX_CHARS} "
                         f"characters: {short(value)}")
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


def _markup_field(value, field: str, what: str, max_bytes: int) -> bytes:
    """A builder-written markup field (``svg``, ``body``) as UTF-8: non-empty, no control characters, not too big."""
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} is required ({what})")
    if any(c not in _ALLOWED_CONTROL and unicodedata.category(c) in ("Cc", "Cs") for c in value):
        raise InputError(f"{field} contains control characters or lone surrogates")
    raw = value.encode("utf-8")
    if len(raw) > max_bytes:
        raise InputError(f"{field} is {len(raw)} bytes; at most {max_bytes}")
    return raw


def _course_with_pack(term: str, course: str) -> tuple[Path, list[dict]]:
    """The course folder and the field packs it uses; a course with no linked pack is refused."""
    course_dir = verify._course_dir(term, course)
    packs = fieldpack.course_packs(ingest._workspace_root(), course_dir)
    if not packs:
        raise InputError(f"field pack missing for course {term}/{course}: run field research for its field "
                         "first, then build again")
    return course_dir, packs


# --- inputs --------------------------------------------------------------------------

def cmd_inputs(data: dict) -> dict:
    check_keys(data, {"term", "course", "subject"})
    term, course = parse_term(data), parse_segment(data, "course")
    subject = fieldpack.parse_subject(data) if "subject" in data else None
    course_dir, packs = _course_with_pack(term, course)
    notation = verify._notation(course_dir)
    fields = ", ".join(p["field"] for p in packs)
    line = (f"{course}: field pack{'s' if len(packs) > 1 else ''} {fields}; "
            f"{'notation section included' if notation else 'no notation section'}")
    out = {"course_dir": str(course_dir), "packs": packs, "notation": notation}
    if subject is not None:
        out["base"] = fieldpack.lookup_base(ingest._workspace_root(), course_dir, subject)
        line += (f"; no base figure {subject} yet" if out["base"]["status"] == "missing"
                 else f"; base figure {subject} from {fieldpack.base_origin(out['base'])}")
    return {**out, "line": line + "."}


def _check_base(data: dict, course_dir: Path, course: str, figures) -> None:
    """With ``base``: refuse a build that does not keep the subject's base figure exactly (``visual_base``)."""
    if "base" not in data:
        return
    subject = fieldpack.parse_subject(data, "base")
    found = fieldpack.find_base(ingest._workspace_root(), course_dir, subject)
    if found is None:
        raise InputError(f"base: no base figure {subject} for {course}; build without base")
    base = visual_labels._tree_from_svg(_checked_svg(found["svg"]))
    visual_base.check_reuse(base, figures(), "base")


# --- svg ---------------------------------------------------------------------------

def _checked_svg(svg) -> ET.Element:
    """The root of ``svg`` after every check of ``visual.py svg``."""
    root = visual_check.check_svg(_markup_field(svg, "svg", "the SVG document as a string", SVG_MAX_BYTES))
    visual_labels.check_svg_labels(root)
    return root


def build_svg(svg) -> str:
    """The standalone SVG file for ``svg``: every check of ``visual.py svg``, then the Skald tokens added."""
    _checked_svg(svg)
    return visual_render.svg_with_tokens(svg)


def base_parts(svg) -> dict[str, tuple]:
    """A base figure's parts: every check of ``visual.py svg``, then the stable part ids (``visual_base``)."""
    return visual_base.parts(visual_labels._tree_from_svg(_checked_svg(svg)), "svg")


def cmd_svg(data: dict) -> dict:
    check_keys(data, {"term", "course", "name", "svg", "base"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    course_dir, _ = _course_with_pack(term, course)
    svg = data.get("svg")
    root = _checked_svg(svg)
    _check_base(data, course_dir, course, lambda: [visual_labels._tree_from_svg(root)])
    return _write_out(course_dir, name, "svg", visual_render.svg_with_tokens(svg).encode("utf-8"))


# --- page ----------------------------------------------------------------------------

def cmd_page(data: dict) -> dict:
    check_keys(data, {"term", "course", "name", "title", "body", "machine", "example", "base"})
    term, course, name = parse_term(data), parse_segment(data, "course"), _name(data)
    if "title" not in data:
        raise InputError("title is required")
    title = verify._text(data["title"], "title", TITLE_MAX_CHARS)
    machine = visual_machine.parse_machine(data["machine"]) if "machine" in data else None
    if machine is None and "example" in data:
        raise InputError("example is only for a page with a machine")
    example = visual_machine.parse_example(data)
    body = data.get("body")
    _markup_field(body, "body", "the page body as an HTML string", PAGE_BODY_MAX_BYTES)
    course_dir, _ = _course_with_pack(term, course)
    index = course_dir / "INDEX.md"
    rows = {p: r for p, r in ingest.registry(index).items() if verify._inside(course_dir, p)}
    body_html, math, steps = visual_check.check_page_body(
        body, lambda marker, k: visual_render.original_html(marker, f"body.original[{k}]", rows, course_dir, index),
        machine["states"] if machine else ())
    visual_labels.check_body_labels(body_html)
    _check_base(data, course_dir, course, lambda: visual_labels.body_figures(body_html))
    page = visual_render.render_page(title, body_html, math, steps, machine, example,
                                     workspace.read_motion(ingest._workspace_root()))
    return _write_out(course_dir, name, "html", page.encode("utf-8"))


# --- open --------------------------------------------------------------------------

def cmd_open(data: dict) -> dict:
    check_keys(data, {"term", "course", "file"})
    term, course = parse_term(data), parse_segment(data, "course")
    value = data.get("file")
    if not isinstance(value, str) or not value:
        raise InputError("file is required (<name>.html or <name>.svg)")
    if has_control(value) or not _FILE.fullmatch(value) or len(value.rsplit(".", 1)[0]) > NAME_MAX_CHARS:
        raise InputError(f"file must be <name>.html or <name>.svg with a valid name: {short(value)}")
    course_dir = verify._course_dir(term, course)
    out = _out_dir(course_dir, create=False)
    path = out / value
    if path.is_symlink() or not path.is_file():
        raise InputError(f"file: {path} is not an existing file in {out}")
    opened = visual_open.open_in_browser(path)
    line = f"Opened `{path}` in your browser." if opened else f"Open `{path}` in your browser."
    return {"path": str(path), "opened": opened, "line": line}


COMMANDS = {
    "inputs": (cmd_inputs, "name the course's field packs and notation section; refuses a course with no pack"),
    "page": (cmd_page, "build an offline Skald page from a checked page body in <course>/.state/out/"),
    "svg": (cmd_svg, "check an SVG document and write it to <course>/.state/out/"),
    "open": (cmd_open, "open a built file in the default browser"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("visual.py",
                             ("Mimir visual builder. Subcommands: inputs, page, svg, open. Reads one JSON object on "
                              "stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
