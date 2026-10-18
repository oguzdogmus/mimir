#!/usr/bin/env python3
"""Mimir answer-key gate: provenance labels and the show/retry/flag/drop decision.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py`` and ``ingest.py`` (same folder). Run as::

    python3 verify.py gate  < input.json

``gate`` reads ONE JSON object on stdin (unknown fields are rejected) and
prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. It needs a workspace at the learning root (see ``workspace.py``) and
an existing course folder; the term and course folders and the course
``.state/`` must not be symlinks. It reads only the course's INDEX.md registry
and writes nothing.

The model writes questions and answer keys; this script owns the trust
labels and the decision whether an item reaches the student. Labels are
always computed here from the registry, never input. The gate is stateless:
the caller sends the verdict history each time, so the same call labels the
items before verification and decides after it.

Items
-----
``{"topic", "origin", "source"?, "page"?, "question"?, "quote"?, "verdicts"?,
"compare"?, "dispute"?}``. Strings are one line without control characters;
``topic`` (required) and ``dispute`` at most TOPIC_MAX_CHARS (120)
characters, ``question`` at most 40. Paths are course-relative registry paths
(e.g. ``past-papers/2024-final.pdf``); pages are integers >= 1. A registry
row whose path is absolute, has a ``..`` part, or resolves outside the
course folder counts as no row. Errors name the field, e.g.
``items[2].source``.

* ``origin`` ``practice`` (a generated question): no ``source``, ``page`` or
  ``question``. Label ``[practice, not from a real paper]``.
* ``origin`` ``real``: ``source`` must have a registry row with role
  ``past-papers``, ``page`` (required) must not pass the row's pages when
  known, ``question`` (e.g. ``Q2``) is optional. Fidelity ``text``: label
  ``[real: <source>, p.<page>]``. Any fidelity other than ``text``
  (``ocr``, blank or unknown; the cautious choice): label ``[real, from
  photo/scan, wording may be off]`` plus ``original`` ``{"path": <absolute
  file path>, "page": <page>}`` to show beside it (the whole page stands in
  for the crop).
* ``quote`` ``{path, page}``: the answer key is a direct quote of professor
  material. The item needs no verification only when ``path`` has a registry
  row with fidelity ``text`` and role ``outline``, ``slides`` or
  ``past-papers`` and ``page`` is within its pages; any other quote (``ocr``,
  ``notes``, unindexed, page out of range) still needs verification.
* ``verdicts``: the verifier's verdicts so far, oldest first, each
  ``correct``, ``wrong``, ``ambiguous`` or ``source-conflict``; at most
  VERIFIER_RETRIES + 1 of them, and none after a ``correct``.
* ``compare`` ``{path, page, question?}``: a solved reference in this course
  to name when the checker still disagrees. It counts only when ``path`` has
  a registry row in this course and ``page`` is within its pages.
* ``dispute``: what the checker disagrees on, e.g. ``step 3``.

Decision
--------
* no verdicts: ``verify`` when the item needs verification, else ``show``;
* last verdict ``correct``: ``show``;
* fewer than VERIFIER_RETRIES + 1 verdicts, last not correct: ``retry``;
* VERIFIER_RETRIES + 1 non-correct verdicts: ``flagged`` when ``compare``
  counts, else ``dropped``.
Given verdicts always apply, also to items that need no verification. Only
``show`` and ``flagged`` items may reach the student; ``counts_for_mastery``
is true only for ``show``. A ``flagged`` item carries ``flag``: ``⚠ my checker
disagrees on <dispute or "this answer">, compare with `<path>` p.<page>[
<question>]``. Each flagged or dropped item adds one ``disagreements`` line
for the session log: ``- YYYY-MM-DD item N (<topic>): <flagged|dropped>,
checker said <last verdict>[, compare <path> p.<page>[ <question>]]``, dated
today by the local clock.

Example (root /home/u/learning; INDEX has past-papers/2024-final.pdf, text)
------------------------------------------------------------------------
gate -- label the items and decide which may be shown.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "items": [
            {"topic": "Pumping lemma", "origin": "real",
             "source": "past-papers/2024-final.pdf", "page": 3, "question": "Q2"},
            {"topic": "DFA minimisation", "origin": "practice",
             "verdicts": ["wrong", "ambiguous"], "dispute": "step 3",
             "compare": {"path": "past-papers/2024-final.pdf", "page": 3,
                         "question": "Q4"}}]}
    out: {"course_dir": "/home/u/learning/2026-Fall/CS201 Theory",
          "results": [
            {"n": 1, "topic": "Pumping lemma", "origin": "real",
             "label": "[real: past-papers/2024-final.pdf, p.3]",
             "needs_verification": true, "decision": "verify",
             "counts_for_mastery": false},
            {"n": 2, "topic": "DFA minimisation", "origin": "practice",
             "label": "[practice, not from a real paper]",
             "needs_verification": true, "decision": "flagged",
             "counts_for_mastery": false,
             "flag": "⚠ my checker disagrees on step 3, compare with
                      `past-papers/2024-final.pdf` p.3 Q4"}],
          "verify": [1], "retry": [],
          "disagreements": ["- 2026-10-18 item 2 (DFA minimisation): flagged,
                             checker said ambiguous, compare
                             past-papers/2024-final.pdf p.3 Q4"],
          "line": "Gate: 2 items, 1 to verify, 1 flagged."}
    ``original`` appears only on real items whose fidelity is not
    ``text``, ``flag`` only on flagged ones. ``verify`` and ``retry`` list item numbers (1-based).

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``verify.py: <message>``) and nothing
on stdout. An unexpected internal error exits 1 with ``verify.py: internal
error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import ingest
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

VERIFIER_RETRIES = 1

_QUESTION_MAX = 40
_VERDICTS = ("correct", "wrong", "ambiguous", "source-conflict")
_ORIGINS = ("practice", "real")
_QUOTE_ROLES = ("outline", "slides", "past-papers")
_ITEM_KEYS = {"topic", "origin", "source", "page", "question", "quote", "verdicts", "compare", "dispute"}
_DECISIONS = ("show", "verify", "retry", "flagged", "dropped")
_PRACTICE_LABEL = "[practice, not from a real paper]"
_OCR_LABEL = "[real, from photo/scan, wording may be off]"


def _text(value, where: str, limit: int | None, required: bool = True) -> str:
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


def _page(value, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InputError(f"{where} must be a page number (an integer >= 1): {_short(value)}")
    return value


def _keys(obj: dict, allowed: set[str], where: str) -> None:
    extra = sorted(set(obj) - allowed)
    if extra:
        raise InputError(f"{where}: unknown field {_short(extra[0])}")


def _ref(value, where: str, with_question: bool) -> dict:
    """A ``{path, page[, question]}`` reference, checked for shape only."""
    if not isinstance(value, dict):
        raise InputError(f"{where} must be an object")
    _keys(value, {"path", "page", "question"} if with_question else {"path", "page"}, where)
    if "path" not in value:
        raise InputError(f"{where}.path is required")
    if "page" not in value:
        raise InputError(f"{where}.page is required")
    ref = {"path": _text(value["path"], f"{where}.path", None), "page": _page(value["page"], f"{where}.page")}
    if with_question and "question" in value:
        ref["question"] = _text(value["question"], f"{where}.question", _QUESTION_MAX, required=False)
    return ref


def _in_range(rows: dict, ref: dict) -> tuple[str, int | None, str] | None:
    """The registry row of ``ref`` when it exists and its page is within the row's pages."""
    row = rows.get(ref["path"])
    if row is None or (row[1] is not None and ref["page"] > row[1]):
        return None
    return row


def _inside(course_dir: Path, path: str) -> bool:
    """True when a registry path is relative, has no ``..`` part and resolves inside the course."""
    rel = Path(path)
    if _has_control(path) or rel.is_absolute() or ".." in rel.parts:
        return False
    return (course_dir / rel).resolve().is_relative_to(course_dir.resolve())


def _course_dir(term: str, course: str) -> Path:
    root = ingest._workspace_root()
    course_dir = root / term / course
    for folder, kind in ((root / term, "term"), (course_dir, "course"), (course_dir / ".state", "course .state")):
        if folder.is_symlink():
            raise InputError(f"{kind} folder {folder} is a symlink; refusing to work through it")
    if not course_dir.is_dir():
        raise InputError(f"no course folder at {course_dir}")
    return course_dir


def _gate_item(item, n: int, rows: dict, course_dir: Path, index: Path, today: str) -> dict:
    where = f"items[{n}]"
    if not isinstance(item, dict):
        raise InputError(f"{where} must be an object")
    _keys(item, _ITEM_KEYS, where)
    if "topic" not in item:
        raise InputError(f"{where}.topic is required")
    topic = _text(item["topic"], f"{where}.topic", ingest.TOPIC_MAX_CHARS)
    origin = item.get("origin")
    if origin not in _ORIGINS:
        raise InputError(f"{where}.origin must be practice or real: {_short(origin)}")
    result: dict = {"n": n, "topic": topic, "origin": origin}

    if origin == "practice":
        for field in ("source", "page", "question"):
            if field in item:
                raise InputError(f"{where}.{field} is not allowed on a practice item "
                                 "(a generated question is never cited as real)")
        result["label"] = _PRACTICE_LABEL
    else:
        if "source" not in item:
            raise InputError(f"{where}.source is required for a real item")
        source = _text(item["source"], f"{where}.source", None)
        if "page" not in item:
            raise InputError(f"{where}.page is required for a real item")
        page = _page(item["page"], f"{where}.page")
        if "question" in item:
            _text(item["question"], f"{where}.question", _QUESTION_MAX, required=False)
        row = rows.get(source)
        if row is None:
            raise InputError(f"{where}.source: {_short(source)} has no registry row in {index}")
        role, pages, fidelity = row
        if role != "past-papers":
            raise InputError(f"{where}.source: {_short(source)} has role {role or 'none'}, not past-papers; "
                             "a real question comes from a past paper (else label it practice)")
        if pages is not None and page > pages:
            raise InputError(f"{where}.page: page {page} is past the last page of {source} ({pages})")
        if fidelity == "text":
            result["label"] = f"[real: {source}, p.{page}]"
        else:
            result["label"] = _OCR_LABEL
            result["original"] = {"path": str(course_dir / source), "page": page}

    needs = True
    if "quote" in item:
        quote = _ref(item["quote"], f"{where}.quote", with_question=False)
        row = _in_range(rows, quote)
        needs = not (row is not None and row[2] == "text" and row[0] in _QUOTE_ROLES)

    verdicts = item.get("verdicts", [])
    if not isinstance(verdicts, list):
        raise InputError(f"{where}.verdicts must be a list")
    if len(verdicts) > VERIFIER_RETRIES + 1:
        raise InputError(f"{where}.verdicts has {len(verdicts)} verdicts; at most {VERIFIER_RETRIES + 1} "
                         f"(one check plus {VERIFIER_RETRIES} retry)")
    for k, verdict in enumerate(verdicts, 1):
        if verdict not in _VERDICTS:
            raise InputError(f"{where}.verdicts[{k}] must be one of {', '.join(_VERDICTS)}: {_short(verdict)}")
        if k < len(verdicts) and verdict == "correct":
            raise InputError(f"{where}.verdicts[{k + 1}] follows a correct verdict; a correct item is not rechecked")

    compare = _ref(item["compare"], f"{where}.compare", with_question=True) if "compare" in item else None
    dispute = _text(item["dispute"], f"{where}.dispute", ingest.TOPIC_MAX_CHARS, required=False) \
        if "dispute" in item else ""

    if not verdicts:
        decision = "verify" if needs else "show"
    elif verdicts[-1] == "correct":
        decision = "show"
    elif len(verdicts) < VERIFIER_RETRIES + 1:
        decision = "retry"
    else:
        reference = compare if compare is not None and _in_range(rows, compare) is not None else None
        decision = "flagged" if reference else "dropped"
        line = f"- {today} item {n} ({topic}): {decision}, checker said {verdicts[-1]}"
        if reference:
            tail = f" p.{reference['page']}" + (f" {reference['question']}" if reference.get("question") else "")
            result["flag"] = (f"⚠ my checker disagrees on {dispute or 'this answer'}, compare with "
                              f"`{reference['path']}`{tail}")
            line += f", compare {reference['path']}{tail}"
        result["disagreement"] = line
    result.update(needs_verification=needs, decision=decision, counts_for_mastery=decision == "show")
    return result


def cmd_gate(data: dict) -> dict:
    _check_keys(data, {"term", "course", "items"})
    term, course = parse_term(data), parse_segment(data, "course")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise InputError("items is required (a non-empty list)")
    course_dir = _course_dir(term, course)
    index = course_dir / "INDEX.md"
    rows = {path: row for path, row in ingest.registry(index).items() if _inside(course_dir, path)}
    today = datetime.date.today().isoformat()
    results = [_gate_item(item, n, rows, course_dir, index, today) for n, item in enumerate(items, 1)]
    disagreements = [r.pop("disagreement") for r in results if "disagreement" in r]
    counts = {d: sum(1 for r in results if r["decision"] == d) for d in _DECISIONS}
    words = {"show": "to show", "verify": "to verify", "retry": "to retry", "flagged": "flagged",
             "dropped": "dropped"}
    parts = [f"{counts[d]} {words[d]}" for d in _DECISIONS if counts[d]]
    noun = "item" if len(results) == 1 else "items"
    return {"course_dir": str(course_dir), "results": results,
            "verify": [r["n"] for r in results if r["decision"] == "verify"],
            "retry": [r["n"] for r in results if r["decision"] == "retry"],
            "disagreements": disagreements,
            "line": f"Gate: {len(results)} {noun}, {', '.join(parts)}."}


COMMANDS = {
    "gate": (cmd_gate, "label answer-key items and decide show, verify, retry, flagged or dropped"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("verify.py",
                             ("Mimir answer-key gate. Subcommand: gate. Reads one JSON object on stdin and "
                              "prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
