#!/usr/bin/env python3
"""Mimir session runner: every date and clock decision a study session needs.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``plan.py`` (same folder). Run as::

    python3 session.py <now|parse-date|start|check|clock|debrief|progress|record>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Only record writes mastery.md atomically; other commands are read-only. Only ``now``
reads the clock; every other subcommand takes "now" as an input (``now``, from
``session.py now``), so the same input and files always give the same output.

Datetimes are ISO 8601 with a time, as ``plan.py`` takes them
(e.g. "2026-10-17T09:00:00+03:00"). "Today" is ``now``'s own calendar date.

Files read (all inside the learning root, see ``workspace.py``)
---------------------------------------------------------------
* ``.state/profile.md``: ``## Exam dates`` rows ``| CODE | exam | date |``
  (date ``YYYY-MM-DD`` or ``unknown``) and ``## Active courses`` rows
  ``| CODE | YYYY-Term/CODE Name |``.
* ``<course>/.state/save.md``: ``last_session:`` (``YYYY-MM-DD HH:MM`` or
  ``YYYY-MM-DD``), ``next_topic:`` and ``pending_debrief:`` (``YYYY-MM-DD
  <exam name>``; ``no``, empty or anything else means none pending).
* ``<course>/.state/mastery.md``: the table ``| topic | status | evidence |
  evidence_date | last_check | assisted | unassisted | frustration_override |``.
  Columns are found by header name (topic, status, evidence, evidence_date,
  last_check, assisted, unassisted, frustration_override); the first row of a
  topic wins. A status other than gap, shaky or mastered counts as unseen; a
  count that is not a whole number counts as 0; an ``evidence_date`` or
  ``last_check`` that is not a valid date is reported as null; ``evidence``
  and ``frustration_override`` are the cell text, trimmed.
* ``<course>/INDEX.md``: the ``## Registry`` roles and ``## Topics`` names
  (``ingest.py`` rules; a non-UTF-8 one exits 2) for the route.
* ``<course>/.state/logs/*.md`` (name order): the first ``first_contact:``
  line whose value is a date or datetime (``plan.py`` rules); for ``debrief``
  also ``started:``/``ended:`` datetimes, ``- `` lines under ``## Verifier
  disagreements``, and ``next_course_offer:`` lines in every course of the
  term. Symlinked, unreadable or non-UTF-8 logs are skipped.
* A ``save.md`` or ``mastery.md`` that is itself a symlink reads as empty.
  Unreadable or non-UTF-8 files of courses other than the chosen one, and
  unreadable logs, are skipped. A course whose term, course or ``.state``
  folder is a symlink is never picked (naming it exits 2).

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
now -- the local time, the one clock read of a session. Standard library only,
    so the same on Linux, macOS and Windows.
    in : {}
    out: {"now": "2026-10-17T09:05:07+03:00", "date": "2026-10-17",
          "log_name": "2026-10-17-0905", "last_session": "2026-10-17 09:05",
          "term": "2026-Fall", "line": "Now: 2026-10-17T09:05:07+03:00."}
    ``now`` is ISO 8601 to the second with the local UTC offset (the session
    timestamp); ``date`` the evidence date; ``log_name`` the log file name
    without ``.md``; ``last_session`` the ``save.md`` stamp; ``term`` the
    fallback term by month: Jan-May Spring, Jun-Aug Summer, Sep-Dec Fall.

parse-date -- the student's exam-date phrase as a date, or a refusal.
    in : {"now": "2026-10-17T09:00:00+03:00", "phrase": "Friday"}
    out: {"date": "2026-10-23", "line": "Exam date: 2026-10-23."}
    Only these phrases, ignoring case and extra spaces: ``YYYY-MM-DD``;
    ``today``; ``tomorrow``; a full English weekday name (``friday``), the
    next such day counting today, so today's own weekday name means today;
    ``N days`` or ``in N days`` (N a whole number). Today is
    ``now``'s own calendar date. This is not natural-language date parsing:
    anything else ("Nov 5", "5/11", "next friday", "fri") exits 2 as
    unsupported. A date that does not exist, is before today, or is more than
    plan.MAX_HORIZON_DAYS days after today also exits 2.

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
          null, "stale": false, "attempt_first": false}, "route_line": null, "first_contact":
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
    ignored like past ones. Route: ``mastery.md`` rows in order; when the
    ``INDEX.md`` registry has no ``outline`` row, each ``## Topics`` name not
    yet listed (ignoring case and repeated spaces) follows as an unseen row,
    in ``INDEX.md`` order. ``remaining`` = route rows not
    ``mastered``, weight 1 each, sent to ``plan.py class`` (and ``delay``,
    whose ``line`` is ``delay_line`` for Standard only, else null). ``topic``:
    ``save.md`` ``next_topic`` when it is remaining, else the first remaining
    topic; with none remaining, the same pick among the stale mastered topics
    (stale as in ``check``: the one-question recheck); else null. Its
    ``attempt_first`` is as in ``check``. ``route_line``: null when ``topic``
    is set; else "No topics on the route yet: drop the outline, slides or
    past papers into `_inbox/` and run mimir-ingest." for an empty route, or
    "Your route is complete: every topic is mastered in mastery.md. Want a
    `mimir-quiz` to keep it fresh?". ``line`` is the class line. ``debrief``: null when ``pending_debrief:``
    holds no valid date P; else {"exam", "exam_name", "due", "deferred"}.
    P today or later: P with the pending name, due and deferred false (a
    date-only exam is past only from the next day, as in ``plan.py``). P
    before today: the target exam is the latest ``## Exam dates`` row of
    ``code`` dated after P and before today (a later passed exam supersedes;
    debriefs never stack), else P (named by the pending value, else by a row
    dated P); ``deferred`` = the class is Urgent, ``due`` = not deferred.
    A workspace with no course folder gives
    ``course`` null, every course field null, and the line "No course yet:
    run mimir-setup, then mimir-ingest."

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

debrief -- what the post-exam debrief needs. Read-only, like the rest.
    in : as ``start`` ({"now": ..., optional "term" and "course"}).
    out: {"term": "2026-Fall", "course": "CS201 Theory", "course_dir": "...",
          "code": "CS201", "inferred": false, "debrief": {"exam":
          "2026-11-05", "exam_name": "final", "due": true, "deferred": false},
          "cram": {<plan.py debrief output>}, "disagreements": ["- item 2:
          ..."], "offer_next_course": true, "line": "Cram bill: ..."}
    ``debrief`` is ``start``'s. Not due: ``cram``, ``disagreements`` and
    ``offer_next_course`` are null and ``line`` says why ("No debrief
    pending for <course>.", "Debrief opens after your <name, else exam> on
    <date>.", "Debrief waits until after your <next exam name, else exam>:
    today is for that.", or, with no next exam, "Debrief waits for a calmer
    session: today is for your exam."; no course: ``start``'s line). Due,
    with target T and previous exam B (the latest row of ``code`` dated
    before T, none when there is none):
    * ``cram``: ``plan.py debrief`` with ``first_contact`` (as in ``start``),
      ``exam`` T, every route row (as in ``start``) weight 1, ``timed`` [] and the
      sessions: each log's ``started:`` and the next ``ended:`` after it,
      kept when the start's own calendar date is after B and on or before T;
      a pair that ends before it starts, overlaps an earlier kept pair or
      mixes offset/no-offset with ``now`` is dropped. ``cram`` is null (line
      "Cram bill: no study sessions logged.") when ``first_contact`` is null,
      after T, or not comparable with ``now``. ``line`` is ``cram.line``.
    * ``disagreements``: distinct non-empty ``- `` lines under ``## Verifier
      disagreements`` (up to the next line starting with ``#``) in logs named
      ``YYYY-MM-DD-HHMM[-suffix].md`` whose date is after B and on or before
      T, in name order.
    * ``offer_next_course``: false when any log of any course in the same
      term has a ``next_course_offer:`` line, else true.

progress -- what Mimir believes the student knows. Read-only; never calls plan.py.
    in : as ``start`` ({"now": ..., optional "term" and "course"}).
    out: {"courses": [<as start>], "term": "2026-Fall", "course": "CS201 Theory",
          "course_dir": "...", "code": "CS201", "inferred": true, "topics": [{"name": "Heaps",
          "status": "mastered", "evidence": "solved heap sort alone",
          "evidence_date": "2026-10-01", "last_check": "2026-10-01",
          "assisted": 0, "unassisted": 1, "frustration_override": "",
          "stale": true}], "counts": {"unseen": 0, "gap": 0, "shaky": 0,
          "mastered": 1}, "table": "| Topic | Status | ...",
          "line": "CS201 Theory: 1 of 1 topics mastered, 0 shaky, 0 gap,
          0 unseen; 1 due a recheck."}
    Course pick, ``inferred`` and errors are ``start``'s. ``topics``: every
    route row (as in ``start``) in order; ``stale`` as in ``check``. ``table``:
    ``| Topic | Status | Evidence | Evidence date | Solved alone / with help |
    Recheck |``, one row per topic, ``-`` for empty evidence or a null date,
    Recheck ``due`` when stale, cells escaped as ``INDEX.md`` cells. ``line``
    ends "; none due a recheck." when no topic is stale. No rows: ``topics``
    [], ``table`` null, line ``start``'s empty-route ``route_line``. No course: ``start``'s line,
    ``courses`` as ``start``'s, every other field null.

record -- persist an eligible answer or a frustration override.
    Required: term, course, topic, item (stable identity), gate (the verifier
    result), outcome (unassisted|assisted|wrong), real_past_paper (boolean),
    session (unique identity), date (YYYY-MM-DD). Optional override and
    explanation_only booleans distinguish control events from item attempts.
    Alternatively {term, course, topic, initialize: true} adds an unseen topic.
    Returns status, recorded, duplicate and line. See the shared recording
    reference for examples and audit D2/D5 for exact transition semantics.
    Legacy Markdown is retained; recorder-owned JSON in a trailing comment
    supplies authoritative rows to check, start and progress.

Exit codes: invalid input (bad field, unknown course, no workspace) exits 2
with one line on stderr (``session.py: <message>``) naming the field, and
nothing on stdout. An unexpected internal error exits 1 with ``session.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import re
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import ingest
import plan
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

STALE_DAYS = 14
EPISODE_MIN_MINUTES = 20
EPISODE_MAX_MINUTES = 25
ATTEMPT_FIRST_ASSISTED = 3

NO_ROUTE_LINE = ("No topics on the route yet: drop the outline, slides or past papers into `_inbox/` "
                 "and run mimir-ingest.")
ROUTE_DONE_LINE = ("Your route is complete: every topic is mastered in mastery.md. "
                   "Want a `mimir-quiz` to keep it fresh?")

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")  # date.weekday() order
STATUSES = ("unseen", "gap", "shaky", "mastered")
_EXAM_TABLE = ("Exam dates", ("course", "exam", "date"))
_ACTIVE_TABLE = ("Active courses", ("course", "path"))
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_LAST_SESSION = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?: ([0-9]{2}:[0-9]{2}))?")
_COUNT = re.compile(r"[0-9]+")
_RELATIVE = re.compile(r"(?:in )?([0-9]+) days?")
_MASTERY_COLUMNS = ("topic", "status", "evidence", "evidence_date", "last_check", "assisted", "unassisted",
                    "frustration_override")


# --- Inputs ------------------------------------------------------------------------

def _moment(data: dict, field: str) -> datetime:
    """A datetime with a time; plan.py's parser, its errors as workspace.InputError."""
    if data.get(field) is None:
        raise InputError(f"{field} is required (a datetime from `session.py now`)")
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
    for key, entry in _record_state(_memory(course_dir, "mastery.md")).items():
        position = next((i for i, r in enumerate(out) if _norm(r["name"]) == key), len(out))
        if position == len(out):
            out.append(entry["row"])
        else:
            out[position] = entry["row"]
    return out


def route(course_dir: Path) -> list[dict]:
    """The route: ``mastery.md`` rows in order. When no ``outline`` file is in the
    ``INDEX.md`` registry, each ``## Topics`` name not yet listed follows as an unseen
    row, in ingestion order (decision D1). Nothing is written."""
    rows = mastery(course_dir)
    index = course_dir / "INDEX.md"
    if any(role == "outline" for role, _, _ in ingest.registry(index).values()):
        return rows
    seen = {_norm(r["name"]) for r in rows}
    for name in ingest.topics(index):
        if _norm(name) not in seen:
            seen.add(_norm(name))
            rows.append(_mastery_row([name], {"topic": 0}))  # an unseen row
    return rows


def _mastery_row(cells: list[str], cols: dict[str, int]) -> dict:
    cells = [ingest._unescape(c).strip() for c in cells]

    def cell(name: str) -> str:
        index = cols.get(name)
        return cells[index] if index is not None and index < len(cells) else ""

    def count(name: str) -> int:
        return int(cell(name)) if _COUNT.fullmatch(cell(name)) else 0

    def day(name: str) -> str | None:
        value = _valid_date(cell(name))
        return value.isoformat() if value else None

    status = cell("status").lower()
    return {"name": " ".join(cell("topic").split()),
            "status": status if status in STATUSES else "unseen",
            "evidence": cell("evidence"), "evidence_date": day("evidence_date"),
            "last_check": day("last_check"), "assisted": count("assisted"),
            "unassisted": count("unassisted"), "frustration_override": cell("frustration_override")}


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


def _logs(course_dir: Path) -> list[tuple[str, str]]:
    """(name, text) of each readable ``.state/logs/*.md`` in name order; symlinks,
    unreadable and non-UTF-8 logs are skipped."""
    logs = course_dir / ".state" / "logs"
    try:
        if logs.is_symlink() or not logs.is_dir():
            return []
        names = sorted(p for p in logs.iterdir() if p.suffix == ".md")
    except OSError:
        return []
    out = []
    for log in names:
        try:
            if log.is_symlink() or not log.is_file():
                continue
            out.append((log.name, _text(log)))
        except (InputError, OSError):
            continue
    return out


def _first_contact(course_dir: Path) -> str | None:
    for _, text in _logs(course_dir):
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
    return max(courses, key=lambda c: (workspace.term_key(c["term"]), c["course"]))


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


# --- Debrief ------------------------------------------------------------------------

_PENDING = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:\s+(.*))?")
_LOG_NAME = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})-[0-9]{4}(?:-[^/]*)?\.md")
_NO_CRAM_LINE = "Cram bill: no study sessions logged."
NO_COURSE_LINE = "No course yet: run mimir-setup, then mimir-ingest."


def _code_exams(profile: str, code: str) -> list[tuple[date, str]]:
    """Dated ``## Exam dates`` rows of a course code, in file order."""
    out = []
    for course, exam, when in _section_rows(profile, _EXAM_TABLE):
        day = _valid_date(when.strip())
        if course.strip().casefold() == code.casefold() and day is not None:
            out.append((day, " ".join(exam.split())))
    return out


def _pending(save: str) -> tuple[date, str | None] | None:
    """``pending_debrief: YYYY-MM-DD <name>`` as (date, name); None when no, empty or malformed."""
    m = _PENDING.fullmatch(_key(save, "pending_debrief"))
    day = _valid_date(m.group(1)) if m else None
    if day is None:
        return None
    return day, " ".join((m.group(2) or "").split()) or None


def _debrief_target(profile: str, code: str, pending: date, pending_name: str | None,
                    today: date) -> tuple[date, str | None, date | None]:
    """(target exam date, its name, previous exam date or None).

    Target: the latest row of the code dated from the day after ``pending``
    to yesterday (a later passed exam supersedes; ties: the first such row),
    else ``pending`` itself, named by ``pending_name``, else by the first named
    row dated ``pending``. Previous: the latest row of the code dated before
    the target."""
    rows = _code_exams(profile, code)
    passed = [(day, exam) for day, exam in rows if pending < day < today]
    target, name = pending, pending_name
    if passed:
        target = max(day for day, _ in passed)
        name = next(exam for day, exam in passed if day == target) or None
    elif name is None:
        name = next((exam for day, exam in rows if day == pending and exam), None)
    before = [day for day, _ in rows if day < target]
    return target, name, max(before) if before else None


def debrief_state(profile: str, save: str, code: str, today: date,
                  klass: str | None) -> tuple[dict | None, tuple[date, date | None] | None]:
    """(``start``'s ``debrief``, the due window (target, previous exam) or None).
    The state is null with no valid pending value."""
    pending = _pending(save)
    if pending is None:
        return None, None
    day, name = pending
    if day >= today:  # a date-only exam is past only from the next day
        return {"exam": day.isoformat(), "exam_name": name, "due": False, "deferred": False}, None
    target, target_name, previous = _debrief_target(profile, code, day, name, today)
    deferred = klass == "Urgent"
    state = {"exam": target.isoformat(), "exam_name": target_name, "due": not deferred,
             "deferred": deferred}
    return state, None if deferred else (target, previous)


def _sessions(logs: list[tuple[str, str]], after: date | None, until: date,
              aware: bool) -> list[dict]:
    """Logged ``started:``/next ``ended:`` pairs that started in (after, until]."""
    kept: list[tuple[datetime, datetime]] = []
    for _, text in logs:
        start = None
        for line in text.splitlines():
            m = re.fullmatch(r"(started|ended):(.*)", line.strip())
            if not m:
                continue
            try:
                moment = plan.parse_moment(m.group(2).strip(), m.group(1), need_time=True)
            except plan.InputError:
                if m.group(1) == "started":
                    start = None
                continue
            if m.group(1) == "started":
                start = moment
                continue
            if start is None:
                continue
            begin, end, start = start, moment, None
            if (begin.tzinfo is not None) != aware or (end.tzinfo is not None) != aware:
                continue
            if end < begin or begin.date() > until or (after is not None and begin.date() <= after):
                continue
            if any(begin < k_end and k_begin < end for k_begin, k_end in kept):
                continue
            kept.append((begin, end))
    return [{"start": b.isoformat(), "end": e.isoformat()} for b, e in kept]


def _disagreements(logs: list[tuple[str, str]], after: date | None, until: date) -> list[str]:
    out: list[str] = []
    for name, text in logs:
        m = _LOG_NAME.fullmatch(name)
        day = _valid_date(m.group(1)) if m else None
        if day is None or day > until or (after is not None and day <= after):
            continue
        inside = False
        for line in text.splitlines():
            if line.startswith("#"):
                inside = line.rstrip() == "## Verifier disagreements"
            elif inside and line.startswith("- ") and line[2:].strip() and line.strip() not in out:
                out.append(line.strip())
    return out


def _offer_next_course(root: Path, term: str) -> bool:
    for course in ingest._courses(root):
        if course["term"] != term or not _usable(root, course):
            continue
        for _, text in _logs(Path(course["course_dir"])):
            if any(re.fullmatch(r"next_course_offer:.*", row.strip()) for row in text.splitlines()):
                return False
    return True


def _cram(course_dir: Path, logs, first_contact: str | None, target: date,
          previous: date | None, now: datetime) -> dict | None:
    if first_contact is None:
        return None
    contact = plan.parse_moment(first_contact, "first_contact")
    aware = now.tzinfo is not None
    if not plan.is_date_only(contact) and (contact.tzinfo is not None) != aware:
        return None  # cannot be compared with the logged sessions
    contact_day = contact if plan.is_date_only(contact) else contact.date()
    if contact_day > target:
        return None
    payload = {"first_contact": first_contact, "exam": target.isoformat(),
               "topics": [{"name": r["name"], "weight": 1} for r in route(course_dir)],
               "timed": [], "sessions": _sessions(logs, previous, target, aware)}
    return _plan(plan.debrief, payload)


# --- Subcommands ----------------------------------------------------------------------

def plan_payload(now: str, exam: str | None, remaining: list[dict]) -> dict:
    """The ``plan.py`` class/delay input for a route: each remaining topic weighs 1."""
    return {"now": now, "exam": exam, "topics": [{"name": r["name"], "weight": 1} for r in remaining],
            "timed": []}


def cmd_start(data: dict) -> dict:
    return _start(data)[0]


def _course_pick(data: dict) -> tuple[datetime, Path, str, list[dict], dict | None, bool | None,
                                      Path | None]:
    """(now, root, profile text, courses, chosen course or None, inferred, its folder) for
    ``start``'s input; the course pick and its errors are ``start``'s."""
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
        return now, root, profile, courses, None, None, None
    else:
        chosen, inferred = _pick(pool, profile), True
    course_dir = workspace.course_folder(root, chosen["term"], chosen["course"])
    return now, root, profile, courses, chosen, inferred, course_dir


def _start(data: dict) -> tuple[dict, tuple[date, date | None] | None]:
    """``start``'s output and the due debrief window (see ``debrief_state``)."""
    now, root, profile, courses, chosen, inferred, course_dir = _course_pick(data)
    if chosen is None:
        return {"root": str(root), "courses": courses, "term": None, "course": None, "course_dir": None,
                "code": None, "inferred": None, "exam": None, "exam_name": None, "q0": None,
                "remaining": [], "class": None, "delay_line": None, "topic": None, "route_line": None,
                "first_contact": None, "debrief": None, "line": NO_COURSE_LINE}, None
    code = chosen["course"].split()[0]
    today = now.date()
    exam, exam_name, q0 = _exam(profile, code, today)
    rows = route(course_dir)
    remaining = [r for r in rows if r["status"] != "mastered"]
    payload = plan_payload(data["now"], exam, remaining)
    klass = _plan(plan.delivery_class, payload)
    delay_line = _plan(plan.cost_of_delay, payload)["line"] if klass["class"] == "Standard" else None
    save = _memory(course_dir, "save.md")
    next_topic = _norm(_key(save, "next_topic"))
    # Nothing unmastered left: a stale mastered topic gets the one-question recheck.
    candidates = remaining or [r for r in rows if topic_state(r, r["name"], today)["stale"]]
    pick = next((r for r in candidates if next_topic and _norm(r["name"]) == next_topic),
                candidates[0] if candidates else None)
    debrief, window = debrief_state(profile, save, code, today, klass["class"])
    topic = None
    if pick is not None:
        state = topic_state(pick, pick["name"], today)
        topic = {k: state[k] for k in ("name", "status", "evidence_date", "stale", "attempt_first")}
    route_line = None if pick is not None else ROUTE_DONE_LINE if rows else NO_ROUTE_LINE
    return {"root": str(root), "courses": courses, "term": chosen["term"], "course": chosen["course"],
            "course_dir": str(course_dir), "code": code, "inferred": inferred, "exam": exam,
            "exam_name": exam_name, "q0": q0,
            "remaining": [{"name": r["name"], "status": r["status"]} for r in remaining],
            "class": klass, "delay_line": delay_line, "topic": topic, "route_line": route_line,
            "first_contact": _first_contact(course_dir),
            "debrief": debrief, "line": klass["line"]}, window


def cmd_debrief(data: dict) -> dict:
    st, window = _start(data)
    out = {"term": st["term"], "course": st["course"], "course_dir": st["course_dir"],
           "code": st["code"], "inferred": st["inferred"], "debrief": st["debrief"],
           "cram": None, "disagreements": None, "offer_next_course": None}
    state = st["debrief"]
    if st["course"] is None:
        return {**out, "line": st["line"]}
    if state is None:
        return {**out, "line": f"No debrief pending for {st['course']}."}
    if state["deferred"]:
        if st["exam"] is None:
            return {**out, "line": "Debrief waits for a calmer session: today is for your exam."}
        upcoming = st["exam_name"] or "exam"
        return {**out, "line": f"Debrief waits until after your {upcoming}: today is for that."}
    if window is None:
        return {**out, "line": f"Debrief opens after your {state['exam_name'] or 'exam'} on {state['exam']}."}
    now = _moment(data, "now")
    root = Path(st["root"])
    course_dir = Path(st["course_dir"])
    target, previous = window
    logs = _logs(course_dir)
    cram = _cram(course_dir, logs, st["first_contact"], target, previous, now)
    return {**out, "cram": cram, "disagreements": _disagreements(logs, previous, target),
            "offer_next_course": _offer_next_course(root, st["term"]),
            "line": cram["line"] if cram else _NO_CRAM_LINE}


_PROGRESS_HEAD = ("| Topic | Status | Evidence | Evidence date | Solved alone / with help | Recheck |\n"
                  "|---|---|---|---|---|---|")


def cmd_progress(data: dict) -> dict:
    now, _, _, courses, chosen, inferred, course_dir = _course_pick(data)
    if chosen is None:
        return {"courses": courses, "term": None, "course": None, "course_dir": None, "code": None,
                "inferred": None, "topics": None, "counts": None, "table": None, "line": NO_COURSE_LINE}
    today = now.date()
    topics = []
    for row in route(course_dir):
        state = topic_state(row, row["name"], today)
        topics.append({"name": row["name"], "status": row["status"], "evidence": row["evidence"],
                       "evidence_date": row["evidence_date"], "last_check": row["last_check"],
                       "assisted": row["assisted"], "unassisted": row["unassisted"],
                       "frustration_override": row["frustration_override"], "stale": state["stale"]})
    counts = {s: sum(1 for t in topics if t["status"] == s) for s in STATUSES}
    out = {"courses": courses, "term": chosen["term"], "course": chosen["course"],
           "course_dir": str(course_dir),
           "code": chosen["course"].split()[0], "inferred": inferred, "topics": topics, "counts": counts}
    if not topics:
        return {**out, "table": None, "line": NO_ROUTE_LINE}
    rows = [_PROGRESS_HEAD] + [
        "| " + " | ".join(ingest._cell(c) for c in (
            t["name"], t["status"], t["evidence"] or "-", t["evidence_date"] or "-",
            f"{t['unassisted']} / {t['assisted']}", "due" if t["stale"] else "")) + " |"
        for t in topics]
    due = sum(1 for t in topics if t["stale"])
    if counts["unseen"] == len(topics):
        line = (f"{chosen['course']}: nothing studied yet, so no topic has evidence "
                f"({len(topics)} unseen). Run mimir-study to start.")
    else:
        line = (f"{chosen['course']}: {counts['mastered']} of {len(topics)} topics mastered, "
                f"{counts['shaky']} shaky, {counts['gap']} gap, {counts['unseen']} unseen; "
                + (f"{due} due a recheck." if due else "none due a recheck."))
    return {**out, "table": "\n".join(rows), "line": line}


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


def _clock() -> datetime:
    """The local wall clock with its UTC offset, to the second. Only ``now`` reads it."""
    return datetime.now().astimezone()


def _season(month: int) -> str:
    return "Spring" if month <= 5 else "Summer" if month <= 8 else "Fall"


def cmd_now(data: dict) -> dict:
    _check_keys(data, set())
    now = _clock().replace(microsecond=0)
    stamp = now.isoformat()
    return {"now": stamp, "date": now.date().isoformat(), "log_name": now.strftime("%Y-%m-%d-%H%M"),
            "last_session": now.strftime("%Y-%m-%d %H:%M"), "term": f"{now.year}-{_season(now.month)}",
            "line": f"Now: {stamp}."}


def cmd_parse_date(data: dict) -> dict:
    _check_keys(data, {"now", "phrase"})
    today = _moment(data, "now").date()
    phrase = data.get("phrase")
    if not isinstance(phrase, str):
        raise InputError("phrase is required (the student's exam-date phrase)")
    text = " ".join(phrase.split()).casefold()
    if not text:
        raise InputError("phrase is empty")
    relative = _RELATIVE.fullmatch(text)
    horizon = today + timedelta(days=plan.MAX_HORIZON_DAYS)
    if text == "today":
        day = today
    elif text == "tomorrow":
        day = today + timedelta(days=1)
    elif relative:
        count = int(relative.group(1))
        day = today + timedelta(days=count) if count <= plan.MAX_HORIZON_DAYS else horizon + timedelta(days=1)
    elif text in WEEKDAYS:
        day = today + timedelta(days=(WEEKDAYS.index(text) - today.weekday()) % 7)
    elif _DATE.fullmatch(text):
        day = _valid_date(text)
        if day is None:
            raise InputError(f"phrase {_short(phrase)} is not a real date")
    else:
        raise InputError(f"phrase {_short(phrase)} is unsupported (use YYYY-MM-DD, today, tomorrow, "
                         "a weekday name or \"in N days\")")
    if day < today:
        raise InputError(f"phrase {_short(phrase)} is in the past ({day.isoformat()})")
    if day > horizon:
        raise InputError(f"phrase {_short(phrase)} is more than {plan.MAX_HORIZON_DAYS} days ahead")
    return {"date": day.isoformat(), "line": f"Exam date: {day.isoformat()}."}


def _record_state(text: str) -> dict:
    marker = "<!-- mimir-record-v1 "
    lines = [line for line in text.splitlines() if line.startswith(marker)]
    if not lines:
        return {}
    try:
        state = json.loads(lines[-1][len(marker):-4])
        if not isinstance(state, dict):
            raise ValueError()
        return state
    except (ValueError, TypeError):
        raise InputError("mastery record state is damaged; restore it before recording") from None


def _save_record(path: Path, text: str, state: dict) -> None:
    lines = [l for l in text.splitlines() if not l.startswith("<!-- mimir-record-v1 ")]
    encoded = json.dumps(state, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e")
    ingest._write_atomic(path, "\n".join(lines) + "\n<!-- mimir-record-v1 " + encoded + " -->\n")


def _initial_record(row: dict) -> dict:
    recent = ([{"date": row["evidence_date"], "evidence": row["evidence"]}]
              if row["evidence_date"] and row["evidence"] else [])
    return {"row": row, "attempts": [], "solves": [], "recent": recent,
            "blocked_session": "legacy" if row["frustration_override"] else None}


def cmd_record(data: dict) -> dict:
    """Record an idempotent attempt; retain legacy text and atomic authoritative state."""
    if data.get("initialize") is True:
        _check_keys(data, {"term", "course", "topic", "initialize"})
        term, course = parse_term(data), parse_segment(data, "course")
        topic = data.get("topic")
        if not isinstance(topic, str) or not topic.strip() or _has_control(topic):
            raise InputError("topic must be a nonempty one-line string")
        folder = workspace.course_folder(ingest._workspace_root(), term, course)
        if not (folder / "INDEX.md").is_file():
            raise InputError("course has no INDEX.md")
        path = folder / ".state" / "mastery.md"
        if path.is_symlink():
            raise InputError("mastery.md must not be a symlink")
        rows = mastery(folder)
        existing = next((r for r in rows if _norm(r["name"]) == _norm(topic)), None)
        if existing:
            return {"status": existing["status"], "recorded": False, "duplicate": True,
                    "line": "Topic already initialized."}
        text = _memory(folder, "mastery.md")
        state = _record_state(text)
        state[_norm(topic)] = _initial_record(_mastery_row([topic], {"topic": 0}))
        _save_record(path, text, state)
        return {"status": "unseen", "recorded": True, "duplicate": False,
                "line": "Topic initialized."}
    _check_keys(data, {"term", "course", "topic", "item", "gate", "outcome",
                       "real_past_paper", "session", "date", "override", "explanation_only"})
    term, course = parse_term(data), parse_segment(data, "course")
    for field in ("topic", "item", "session", "date"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or _has_control(value):
            raise InputError(f"{field} must be a nonempty one-line string")
    day = _valid_date(data["date"])
    if day is None:
        raise InputError("date must be YYYY-MM-DD")
    if data.get("outcome") not in ("unassisted", "assisted", "wrong"):
        raise InputError("outcome must be unassisted, assisted or wrong")
    for field in ("real_past_paper", "override", "explanation_only"):
        if type(data.get(field, False)) is not bool:
            raise InputError(f"{field} must be boolean")
    if "real_past_paper" not in data:
        raise InputError("real_past_paper is required")
    gate = data.get("gate")
    if not isinstance(gate, dict) or gate.get("decision") not in ("show", "flagged", "drop", "verify"):
        raise InputError("gate must contain a valid decision")
    if type(gate.get("counts_for_mastery")) is not bool:
        raise InputError("gate.counts_for_mastery must be boolean")
    folder = workspace.course_folder(ingest._workspace_root(), term, course)
    if not (folder / "INDEX.md").is_file():
        raise InputError("course has no INDEX.md")
    path = folder / ".state" / "mastery.md"
    if path.is_symlink():
        raise InputError("mastery.md must not be a symlink")
    text = _memory(folder, "mastery.md")
    state = _record_state(text)
    key = _norm(data["topic"])
    legacy = next((r for r in mastery(folder) if _norm(r["name"]) == key),
                  _mastery_row([data["topic"]], {"topic": 0}))
    entry = state.get(key, _initial_record(legacy))
    row = entry["row"]
    result = {"status": row["status"], "duplicate": False, "recorded": False}
    identity = [data["session"], data["item"], bool(data.get("override"))]
    if identity in entry["attempts"]:
        return {**result, "duplicate": True, "line": "Attempt already recorded."}
    override = data.get("override", False)
    explanation = override and data.get("explanation_only", False) and gate["decision"] == "drop"
    if not explanation and (gate["decision"] != "show" or not gate["counts_for_mastery"]):
        return {**result, "line": "Attempt does not count: item is flagged or not shown."}
    if entry["blocked_session"] == data["session"] and not override:
        return {**result, "line": "After frustration override, not counted."}
    if entry.get("last_date") and data["date"] < entry["last_date"]:
        raise InputError("date precedes the latest recorded attempt")
    entry["attempts"].append(identity)
    entry["last_date"] = data["date"]
    outcome = data["outcome"]
    if override:
        row["status"] = "shaky"
        row["frustration_override"] = data["date"]
        entry["blocked_session"] = data["session"]
        entry["solves"] = []
        evidence = "frustration override: answer given"
    else:
        evidence = f'{data["item"]} {gate.get("label", "")}: {outcome}'.strip()
        if outcome == "wrong":
            row["status"] = "shaky" if row["status"] == "mastered" else "gap"
            entry["solves"] = []
        elif outcome == "assisted":
            row["assisted"] += 1
            if not entry["blocked_session"] and row["status"] != "mastered":
                row["status"] = "shaky"
        else:
            row["unassisted"] += 1
            entry["blocked_session"] = None
            row["frustration_override"] = ""
            solve = {"item": data["item"], "date": data["date"], "real": data["real_past_paper"]}
            entry["solves"].append(solve)
            qualifies = any(a["item"] != b["item"] and
                            (a["date"] != b["date"] or a["real"] or b["real"])
                            for a in entry["solves"] for b in entry["solves"])
            row["status"] = "mastered" if qualifies or row["status"] == "mastered" else "shaky"
    entry["recent"] = (entry["recent"] + [{"date": data["date"], "evidence": evidence}])[-3:]
    row.update(evidence="; ".join(f'{e["date"]}: {e["evidence"]}' for e in entry["recent"]),
               evidence_date=data["date"], last_check=data["date"])
    state[key] = entry
    _save_record(path, text, state)
    return {"status": row["status"], "duplicate": False, "recorded": True,
            "line": f'{row["name"]}: {row["status"]}.'}


COMMANDS = {
    "record": (cmd_record, "record mastery evidence and frustration overrides"),
    "now": (cmd_now, "the local time: ISO timestamp, evidence date, log name, last_session stamp and term"),
    "parse-date": (cmd_parse_date, "the student's exam-date phrase as a YYYY-MM-DD date, or a refusal"),
    "start": (cmd_start, "pick the course, exam, delivery class and first topic for a session"),
    "check": (cmd_check, "status, counts and staleness for named topics"),
    "clock": (cmd_clock, "elapsed episode minutes and phase (teach, wrap, over)"),
    "debrief": (cmd_debrief, "post-exam debrief state, cram bill, verifier disagreements and next-course flag"),
    "progress": (cmd_progress, "every mastery row with its evidence, counts and staleness, as a table"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("session.py",
                             ("Mimir session runner. Subcommands: now, parse-date, start, check, clock, debrief, progress, record. Reads one JSON "
                              "object on stdin and prints one JSON object on stdout. Only record writes mastery state."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
