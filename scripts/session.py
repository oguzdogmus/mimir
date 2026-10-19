#!/usr/bin/env python3
"""Mimir session runner: every date and clock decision a study session needs.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``plan.py`` (same folder). Run as::

    python3 session.py <start|check|clock>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Read-only: it never writes, moves or creates a file. "Now" is an
input (``now``, from ``date -Iseconds``); the clock is never read, so the same
input and files always give the same output.

Datetimes are ISO 8601 with a time, as ``plan.py`` takes them
(e.g. "2026-10-17T09:00:00+03:00"). "Today" is ``now``'s own calendar date.

Files read (all inside the learning root, see ``workspace.py``)
---------------------------------------------------------------
* ``.state/profile.md``: ``## Exam dates`` rows ``| CODE | exam | date |``
  (date ``YYYY-MM-DD`` or ``unknown``) and ``## Active courses`` rows
  ``| CODE | YYYY-Term/CODE Name |``.
* ``<course>/.state/save.md``: ``last_session:`` (``YYYY-MM-DD HH:MM`` or
  ``YYYY-MM-DD``) and ``next_topic:``.
* ``<course>/.state/mastery.md``: the table ``| topic | status | evidence |
  evidence_date | last_check | assisted | unassisted | frustration_override |``.
  Columns are found by header name (topic, status, evidence_date, assisted,
  unassisted); the first row of a topic wins. A status other than gap, shaky
  or mastered counts as unseen; a count that is not a whole number counts as
  0; an ``evidence_date`` that is not a valid date is reported as null.
* ``<course>/.state/logs/*.md`` (name order): the first ``first_contact:``
  line whose value is a date or datetime (``plan.py`` rules).
* A ``save.md`` or ``mastery.md`` that is itself a symlink reads as empty.
  Unreadable or non-UTF-8 files of courses other than the chosen one, and
  unreadable logs, are skipped. A course whose term, course or ``.state``
  folder is a symlink is never picked (naming it exits 2).

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
start -- pick the course, the exam and the class for a new session.
    in : {"now": "2026-10-17T09:00:00+03:00"}
         optional "course" (a course folder name, e.g. "CS201 Theory") and
         "term" (YYYY-Term). A term alone limits the pick to that term; a
         course name found in several terms needs its term.
    out: {"root": "/home/u/learning", "courses": [{"term": "2026-Fall",
          "course": "CS201 Theory", "course_dir": "..."}], "term":
          "2026-Fall", "course": "CS201 Theory", "course_dir": "...",
          "code": "CS201", "inferred": true, "exam": "2026-11-05",
          "exam_name": "final", "q0": false, "remaining": [{"name": "Heaps",
          "status": "gap"}, {"name": "Graphs", "status": "unseen"}],
          "class": {<plan.py class output>}, "delay_line": "Start today: ...",
          "topic": {"name": "Graphs", "status": "unseen", "evidence_date":
          null, "stale": false, "attempt_first": false}, "first_contact":
          "2026-10-10T20:00:00+03:00",
          "line": "Standard delivery: exam in 19 days"}
    Course: the given one (``inferred`` false); else the latest ``save.md``
    ``last_session:`` (ties: first by course name); else the first ``##
    Active courses`` row whose folder exists; else the last course in
    term/name order (year, then Spring < Summer < Fall < other words
    alphabetically, then course name). ``code`` is the first word of the
    course name. Exam: the earliest ``## Exam dates`` row for ``code`` dated
    today or later; else, when a row for ``code`` says ``unknown``, exam null
    with ``q0`` false; else exam null with ``q0`` true (ask "When's the
    exam?"). Rows dated more than plan.MAX_HORIZON_DAYS days ahead are
    ignored like past ones. Route: ``mastery.md`` rows in order; ``remaining`` = rows not
    ``mastered``, weight 1 each, sent to ``plan.py class`` (and ``delay``,
    whose ``line`` is ``delay_line`` for Standard only, else null). ``topic``:
    ``save.md`` ``next_topic`` when it is remaining, else the first remaining
    topic, null when none is left; its ``attempt_first`` is as in ``check``.
    ``line`` is the class line. A workspace with no course folder gives
    ``course`` null, every course field null, and the line "No course yet:
    run /mimir:setup, then /mimir:ingest."

check -- staleness and counts for named topics.
    in : {"now": "...", "term": "2026-Fall", "course": "CS201 Theory",
          "topics": ["Heaps"]}
    out: {"course_dir": "...", "topics": [{"name": "Heaps", "status": "gap",
          "evidence_date": "2026-10-01", "assisted": 1, "unassisted": 0,
          "stale": true, "attempt_first": false}],
          "line": "1 topic checked, 1 stale: Heaps."}
    Topic names match ``mastery.md`` ignoring case and repeated spaces; an
    absent topic is ``unseen``. ``stale`` = status not ``unseen`` and (no valid
    ``evidence_date``, an evidence date in the future, or evidence older than
    STALE_DAYS days). ``attempt_first`` = status not ``unseen``, ``assisted``
    at least ATTEMPT_FIRST_ASSISTED and ``unassisted`` 0 (false for an absent
    topic or one whose status reads as ``unseen``):
    the student tries a practice item before any hint or explanation.

clock -- where an episode stands.
    in : {"start": "2026-10-17T09:00:00+03:00", "now": "2026-10-17T09:21:30+03:00"}
    out: {"elapsed_minutes": 21, "phase": "wrap", "line": "Episode: 21 min, wrap up."}
    ``elapsed_minutes`` is whole minutes, rounded down. ``phase``: ``teach``
    under EPISODE_MIN_MINUTES, ``wrap`` from it to under EPISODE_MAX_MINUTES,
    ``over`` from EPISODE_MAX_MINUTES. ``now`` before ``start`` exits 2.

Exit codes: invalid input (bad field, unknown course, no workspace) exits 2
with one line on stderr (``session.py: <message>``) naming the field, and
nothing on stdout. An unexpected internal error exits 1 with ``session.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

import ingest
import plan
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

STALE_DAYS = 14
EPISODE_MIN_MINUTES = 20
EPISODE_MAX_MINUTES = 25
ATTEMPT_FIRST_ASSISTED = 3

STATUSES = ("unseen", "gap", "shaky", "mastered")
_SEASONS = ("spring", "summer", "fall")
_EXAM_TABLE = ("Exam dates", ("course", "exam", "date"))
_ACTIVE_TABLE = ("Active courses", ("course", "path"))
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_LAST_SESSION = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?: ([0-9]{2}:[0-9]{2}))?")
_COUNT = re.compile(r"[0-9]+")
_MASTERY_COLUMNS = ("topic", "status", "evidence_date", "assisted", "unassisted")


# --- Inputs ------------------------------------------------------------------------

def _moment(data: dict, field: str) -> datetime:
    """A datetime with a time; plan.py's parser, its errors as workspace.InputError."""
    if data.get(field) is None:
        raise InputError(f"{field} is required (a datetime from `date -Iseconds`)")
    try:
        return plan.parse_moment(data[field], field, need_time=True)
    except plan.InputError as exc:
        raise InputError(str(exc)) from None


def _plan(fn, payload: dict) -> dict:
    try:
        return fn(payload)
    except plan.InputError as exc:
        raise InputError(str(exc)) from None


def _valid_date(text: str) -> date | None:
    if not _DATE.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


# --- Memory file readers -------------------------------------------------------------

def _text(path: Path) -> str:
    return ingest.read_text(path) or ""


def _memory(course_dir: Path, name: str) -> str:
    """A course memory file's text; '' when it is missing or is itself a symlink."""
    path = course_dir / ".state" / name
    return "" if path.is_symlink() else _text(path)


def _key(text: str, key: str) -> str:
    """Value of the first ``key:`` line ('' when missing)."""
    for line in text.splitlines():
        m = re.fullmatch(rf"{key}:(.*)", line.strip())
        if m:
            return m.group(1).strip()
    return ""


def _section_rows(text: str, section) -> list[list[str]]:
    lines = text.splitlines()
    first, end = ingest._section_table(lines, section)  # repairs only this copy
    width = len(section[1])
    return [[ingest._unescape(c) for c in (ingest._split_row(l) + [""] * width)[:width]]
            for l in lines[first:end]]


def _norm(name: str) -> str:
    return " ".join(name.split()).casefold()


def mastery(course_dir: Path) -> list[dict]:
    """``mastery.md`` rows in route order, columns mapped by header name; the
    first row of a topic wins. The file is never changed."""
    lines = _memory(course_dir, "mastery.md").splitlines()
    rows: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if ingest._is_row(line) and not ingest._is_align(line):
            header = [c.strip().lower() for c in ingest._split_row(line)]
            if "topic" in header and "status" in header:
                cols = {name: header.index(name) for name in _MASTERY_COLUMNS if name in header}
                i += 1
                while i < len(lines) and ingest._is_row(lines[i]):
                    if not ingest._is_align(lines[i]):
                        rows.append(_mastery_row(ingest._split_row(lines[i]), cols))
                    i += 1
                break
        i += 1
    seen: set[str] = set()
    out = []
    for row in rows:
        if row["name"] and _norm(row["name"]) not in seen:
            seen.add(_norm(row["name"]))
            out.append(row)
    return out


def _mastery_row(cells: list[str], cols: dict[str, int]) -> dict:
    cells = [ingest._unescape(c).strip() for c in cells]

    def cell(name: str) -> str:
        index = cols.get(name)
        return cells[index] if index is not None and index < len(cells) else ""

    def count(name: str) -> int:
        return int(cell(name)) if _COUNT.fullmatch(cell(name)) else 0

    status = cell("status").lower()
    evidence = _valid_date(cell("evidence_date"))
    return {"name": " ".join(cell("topic").split()),
            "status": status if status in STATUSES else "unseen",
            "evidence_date": evidence.isoformat() if evidence else None,
            "assisted": count("assisted"), "unassisted": count("unassisted")}


def topic_state(row: dict | None, name: str, today: date) -> dict:
    if row is None:
        return {"name": name, "status": "unseen", "evidence_date": None,
                "assisted": 0, "unassisted": 0, "stale": False, "attempt_first": False}
    evidence = _valid_date(row["evidence_date"] or "")
    stale = row["status"] != "unseen" and (
        evidence is None or evidence > today or (today - evidence).days > STALE_DAYS)
    return {"name": row["name"], "status": row["status"], "evidence_date": row["evidence_date"],
            "assisted": row["assisted"], "unassisted": row["unassisted"], "stale": stale,
            "attempt_first": (row["status"] != "unseen" and row["assisted"] >= ATTEMPT_FIRST_ASSISTED
                              and row["unassisted"] == 0)}


def _last_session(course_dir: Path) -> str | None:
    try:
        value = _key(_memory(course_dir, "save.md"), "last_session")
    except (InputError, OSError):  # another course's unreadable save.md does not block the pick
        return None
    m = _LAST_SESSION.fullmatch(value)
    if not m or _valid_date(m.group(1)) is None:
        return None
    clock = m.group(2) or "00:00"
    hh, mm = int(clock[:2]), int(clock[3:])
    return f"{m.group(1)} {clock}" if hh < 24 and mm < 60 else None


def _first_contact(course_dir: Path) -> str | None:
    logs = course_dir / ".state" / "logs"
    try:
        if logs.is_symlink() or not logs.is_dir():
            return None
        names = sorted(p for p in logs.iterdir() if p.suffix == ".md")
    except OSError:
        return None
    for log in names:
        try:
            if log.is_symlink() or not log.is_file():
                continue
            text = _text(log)
        except (InputError, OSError):
            continue
        for line in text.splitlines():
            m = re.fullmatch(r"first_contact:(.*)", line.strip())
            if m and _valid_moment(m.group(1).strip()):
                return m.group(1).strip()
    return None


def _valid_moment(text: str) -> bool:
    """True for a date or datetime under plan.py's parse rules."""
    if not text:
        return False
    try:
        plan.parse_moment(text, "first_contact")
    except plan.InputError:
        return False
    return True


# --- Course pick ----------------------------------------------------------------------

def _term_key(term: str) -> tuple:
    year, word = term.split("-", 1)
    w = word.lower()
    return (int(year), (0, _SEASONS.index(w), "") if w in _SEASONS else (1, 0, w))


def _pick(courses: list[dict], profile: str) -> dict:
    stamped = [(c, s) for c in courses if (s := _last_session(Path(c["course_dir"])))]
    if stamped:
        latest = max(s for _, s in stamped)
        return min((c for c, s in stamped if s == latest), key=lambda c: c["course"])
    by_path = {f"{c['term']}/{c['course']}": c for c in courses}
    for _, path in _section_rows(profile, _ACTIVE_TABLE):
        hit = by_path.get(path.strip().strip("/"))
        if hit:
            return hit
    return max(courses, key=lambda c: (_term_key(c["term"]), c["course"]))


def _usable(root: Path, course: dict) -> bool:
    try:
        workspace.course_folder(root, course["term"], course["course"])
    except InputError:
        return False
    return True


def _exam(profile: str, code: str, today: date) -> tuple[str | None, str | None, bool]:
    """(exam date, exam name, q0) for the course code."""
    best, unknown = None, False
    for course, exam, when in _section_rows(profile, _EXAM_TABLE):
        if course.strip().casefold() != code.casefold():
            continue
        when = when.strip()
        if when.lower() == "unknown":
            unknown = True
            continue
        day = _valid_date(when)
        if (day is not None and 0 <= (day - today).days <= plan.MAX_HORIZON_DAYS
                and (best is None or day < best[0])):
            best = (day, exam.strip())
    if best:
        return best[0].isoformat(), best[1] or None, False
    return None, None, not unknown


# --- Subcommands ----------------------------------------------------------------------

def cmd_start(data: dict) -> dict:
    _check_keys(data, {"now", "term", "course"})
    now = _moment(data, "now")
    term = parse_term(data) if data.get("term") is not None else None
    given = parse_segment(data, "course") if data.get("course") is not None else None
    root = ingest._workspace_root()
    profile = _text(root / ".state" / "profile.md")
    courses = ingest._courses(root)
    pool = [c for c in courses if term is None or c["term"] == term]
    if given is None:  # a refused (symlinked) candidate is skipped; a given one exits 2 below
        pool = [c for c in pool if _usable(root, c)]
    empty = {"root": str(root), "courses": courses, "term": None, "course": None, "course_dir": None,
             "code": None, "inferred": None, "exam": None, "exam_name": None, "q0": None,
             "remaining": [], "class": None, "delay_line": None, "topic": None,
             "first_contact": None, "line": "No course yet: run /mimir:setup, then /mimir:ingest."}
    if given is not None:
        hits = [c for c in pool if c["course"] == given]
        if not hits:
            where = f" in term {term}" if term else ""
            raise InputError(f"course {_short(given)} has no course folder with an INDEX.md{where}")
        if len(hits) > 1:
            raise InputError(f"course {_short(given)} is in several terms; pass term")
        chosen, inferred = hits[0], False
    elif term is not None and not pool:
        raise InputError(f"term {_short(term)} has no course folder with an INDEX.md")
    elif not pool:
        return empty
    else:
        chosen, inferred = _pick(pool, profile), True

    course_dir = workspace.course_folder(root, chosen["term"], chosen["course"])
    code = chosen["course"].split()[0]
    today = now.date()
    exam, exam_name, q0 = _exam(profile, code, today)
    rows = mastery(course_dir)
    remaining = [r for r in rows if r["status"] != "mastered"]
    payload = {"now": data["now"], "exam": exam,
               "topics": [{"name": r["name"], "weight": 1} for r in remaining], "timed": []}
    klass = _plan(plan.delivery_class, payload)
    delay_line = _plan(plan.cost_of_delay, payload)["line"] if klass["class"] == "Standard" else None
    next_topic = _norm(_key(_memory(course_dir, "save.md"), "next_topic"))
    pick = next((r for r in remaining if next_topic and _norm(r["name"]) == next_topic),
                remaining[0] if remaining else None)
    topic = None
    if pick is not None:
        state = topic_state(pick, pick["name"], today)
        topic = {k: state[k] for k in ("name", "status", "evidence_date", "stale", "attempt_first")}
    return {"root": str(root), "courses": courses, "term": chosen["term"], "course": chosen["course"],
            "course_dir": str(course_dir), "code": code, "inferred": inferred, "exam": exam,
            "exam_name": exam_name, "q0": q0,
            "remaining": [{"name": r["name"], "status": r["status"]} for r in remaining],
            "class": klass, "delay_line": delay_line, "topic": topic,
            "first_contact": _first_contact(course_dir), "line": klass["line"]}


def cmd_check(data: dict) -> dict:
    _check_keys(data, {"now", "term", "course", "topics"})
    now = _moment(data, "now")
    term, course = parse_term(data), parse_segment(data, "course")
    names = data.get("topics")
    if not isinstance(names, list) or not names:
        raise InputError("topics is required (a non-empty list of topic names)")
    for n, name in enumerate(names, 1):
        if not isinstance(name, str) or not name.strip() or _has_control(name):
            raise InputError(f"topics[{n}] must be a one-line topic name")
    root = ingest._workspace_root()
    course_dir = workspace.course_folder(root, term, course)
    if not (course_dir / "INDEX.md").is_file():
        raise InputError(f"course {_short(course)} has no course folder with an INDEX.md in term {term}")
    rows = {_norm(r["name"]): r for r in mastery(course_dir)}
    today = now.date()
    out = [topic_state(rows.get(_norm(name)), " ".join(name.split()), today) for name in names]
    stale = [t["name"] for t in out if t["stale"]]
    noun = "topic" if len(out) == 1 else "topics"
    line = f"{len(out)} {noun} checked, {len(stale)} stale" + (f": {', '.join(stale)}." if stale else ".")
    return {"course_dir": str(course_dir), "topics": out, "line": line}


def cmd_clock(data: dict) -> dict:
    _check_keys(data, {"start", "now"})
    start, now = _moment(data, "start"), _moment(data, "now")
    if (start.tzinfo is None) != (now.tzinfo is None):
        raise InputError("now and start mix values with and without a UTC offset")
    if now < start:
        raise InputError("now is before start")
    seconds = (now - start).total_seconds()
    minutes = int(seconds // 60)
    if seconds < EPISODE_MIN_MINUTES * 60:
        phase, what = "teach", "keep teaching"
    elif seconds < EPISODE_MAX_MINUTES * 60:
        phase, what = "wrap", "wrap up"
    else:
        phase, what = "over", "close now"
    return {"elapsed_minutes": minutes, "phase": phase, "line": f"Episode: {minutes} min, {what}."}


COMMANDS = {
    "start": (cmd_start, "pick the course, exam, delivery class and first topic for a session"),
    "check": (cmd_check, "status, counts and staleness for named topics"),
    "clock": (cmd_clock, "elapsed episode minutes and phase (teach, wrap, over)"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("session.py",
                             ("Mimir session runner. Subcommands: start, check, clock. Reads one JSON "
                              "object on stdin and prints one JSON object on stdout. Writes nothing."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
