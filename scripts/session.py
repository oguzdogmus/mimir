#!/usr/bin/env python3
"""Mimir session runner: every date and clock decision a study session needs.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``plan.py`` (same folder). Run as::

    python3 session.py <now|parse-date|start|check|close|gauge|debrief|progress|record|prefs|pref-event>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Only record (mastery.md), close and gauge (a session log), pref-event
(``.state/preferences.json``) and start with ``lasting`` (``save.md``) write,
atomically; other commands are read-only. Only ``now``
reads the clock; every other subcommand takes "now" as an input (``now``, from
``session.py now``), so the same input and files always give the same output.

Datetimes are ISO 8601 with a time, as ``plan.py`` takes them
(e.g. "2026-10-17T09:00:00+03:00"). "Today" is ``now``'s own calendar date.

Files read (all inside the learning root, see ``workspace.py``)
---------------------------------------------------------------
* ``.state/profile.md``: ``## Exam dates`` rows ``| CODE | exam | date |``
  and ``## Active courses`` rows ``| CODE | YYYY-Term/CODE Name |``. The
  date cell is one of: ``unknown`` (date unknown); ``YYYY-MM-DD`` (time
  unknown); ``YYYY-MM-DD time unknown`` (time unknown, already asked for once
  more); a date with a time, ``YYYY-MM-DD HH:MM[:SS]`` or ``YYYY-MM-DDTHH:MM[:SS]``,
  optionally followed by ``Z`` or a ``+HH:MM``/``-HH:MM`` offset (no offset:
  ``now``'s offset). Case and extra spaces are ignored. Any other cell of the
  course is unreadable and reported in ``exam_problems``, never skipped silently.
* ``.state/preferences.json``: the global teaching settings, written only
  by ``pref-event``. Before it exists, ``dial_preference:`` in the profile
  (set unless empty, ``none`` or a ``<...>`` placeholder) is the legacy value.
* ``<course>/.state/save.md``: ``last_session:`` (``YYYY-MM-DD HH:MM`` or
  ``YYYY-MM-DD``), ``next_topic:``, ``pending_debrief:`` (``YYYY-MM-DD
  <exam name>``; ``no``, empty or anything else means none pending) and
  ``delivery_choice:`` (``Standard|Urgent YYYY-MM-DD <exam name>``, the
  lasting choice ``start`` saves; anything else means none).
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
  and the first ``gauge_done:`` line whose value is a date or datetime (the
  gauge-done marker); for ``debrief``
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

parse-date -- the student's exam date-and-time phrase as an exam value, or a refusal.
    in : {"now": "2026-10-17T09:00:00+03:00", "phrase": "12:30 Friday"}
    out: {"date": "2026-10-23", "time": "12:30", "exam":
          "2026-10-23T12:30:00+03:00", "line": "Exam: 2026-10-23 at 12:30."}
    Without a time: {"date": "2026-10-23", "time": null, "exam":
    "2026-10-23", "line": "Exam date: 2026-10-23."}. ``exam`` is the value
    for the ``## Exam dates`` cell (a time is at ``now``'s offset).
    Only these date phrases, ignoring case and extra spaces: ``YYYY-MM-DD``;
    ``today``; ``tomorrow``; a full English weekday name (``friday``), the
    next such day counting today, so today's own weekday name means today;
    ``N days`` or ``in N days`` (N a whole number). Today is
    ``now``'s own calendar date. A time may come before the date phrase or
    after it (optionally after ``at``): ``H:MM`` or ``HH:MM`` (24-hour), or
    with ``am``/``pm`` (``2pm``, ``12:30 am``). This is not natural-language
    date parsing: anything else ("Nov 5", "5/11", "next friday", "fri",
    "noon", a time alone) exits 2 as unsupported. A date that does not exist,
    a time that does not exist, a date before today, a time not after ``now``,
    or a date more than plan.MAX_HORIZON_DAYS days after today also exits 2.

start -- pick the course, the exam and the class for a new session.
    in : {"now": "2026-10-17T09:00:00+03:00"}
         optional "course" (a course folder name, e.g. "CS201 Theory") and
         "term" (YYYY-Term). A term alone limits the pick to that term; a
         course name found in several terms needs its term. Optional
         "choice" ("Standard" or "Urgent"): the student's choice of class,
         for this session only; with "lasting": true, for every session
         until the picked exam passes.
    out: {"root": "/home/u/learning", "courses": [{"term": "2026-Fall",
          "course": "CS201 Theory", "course_dir": "..."}], "term":
          "2026-Fall", "course": "CS201 Theory", "course_dir": "...",
          "code": "CS201", "inferred": true, "exam": "2026-11-05",
          "exam_date": "2026-11-05", "exam_name": "final", "q0": false, "exam_problems": [],
          "ask_exam_time": false, "ask_exam_ahead": false, "remaining": [{"name": "Heaps",
          "status": "gap"}, {"name": "Graphs", "status": "unseen"}],
          "class": {<plan.py class output>},
          "topic": {"name": "Graphs", "status": "unseen", "evidence_date":
          null, "stale": false, "attempt_first": false}, "route_line": null, "first_contact":
          "2026-10-10T20:00:00+03:00", "gauge": {"done": false, "topics": ["Graphs"]},
          "line": "Standard delivery: exam in 19 days"}
    (``class`` here includes "decided_by": "exam date".)
    Course: the given one (``inferred`` false); else the latest ``save.md``
    ``last_session:`` (ties: first by course name); else the first ``##
    Active courses`` row whose folder exists; else the last course in
    term/name order (year, then Spring < Summer < Fall < other words
    alphabetically, then course name). ``code`` is the first word of the
    course name. Exam: the earliest upcoming ``## Exam dates`` row for
    ``code``: a date-only row dated today or later (ordered as 00:00 that day),
    or a row with a time after ``now``. ``exam`` is ``YYYY-MM-DD`` for a
    date-only row, else the ISO datetime at ``now``'s offset (as ``plan.py``
    takes it); ``exam_date`` is its calendar day. With none, when a row for
    ``code`` says ``unknown``, exam null with ``q0`` false; else exam null with
    ``q0`` true (ask "When's the exam?"). Rows more than plan.MAX_HORIZON_DAYS days ahead are ignored like
    past ones. ``exam_problems``: the unreadable cells of ``code``, as
    [{"exam", "date"}] in file order. ``ask_exam_time``: the exam is date-only,
    not marked ``time unknown``, and at most TIME_ASK_DAYS days ahead (ask for
    its time once more). ``ask_exam_ahead``: the exam is date-only and today
    (ask whether it is still ahead). Route: ``mastery.md`` rows in order; when the
    ``INDEX.md`` registry has no ``outline`` row, each ``## Topics`` name not
    yet listed (ignoring case and repeated spaces) follows as an unseen row,
    in ``INDEX.md`` order. ``remaining`` = route rows not
    ``mastered``. ``class``: ``plan.py class`` with ``now`` and the exam only (the
    route's size never decides) plus ``decided_by``, the rule that decided,
    first match wins:
      "session choice" -- ``choice`` without ``lasting``: that class, line
          "<choice> delivery: you asked; <plan.py line after 'delivery: '>",
          e.g. "Standard delivery: you asked; exam in 30 hours". Nothing is saved.
      "lasting choice" -- ``choice`` with ``lasting``, or a saved
          ``delivery_choice:`` whose date is ``exam_date`` and whose name is
          ``exam_name`` (case and repeated spaces ignored): that class, line
          "<class> delivery: you asked, until your <exam_name, else exam>;
          <plan.py tail>". With ``lasting``, ``save.md`` gets the line
          ``delivery_choice: <choice> <exam_date> <exam_name>``, replacing the
          first ``delivery_choice:`` line, else after the last ``key:`` line
          above the first ``##`` heading; an equal line is not rewritten.
          Once that exam passes, ``start`` picks another exam (or none), so the
          saved choice stops applying. ``lasting`` with exam null, or a
          symlinked ``save.md``, exits 2 and writes nothing.
      "exam date" -- otherwise: ``plan.py class`` unchanged.
    ``reason``, ``hours_to_exam`` and ``days_to_exam`` are always the exam
    date's. ``topic``:
    ``save.md`` ``next_topic`` when it is remaining, else the first remaining
    topic; with none remaining, the same pick among the stale mastered topics
    (stale as in ``check``: the one-question recheck); else null. Its
    ``attempt_first`` is as in ``check``. ``route_line``: null when ``topic``
    is set; else "No topics on the route yet: drop the outline, slides or
    past papers into `_inbox/` and run mimir-ingest." for an empty route, or
    "Your route is complete: every topic is mastered in mastery.md. Want a
    `mimir-quiz` to keep it fresh?". ``gauge`` (the knowledge gauge): null when the
    route is empty (no gauge; never gauge from the course name); else ``done``
    (the course has a gauge-done marker, set by ``gauge``) and ``topics``, the
    route's ``unseen`` topic names in route order ([] when done).
    ``line`` is the class line. ``debrief``: null when ``pending_debrief:``
    holds no valid date P; else {"exam", "exam_name", "due", "deferred"}.
    P today or later: P with the pending name, due and deferred false (a
    date-only exam is past only from the next day, as in ``plan.py``). P
    before today: the target exam is the latest ``## Exam dates`` row of
    ``code`` dated after P and before today (a later passed exam supersedes;
    debriefs never stack), else P (named by the pending value, else by a row
    dated P); ``deferred`` = the class (as decided above) is Urgent, ``due`` = not deferred.
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

close -- stamp a session's end in its log, once.
    in : {"now": "2026-10-17T10:47:30+03:00", "term": "2026-Fall", "course":
          "CS201 Theory", "log": "2026-10-17-0900", "started": "2026-10-17T09:00:00+03:00"}
    out: {"log": ".../.state/logs/2026-10-17-0900.md", "started": "...", "ended":
          "2026-10-17T10:47:30+03:00", "minutes": 107, "last_session":
          "2026-10-17 10:47", "already_closed": false,
          "line": "Session closed after 107 min."}
    ``log`` is ``session.py now``'s ``log_name``; ``started`` the session's
    ``started:`` value in that log, matched exactly. When that session's block
    (up to the next ``started:`` line) has no ``ended:`` line, appends ``ended:
    <now>`` to the log; when it has one, writes nothing and reports that stamp
    with ``already_closed`` true ("Session already closed after N min."), so a
    session gets one end stamp however often it is closed. ``minutes`` is whole
    minutes from started to ended, rounded down; ``last_session`` the end stamp
    as the ``save.md`` value. Exits 2 when the log is missing or a symlink,
    has no such ``started:`` line, a later session already started in it
    while this one is open, its ``ended:`` line is not a datetime, or ``now``
    is before ``started`` or mixes offset and no-offset with it.

gauge -- set the course's gauge-done marker, once.
    in : {"now": "2026-10-17T09:40:00+03:00", "term": "2026-Fall", "course":
          "CS201 Theory", "log": "2026-10-17-0900"}
    out: {"log": ".../.state/logs/2026-10-17-0900.md", "gauge_done":
          "2026-10-17T09:40:00+03:00", "already_done": false,
          "line": "Knowledge gauge done for CS201 Theory: it will not run again."}
    ``log`` is this session's log name (it must exist). When no log of the
    course has a gauge-done marker, appends ``gauge_done: <now>`` to the log;
    otherwise writes nothing and reports the existing marker with
    ``already_done`` true ("Knowledge gauge already done for <course>.").
    Exits 2 when the course has no topics yet (the route is empty: no gauge, so
    the marker stays unset), or on the ``close`` log errors.

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
    * ``cram``: ``plan.py debrief`` (actual hours studied only) with
      ``first_contact`` (as in ``start``), ``exam`` T and the sessions:
      each log's ``started:`` and the next ``ended:`` after it, kept when the start's own calendar date is after B and on or before T;
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
    Per session, item and event, the first wrong answer records once (later
    misses return duplicate) and a right answer after it records as assisted.
    Alternatively {term, course, topic, initialize: true} adds an unseen topic.
    Returns status, recorded, duplicate and line. See the shared recording
    reference for examples and audit D2/D5 for exact transition semantics.
    Legacy Markdown is retained; recorder-owned JSON in a trailing comment
    supplies authoritative rows to check, start and progress.

prefs -- the global teaching settings. Read-only.
    in : {}
    out: {"axes": {"support": {"level": "method-first", "provenance":
          "default", "wording": null}, "frequency": {...}, "depth": {...}},
          "saved": false, "sampler": {"open": true, "started": false,
          "remaining": ["support", "frequency", "depth"]}, "line": "Teaching
          settings: support method-first (default), ..."}
    Axes and levels, more guided to more independent: support example-first,
    method-first, try-first; frequency checks only, key decisions, every
    step; depth next step, why, what-if. Provenance is default, sampler,
    learned, explicit or legacy; ``wording`` is the student's words for an
    explicit value, else null. ``saved`` = ``preferences.json`` exists. Before
    it does, every axis is at its middle level with provenance default, except
    that a set profile ``dial_preference:`` reads as frequency checks only with
    provenance legacy (``## Rung hints`` are ignored). A damaged or symlinked
    ``preferences.json`` exits 2.
    ``sampler`` is the setup sampler: ``remaining`` lists the axes still at
    default, in order, while setup is not done (no ``setup_done:`` date in the
    profile) and the sampler was not skipped, else []; ``open`` = remaining is
    non-empty; ``started`` = some axis has provenance sampler.

pref-event -- apply one teaching-settings event and save the state.
    in : {"event": "explicit", "axis": "frequency", "level": "checks only",
          "wording": "ask fewer questions"}
         or {"event": "sampler", "axis": "support", "level": "example-first"}
         or {"event": "sampler-skip"} or {"event": "legacy-import"}
    out: as ``prefs`` plus "changed", with ``saved`` true; line e.g.
         "Saved for every course: guiding-question frequency is now checks only."
    ``explicit``: the student's lasting request sets that axis to that level
    (any distance), provenance explicit, wording kept with spaces collapsed;
    other axes are untouched. ``sampler``: one setup-sampler choice; it
    fills the axis only while that axis is at default (provenance sampler),
    never overwriting a sampler, learned, explicit or legacy value ("Kept:
    ..."), and after a skip changes nothing. The choice that leaves no axis
    remaining says the tentative summary of all three levels.
    ``sampler-skip``: ends the sampler for good; completed choices stay and
    unanswered axes keep their defaults. Both sampler events exit 2 once
    setup is done. ``legacy-import``: saves the state ``prefs``
    shows (the legacy value included) when nothing is saved yet; otherwise
    changes nothing. A state that would not change is not rewritten, so a
    rerun leaves the file byte-identical. An unknown event, axis, or a level
    from another axis exits 2 and writes nothing.

Exit codes: invalid input (bad field, unknown course, no workspace) exits 2
with one line on stderr (``session.py: <message>``) naming the field, and
nothing on stdout. An unexpected internal error exits 1 with ``session.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import re
import json
import sys
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path

import ingest
import plan
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

STALE_DAYS = 14
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
_EXAM_AT = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[T ]([0-9]{2}:[0-9]{2}(?::[0-9]{2})?)(Z|[+-][0-9]{2}:[0-9]{2})?")
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


def _logs(course_dir: Path):
    """(name, text) of each readable ``.state/logs/*.md`` in name order; symlinks,
    unreadable and non-UTF-8 logs are skipped."""
    logs = course_dir / ".state" / "logs"
    try:
        if logs.is_symlink() or not logs.is_dir():
            return
        names = sorted(p for p in logs.iterdir() if p.suffix == ".md")
    except OSError:
        return
    for log in names:
        try:
            if log.is_symlink() or not log.is_file():
                continue
            yield log.name, _text(log)
        except (InputError, OSError):
            continue


def _first_contact(course_dir: Path) -> str | None:
    for _, text in _logs(course_dir):
        for line in text.splitlines():
            m = re.fullmatch(r"first_contact:(.*)", line.strip())
            if m and _valid_moment(m.group(1).strip()):
                return m.group(1).strip()
    return None


def _gauge_done(course_dir: Path) -> str | None:
    """The course's gauge-done marker: the first ``gauge_done:`` log line holding a date or datetime."""
    for _, text in _logs(course_dir):
        for line in text.splitlines():
            m = re.fullmatch(r"gauge_done:(.*)", line.strip())
            if m and _valid_moment(m.group(1).strip()):
                return m.group(1).strip()
    return None


def _gauge(course_dir: Path, rows: list[dict]) -> dict | None:
    """``start``'s gauge: null with no topics; else done, and the unseen topics while not done."""
    if not rows:
        return None
    done = _gauge_done(course_dir) is not None
    return {"done": done, "topics": [] if done else [r["name"] for r in rows if r["status"] == "unseen"]}


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


_TIME_ASKED = re.compile(r"(.*\S)\s+time\s+unknown", re.IGNORECASE)
TIME_ASK_DAYS = 2  # ask once more for a date-only exam's time within this many days


def exam_value(cell: str, tz: tzinfo | None) -> date | datetime | str | None:
    """An ``## Exam dates`` cell: "unknown", a date (time unknown; also
    ``YYYY-MM-DD time unknown``), a datetime (a time without a UTC offset is
    taken at ``tz``), or None when unreadable."""
    text = " ".join(cell.split())
    if text.casefold() == "unknown":
        return "unknown"
    asked = _TIME_ASKED.fullmatch(text)
    day = _valid_date(asked.group(1) if asked else text)
    if day is not None or asked:
        return day
    m = _EXAM_AT.fullmatch(text)
    if not m:
        return None
    try:
        moment = datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}{m.group(3) or ''}")
    except ValueError:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz) if tz is not None else moment.replace(tzinfo=None)


def _exam_day(value: date | datetime, tz: tzinfo | None) -> date:
    return value if plan.is_date_only(value) else value.astimezone(tz).date() if tz else value.date()


def _exam(profile: str, code: str, now: datetime) -> dict:
    """``start``'s exam fields for the course code: exam, exam_date, exam_name, q0,
    exam_problems, ask_exam_time, ask_exam_ahead."""
    best, unknown, today, problems = None, False, now.date(), []
    for course, exam, when in _section_rows(profile, _EXAM_TABLE):
        if course.strip().casefold() != code.casefold():
            continue
        value = exam_value(when, now.tzinfo)
        if value == "unknown":
            unknown = True
            continue
        if value is None:
            problems.append({"exam": " ".join(exam.split()), "date": " ".join(when.split())})
            continue
        if plan.is_date_only(value):
            at = datetime.combine(value, time(0), tzinfo=now.tzinfo)  # orders before a timed exam that day
            upcoming = 0 <= (value - today).days <= plan.MAX_HORIZON_DAYS
        else:
            at = value
            upcoming = timedelta(0) < value - now <= timedelta(days=plan.MAX_HORIZON_DAYS)
        if upcoming and (best is None or at < best[0]):
            best = (at, value, exam.strip(), bool(_TIME_ASKED.fullmatch(" ".join(when.split()))))
    out = {"exam": None, "exam_date": None, "exam_name": None, "q0": not unknown, "exam_problems": problems,
           "ask_exam_time": False, "ask_exam_ahead": False}
    if best:
        _, value, name, asked = best
        dated = plan.is_date_only(value)
        out.update(exam=value.isoformat(), exam_date=_exam_day(value, now.tzinfo).isoformat(),
                   exam_name=name or None, q0=False,
                   ask_exam_time=dated and not asked and (value - today).days <= TIME_ASK_DAYS,
                   ask_exam_ahead=dated and value == today)
    return out


# --- Debrief ------------------------------------------------------------------------

_PENDING = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:T\S*)?(?:\s+(.*))?")  # a time is ignored
_CLOSE_LOG = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}(?:-[A-Za-z0-9-]+)?")
_LOG_NAME = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})-[0-9]{4}(?:-[^/]*)?\.md")
_NO_CRAM_LINE = "Cram bill: no study sessions logged."
NO_COURSE_LINE = "No course yet: run mimir-setup, then mimir-ingest."


def _code_exams(profile: str, code: str, tz: tzinfo | None) -> list[tuple[date, str]]:
    """Dated ``## Exam dates`` rows of a course code as (day in ``tz``, name), in file order."""
    out = []
    for course, exam, when in _section_rows(profile, _EXAM_TABLE):
        value = exam_value(when, tz)
        if course.strip().casefold() == code.casefold() and isinstance(value, date):
            out.append((_exam_day(value, tz), " ".join(exam.split())))
    return out


def _pending(save: str) -> tuple[date, str | None] | None:
    """``pending_debrief: YYYY-MM-DD <name>`` as (date, name); None when no, empty or malformed."""
    m = _PENDING.fullmatch(_key(save, "pending_debrief"))
    day = _valid_date(m.group(1)) if m else None
    if day is None:
        return None
    return day, " ".join((m.group(2) or "").split()) or None


def _debrief_target(profile: str, code: str, pending: date, pending_name: str | None,
                    now: datetime) -> tuple[date, str | None, date | None]:
    """(target exam date, its name, previous exam date or None).

    Target: the latest row of the code dated from the day after ``pending``
    to yesterday (a later passed exam supersedes; ties: the first such row),
    else ``pending`` itself, named by ``pending_name``, else by the first named
    row dated ``pending``. Previous: the latest row of the code dated before
    the target."""
    rows, today = _code_exams(profile, code, now.tzinfo), now.date()
    passed = [(day, exam) for day, exam in rows if pending < day < today]
    target, name = pending, pending_name
    if passed:
        target = max(day for day, _ in passed)
        name = next(exam for day, exam in passed if day == target) or None
    elif name is None:
        name = next((exam for day, exam in rows if day == pending and exam), None)
    before = [day for day, _ in rows if day < target]
    return target, name, max(before) if before else None


def debrief_state(profile: str, save: str, code: str, now: datetime,
                  klass: str | None) -> tuple[dict | None, tuple[date, date | None] | None]:
    """(``start``'s ``debrief``, the due window (target, previous exam) or None).
    The state is null with no valid pending value."""
    pending = _pending(save)
    if pending is None:
        return None, None
    day, name = pending
    if day >= now.date():  # a date-only exam is past only from the next day
        return {"exam": day.isoformat(), "exam_name": name, "due": False, "deferred": False}, None
    target, target_name, previous = _debrief_target(profile, code, day, name, now)
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
    return _plan(plan.debrief, {"now": now.isoformat(), "exam": target.isoformat(),
                                "first_contact": first_contact,
                                "sessions": _sessions(logs, previous, target, aware)})


# --- Subcommands ----------------------------------------------------------------------

def cmd_start(data: dict) -> dict:
    choice, lasting = data.get("choice"), data.get("lasting", False)
    if choice is not None and choice not in plan.TRIAGE_CLASSES:
        raise InputError("choice must be Standard or Urgent")
    if not isinstance(lasting, bool) or (lasting and choice is None):
        raise InputError("lasting must be true or false, and true needs a choice")
    return _start({k: v for k, v in data.items() if k not in ("choice", "lasting")}, choice, lasting)[0]


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


_CHOICE = re.compile(r"(Standard|Urgent)\s+([0-9]{4}-[0-9]{2}-[0-9]{2})(?:\s+(.*))?", re.IGNORECASE)


def _lasting_choice(save: str, exam: dict) -> str | None:
    """The saved ``delivery_choice:`` class when it names the exam ``start`` picked, else None:
    once that exam passes, ``start`` picks another exam (or none) and the choice stops applying."""
    m = _CHOICE.fullmatch(_key(save, "delivery_choice"))
    if not m or exam["exam_date"] is None or m.group(2) != exam["exam_date"]:
        return None
    if _norm(m.group(3) or "") != _norm(exam["exam_name"] or ""):
        return None
    return m.group(1).capitalize()


def _choice_line(choice: str, exam: dict) -> str:
    name = " ".join((exam["exam_name"] or "").split())
    return f"delivery_choice: {choice} {exam['exam_date']} {name}".rstrip()


def _save_choice(course_dir: Path, line: str) -> None:
    """Write the ``delivery_choice:`` line into ``save.md``: replace the first one, else add it
    after the last key line above the first ``##`` heading (else at the end)."""
    path = course_dir / ".state" / "save.md"
    if path.is_symlink():
        raise InputError("save.md must not be a symlink")
    lines = _text(path).splitlines()
    at = next((i for i, row in enumerate(lines) if re.fullmatch(r"delivery_choice:.*", row.strip())), None)
    if at is not None:
        if lines[at] == line:
            return
        lines[at] = line
    else:
        head = next((i for i, row in enumerate(lines) if row.startswith("## ")), len(lines))
        keys = [i for i in range(head) if re.fullmatch(r"[a-z_]+:.*", lines[i])]
        lines.insert(keys[-1] + 1 if keys else head, line)
    ingest._write_atomic(path, "\n".join(lines) + "\n")


def _class(now: str, exam: dict, choice: str | None, lasting: bool, save: str) -> dict:
    """``start``'s class: the student's choice for this session, else a saved lasting
    choice for this exam, else ``plan.py class`` for the exam."""
    klass = _plan(plan.delivery_class, {"now": now, "exam": exam["exam"]})
    tail = klass["line"].split(": ", 1)[1]  # "exam in 30 hours"
    if choice is not None and not lasting:
        return {**klass, "class": choice, "decided_by": "session choice",
                "line": f"{choice} delivery: you asked; {tail}"}
    saved = choice if lasting else _lasting_choice(save, exam)
    if saved is None:
        return {**klass, "decided_by": "exam date"}
    return {**klass, "class": saved, "decided_by": "lasting choice",
            "line": f"{saved} delivery: you asked, until your {exam['exam_name'] or 'exam'}; {tail}"}


def _start(data: dict, choice: str | None = None,
           lasting: bool = False) -> tuple[dict, tuple[date, date | None] | None]:
    """``start``'s output and the due debrief window (see ``debrief_state``)."""
    now, root, profile, courses, chosen, inferred, course_dir = _course_pick(data)
    if chosen is None:
        return {"root": str(root), "courses": courses, "term": None, "course": None, "course_dir": None,
                "code": None, "inferred": None, "exam": None, "exam_date": None, "exam_name": None, "q0": None,
                "exam_problems": None, "ask_exam_time": None, "ask_exam_ahead": None,
                "remaining": [], "class": None, "topic": None, "route_line": None,
                "first_contact": None, "gauge": None, "debrief": None, "line": NO_COURSE_LINE}, None
    code = chosen["course"].split()[0]
    today = now.date()
    exam = _exam(profile, code, now)
    rows = route(course_dir)
    remaining = [r for r in rows if r["status"] != "mastered"]
    save = _memory(course_dir, "save.md")
    if lasting:
        if exam["exam"] is None:
            raise InputError("lasting needs an upcoming exam; without one a choice lasts this session only")
        _save_choice(course_dir, _choice_line(choice, exam))
    klass = _class(data["now"], exam, choice, lasting, save)
    next_topic = _norm(_key(save, "next_topic"))
    # Nothing unmastered left: a stale mastered topic gets the one-question recheck.
    candidates = remaining or [r for r in rows if topic_state(r, r["name"], today)["stale"]]
    pick = next((r for r in candidates if next_topic and _norm(r["name"]) == next_topic),
                candidates[0] if candidates else None)
    debrief, window = debrief_state(profile, save, code, now, klass["class"])
    topic = None
    if pick is not None:
        state = topic_state(pick, pick["name"], today)
        topic = {k: state[k] for k in ("name", "status", "evidence_date", "stale", "attempt_first")}
    route_line = None if pick is not None else ROUTE_DONE_LINE if rows else NO_ROUTE_LINE
    return {"root": str(root), "courses": courses, "term": chosen["term"], "course": chosen["course"],
            "course_dir": str(course_dir), "code": code, "inferred": inferred, **exam,
            "remaining": [{"name": r["name"], "status": r["status"]} for r in remaining],
            "class": klass, "topic": topic, "route_line": route_line,
            "first_contact": _first_contact(course_dir), "gauge": _gauge(course_dir, rows),
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
    logs = list(_logs(course_dir))
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


def _session_log(data: dict) -> tuple[Path, Path]:
    """(course folder, log path) for a ``term``, ``course`` and ``log`` name from ``session.py now``;
    exits 2 when the course or the log is missing, or the log is a symlink."""
    term, course = parse_term(data), parse_segment(data, "course")
    name = data.get("log")
    if not isinstance(name, str) or not _CLOSE_LOG.fullmatch(name):
        raise InputError("log must be a log name from `session.py now` (YYYY-MM-DD-HHMM)")
    course_dir = workspace.course_folder(ingest._workspace_root(), term, course)
    if not (course_dir / "INDEX.md").is_file():
        raise InputError(f"course {_short(course)} has no course folder with an INDEX.md in term {term}")
    path = course_dir / ".state" / "logs" / f"{name}.md"
    if path.is_symlink() or not path.is_file():
        raise InputError(f"log {name} not found in {_short(course)}")
    return course_dir, path


def _append(path: Path, text: str, line: str) -> None:
    ingest._write_atomic(path, text + ("" if text.endswith("\n") or not text else "\n") + line + "\n")


def cmd_close(data: dict) -> dict:
    """Stamp a session's end in its log once; a repeated close reuses the stamp and writes nothing."""
    _check_keys(data, {"now", "term", "course", "log", "started"})
    now, started = _moment(data, "now"), _moment(data, "started")
    _, path = _session_log(data)
    name = data["log"]
    text = _text(path)
    ended, found, inside = None, False, False
    for line in text.splitlines():
        m = re.fullmatch(r"(started|ended):(.*)", line.strip())
        if not m:
            continue
        value = m.group(2).strip()
        if m.group(1) == "started":
            if inside and ended is None:
                raise InputError(f"a later session started in log {name} before this one was closed")
            inside = value == data["started"]
            found = found or inside
        elif inside and ended is None:
            try:
                ended = plan.parse_moment(value, "ended", need_time=True)
            except plan.InputError:
                raise InputError(f"log {name} has an ended line that is not a datetime") from None
    if not found:
        raise InputError(f"log {name} has no started: {data['started']} line")
    already = ended is not None
    if not already:
        if (started.tzinfo is None) != (now.tzinfo is None):
            raise InputError("now and started mix values with and without a UTC offset")
        if now < started:
            raise InputError("now is before started")
        ended = now
        _append(path, text, f"ended: {data['now']}")
    minutes = max(0, int((ended - started).total_seconds() // 60))
    line = f"Session {'already closed' if already else 'closed'} after {minutes} min."
    return {"log": str(path), "started": data["started"], "ended": ended.isoformat(), "minutes": minutes,
            "last_session": ended.strftime("%Y-%m-%d %H:%M"), "already_closed": already, "line": line}


def cmd_gauge(data: dict) -> dict:
    """Set the course's gauge-done marker once: a ``gauge_done:`` line in this session's log."""
    _check_keys(data, {"now", "term", "course", "log"})
    _moment(data, "now")
    course_dir, path = _session_log(data)
    course = course_dir.name
    if not route(course_dir):
        raise InputError(f"course {_short(course)} has no topics yet: no gauge, and its marker stays unset")
    done = _gauge_done(course_dir)
    if done is None:
        _append(path, _text(path), f"gauge_done: {data['now']}")
    line = (f"Knowledge gauge already done for {course}." if done else
            f"Knowledge gauge done for {course}: it will not run again.")
    return {"log": str(path), "gauge_done": done or data["now"], "already_done": done is not None, "line": line}


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


_CLOCK = r"[0-9]{1,2}(?::[0-9]{2} ?(?:am|pm)?| ?(?:am|pm))"
_TIME_FIRST = re.compile(rf"({_CLOCK}) (.+)")
_TIME_LAST = re.compile(rf"(.+?) (?:at )?({_CLOCK})")
_CLOCK_PARTS = re.compile(r"([0-9]{1,2})(?::([0-9]{2}))? ?(am|pm)?")


def _clock_time(text: str, phrase: str) -> time:
    hour, minute, half = _CLOCK_PARTS.fullmatch(text).groups()
    hour, minute = int(hour), int(minute or 0)
    if hour > (12 if half else 23) or minute > 59 or (half and hour == 0):
        raise InputError(f"phrase {_short(phrase)} is not a real time")
    if half:
        hour = hour % 12 + (12 if half == "pm" else 0)
    return time(hour, minute)


def _phrase_day(text: str, today: date, phrase: str) -> date:
    relative = _RELATIVE.fullmatch(text)
    if text == "today":
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    if relative:
        count = int(relative.group(1))
        return today + timedelta(days=min(count, plan.MAX_HORIZON_DAYS + 1))
    if text in WEEKDAYS:
        return today + timedelta(days=(WEEKDAYS.index(text) - today.weekday()) % 7)
    if _DATE.fullmatch(text):
        day = _valid_date(text)
        if day is None:
            raise InputError(f"phrase {_short(phrase)} is not a real date")
        return day
    raise InputError(f"phrase {_short(phrase)} is unsupported (use YYYY-MM-DD, today, tomorrow, "
                     "a weekday name or \"in N days\", optionally with a time such as 12:30 or 2pm)")


def cmd_parse_date(data: dict) -> dict:
    _check_keys(data, {"now", "phrase"})
    now = _moment(data, "now")
    today = now.date()
    phrase = data.get("phrase")
    if not isinstance(phrase, str):
        raise InputError("phrase is required (the student's exam-date phrase)")
    text = " ".join(phrase.split()).casefold()
    if not text:
        raise InputError("phrase is empty")
    clock = None
    if m := _TIME_FIRST.fullmatch(text):
        clock, text = m.group(1), m.group(2)
    elif m := _TIME_LAST.fullmatch(text):
        text, clock = m.group(1), m.group(2)
    day = _phrase_day(text, today, phrase)
    at = None if clock is None else _clock_time(clock, phrase)
    if day < today:
        raise InputError(f"phrase {_short(phrase)} is in the past ({day.isoformat()})")
    if day > today + timedelta(days=plan.MAX_HORIZON_DAYS):
        raise InputError(f"phrase {_short(phrase)} is more than {plan.MAX_HORIZON_DAYS} days ahead")
    if at is None:
        return {"date": day.isoformat(), "time": None, "exam": day.isoformat(),
                "line": f"Exam date: {day.isoformat()}."}
    moment = datetime.combine(day, at, tzinfo=now.tzinfo)
    if moment <= now:
        raise InputError(f"phrase {_short(phrase)} is in the past ({moment.isoformat()})")
    shown = at.strftime("%H:%M")
    return {"date": day.isoformat(), "time": shown, "exam": moment.isoformat(),
            "line": f"Exam: {day.isoformat()} at {shown}."}


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
    # One miss and one right answer per session, item and event: retries after a
    # miss record nothing more until the right answer, which counts as assisted.
    # Three-element identities predate this split and block both.
    base = [data["session"], data["item"], bool(data.get("override"))]
    outcome = data["outcome"]
    kind = "wrong" if outcome == "wrong" else "right"
    blocking = [base, base + ["right"]] + ([base + ["wrong"]] if kind == "wrong" else [])
    if any(identity in entry["attempts"] for identity in blocking):
        return {**result, "duplicate": True, "line": "Attempt already recorded."}
    if kind == "right" and base + ["wrong"] in entry["attempts"]:
        outcome = "assisted"
    identity = base + [kind]
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


# Teaching settings: three global axes, each with three levels from more guided to more independent.
AXES = {"support": ("example-first", "method-first", "try-first"),
        "frequency": ("checks only", "key decisions", "every step"),
        "depth": ("next step", "why", "what-if")}
AXIS_NAMES = {"support": "support", "frequency": "guiding-question frequency", "depth": "guiding-question depth"}
PROVENANCES = ("default", "sampler", "learned", "explicit", "legacy")
PREFS_FILE = "preferences.json"
PREFS_VERSION = 1
MAX_WORDING = 200


def _default_axes() -> dict:
    return {axis: {"level": levels[1], "provenance": "default", "wording": None} for axis, levels in AXES.items()}


def _prefs_path(root: Path) -> Path:
    path = root / ".state" / PREFS_FILE
    if path.is_symlink():
        raise InputError(f"{PREFS_FILE} must not be a symlink")
    return path


def _prefs_state(root: Path) -> tuple[dict, bool]:
    """(state, saved): the saved preference state, else defaults with any legacy
    ``dial_preference`` already imported (what the legacy-import event would save)."""
    path = _prefs_path(root)
    if not path.exists():
        axes = _default_axes()
        if _set(_key(_text(root / ".state" / "profile.md"), "dial_preference")):
            axes["frequency"] = {"level": "checks only", "provenance": "legacy", "wording": None}
        return {"version": PREFS_VERSION, "axes": axes}, False
    damaged = InputError(f"{PREFS_FILE} is damaged; restore it or delete it to use the defaults")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise damaged from None
    if not isinstance(state, dict) or state.get("version") != PREFS_VERSION or not isinstance(state.get("axes"), dict) \
            or set(state["axes"]) != set(AXES):
        raise damaged
    if state.get("sampler_skipped", True) is not True:  # optional; present only once the sampler was skipped
        raise damaged
    for axis, entry in state["axes"].items():
        if not isinstance(entry, dict) or set(entry) != {"level", "provenance", "wording"} \
                or entry["level"] not in AXES[axis] or entry["provenance"] not in PROVENANCES \
                or (entry["wording"] is None) == (entry["provenance"] == "explicit") \
                or not (entry["wording"] is None or isinstance(entry["wording"], str)):
            raise damaged
    return state, True


def _set(value: str) -> bool:
    """A profile value counts as set unless empty, ``none`` or a ``<...>`` template placeholder."""
    return bool(value) and value.casefold() != "none" and not (value.startswith("<") and value.endswith(">"))


def _sampler(state: dict, root: Path) -> dict:
    """The setup sampler: open only before setup is done and until skipped; it fills default axes only."""
    axes = state["axes"]
    open_ = workspace.read_setup_done(root) is None and not state.get("sampler_skipped", False)
    remaining = [a for a in AXES if axes[a]["provenance"] == "default"] if open_ else []
    return {"open": bool(remaining), "started": any(axes[a]["provenance"] == "sampler" for a in AXES),
            "remaining": remaining}


def _prefs_out(state: dict, saved: bool, root: Path) -> dict:
    axes = state["axes"]
    parts = ", ".join(f"{AXIS_NAMES[a]} {axes[a]['level']} ({axes[a]['provenance']})" for a in AXES)
    return {"axes": axes, "saved": saved, "sampler": _sampler(state, root), "line": f"Teaching settings: {parts}."}


def cmd_prefs(data: dict) -> dict:
    """The global teaching settings and the setup sampler's state; read-only."""
    _check_keys(data, set())
    root = ingest._workspace_root()
    return _prefs_out(*_prefs_state(root), root)


def cmd_pref_event(data: dict) -> dict:
    """Apply one teaching-settings event and save the state atomically (unchanged state writes nothing)."""
    event = data.get("event")
    if event in ("legacy-import", "sampler-skip"):
        _check_keys(data, {"event"})
    elif event == "explicit":
        _check_keys(data, {"event", "axis", "level", "wording"})
    elif event == "sampler":
        _check_keys(data, {"event", "axis", "level"})
    else:
        raise InputError("event must be explicit, sampler, sampler-skip or legacy-import")
    axis, level = data.get("axis"), data.get("level")
    if event in ("explicit", "sampler"):
        if axis not in AXES:
            raise InputError(f"axis must be one of {', '.join(AXES)}")
        if level not in AXES[axis]:
            raise InputError(f"level for {axis} must be one of {', '.join(AXES[axis])}")
    root = ingest._workspace_root()
    if event.startswith("sampler") and workspace.read_setup_done(root) is not None:
        raise InputError("the sampler runs only during setup")
    state, saved = _prefs_state(root)
    before = json.dumps(state, sort_keys=True)
    line = None
    if event == "sampler-skip":
        line = "Sampler already skipped." if state.get("sampler_skipped") else \
            "Sampler skipped. Unanswered settings stay at the defaults and adapt as you study."
        state["sampler_skipped"] = True
    if event == "sampler":
        current = state["axes"][axis]
        if state.get("sampler_skipped"):
            line = "The sampler was skipped; settings unchanged."
        elif current["provenance"] == "default":  # never overwrites a sampler, learned, explicit or legacy value
            state["axes"][axis] = {"level": level, "provenance": "sampler", "wording": None}
            line = f"Noted for now: {AXIS_NAMES[axis]} {level}."
            if not _sampler(state, root)["remaining"]:
                levels = ", ".join(f"{AXIS_NAMES[a]} {state['axes'][a]['level']}" for a in AXES)
                line = f"Tentative starting settings: {levels}. They keep adapting as you study."
        else:
            line = f"Kept: {AXIS_NAMES[axis]} stays {current['level']} ({current['provenance']})."
    if event == "explicit":
        wording = data.get("wording")
        if not isinstance(wording, str) or not wording.strip() or _has_control(wording) \
                or len(wording) > MAX_WORDING:
            raise InputError(f"wording must be the student's request, one line of at most {MAX_WORDING} characters")
        state["axes"][axis] = {"level": level, "provenance": "explicit", "wording": " ".join(wording.split())}
        line = f"Saved for every course: {AXIS_NAMES[axis]} is now {level}."
    changed = not saved or json.dumps(state, sort_keys=True) != before
    if changed:
        ingest._write_atomic(_prefs_path(root), json.dumps(state, indent=2) + "\n")
    out = _prefs_out(state, True, root)
    if line is None:  # legacy-import: saved now only when nothing was saved before
        line = ("Teaching settings already saved." if not changed else
                "Your earlier \"fewer questions\" choice is now guiding-question frequency checks only."
                if state["axes"]["frequency"]["provenance"] == "legacy" else
                "Teaching settings saved with the defaults.")
    return {**out, "changed": changed, "line": line}


COMMANDS = {
    "prefs": (cmd_prefs, "the global teaching settings: level and provenance per axis"),
    "pref-event": (cmd_pref_event, "apply one teaching-settings event (explicit request, setup sampler, legacy import)"),
    "record": (cmd_record, "record mastery evidence and frustration overrides"),
    "now": (cmd_now, "the local time: ISO timestamp, evidence date, log name, last_session stamp and term"),
    "parse-date": (cmd_parse_date, "the student's exam date-and-time phrase as an exam value, or a refusal"),
    "start": (cmd_start, "pick the course, exam, delivery class and first topic for a session"),
    "check": (cmd_check, "status, counts and staleness for named topics"),
    "close": (cmd_close, "stamp the end of a session in its log once and report its length"),
    "gauge": (cmd_gauge, "set the course's knowledge-gauge-done marker in the session log, once"),
    "debrief": (cmd_debrief, "post-exam debrief state, cram bill, verifier disagreements and next-course flag"),
    "progress": (cmd_progress, "every mastery row with its evidence, counts and staleness, as a table"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("session.py",
                             ("Mimir session runner. Subcommands: now, parse-date, start, check, close, gauge, debrief, "
                              "progress, record, prefs, pref-event. Reads one JSON object on stdin and prints one JSON "
                              "object on stdout. Only record, close, gauge, pref-event and start with lasting write."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
