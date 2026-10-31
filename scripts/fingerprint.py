#!/usr/bin/env python3
"""Mimir professor fingerprint: render fingerprint.md, link a retaken course.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py`` and ``ingest.py`` (same folder). Run as::

    python3 fingerprint.py <write|retake>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Both subcommands need a
workspace at the learning root (see ``workspace.py``). The term and course
folders (and the course ``.state/``) must not be symlinks. On any error
nothing is written.

The model reads the papers and proposes entries; this script owns the trust
labels: ``(tentative)``, ``(prior term)``, the ``label:`` line and question
type frequencies are always computed from INDEX.md registries and are never
input. ``fingerprint.md`` is only ever changed through this script.

Sources
-------
Every entry and row has at least one source, each one of:
* a course-relative path with a registry row in this course's INDEX.md,
  e.g. ``past-papers/2024-final.pdf``;
* ``prior-term:<path>``: a path with a registry row in the prior course's
  INDEX.md; allowed only when this fingerprint's ``prior_term:`` line says
  ``same professor`` (assumed or not) and ``<course>/.state/prior-term`` is a
  symlink resolving to that prior course's ``.state/``;
* ``debrief YYYY-MM-DD``: what the student reported after an exam.

Computed markers: ``(tentative)`` when no source has ``text`` fidelity and
none is a debrief; ``(prior term)`` when every source is ``prior-term:``.
``label:`` is ``prior term (<prior term>)`` when any line carries ``(prior
term)``, else ``current term``. A question type's frequency is ``n of m
papers``: n = distinct sources of the row that are past papers (registry role
``past-papers``) or debriefs, m = the same count over all rows (``-`` when m
is 0).

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
write -- render the whole fingerprint.md from the complete content.
    in : {"term": "2027-Spring", "course": "CS201 Theory",
          "professor": "Dr. Ayse Kaya",
          "notation": [{"text": "Uses := for definitions",
                        "sources": ["past-papers/2024-final.pdf"]}],
          "phrasing": [], "disguises": [],
          "question_types": [{"type": "Pumping lemma proof", "marks": "20",
                              "sources": ["past-papers/2024-final.pdf",
                                          "debrief 2027-01-20"]}]}
    out: {"fingerprint": "/home/u/learning/2027-Spring/CS201 Theory/.state/
          fingerprint.md", "course_dir": "...", "lines": 19,
          "label": "current term", "entries": 2, "tentative": 0,
          "prior_term_entries": 0, "line": "Fingerprint saved: ... (19 of 60
          lines, 2 entries, 0 tentative)."}
    The four lists are optional (absent = empty); the file is rewritten from
    exactly what is sent, so send everything to keep. Entry ``{text,
    sources}``, row ``{type, sources, marks}`` (``marks`` may be empty).
    ``text``, ``type``, ``marks`` and ``professor`` are one line without
    control characters, at most ENTRY_MAX_CHARS characters; ``|`` is stored
    as ``\\|`` in table cells. ``text``, ``type`` and ``marks`` may not contain
    the reserved markers ``(source:``, ``(tentative)`` or ``(prior term)``.
    Absent ``professor`` keeps the current value, ``""`` writes ``unknown``.
    ``prior_term:`` is always kept from the file (``retake`` sets it). Rendered shape: the template comment, ``label:``,
    ``professor:``, ``prior_term:``, then Notation, Phrasing, Disguise types
    (bullets ``- <text> (source: a; b)[ (tentative)][ (prior term)]``) and
    the Question types table (``| <type> (source: a; b)[ markers] | n of m
    papers | marks |``). Over FINGERPRINT_MAX_LINES lines exits 2 with the
    count: merge or drop the weakest entries and rerun.

retake -- link a retaken course to its prior term, decide the professor.
    in : {"term": "2027-Spring", "course": "CS201 Theory",
          "prior_term": "2026-Fall", "prior_course": "CS201 Theory",
          "professor": "Dr. Ayse Kaya"}
    out: {"course_dir": "...", "link": "/home/u/learning/2027-Spring/CS201
          Theory/.state/prior-term", "professor": "Dr. Ayse Kaya",
          "prior_professor": "dr ayse kaya", "same_professor": true,
          "assumed": false, "carry": true, "prior_fingerprint": "/home/u/
          learning/2026-Fall/CS201 Theory/.state/fingerprint.md",
          "line": "Linked ... same professor (Dr. Ayse Kaya) ..."}
    ``prior_term`` must sort strictly before ``term`` in term order
    (``workspace.term_key``: year, then Spring < Summer < Fall, then other
    words alphabetically; any case); the prior course folder and its
    ``.state/`` must exist and not be symlinks. The course is built if new
    (``workspace.build_course``). ``<course>/.state/prior-term`` becomes a
    RELATIVE symlink to the prior ``.state/`` (so ``workspace.py relocate``
    keeps it valid); an existing link to that same target is kept, anything
    else there exits 2. The prior professor is the prior fingerprint's
    ``professor:`` (blank or ``unknown`` = unknown). An input ``professor``
    of ``unknown`` counts as ``""``. Decision: ``""`` with a link and a
    decision already recorded for this prior course keeps that decision and
    the professor; ``""`` with no recorded decision uses a name already in
    this course's ``professor:`` as the given name; ``""`` otherwise, or an
    unknown prior professor, means same professor, assumed; names equal ignoring
    case, whitespace, ``.`` and ``,`` mean same professor; anything else is
    another professor. Writes ``professor:`` (given, else the prior's, else
    ``unknown``) and ``prior_term: <prior term>/<prior course>, same
    professor[ (assumed)]`` or ``..., another professor's papers``; the rest
    of the fingerprint is untouched. ``carry`` is true only when the decision
    is same professor, the link was created now or the recorded decision was
    not already same professor, and the prior fingerprint
    (``prior_fingerprint``, null when absent) has at least one entry (bullet
    or question-type row); ``line`` claims carrying only then. On any failure
    after the course is built, the new link and everything this call created
    are removed. Nothing is ever written through the link.

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``fingerprint.py: <message>``) and
nothing on stdout. An unexpected internal error exits 1 with
``fingerprint.py: internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import datetime
import os
import re
import sys
from pathlib import Path

import ingest
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

FINGERPRINT_MAX_LINES = 60
ENTRY_MAX_CHARS = 160

_SECTIONS = (("notation", "Notation"), ("phrasing", "Phrasing"), ("disguises", "Disguise types"))
_TABLE = ("question_types", "Question types")
_QT_TABLE = ("Question types", ("type", "frequency", "marks"))
_PRIOR = "prior-term:"
_LINK = "prior-term"
_DEBRIEF = re.compile(r"debrief ([0-9]{4}-[0-9]{2}-[0-9]{2})")
_RESERVED = ("(source:", "(tentative)", "(prior term)")
_PRIOR_LINE = re.compile(r"([^/]+)/([^/]+), (same professor(?: \(assumed\))?|another professor's papers)")


# --- Shared helpers ------------------------------------------------------------------

def _line(value, where: str, required: bool, limit: int | None = ENTRY_MAX_CHARS) -> str:
    if not isinstance(value, str):
        raise InputError(f"{where} must be a string")
    if _has_control(value):
        raise InputError(f"{where} must be one line without control characters")
    value = value.strip()
    if required and not value:
        raise InputError(f"{where} is required")
    if limit is not None and len(value) > limit:
        raise InputError(f"{where} is longer than {limit} characters")
    return value


def _no_markers(value: str, where: str) -> str:
    for marker in _RESERVED:
        if marker in value.casefold():
            raise InputError(f"{where} contains the reserved marker {marker!r}; markers and sources are "
                             "computed, send them only in sources")
    return value


def _entry_count(text: str | None) -> int:
    """Bullets plus question-type data rows of a fingerprint (0 when absent)."""
    if text is None:
        return 0
    lines = text.splitlines()
    bullets = sum(1 for l in lines if l.lstrip().startswith("- "))
    copy = list(lines)
    first, end = ingest._section_table(copy, _QT_TABLE)
    return bullets + sum(1 for l in copy[first:end] if not ingest._is_align(l))


def _key_value(text: str | None, key: str) -> str | None:
    """Value of the first ``key:`` line, or None when the line is missing."""
    for line in (text or "").splitlines():
        m = re.fullmatch(rf"{key}:(.*)", line.strip())
        if m:
            return m.group(1).strip()
    return None


def _parse_prior(value: str | None) -> tuple[str, str, bool, bool] | None:
    """(term, course, same_professor, assumed) from a ``prior_term:`` value."""
    m = _PRIOR_LINE.fullmatch(value or "")
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3).startswith("same"), m.group(3).endswith("(assumed)")


_course = workspace.course_folder


def _template_comment() -> list[str]:
    text = (workspace._TEMPLATE_DIR / "fingerprint.md").read_text(encoding="utf-8")
    return [l for l in text.splitlines() if l.strip().startswith("<!--")]


# --- write ---------------------------------------------------------------------------

def _sources(entry: dict, where: str, current: dict, prior: dict | None, prior_note: str) -> list[dict]:
    raw = entry.get("sources")
    if not isinstance(raw, list) or not raw:
        raise InputError(f"{where}.sources is required (a non-empty list)")
    out: list[dict] = []
    for k, value in enumerate(raw, 1):
        swhere = f"{where}.sources[{k}]"
        text = _line(value, swhere, required=True, limit=None)
        if (m := _DEBRIEF.fullmatch(text)):
            try:
                datetime.date.fromisoformat(m.group(1))
            except ValueError:
                raise InputError(f"{swhere}: not a valid debrief date: {_short(text)}") from None
            src = {"text": text, "kind": "debrief", "role": "debrief", "fidelity": "text"}
        elif text.startswith(_PRIOR):
            path = text[len(_PRIOR):].strip()
            if prior is None:
                raise InputError(f"{swhere}: {_short(text)} needs prior_term: to say same professor "
                                 f"{prior_note}")
            if path not in prior["rows"]:
                raise InputError(f"{swhere}: {_short(path)} has no registry row in {prior['index']}")
            role, _, fidelity = prior["rows"][path]
            text = _PRIOR + path
            src = {"text": text, "kind": "prior", "role": role, "fidelity": fidelity}
        elif text in current["rows"]:
            role, _, fidelity = current["rows"][text]
            src = {"text": text, "kind": "current", "role": role, "fidelity": fidelity}
        else:
            raise InputError(f"{swhere}: {_short(text)} has no registry row in {current['index']} "
                             "(use a course-relative path, prior-term:<path> or debrief YYYY-MM-DD)")
        if all(s["text"] != src["text"] for s in out):
            out.append(src)
    return out


def _markers(sources: list[dict]) -> tuple[bool, bool]:
    tentative = not any(s["kind"] == "debrief" or s["fidelity"] == "text" for s in sources)
    prior = all(s["kind"] == "prior" for s in sources)
    return tentative, prior


def _decorate(text: str, sources: list[dict]) -> str:
    tentative, prior = _markers(sources)
    out = f"{text} (source: {'; '.join(s['text'] for s in sources)})"
    if tentative:
        out += " (tentative)"
    if prior:
        out += " (prior term)"
    return out


def _counted(sources: list[dict]) -> set[str]:
    return {s["text"] for s in sources if s["kind"] == "debrief" or s["role"] == "past-papers"}


def source_context(root: Path, course_dir: Path, fp_text: str | None) -> tuple[dict, dict | None, str, tuple | None]:
    """Registries ``_sources`` checks against: (current, prior, prior_note, parsed prior_term).

    ``fp_text`` is the course's fingerprint.md text (None when absent); its
    ``prior_term:`` line decides whether ``prior-term:<path>`` sources are
    allowed (``prior`` is None when they are not; ``prior_note`` says why).
    """
    prior_value = _key_value(fp_text, "prior_term") or ""
    parsed = _parse_prior(prior_value)
    index = course_dir / "INDEX.md"
    current = {"index": index, "rows": ingest.registry(index)}
    prior = None
    prior_note = f"(it says {_short(prior_value)})" if prior_value else "(it is blank; run retake first)"
    if parsed and parsed[2]:
        link = course_dir / ".state" / _LINK
        prior_state = root / parsed[0] / parsed[1] / ".state"
        if link.is_symlink() and link.resolve() == prior_state.resolve():
            prior_index = root / parsed[0] / parsed[1] / "INDEX.md"
            prior = {"index": prior_index, "rows": ingest.registry(prior_index)}
        else:
            prior_note = f"and {link} to link to {prior_state} (run retake first)"
    return current, prior, prior_note, parsed


def cmd_write(data: dict) -> dict:
    keys = {"term", "course", "professor", *(k for k, _ in _SECTIONS), _TABLE[0]}
    _check_keys(data, keys)
    term, course = parse_term(data), parse_segment(data, "course")
    professor = _line(data["professor"], "professor", required=False) if "professor" in data else None
    root = ingest._workspace_root()
    course_dir = _course(root, term, course)
    if not course_dir.is_dir():
        raise InputError(f"no course folder at {course_dir}")
    fp = course_dir / ".state" / "fingerprint.md"
    if fp.is_symlink():
        raise InputError(f"{fp} is a symlink; refusing to write through it")
    old = ingest.read_text(fp)
    prior_value = _key_value(old, "prior_term") or ""
    current_prof = _key_value(old, "professor")
    current, prior, prior_note, parsed = source_context(root, course_dir, old)

    blocks: dict[str, list[tuple[str, list[dict]]]] = {}
    for key, _ in _SECTIONS:
        items = data.get(key, [])
        if not isinstance(items, list):
            raise InputError(f"{key} must be a list")
        blocks[key] = []
        for n, entry in enumerate(items, 1):
            where = f"{key}[{n}]"
            if not isinstance(entry, dict):
                raise InputError(f"{where} must be an object")
            _check_keys(entry, {"text", "sources"})
            text = _no_markers(_line(entry.get("text"), f"{where}.text", required=True), f"{where}.text")
            blocks[key].append((text, _sources(entry, where, current, prior, prior_note)))
    rows: list[tuple[str, str, list[dict]]] = []
    items = data.get(_TABLE[0], [])
    if not isinstance(items, list):
        raise InputError(f"{_TABLE[0]} must be a list")
    for n, entry in enumerate(items, 1):
        where = f"{_TABLE[0]}[{n}]"
        if not isinstance(entry, dict):
            raise InputError(f"{where} must be an object")
        _check_keys(entry, {"type", "sources", "marks"})
        qtype = _no_markers(_line(entry.get("type"), f"{where}.type", required=True), f"{where}.type")
        marks = _no_markers(_line(entry.get("marks", ""), f"{where}.marks", required=False), f"{where}.marks")
        rows.append((qtype, marks, _sources(entry, where, current, prior, prior_note)))

    every = [s for b in blocks.values() for _, s in b] + [s for _, _, s in rows]
    prior_lines = sum(1 for s in every if _markers(s)[1])
    label = f"prior term ({parsed[0]})" if prior_lines and parsed else "current term"
    if professor is None:
        prof_value = current_prof or ""
    else:
        prof_value = professor or "unknown"
    papers = set().union(*(_counted(s) for _, _, s in rows)) if rows else set()
    out = _template_comment() + ["# Fingerprint", "", f"label: {label}",
                                 f"professor: {prof_value}".rstrip(), f"prior_term: {prior_value}".rstrip(), ""]
    for key, title in _SECTIONS:
        out.append(f"## {title}")
        out += [f"- {_decorate(text, srcs)}" for text, srcs in blocks[key]]
        out.append("")
    out += [f"## {_TABLE[1]}", "| type | frequency | marks |", "|---|---|---|"]
    for qtype, marks, srcs in rows:
        freq = f"{len(_counted(srcs))} of {len(papers)} papers" if papers else "-"
        out.append(f"| {ingest._cell(_decorate(qtype, srcs))} | {freq} | {ingest._cell(marks)} |")
    if len(out) > FINGERPRINT_MAX_LINES:
        raise InputError(f"the fingerprint would be {len(out)} lines, over the {FINGERPRINT_MAX_LINES}-line "
                         "cap; merge or drop the weakest entries and rerun (nothing was changed)")
    text = "\n".join(out) + "\n"
    workspace.build_course(root, term, course, [])  # restores a missing .state/ or fingerprint.md
    if text != ingest.read_text(fp):
        ingest._write_atomic(fp, text)
    tentative = sum(1 for s in every if _markers(s)[0])
    line = (f"Fingerprint saved: {fp} ({len(out)} of {FINGERPRINT_MAX_LINES} lines, "
            f"{len(every)} {'entry' if len(every) == 1 else 'entries'}, {tentative} tentative")
    line += f", {prior_lines} from the prior term)." if prior_lines else ")."
    return {"fingerprint": str(fp), "course_dir": str(course_dir), "lines": len(out), "label": label,
            "entries": len(every), "tentative": tentative, "prior_term_entries": prior_lines, "line": line}


# --- retake --------------------------------------------------------------------------

def _norm(name: str) -> str:
    return " ".join(re.sub(r"[.,]", " ", name.casefold()).split())


def _set_key(text: str, key: str, value: str, after: tuple[str, ...]) -> str:
    """Replace the ``key:`` line, or insert it after the first line matching ``after``."""
    lines = text.splitlines()
    new = f"{key}: {value}".rstrip()
    for i, line in enumerate(lines):
        if re.fullmatch(rf"{key}:.*", line.strip()):
            lines[i] = new
            return "\n".join(lines) + "\n"
    for anchor in after:
        for i, line in enumerate(lines):
            if re.fullmatch(anchor, line.strip()):
                lines.insert(i + 1, new)
                return "\n".join(lines) + "\n"
    lines.insert(0, new)
    return "\n".join(lines) + "\n"


def _rollback(link: Path | None, created: list[str]) -> None:
    """Undo a failed retake: the new link, then everything build_course created (newest first)."""
    if link is not None:
        try:
            link.unlink()
        except OSError:
            pass
    for path in reversed(created):
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                os.rmdir(path)
            else:
                os.unlink(path)
        except OSError:
            pass


def _decide(professor: str, prior_prof: str) -> tuple[bool, bool, str]:
    """(same_professor, assumed, professor to write) for a fresh decision."""
    if not professor or not prior_prof:
        return True, True, professor or prior_prof or "unknown"
    return _norm(professor) == _norm(prior_prof), False, professor


def cmd_retake(data: dict) -> dict:
    _check_keys(data, {"term", "course", "prior_term", "prior_course", "professor"})
    term, course = parse_term(data), parse_segment(data, "course")
    prior_term = parse_segment(data, "prior_term")
    if not workspace._TERM.fullmatch(prior_term):
        raise InputError(f"prior_term must be YYYY-<word>, e.g. 2026-Fall: {_short(prior_term)}")
    prior_course = parse_segment(data, "prior_course")
    if "professor" not in data:
        raise InputError("professor is required (a name, or \"\" when none was found)")
    professor = _line(data["professor"], "professor", required=False)
    if _norm(professor) == "unknown":
        professor = ""
    prior_key, term_key = workspace.term_key(prior_term), workspace.term_key(term)
    if prior_key == term_key:
        raise InputError(f"prior_term {prior_term} is the same term as the course; a retake links an earlier term")
    if prior_key > term_key:
        raise InputError(f"prior_term {prior_term} is later than {term}; a retake links an earlier term")
    root = ingest._workspace_root()
    course_dir = _course(root, term, course)
    prior_dir = _course(root, prior_term, prior_course, "prior course")
    prior_state = prior_dir / ".state"
    if not prior_dir.is_dir():
        raise InputError(f"no prior course folder at {prior_dir}")
    if not prior_state.is_dir():
        raise InputError(f"the prior course has no .state/ folder at {prior_state}")
    link = course_dir / ".state" / _LINK
    target = os.path.relpath(prior_state, link.parent)
    linked = link.is_symlink() and os.readlink(link) == target
    if not linked and (link.exists() or link.is_symlink()):
        raise InputError(f"{link} already exists and is not a link to {prior_state}; nothing was changed")
    fp = course_dir / ".state" / "fingerprint.md"
    if fp.is_symlink():
        raise InputError(f"{fp} is a symlink; refusing to write through it")
    old = ingest.read_text(fp)
    prior_fp = prior_state / "fingerprint.md"
    prior_text = ingest.read_text(prior_fp)
    prior_prof = _key_value(prior_text, "professor") or ""
    if prior_prof.casefold() == "unknown":
        prior_prof = ""

    decided = _parse_prior(_key_value(old, "prior_term"))
    recorded = decided if decided and decided[:2] == (prior_term, prior_course) else None
    current_prof = _key_value(old, "professor") or ""
    if not professor and linked and recorded:
        same, assumed = recorded[2], recorded[3]
        new_prof = current_prof or "unknown"
    else:
        if not professor and _norm(current_prof) not in ("", "unknown"):
            professor = current_prof  # a name already recorded for this course counts as given
        same, assumed, new_prof = _decide(professor, prior_prof)
    outcome = ("same professor (assumed)" if assumed else "same professor") if same \
        else "another professor's papers"
    prior_value = f"{prior_term}/{prior_course}, {outcome}"

    text = old if old is not None else workspace.instance_template(
        (workspace._TEMPLATE_DIR / "fingerprint.md").read_text(encoding="utf-8"))
    text = _set_key(text, "professor", new_prof, (r"label:.*", r"#\s*Fingerprint"))
    text = _set_key(text, "prior_term", prior_value, (r"professor:.*",))

    created: list[str] = []
    made_link = False
    try:
        workspace.build_course(root, term, course, created)
        if not linked:
            os.symlink(target, link, target_is_directory=True)
            made_link = True
        if text != ingest.read_text(fp):
            ingest._write_atomic(fp, text)
    except BaseException:
        _rollback(link if made_link else None, created)
        raise

    fresh = made_link or not (recorded and recorded[2])  # newly linked, or newly the same professor
    carry = same and fresh and _entry_count(prior_text) > 0
    where = f"{prior_term}/{prior_course}"
    line = f"Linked {term}/{course} read-only to {where}."
    if not same:
        line += (f" Different professor ({new_prof}; {prior_term}: {prior_prof or 'unknown'}), so the "
                 f"{prior_term} papers count as another professor's papers.")
    elif not assumed:
        line += f" Same professor ({new_prof})."
    elif professor:
        line += f" {prior_term} has no professor name, so I'm assuming the same professor ({new_prof})."
    else:
        named = f" ({new_prof})" if new_prof != "unknown" else ""
        line += f" No professor name to compare, so I'm assuming the same professor{named} as {prior_term}."
    if carry:
        line += f" Carrying the {prior_term} fingerprint forward, labelled prior term."
    return {"course_dir": str(course_dir), "link": str(link), "professor": new_prof,
            "prior_professor": prior_prof or None, "same_professor": same, "assumed": assumed,
            "carry": carry, "prior_fingerprint": str(prior_fp) if prior_text is not None else None,
            "line": line}


COMMANDS = {
    "write": (cmd_write, "render a course's fingerprint.md from its complete content"),
    "retake": (cmd_retake, "link a retaken course to its prior term and decide the professor"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("fingerprint.py",
                             ("Mimir professor fingerprint. Subcommands: write, retake. Reads one JSON object "
                              "on stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
