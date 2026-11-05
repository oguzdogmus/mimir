#!/usr/bin/env python3
"""Mimir planning engine: delivery class, cram bill, first-contact summary, question-type triage.

Deterministic, standard library only, Python 3.11+. Run as::

    python3 plan.py <class|debrief|summary|triage>  < input.json

Each subcommand reads ONE JSON object on stdin and prints ONE JSON object on
stdout: structured data plus a ready-to-print ``line``. "Now" is an input
(``now``, from ``session.py now``); the clock is never read, so the same input
always gives byte-identical output.

Stdin schema (a date-only value is exactly ``YYYY-MM-DD``; a datetime is an
extended ISO 8601 datetime with ``T``, e.g. "2026-11-05T09:00:00+02:00";
other ISO forms such as "20261105" or "2026-W45-4" are rejected)
--------------------------------------------------------------------------
now            datetime with time, e.g. "2026-10-17T09:00:00+03:00".
               Required by ``class`` and ``triage``; optional elsewhere.
exam           datetime, date-only, or null (date unknown). Optional, null if
               missing.
sessions       list of {"start": datetime, "end": datetime} (debrief, summary;
               optional, missing or null means none).
first_contact  datetime or date-only. Required by debrief and summary.
course,
exam_name      optional strings for the summary label ("CS201", "final").
types          triage only, required (use [] for none): list of {"name": str,
               "marks": number >= 0 or null, "seen": int >= 0, "papers":
               int >= 0, "status": unseen|gap|shaky|mastered}. ``seen`` and
               ``papers`` default to 0, ``status`` to unseen; seen <= papers.
basis          triage only: "papers" (default) or "outline".
class          triage only: "Urgent" (default) or "Standard" -- the session's
               delivery class.

Date rules
----------
* A date-only exam has an unknown time. ``class`` gives it no hour count:
  Urgent on its own calendar day (``today``) and the day before
  (``tomorrow``), Standard earlier. It is past only from the next day.
  Elsewhere (triage budgets, debrief day counts) it means 00:00 that day at
  ``now``'s UTC offset (or at the first datetime's offset when ``now`` is
  absent).
* DST note: the offset of ``now`` is reused for the exam date, so a daylight
  saving change between now and the exam can shift the result by up to 1 h.
  This is accepted. Callers pass a full datetime when the exam time is known.
* Calendar days ("exam in 19 days") are counted in ``now``'s offset.
* All datetimes must agree: either all carry a UTC offset or none do.

Subcommands and examples
------------------------
class -- delivery class with reason. Only exam proximity decides: there is no
    learning-time estimate and no route-time trigger.
    in : {"now": "2026-10-17T09:00:00+03:00", "exam": "2026-11-05"}
    out: {"class": "Standard", "reason": "calm", "hours_to_exam": null,
          "days_to_exam": 19, "line": "Standard delivery: exam in 19 days"}
    ``reason`` is one of:
      unknown  -- exam date is null: Standard.
      today    -- date-only exam falls on today's date: Urgent, line "Urgent
                  delivery: exam today, time unknown".
      tomorrow -- date-only exam falls on tomorrow's date: Urgent, line
                  "Urgent delivery: exam tomorrow, time unknown".
      floor    -- exam with a time, hours to exam <= URGENT_FLOOR_HOURS: Urgent.
      calm     -- none of the above: Standard.
    A date-only exam has no known time, so ``hours_to_exam`` is null for it
    (never a countdown to midnight); ``days_to_exam`` is still given.

debrief -- cram bill: the hours actually studied, with no estimate of what
    the route should have taken.
    in : {"first_contact": "2026-11-03T20:00:00+02:00", "exam": "2026-11-05",
          "sessions": [{"start": "2026-11-03T20:00:00+02:00",
                        "end": "2026-11-03T23:30:00+02:00"}]}
    out: {"actual_minutes": 210, "actual_hours": 3.5, "session_count": 1,
          "days_before_exam": 2, "line": "Cram bill: 3.5 h studied in 1
          session. First contact: 2 days before the exam."}
    No sessions: "Cram bill: no study sessions logged."; exam null drops the
    first-contact sentence.

summary -- one shareable first-contact line.
    in : {"course": "CS201", "exam_name": "final", "first_contact":
          "2026-11-03", "exam": "2026-11-05", "sessions": [...]}
    out: {"course": "CS201", "exam_name": "final", "days_before_exam": 2,
          "studied_minutes": 390, "session_count": 3, "line": "CS201 final:
          first contact 2 days before the exam, 6.5 h studied in 3
          sessions."}
    A missing or empty sessions list drops the hours clause; exam null gives
    "<label>: exam date unknown."; no course or exam_name gives label "Exam".

triage -- question-type triage: rank question types by points per hour, drill or skip.
    in : {"now": "2026-11-04T21:00:00+02:00", "exam": "2026-11-05T09:00:00+02:00",
          "basis": "papers", "types": [
            {"name": "Pumping lemma proof", "marks": 20, "seen": 2, "papers": 2, "status": "gap"},
            {"name": "DFA construction", "marks": 10, "seen": 1, "papers": 2, "status": "unseen"},
            {"name": "Regex", "marks": 5, "seen": 2, "papers": 2, "status": "mastered"}]}
    out: {"drill": [{"name": "Pumping lemma proof", "marks": 20, "frequency": 1,
          "weight": 3, "minutes": 75, "pph": 16}, {"name": "DFA construction",
          ..., "minutes": 50, "pph": 6}], "skip": [{"name": "Regex", "reason":
          "mastered"}], "budget_minutes": 240, "basis": "papers", "line":
          "Drilling: Pumping lemma proof, DFA construction. Skipping: Regex
          (mastered)."}
    Per type: ``marks`` null = mean of the known marks, else 1; frequency =
    seen/papers when papers > 0, else 1; weight = ceil(3 x marks / max marks)
    clamped WEIGHT_MIN..WEIGHT_MAX (1 when every mark is 0); minutes =
    EPISODE_MINUTES x weight, x SHAKY_TIME_FACTOR when ``shaky``; pph = marks x
    frequency / (minutes / 60). ``class`` Urgent (default): ``mastered`` types
    are skipped (``mastered``); Standard: they are ranked with the rest.
    The rest are ranked by pph, highest first, ties in input order. Budget =
    hours_to_exam x 60 x URGENT_STUDY_SHARE (either class): types are drilled in rank order
    while the cumulative minutes fit, always at least one. Drilling stops at
    the first type that does not fit: no smaller later type is packed into
    the remaining budget. The rest are skipped (``lower yield``). Type names
    must be unique (ignoring case and repeated spaces). Exam null: every type not skipped as mastered is drilled
    (budget_minutes null). Date-only exam today: only the top type
    (budget_minutes null). ``basis`` "outline" appends "No past papers, so the
    forecast is weaker." to ``line``. ``drill`` is in rank order; ``skip``
    lists lower-yield types in rank order, then mastered ones in input order.

Exit codes: invalid input exits 2 with one line on stderr
(``plan.py: <message>``) and nothing on stdout. An unexpected internal error
(a bug, not bad input) exits 1 with ``plan.py: internal error (<Type>)`` and
nothing on stdout. No traceback is ever printed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime, time, timedelta
from fractions import Fraction

# --- Tunables (constants.md) -------------------------------------------------
EPISODE_MINUTES = 25                 # triage minutes per weight unit
URGENT_FLOOR_HOURS = 48              # always Urgent within this many hours of the exam
WEIGHT_MIN, WEIGHT_MAX = 1, 3        # mark-share weight ×1–×3
MAX_HORIZON_DAYS = 366               # reject exams further away than this
URGENT_STUDY_SHARE = Fraction(1, 3)  # share of the hours to the exam spent drilling (triage budget)
SHAKY_TIME_FACTOR = Fraction(1, 2)   # a shaky type takes half the minutes of an unseen one
TRIAGE_STATUSES = ("unseen", "gap", "shaky", "mastered")
TRIAGE_BASES = ("papers", "outline")
TRIAGE_CLASSES = ("Urgent", "Standard")

_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}T.+")


class InputError(Exception):
    """Invalid input; reported as one stderr line with exit code 2."""


# --- Input parsing -------------------------------------------------------------

def _parse_float(text: str) -> Fraction:
    value = float(text)
    if not math.isfinite(value):
        raise InputError("numbers must be finite")
    return Fraction(repr(value))


def _reject_constant(name: str):
    raise InputError(f"non-finite number {name} is not allowed")


def read_input(raw: bytes) -> dict:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError("input is not valid UTF-8") from None
    try:
        data = json.loads(text, parse_float=_parse_float, parse_constant=_reject_constant)
    except RecursionError:
        raise InputError("input is too deeply nested") from None
    except json.JSONDecodeError as exc:
        raise InputError(f"input is not valid JSON ({exc.msg}, line {exc.lineno} column {exc.colno})") from None
    except ValueError:
        raise InputError("input is not valid JSON (number out of range)") from None
    if not isinstance(data, dict):
        raise InputError("input must be one JSON object")
    return data


def _short(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text if len(text) <= 40 else text[:37] + "..."
    return repr(text)


def is_date_only(moment) -> bool:
    return isinstance(moment, date) and not isinstance(moment, datetime)


def parse_moment(value, field: str, *, need_time: bool = False):
    """Parse an ISO date (-> date) or datetime (-> datetime)."""
    if not isinstance(value, str):
        raise InputError(f"{field} must be an ISO date or datetime string")
    text = value.strip()
    if not (_DATE_ONLY.fullmatch(text) or _DATETIME.fullmatch(text)):
        raise InputError(f"{field} must be YYYY-MM-DD or an ISO datetime")
    try:
        if _DATE_ONLY.fullmatch(text):
            moment = date.fromisoformat(text)
        else:
            moment = datetime.fromisoformat(text)
    except ValueError:
        raise InputError(f"{field} is not a valid date: {_short(value)}") from None
    if need_time and is_date_only(moment):
        raise InputError(f"{field} must include a time, e.g. from `session.py now`")
    return moment


def required_moment(data: dict, field: str, *, need_time: bool = False):
    if data.get(field) is None:
        raise InputError(f"{field} is required")
    return parse_moment(data[field], field, need_time=need_time)


def optional_moment(data: dict, field: str, *, need_time: bool = False):
    if data.get(field) is None:
        return None
    return parse_moment(data[field], field, need_time=need_time)


def parse_number(value, field: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise InputError(f"{field} must be a number")
    return Fraction(value)


def _object_list(data: dict, field: str, *, required: bool) -> list:
    value = data.get(field)
    if value is None:
        if required:
            raise InputError(f"{field} is required (use [] for none)")
        return []
    if not isinstance(value, list):
        raise InputError(f"{field} must be a list")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise InputError(f"{field}[{index}] must be an object")
    return value


def parse_sessions(data: dict) -> list[tuple[datetime, datetime]]:
    sessions = []
    for i, item in enumerate(_object_list(data, "sessions", required=False)):
        pair = []
        for key in ("start", "end"):
            field = f"sessions[{i}].{key}"
            if item.get(key) is None:
                raise InputError(f"{field} is required")
            pair.append(parse_moment(item[key], field, need_time=True))
        sessions.append((pair[0], pair[1]))
    return sessions


def parse_label(data: dict, field: str) -> str:
    value = data.get(field)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise InputError(f"{field} must be a string")
    return " ".join(value.split())


class Clock:
    """Calendar math in one reference offset (now's, else the first datetime's)."""

    def __init__(self, *moments):
        stamps = [m for m in moments if isinstance(m, datetime)]
        if len({m.tzinfo is None for m in stamps}) > 1:
            raise InputError("datetimes mix values with and without a UTC offset")
        self.tz = stamps[0].tzinfo if stamps else None

    def day(self, moment) -> date:
        if is_date_only(moment):
            return moment
        if moment.tzinfo is not None:
            return moment.astimezone(self.tz).date()
        return moment.date()

    def instant(self, moment) -> datetime:
        if is_date_only(moment):
            return datetime.combine(moment, time(0), tzinfo=self.tz)
        return moment


def check_sessions(sessions) -> Fraction:
    total = Fraction(0)
    for i, (start, end) in enumerate(sessions):
        if end < start:
            raise InputError(f"sessions[{i}] ends before it starts")
        total += _minutes(end - start)
    return total


def _minutes(delta: timedelta) -> Fraction:
    return Fraction(delta // timedelta(microseconds=1), 60_000_000)


# --- Display helpers -------------------------------------------------------------

def round_half_up(value: Fraction, step: Fraction) -> Fraction:
    return math.floor(value / step + Fraction(1, 2)) * step


_TOO_LARGE = "a number in the input is too large to compute with"


def num(value: Fraction):
    """JSON number: int when whole, else rounded half-up to 2 decimals."""
    value = Fraction(value)
    if value.denominator == 1:
        return int(value)
    rounded = round_half_up(value, Fraction(1, 100))
    try:
        return int(rounded) if rounded.denominator == 1 else float(rounded)
    except OverflowError:
        raise InputError(_TOO_LARGE) from None


def _plain(value: Fraction) -> str:
    try:
        return str(int(value)) if value.denominator == 1 else f"{float(value):g}"
    except (OverflowError, ValueError):  # float overflow, or int over the str-digit limit
        raise InputError(_TOO_LARGE) from None


def _minute_text(minutes: Fraction) -> str:
    if minutes == 0:
        return "0"
    step = 1 if minutes < 10 else 5
    shown = round_half_up(minutes, Fraction(step))
    return "<1" if shown == 0 else _plain(shown)


def fmt_duration(minutes: Fraction) -> str:
    """Minutes while the value, rounded to its 5-min step, is under an hour
    (5-min steps, 1-min below 10, "<1" for a positive amount that rounds to
    0), else hours in 0.5 steps."""
    if round_half_up(minutes, Fraction(5)) < 60:
        return f"{_minute_text(minutes)} min"
    return f"{_plain(round_half_up(minutes / 60, Fraction(1, 2)))} h"


def count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


# --- Engine --------------------------------------------------------------------

def exam_window(clock: Clock, now: datetime, exam):
    """Return (today, exam_day, hours_to_exam); hours is None for a date-only exam today."""
    today, exam_day = clock.day(now), clock.day(exam)
    if is_date_only(exam):
        if exam_day < today:
            raise InputError("exam is not in the future")
        if exam_day == today:
            return today, exam_day, None
    exam_at = clock.instant(exam)
    if exam_at <= now:
        raise InputError("exam is not in the future")
    if exam_at - now > timedelta(days=MAX_HORIZON_DAYS):
        raise InputError(f"exam is more than {MAX_HORIZON_DAYS} days away")
    return today, exam_day, _minutes(exam_at - now) / 60


def delivery_class(data: dict) -> dict:
    now = required_moment(data, "now", need_time=True)
    exam = optional_moment(data, "exam")
    clock = Clock(now, exam)
    hours = days = None
    if exam is None:
        klass, reason, line = "Standard", "unknown", "Standard delivery: exam date unknown"
    else:
        today, exam_day, hours = exam_window(clock, now, exam)
        days = (exam_day - today).days
        if is_date_only(exam):  # exam time unknown: no hour count, never a countdown to midnight
            hours = None
        if hours is None and days <= 1:
            when = "today" if days == 0 else "tomorrow"
            klass, reason, line = "Urgent", when, f"Urgent delivery: exam {when}, time unknown"
        elif hours is not None and hours <= URGENT_FLOOR_HOURS:
            shown = "under 1 hour" if hours < 1 else count(int(round_half_up(hours, Fraction(1))), "hour")
            klass, reason, line = "Urgent", "floor", f"Urgent delivery: exam in {shown}"
        else:
            klass, reason, line = "Standard", "calm", f"Standard delivery: exam in {count(days, 'day')}"
    return {
        "class": klass,
        "reason": reason,
        "hours_to_exam": None if hours is None else num(hours),
        "days_to_exam": days,
        "line": line,
    }


def _days_before(clock: Clock, first_contact, exam) -> int | None:
    if exam is None:
        return None
    if is_date_only(exam) or is_date_only(first_contact):
        after = clock.day(first_contact) > clock.day(exam)
    else:
        after = first_contact > exam
    if after:
        raise InputError("first_contact is after the exam")
    return (clock.day(exam) - clock.day(first_contact)).days


def _first_contact_text(days_before: int) -> str:
    if days_before == 0:
        return "on the day of the exam"
    return f"{count(days_before, 'day')} before the exam"


def _context(data: dict):
    if "now" in data and data["now"] is None:
        raise InputError("now must not be null")
    now = optional_moment(data, "now", need_time=True)
    first_contact = required_moment(data, "first_contact")
    exam = optional_moment(data, "exam")
    sessions = parse_sessions(data)
    clock = Clock(now, first_contact, exam, *(m for pair in sessions for m in pair))
    studied = check_sessions(sessions)
    return clock, first_contact, exam, sessions, studied, _days_before(clock, first_contact, exam)


def debrief(data: dict) -> dict:
    clock, first_contact, exam, sessions, studied, days_before = _context(data)
    if sessions:
        sentences = [f"Cram bill: {fmt_duration(studied)} studied in {count(len(sessions), 'session')}."]
    else:
        sentences = ["Cram bill: no study sessions logged."]
    if days_before is not None:
        sentences.append(f"First contact: {_first_contact_text(days_before)}.")
    return {
        "actual_minutes": num(studied),
        "actual_hours": num(studied / 60),
        "session_count": len(sessions),
        "days_before_exam": days_before,
        "line": " ".join(sentences),
    }


def summary(data: dict) -> dict:
    course, exam_name = parse_label(data, "course"), parse_label(data, "exam_name")
    _, _, _, sessions, studied, days_before = _context(data)
    label = " ".join(part for part in (course, exam_name) if part) or "Exam"
    if days_before is None:
        clause = "exam date unknown"
    else:
        clause = f"first contact {_first_contact_text(days_before)}"
    if sessions:
        clause += f", {fmt_duration(studied)} studied in {count(len(sessions), 'session')}"
    return {
        "course": course,
        "exam_name": exam_name,
        "days_before_exam": days_before,
        "studied_minutes": num(studied),
        "session_count": len(sessions),
        "line": f"{label}: {clause}.",
    }


def _whole(value, field: str) -> int:
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InputError(f"{field} must be a whole number >= 0")
    return value


def parse_types(data: dict) -> list[dict]:
    types = []
    seen_names: set[str] = set()
    for i, item in enumerate(_object_list(data, "types", required=True)):
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise InputError(f"types[{i}].name must be a non-empty string")
        key = " ".join(name.split()).casefold()
        if key in seen_names:
            raise InputError(f"types[{i}].name repeats an earlier type name")
        seen_names.add(key)
        marks = item.get("marks")
        if marks is not None:
            marks = parse_number(marks, f"types[{i}].marks")
            if marks < 0:
                raise InputError(f"types[{i}].marks must be >= 0 or null")
        seen = _whole(item.get("seen"), f"types[{i}].seen")
        papers = _whole(item.get("papers"), f"types[{i}].papers")
        if seen > papers:
            raise InputError(f"types[{i}].seen must not exceed types[{i}].papers")
        status = item.get("status")
        status = "unseen" if status is None else status
        if status not in TRIAGE_STATUSES:
            raise InputError(f"types[{i}].status must be one of {', '.join(TRIAGE_STATUSES)}")
        types.append({"name": " ".join(name.split()), "marks": marks, "status": status,
                      "frequency": Fraction(seen, papers) if papers > 0 else Fraction(1)})
    return types


def mark_weight(marks, top) -> int:
    """Shared mark-share policy for triage and session planning."""
    return min(WEIGHT_MAX, max(WEIGHT_MIN, math.ceil(3 * marks / top))) if top > 0 else WEIGHT_MIN


def triage(data: dict) -> dict:
    now = required_moment(data, "now", need_time=True)
    exam = optional_moment(data, "exam")
    types = parse_types(data)
    basis = data.get("basis")
    basis = "papers" if basis is None else basis
    if basis not in TRIAGE_BASES:
        raise InputError(f"basis must be one of {', '.join(TRIAGE_BASES)}")
    klass = data.get("class")
    klass = "Urgent" if klass is None else klass
    if klass not in TRIAGE_CLASSES:
        raise InputError(f"class must be one of {', '.join(TRIAGE_CLASSES)}")
    clock = Clock(now, exam)
    hours = None
    today_only = False
    if exam is not None:
        _, _, hours = exam_window(clock, now, exam)
        today_only = hours is None

    known = [t["marks"] for t in types if t["marks"] is not None]
    fill = sum(known, Fraction(0)) / len(known) if known else Fraction(1)
    for t in types:
        if t["marks"] is None:
            t["marks"] = fill
    top = max((t["marks"] for t in types), default=Fraction(0))
    for t in types:
        t["weight"] = mark_weight(t["marks"], top)
        t["minutes"] = EPISODE_MINUTES * t["weight"] * (SHAKY_TIME_FACTOR if t["status"] == "shaky" else 1)
        t["pph"] = t["marks"] * t["frequency"] / (t["minutes"] / 60)

    # Urgent spends the time left on gaps; Standard practice revises mastered types too.
    skip_mastered = klass == "Urgent"
    mastered = [t for t in types if skip_mastered and t["status"] == "mastered"]
    ranked = sorted((t for t in types if not (skip_mastered and t["status"] == "mastered")),
                    key=lambda t: -t["pph"])
    budget = None if hours is None else hours * 60 * URGENT_STUDY_SHARE
    drill, lower = [], []
    for t in ranked:
        if not drill:
            fits = True
        elif today_only:
            fits = False
        elif budget is None:
            fits = True
        else:
            fits = not lower and sum((d["minutes"] for d in drill), t["minutes"]) <= budget
        (drill if fits else lower).append(t)

    skip = [{"name": t["name"], "reason": "lower yield"} for t in lower]
    skip += [{"name": t["name"], "reason": "mastered"} for t in mastered]
    if drill:
        parts = ["Drilling: " + ", ".join(t["name"] for t in drill) + "."]
    elif types:
        parts = ["Nothing to drill: every question type is mastered."]
    else:
        parts = ["Nothing to drill: no question types."]
    if skip:
        parts.append("Skipping: " + ", ".join(f"{s['name']} ({s['reason']})" for s in skip) + ".")
    if basis == "outline":
        parts.append("No past papers, so the forecast is weaker.")
    return {
        "drill": [{"name": t["name"], "marks": num(t["marks"]), "frequency": num(t["frequency"]),
                   "weight": t["weight"], "minutes": num(t["minutes"]), "pph": num(t["pph"])}
                  for t in drill],
        "skip": skip,
        "budget_minutes": None if budget is None else num(budget),
        "basis": basis,
        "line": " ".join(parts),
    }


COMMANDS = {
    "class": (delivery_class, "delivery class (Standard/Urgent) with its reason"),
    "debrief": (debrief, "cram bill: actual hours studied and sessions"),
    "summary": (summary, "one shareable first-contact summary line"),
    "triage": (triage, "triage: question types to drill or skip, by points per hour"),
}


def _fail(message: str, code: int = 2) -> int:
    sys.stderr.write(f"plan.py: {message}\n")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plan.py",
        description=("Mimir planning engine. Subcommands: class (delivery class), "
                     "debrief (cram bill), summary (first-contact line), triage (urgent "
                     "drill/skip by points per hour). Reads one JSON "
                     "object on stdin and prints one JSON object on stdout."),
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="{class,debrief,summary,triage}")
    for name, (_, help_text) in COMMANDS.items():
        sub.add_parser(name, help=help_text)
    args = parser.parse_args(argv)
    try:
        result = COMMANDS[args.command][0](read_input(sys.stdin.buffer.read()))
        try:
            output = json.dumps(result, ensure_ascii=False) + "\n"
        except ValueError:  # an int past the str-digit limit
            raise InputError(_TOO_LARGE) from None
    except InputError as exc:
        return _fail(str(exc))
    except Exception as exc:  # a bug, not bad input; still never a traceback
        return _fail(f"internal error ({type(exc).__name__})", code=1)
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
