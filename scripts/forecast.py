#!/usr/bin/env python3
"""Mimir exam forecast: store forecasts, score them, keep the hit-rate record.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``fingerprint.py`` (same folder). Run as::

    python3 forecast.py <write|score>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Both subcommands need a
workspace at the learning root (see ``workspace.py``) and an existing course
folder; the term and course folders, the course ``.state/`` and
``forecast.md`` must not be symlinks. The clock is never read: ``date`` is an
input (``session.py now``'s ``date``). On any error nothing is written.

The model picks the topics and their evidence; this script owns the trust
numbers: the confidence line, hit rates and the cumulative record are always
computed, never input. ``forecast.md`` and the profile's ``forecast_record:``
line are only ever changed through this script.

Sources
-------
Each topic has at least one source, validated exactly as fingerprint sources
(``fingerprint._sources``): a course-relative path with a registry row in
this course's INDEX.md, ``prior-term:<path>`` (only when this course's
fingerprint says same professor and the ``.state/prior-term`` link is in
place) or ``debrief YYYY-MM-DD``.

Confidence, from n = distinct cited sources that are past papers (registry
role ``past-papers``) or debriefs, over all topics:
* 0: ``low - No past papers or debriefs to go on, only the outline and
  slides, so this is a rough guess.``
* 1: ``low - Only one paper to go on, so this is a rough guess.``
* 2-3: ``medium - Based on <n> papers; more papers would sharpen it.``
* 4 or more: ``high - Based on <n> papers.``

Block shape (``assets/templates/forecast.md``), newest block first::

    ## <exam> <exam_name>
    date: <date>
    label: [forecast, not a guarantee]
    confidence: <computed line>
    hit_rate: pending

    | rank | topic | evidence |
    |---|---|---|
    | 1 | <topic> | <evidence> (source: a; b) |

A block is identified by its exam date and name (name compared ignoring case
and repeated spaces). ``|`` in a cell is stored as ``\\|``.

Record: H, M, K = sums of ``<h> of <m>`` and the count over every scored
block (see ``write``) in every
``<root>/<YYYY-Term>/<course>/.state/forecast.md`` whose term, course,
``.state`` and file are not symlinks (unreadable files of other courses are
skipped). It is recomputed from scratch each time, so rescoring never
double-counts.

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
write -- store one forecast block for an exam.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "date": "2026-10-19",
          "exam": "2026-11-05", "exam_name": "final",
          "topics": [{"topic": "Pumping lemma", "evidence": "On both past
                      finals, 20 marks each",
                      "sources": ["past-papers/2024-final.pdf"]}]}
    out: {"forecast": "/home/u/learning/2026-Fall/CS201 Theory/.state/
          forecast.md", "course_dir": "...", "exam": "2026-11-05",
          "exam_name": "final", "label": "[forecast, not a guarantee]",
          "confidence": "low - Only one paper to go on, so this is a rough
          guess.", "papers": 1, "topics": [{"rank": 1, "topic": "...",
          "evidence": "...", "sources": ["past-papers/2024-final.pdf"]}],
          "replaced": false, "record_line": null,
          "line": "Forecast saved: ... (1 topic, low confidence)."}
    ``date`` and ``exam`` are ``YYYY-MM-DD``; ``exam`` may not be before
    ``date``. ``exam_name``, ``topic`` and
    ``evidence`` are one line without control characters, at most
    ENTRY_MAX_CHARS characters, without ``(source:``, ``(tentative)`` or
    ``(prior term)``. 1 to MAX_TOPICS topics, distinct ignoring case, in rank
    order. A pending block for the same exam is replaced (``replaced``
    true); a scored one exits 2. Scored means ``hit_rate: <h> of <m>``,
    optionally followed by `` (scored YYYY-MM-DD)``, with 1 <= m and h <= m;
    any other ``hit_rate:`` value (pending, blank, malformed) is pending.
    Everything is checked before anything is created or written. ``record_line`` is "Past forecasts: H of M
    top topics appeared, across K forecast[s]." or null when nothing is
    scored. The profile is not changed.

score -- store the hit rate of an exam's forecast and recompute the record.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "date": "2026-11-12",
          "exam": "2026-11-05", "exam_name": "final", "hits": [1, 3, 4]}
    out: {"forecast": "...", "profile": "/home/u/learning/.state/profile.md",
          "course_dir": "...", "hit_rate": "3 of 5", "hits": 3, "of": 5,
          "record": {"hits": 3, "of": 5, "forecasts": 1},
          "record_line": "Past forecasts: 3 of 5 top topics appeared, across 1
          forecast.", "line": "Forecast for final (2026-11-05): 3 of 5 top
          topics appeared. Past forecasts: ..."}
    ``hits`` are the distinct ranks that appeared, each within 1..m, m =
    min(TOP_N, topics in the block); ``[]`` scores 0. ``date`` may not be
    before ``exam``. The block (pending or
    already scored: rescoring overwrites) must exist. Writes ``hit_rate: <h>
    of <m> (scored <date>)``, then replaces the profile's ``forecast_record:
    <H> of <M> across <K> forecast[s]`` line inside its ``## Forecast record``
    section (the line, or the section and line, added when missing). Neither
    ``<root>/.state`` nor the profile may be a symlink. If the profile write
    fails, the forecast is restored (best effort) and the original error is
    reported.

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``forecast.py: <message>``) and
nothing on stdout. An unexpected internal error exits 1 with ``forecast.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

import fingerprint
import ingest
import workspace
from workspace import InputError, _check_keys, _short, parse_segment, parse_term

MAX_TOPICS = 10
TOP_N = 5
ENTRY_MAX_CHARS = fingerprint.ENTRY_MAX_CHARS
LABEL = "[forecast, not a guarantee]"

_HEADING = re.compile(r"##\s+([0-9]{4}-[0-9]{2}-[0-9]{2})\s+(.+)")
_HIT = re.compile(r"([0-9]+) of ([0-9]+)(?: \(scored [0-9]{4}-[0-9]{2}-[0-9]{2}\))?")
_TABLE_HEADER = ["| rank | topic | evidence |", "|---|---|---|"]


def _date(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise InputError(f"{key} is required (YYYY-MM-DD)")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise InputError(f"{key} is not a valid date: {_short(value)}") from None
    return value


def _norm(name: str) -> str:
    return " ".join(name.casefold().split())


def confidence(n: int) -> str:
    if n == 0:
        return "low - No past papers or debriefs to go on, only the outline and slides, so this is a rough guess."
    if n == 1:
        return "low - Only one paper to go on, so this is a rough guess."
    if n <= 3:
        return f"medium - Based on {n} papers; more papers would sharpen it."
    return f"high - Based on {n} papers."


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


# --- forecast.md parsing --------------------------------------------------------------

def _split(text: str | None) -> tuple[list[str], list[list[str]]]:
    """(preamble lines, blocks) of a forecast.md; each block starts with its ``## `` heading."""
    if text is None or not text.strip():
        tmpl = (workspace._TEMPLATE_DIR / "forecast.md").read_text(encoding="utf-8")
        text = workspace.instance_template(tmpl)
    pre: list[str] = []
    blocks: list[list[str]] = []
    for line in text.splitlines():
        if line.startswith("## "):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
        else:
            pre.append(line)
    for part in [pre, *blocks]:
        while part and not part[-1].strip():
            part.pop()
    return pre, blocks


def _join(pre: list[str], blocks: list[list[str]]) -> str:
    out = list(pre)
    for block in blocks:
        out += ["", *block]
    return "\n".join(out) + "\n"


def _ident(block: list[str]) -> tuple[str, str] | None:
    m = _HEADING.fullmatch(block[0].strip())
    return (m.group(1), _norm(m.group(2))) if m else None


def _hit_rate(block: list[str]) -> str | None:
    """The block's ``hit_rate:`` value, None when the line is missing."""
    for line in block[1:]:
        m = re.fullmatch(r"hit_rate:(.*)", line.strip())
        if m:
            return m.group(1).strip()
    return None


def _scored(block: list[str]) -> tuple[int, int] | None:
    """(h, m) when the block is scored: ``hit_rate: <h> of <m>[ (scored YYYY-MM-DD)]``, 1 <= m, h <= m.

    The one definition of "scored": anything else (pending, blank, malformed)
    is pending, counts nowhere and may be replaced by ``write``.
    """
    value = _hit_rate(block)
    m = _HIT.fullmatch(value or "")
    if not m:
        return None
    h, of = int(m.group(1)), int(m.group(2))
    return (h, of) if 1 <= of and h <= of else None


def _rows(block: list[str]) -> int:
    rows = [l for l in block if ingest._is_row(l) and not ingest._is_align(l)]
    return max(0, len(rows) - 1)  # minus the header row


# --- record ---------------------------------------------------------------------------

def _forecast_files(root: Path) -> list[Path]:
    out = []
    for term in sorted(root.iterdir()):
        if term.is_symlink() or not term.is_dir() or not workspace._TERM.fullmatch(term.name):
            continue
        try:
            courses = sorted(term.iterdir())
        except OSError:
            continue
        for course in courses:
            state = course / ".state"
            fc = state / "forecast.md"
            if (not course.is_symlink() and course.is_dir() and not state.is_symlink()
                    and not fc.is_symlink() and fc.is_file()):
                out.append(fc)
    return out


def record(root: Path, override: tuple[Path, str] | None = None) -> tuple[int, int, int]:
    """(H, M, K) over every scored block; ``override`` = (path, text) to use instead of that file."""
    texts: dict[Path, str] = {}
    for fc in _forecast_files(root):
        try:
            texts[fc] = fc.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    if override is not None:
        texts[override[0]] = override[1]
    hits = of = count = 0
    for text in texts.values():
        for block in _split(text)[1]:
            scored = _scored(block)
            if scored:
                hits, of, count = hits + scored[0], of + scored[1], count + 1
    return hits, of, count


def record_line(rec: tuple[int, int, int]) -> str | None:
    h, m, k = rec
    if not k:
        return None
    return f"Past forecasts: {h} of {m} top topics appeared, across {_plural(k, 'forecast')}."


def _profile_text(text: str, value: str) -> str:
    """Replace ``forecast_record:`` inside ``## Forecast record`` (section and line added when missing)."""
    lines = text.splitlines()
    new = f"forecast_record: {value}"
    heading = next((i for i, l in enumerate(lines) if re.fullmatch(r"##\s+Forecast record\s*", l.strip(),
                                                                     re.IGNORECASE)), None)
    if heading is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## Forecast record", new]
        return "\n".join(lines) + "\n"
    end = next((i for i in range(heading + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    at = next((i for i in range(heading + 1, end) if re.fullmatch(r"forecast_record:.*", lines[i].strip())), None)
    if at is None:
        lines.insert(heading + 1, new)
    else:
        lines[at] = new
    return "\n".join(lines) + "\n"


# --- shared ---------------------------------------------------------------------------

def _target(data: dict) -> tuple[Path, Path, Path, str, str]:
    term, course = parse_term(data), parse_segment(data, "course")
    root = ingest._workspace_root()
    course_dir = workspace.course_folder(root, term, course)
    if not course_dir.is_dir():
        raise InputError(f"no course folder at {course_dir}")
    fc = course_dir / ".state" / "forecast.md"
    if fc.is_symlink():
        raise InputError(f"{fc} is a symlink; refusing to write through it")
    return root, course_dir, fc, term, course


def _exam(data: dict) -> tuple[str, str]:
    exam = _date(data, "exam")
    name = fingerprint._no_markers(fingerprint._line(data.get("exam_name"), "exam_name", required=True),
                                   "exam_name")
    return exam, " ".join(name.split())


# --- write ----------------------------------------------------------------------------

def cmd_write(data: dict) -> dict:
    _check_keys(data, {"term", "course", "date", "exam", "exam_name", "topics"})
    date = _date(data, "date")
    exam, exam_name = _exam(data)
    if exam < date:
        raise InputError(f"exam {exam} is before date {date}; a forecast is for an exam still ahead")
    items = data.get("topics")
    if not isinstance(items, list) or not items:
        raise InputError(f"topics is required (a list of 1 to {MAX_TOPICS} topics)")
    if len(items) > MAX_TOPICS:
        raise InputError(f"topics has {len(items)} entries, over the {MAX_TOPICS}-topic cap; keep the strongest")
    root, course_dir, fc, term, course = _target(data)
    fp_text = ingest.read_text(course_dir / ".state" / "fingerprint.md")
    current, prior, prior_note, _ = fingerprint.source_context(root, course_dir, fp_text)

    topics, seen, papers = [], set(), set()
    for n, entry in enumerate(items, 1):
        where = f"topics[{n}]"
        if not isinstance(entry, dict):
            raise InputError(f"{where} must be an object")
        _check_keys(entry, {"topic", "evidence", "sources"})
        topic = fingerprint._no_markers(fingerprint._line(entry.get("topic"), f"{where}.topic", required=True),
                                        f"{where}.topic")
        evidence = fingerprint._no_markers(
            fingerprint._line(entry.get("evidence"), f"{where}.evidence", required=True), f"{where}.evidence")
        if _norm(topic) in seen:
            raise InputError(f"{where}.topic {_short(topic)} repeats an earlier topic (topics are distinct "
                             "ignoring case)")
        seen.add(_norm(topic))
        srcs = fingerprint._sources(entry, where, current, prior, prior_note)
        papers |= fingerprint._counted(srcs)
        topics.append({"rank": n, "topic": topic, "evidence": evidence, "sources": [s["text"] for s in srcs]})

    conf = confidence(len(papers))
    old = ingest.read_text(fc)
    pre, blocks = _split(old)
    replaced = False
    kept = []
    for block in blocks:
        if _ident(block) == (exam, _norm(exam_name)):
            if _scored(block):
                raise InputError(f"the forecast for {exam} {_short(exam_name)} is already scored "
                                 f"({_hit_rate(block)}); a scored forecast is never rewritten")
            replaced = True
            continue
        kept.append(block)
    block = [f"## {exam} {exam_name}", f"date: {date}", f"label: {LABEL}", f"confidence: {conf}",
             "hit_rate: pending", "", *_TABLE_HEADER]
    for t in topics:
        cell = f"{t['evidence']} (source: {'; '.join(t['sources'])})"
        block.append(f"| {t['rank']} | {ingest._cell(t['topic'])} | {ingest._cell(cell)} |")
    text = _join(pre, [block, *kept])
    rec_line = record_line(record(root, (fc, text)))
    level = conf.split(" - ")[0]
    line = f"Forecast saved: {fc} ({_plural(len(topics), 'topic')}, {level} confidence)."

    workspace.build_course(root, term, course, [])  # after every check: restores a missing .state/ or file
    if text != ingest.read_text(fc):
        ingest._write_atomic(fc, text)
    return {"forecast": str(fc), "course_dir": str(course_dir), "exam": exam, "exam_name": exam_name,
            "label": LABEL, "confidence": conf, "papers": len(papers), "topics": topics, "replaced": replaced,
            "record_line": rec_line, "line": line}


# --- score ----------------------------------------------------------------------------

def cmd_score(data: dict) -> dict:
    _check_keys(data, {"term", "course", "date", "exam", "exam_name", "hits"})
    date = _date(data, "date")
    exam, exam_name = _exam(data)
    if date < exam:
        raise InputError(f"date {date} is before exam {exam}; a forecast is scored after its exam")
    hits = data.get("hits")
    if not isinstance(hits, list):
        raise InputError("hits is required (a list of the ranks that appeared, [] for none)")
    root, course_dir, fc, _, _ = _target(data)
    profile = root / ".state" / "profile.md"
    for path in (root / ".state", profile):
        if path.is_symlink():
            raise InputError(f"{path} is a symlink; refusing to write through it")
    old = ingest.read_text(fc)
    pre, blocks = _split(old)
    at = next((i for i, b in enumerate(blocks) if _ident(b) == (exam, _norm(exam_name))), None)
    if at is None:
        raise InputError(f"no forecast for {exam} {_short(exam_name)} in {fc}; nothing to score")
    block = blocks[at]
    of = min(TOP_N, _rows(block))
    if of == 0:
        raise InputError(f"the forecast for {exam} {_short(exam_name)} has no topic rows; nothing to score")
    for n, rank in enumerate(hits, 1):
        if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= of:
            raise InputError(f"hits[{n}] must be a rank from 1 to {of} (the top {of} topics): {_short(str(rank))}")
    if len(set(hits)) != len(hits):
        raise InputError("hits lists a rank more than once")
    value = f"{len(hits)} of {of}"
    new_line = f"hit_rate: {value} (scored {date})"
    idx = next((i for i, l in enumerate(block) if re.fullmatch(r"hit_rate:.*", l.strip())), None)
    if idx is None:
        conf = next((i for i, l in enumerate(block) if l.strip().startswith("confidence:")), 0)
        block.insert(conf + 1, new_line)
    else:
        block[idx] = new_line
    text = _join(pre, blocks)
    rec = record(root, (fc, text))
    prof_old = ingest.read_text(profile)
    if prof_old is None:
        raise InputError(f"no profile at {profile}")
    prof_text = _profile_text(prof_old, f"{rec[0]} of {rec[1]} across {_plural(rec[2], 'forecast')}")

    if text != old:
        ingest._write_atomic(fc, text)
    try:
        if prof_text != prof_old:
            ingest._write_atomic(profile, prof_text)
    except BaseException:
        if text != old and old is not None:
            try:
                ingest._write_atomic(fc, old)
            except OSError:
                pass  # the original failure is what gets reported
        raise
    rec_line = record_line(rec)
    line = f"Forecast for {exam_name} ({exam}): {value} top topics appeared. {rec_line}"
    return {"forecast": str(fc), "profile": str(profile), "course_dir": str(course_dir), "hit_rate": value,
            "hits": len(hits), "of": of, "record": {"hits": rec[0], "of": rec[1], "forecasts": rec[2]},
            "record_line": rec_line, "line": line}


COMMANDS = {
    "write": (cmd_write, "store one forecast block for an exam, with computed confidence"),
    "score": (cmd_score, "store a forecast's hit rate and recompute the profile's forecast record"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("forecast.py",
                             ("Mimir exam forecast. Subcommands: write, score. Reads one JSON object on stdin "
                              "and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
