"""Boundary tests for scripts/plan.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

PLAN = Path(__file__).resolve().parent.parent / "scripts" / "plan.py"

_spec = importlib.util.spec_from_file_location("plan", PLAN)
plan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan)

NOW = "2026-10-17T09:00:00+03:00"


def run(cmd: str, payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(PLAN), cmd], input=stdin, capture_output=True)


def ok(cmd: str, payload) -> dict:
    proc = run(cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b""
    return json.loads(proc.stdout)


def topics(*weights):
    return [{"name": f"t{i}", "weight": w} for i, w in enumerate(weights)]


def timed(minutes, weight=1, n=3):
    return [{"weight": weight, "minutes": minutes}] * n


# --- I/O matrix: class ---------------------------------------------------------

def test_calm():
    out = ok("class", {"now": NOW, "exam": "2026-11-05", "topics": topics(2, 1)})
    assert out["class"] == "Standard"
    assert out["reason"] == "calm"
    assert out["days_to_exam"] == 19
    assert out["line"] == "Standard delivery: exam in 19 days"
    assert set(out) == {"class", "reason", "hours_to_exam", "days_to_exam", "route_minutes",
                        "capacity_minutes", "confidence", "line"}
    assert out["route_minutes"] == {"low": 37.5, "point": 75, "high": 112.5}


def test_threshold_equal_is_standard():
    # 10 days exactly -> capacity 500 min; calibrated route point 500 min.
    out = ok("class", {"now": NOW, "exam": "2026-10-27T09:00:00+03:00",
                       "topics": topics(1), "timed": timed(500)})
    assert out["capacity_minutes"] == 500
    assert out["route_minutes"]["point"] == 500
    assert (out["class"], out["reason"]) == ("Standard", "calm")


def test_threshold_plus_one_minute_is_urgent_route():
    out = ok("class", {"now": NOW, "exam": "2026-10-27T09:00:00+03:00",
                       "topics": topics(1), "timed": timed(501)})
    assert (out["class"], out["reason"]) == ("Urgent", "route")
    assert out["line"] == "Urgent delivery: about 8.5 h of route left, 10 days to the exam"


def test_route_line_format():
    out = ok("class", {"now": NOW, "exam": "2026-10-26T09:00:00+03:00",
                       "topics": topics(1), "timed": timed(14 * 60)})
    assert out["line"] == "Urgent delivery: about 14 h of route left, 9 days to the exam"


def test_floor_exactly_48h_empty_route():
    out = ok("class", {"now": NOW, "exam": "2026-10-19T09:00:00+03:00", "topics": []})
    assert (out["class"], out["reason"]) == ("Urgent", "floor")
    assert out["line"] == "Urgent delivery: exam in 48 hours"
    assert out["hours_to_exam"] == 48


def test_floor_plus_one_minute_is_standard():
    out = ok("class", {"now": NOW, "exam": "2026-10-19T09:01:00+03:00", "topics": []})
    assert (out["class"], out["reason"]) == ("Standard", "calm")
    assert out["line"] == "Standard delivery: exam in 2 days"


def test_floor_47_5_hours_rounds_to_48():
    out = ok("class", {"now": NOW, "exam": "2026-10-19T08:30:00+03:00", "topics": []})
    assert out["hours_to_exam"] == 47.5
    assert out["line"] == "Urgent delivery: exam in 48 hours"


def test_non_whole_capacity_minutes():
    out = ok("class", {"now": NOW, "exam": "2026-10-20T09:07:00+03:00", "topics": []})
    # 72 h 7 min -> 4327/1440 days x 50 = 150.2430... min
    assert out["capacity_minutes"] == 150.24


def test_floor_30_hours_and_under_one_hour():
    out = ok("class", {"now": NOW, "exam": "2026-10-18T15:00:00+03:00", "topics": []})
    assert out["line"] == "Urgent delivery: exam in 30 hours"
    out = ok("class", {"now": NOW, "exam": "2026-10-17T09:59:00+03:00", "topics": []})
    assert out["line"] == "Urgent delivery: exam in under 1 hour"
    out = ok("class", {"now": NOW, "exam": "2026-10-17T10:00:00+03:00", "topics": []})
    assert out["line"] == "Urgent delivery: exam in 1 hour"


def test_unknown_date():
    out = ok("class", {"now": NOW, "exam": None, "topics": topics(1)})
    assert (out["class"], out["reason"]) == ("Standard", "unknown")
    assert out["line"] == "Standard delivery: exam date unknown"
    assert out["hours_to_exam"] is None and out["days_to_exam"] is None


def test_exam_today_date_only():
    payload = {"now": "2026-11-05T07:00:00+02:00", "exam": "2026-11-05", "topics": topics(2)}
    out = ok("class", payload)
    assert (out["class"], out["reason"]) == ("Urgent", "today")
    assert out["line"] == "Urgent delivery: exam today"
    assert out["hours_to_exam"] is None          # exam time unknown
    assert out["days_to_exam"] == 0
    assert out["capacity_minutes"] == 0
    delay = ok("delay", payload)
    assert len(delay["rows"]) == 1
    assert delay["rows"][0] == {"start": "2026-11-05", "days": 1,
                                "minutes_per_day": {"low": 25, "high": 75}}
    assert delay["line"] == ("Start today: 1 day × 25–75 min. "
                             "(rough: no topics timed yet, ±50%)")


def test_date_only_exam_earlier_day_is_midnight():
    out = ok("class", {"now": "2026-11-03T12:00:00+02:00", "exam": "2026-11-05", "topics": []})
    assert out["hours_to_exam"] == 36
    assert out["reason"] == "floor"


@pytest.mark.parametrize("payload", [
    {"now": "2026-11-05T09:00:00+02:00", "exam": "2026-11-05T09:00:00+02:00", "topics": []},
    {"now": "2026-11-05T10:00:00+02:00", "exam": "2026-11-05T09:00:00+02:00", "topics": []},
    {"now": "2026-11-06T00:00:00+02:00", "exam": "2026-11-05", "topics": []},
])
@pytest.mark.parametrize("cmd", ["class", "delay"])
def test_past_exam(cmd, payload):
    proc = run(cmd, payload)
    assert proc.returncode == 2
    assert proc.stdout == b""
    assert proc.stderr.decode() == "plan.py: exam is not in the future\n"


def test_horizon():
    proc = run("delay", {"now": NOW, "exam": "2027-10-19T09:00:00+03:00", "topics": []})  # 367 days
    assert proc.returncode == 2
    assert b"366 days" in proc.stderr
    assert proc.stdout == b""
    out = ok("delay", {"now": NOW, "exam": "2027-10-18T09:00:00+03:00", "topics": []})  # 366 days
    assert len(out["rows"]) == 366


def test_null_now():
    proc = run("class", {"now": None, "exam": "2026-11-05", "topics": []})
    assert proc.returncode == 2 and proc.stdout == b""
    assert proc.stderr.decode() == "plan.py: now is required\n"


# --- Estimates -------------------------------------------------------------------

def test_cold_start_estimate_and_partial_timing():
    est = plan.estimate([Fraction(1), Fraction(3)], [])
    assert (est["low"], est["point"], est["high"]) == (50, 100, 150)
    assert est["confidence"] == "rough: no topics timed yet, ±50%"
    two = plan.estimate([Fraction(1)], [(Fraction(1), Fraction(60))] * 2)
    assert two["point"] == 25
    assert two["confidence"] == "rough: only 2 topics timed so far, ±50%"


def test_calibrated_estimate_normalizes_by_weight():
    logged = [(Fraction(1), Fraction(20)), (Fraction(2), Fraction(80)), (Fraction(3), Fraction(90))]
    est = plan.estimate([Fraction(3), Fraction(1)], logged)  # ratios 20, 40, 30
    assert (est["low"], est["point"], est["high"]) == (80, 120, 160)
    assert est["confidence"] == "based on 3 timed topics"


# --- Delay -----------------------------------------------------------------------

def test_delay_rows_and_line():
    out = ok("delay", {"now": NOW, "exam": "2026-11-05", "topics": topics(3, 3, 3, 3, 3, 3, 3, 1)})
    rows = out["rows"]
    assert len(rows) == 19
    assert rows[0]["start"] == "2026-10-17" and rows[0]["days"] == 19
    assert rows[0]["minutes_per_day"] == {"low": 14.47, "high": 43.42}   # 275/19, 825/19
    assert rows[-1]["start"] == "2026-11-04" and rows[-1]["days"] == 1
    assert [r["days"] for r in rows] == list(range(19, 0, -1))
    assert out["line"] == ("Start today: 19 days × 15–45 min. Start Mon Oct 26: 10 days × 30–85 min. "
                           "Start Wed Nov 4: 1 day × 4.5–14 h. (rough: no topics timed yet, ±50%)")


def test_delay_exam_tomorrow_single_row_and_two_rows():
    out = ok("delay", {"now": NOW, "exam": "2026-10-18", "topics": topics(1)})
    assert [r["days"] for r in out["rows"]] == [1]
    out = ok("delay", {"now": NOW, "exam": "2026-10-19", "topics": topics(1)})
    assert out["line"].startswith("Start today: 2 days × ")
    assert "Start Sun Oct 18: 1 day × " in out["line"]
    assert out["line"].count("Start ") == 2


def test_delay_unknown_and_empty_route():
    out = ok("delay", {"now": NOW, "exam": None, "topics": topics(1)})
    assert out["rows"] == [] and out["line"] == "Cost of delay: exam date unknown."
    out = ok("delay", {"now": NOW, "exam": "2026-11-05", "topics": []})
    assert out["line"] == "Cost of delay: no topics left on the route."


def test_duration_formatting():
    F = Fraction
    assert plan.fmt_range(F(15), F(45)) == "15–45 min"
    assert plan.fmt_range(F(28, 3), F(9)) == "9 min"            # under 10: 1-min steps, collapse
    assert plan.fmt_range(F(7, 2), F(85, 10)) == "4–9 min"       # half rounds up
    assert plan.fmt_range(F(1, 4), F(2)) == "<1–2 min"          # positive never shows 0
    assert plan.fmt_duration(F(1, 3)) == "<1 min"
    assert plan.fmt_duration(F(0)) == "0 min"
    assert plan.fmt_range(F(57, 2), F(171, 2)) == "30–85 min"    # 5-min steps
    assert plan.fmt_range(F(60), F(855)) == "1–14.5 h"           # hours, 0.5 steps
    assert plan.fmt_duration(F(390)) == "6.5 h"
    assert plan.fmt_range(F(58), F(500)) == "1–8.5 h"            # low rounds to 60 -> hours
    assert plan.fmt_range(F(57, 2), F(500)) == "30–500 min"
    assert plan.fmt_range(F(57.4), F(500)) == "55–500 min"


def test_low_end_near_an_hour_shows_hours():
    # Calibrated 58 min x 1 topic over 1 day: "58–58" low rounds to 60 -> hours.
    out = ok("delay", {"now": NOW, "exam": "2026-10-18", "topics": topics(1),
                       "timed": [{"weight": 1, "minutes": 58}, {"weight": 1, "minutes": 58},
                                 {"weight": 1, "minutes": 500}]})
    assert out["line"] == "Start today: 1 day × 1–8.5 h. (based on 3 timed topics)"


def test_delay_tiny_amount_shows_under_one_minute():
    # 12.5 min low spread over 366 days.
    out = ok("delay", {"now": NOW, "exam": "2027-10-18T09:00:00+03:00", "topics": topics(1)})
    assert out["line"].startswith("Start today: 366 days × <1 min. ")


# --- Debrief ---------------------------------------------------------------------

SESSION = {"start": "2026-11-03T20:00:00+02:00", "end": "2026-11-03T23:30:00+02:00"}


def test_debrief_basic_and_spread_not_multiple_of_50():
    out = ok("debrief", {"first_contact": "2026-11-03T20:00:00+02:00", "exam": "2026-11-05",
                         "topics": topics(2, 3, 1), "sessions": [SESSION]})
    assert out["actual_minutes"] == 210 and out["actual_hours"] == 3.5
    assert out["counterfactual_minutes"] == {"low": 75, "point": 150, "high": 225}
    assert out["spread_days"] == {"low": 2, "high": 5}    # 75/50 -> 2, 225/50 -> 5
    assert out["days_before_exam"] == 2
    assert out["line"] == ("Cram bill: 3.5 h studied in 1 session. Counterfactual at 50 min a day: "
                           "roughly 1.5–4 h over 2–5 days (rough: no topics timed yet, ±50%). "
                           "First contact: 2 days before the exam.")


def test_debrief_minutes_text_and_equal_range_collapse():
    out = ok("debrief", {"first_contact": "2026-11-04", "exam": "2026-11-05",
                         "topics": topics(1), "timed": timed(40), "sessions": []})
    assert out["counterfactual_text"] == "40 min"
    assert out["spread_days"] == {"low": 1, "high": 1}
    assert out["line"] == ("Cram bill: no study sessions logged. Counterfactual at 50 min a day: "
                           "roughly 40 min over 1 day (based on 3 timed topics). "
                           "First contact: 1 day before the exam.")


def test_debrief_empty_route_and_null_exam():
    out = ok("debrief", {"first_contact": "2026-11-04", "exam": None, "topics": [],
                         "sessions": [SESSION]})
    assert out["days_before_exam"] is None
    assert out["spread_days"] == {"low": 0, "high": 0}
    assert out["line"] == "Cram bill: 3.5 h studied in 1 session. Counterfactual: no topics on the route."


def test_debrief_now_offset_moves_calendar_day():
    out = ok("debrief", {"now": "2026-11-04T01:00:00+03:00",
                         "first_contact": "2026-11-03T23:30:00+00:00",   # Nov 4 02:30 at +03:00
                         "exam": "2026-11-05", "topics": []})
    assert out["days_before_exam"] == 1


def test_debrief_short_session_minutes():
    out = ok("debrief", {"first_contact": "2026-11-05", "exam": "2026-11-05", "topics": [],
                         "sessions": [{"start": "2026-11-05T07:00:00+02:00",
                                       "end": "2026-11-05T07:00:20+02:00"}]})
    assert out["line"].startswith("Cram bill: <1 min studied in 1 session.")
    assert out["line"].endswith("First contact: on the day of the exam.")


# --- Summary ---------------------------------------------------------------------

def test_summary_line():
    sessions = [
        {"start": "2026-11-03T20:00:00+02:00", "end": "2026-11-03T23:00:00+02:00"},
        {"start": "2026-11-04T10:00:00+02:00", "end": "2026-11-04T12:30:00+02:00"},
        {"start": "2026-11-04T20:00:00+02:00", "end": "2026-11-04T21:00:00+02:00"},
    ]
    out = ok("summary", {"course": "CS201", "exam_name": "final", "first_contact": "2026-11-03",
                         "exam": "2026-11-05", "sessions": sessions})
    assert out["line"] == "CS201 final: first contact 2 days before the exam, 6.5 h studied in 3 sessions."


@pytest.mark.parametrize("sessions", [[], None, "missing"])
def test_summary_without_sessions_same_day(sessions):
    payload = {"course": "CS201", "exam_name": "final", "first_contact": "2026-11-05T07:00:00+02:00",
               "exam": "2026-11-05"}
    if sessions != "missing":
        payload["sessions"] = sessions
    out = ok("summary", payload)
    assert out["line"] == "CS201 final: first contact on the day of the exam."


def test_summary_unknown_exam_no_labels():
    out = ok("summary", {"course": None, "exam_name": "", "first_contact": "2026-11-03", "exam": None})
    assert out["line"] == "Exam: exam date unknown."
    assert out["days_before_exam"] is None
    assert out["studied_minutes"] == 0 and out["session_count"] == 0


def test_summary_label_whitespace_and_fields():
    out = ok("summary", {"course": "  CS\n201 ", "exam_name": " final\t exam ",
                         "first_contact": "2026-11-03", "exam": "2026-11-05", "sessions": [SESSION]})
    assert out["course"] == "CS 201" and out["exam_name"] == "final exam"
    assert out["line"] == "CS 201 final exam: first contact 2 days before the exam, 3.5 h studied in 1 session."
    assert out["days_before_exam"] == 2
    assert out["studied_minutes"] == 210
    assert out["session_count"] == 1


def test_first_contact_later_same_day_than_datetime_exam():
    proc = run("summary", {"first_contact": "2026-11-05T10:00:00+02:00",
                           "exam": "2026-11-05T09:00:00+02:00"})
    assert proc.returncode == 2 and proc.stdout == b""
    assert proc.stderr.decode() == "plan.py: first_contact is after the exam\n"


def test_summary_first_contact_after_exam():
    proc = run("summary", {"first_contact": "2026-11-06", "exam": "2026-11-05"})
    assert proc.returncode == 2 and b"after the exam" in proc.stderr


# --- Offsets ---------------------------------------------------------------------

def test_mixed_offset_calendar_dates():
    # now is Oct 18 01:00 at +03:00 (Oct 17 22:00 UTC); the exam is Oct 20 02:30 at +03:00.
    out = ok("class", {"now": "2026-10-18T01:00:00+03:00", "exam": "2026-10-19T23:30:00+00:00",
                       "topics": []})
    assert out["days_to_exam"] == 2
    assert out["hours_to_exam"] == 49.5
    delay = ok("delay", {"now": "2026-10-18T01:00:00+03:00", "exam": "2026-10-19T23:30:00+00:00",
                         "topics": topics(1)})
    assert [r["start"] for r in delay["rows"]] == ["2026-10-18", "2026-10-19"]


def test_naive_datetimes_are_accepted_together():
    out = ok("class", {"now": "2026-10-17T09:00:00", "exam": "2026-11-05", "topics": []})
    assert out["days_to_exam"] == 19


# --- Determinism -------------------------------------------------------------------

@pytest.mark.parametrize("cmd,payload", [
    ("class", {"now": NOW, "exam": "2026-11-05", "topics": topics(1, 2, 3), "timed": timed(33.3)}),
    ("delay", {"now": NOW, "exam": "2026-11-05", "topics": topics(1, 2, 3)}),
    ("debrief", {"first_contact": "2026-11-03", "exam": "2026-11-05", "topics": topics(2),
                 "sessions": [SESSION]}),
    ("summary", {"course": "CS201", "first_contact": "2026-11-03", "exam": "2026-11-05",
                 "sessions": [SESSION]}),
])
def test_byte_identical_rerun(cmd, payload):
    first, second = run(cmd, payload), run(cmd, payload)
    assert first.returncode == 0
    assert first.stdout == second.stdout


# --- Exit-2 rules -------------------------------------------------------------------

BASE = {"now": NOW, "exam": "2026-11-05", "topics": topics(1)}


@pytest.mark.parametrize("cmd,payload,message", [
    ("class", b"{not json", "not valid JSON"),
    ("class", b"[1, 2]", "one JSON object"),
    ("class", b'{"now": "\xff"}', "not valid UTF-8"),
    ("class", b"[" * 100_000, "too deeply nested"),
    ("class", {"exam": "2026-11-05", "topics": []}, "now is required"),
    ("class", {"now": NOW, "exam": "2026-11-05"}, "topics is required"),
    ("delay", {"now": NOW, "exam": "2026-11-05", "topics": None}, "topics is required"),
    ("debrief", {"exam": "2026-11-05", "topics": []}, "first_contact is required"),
    ("summary", {"first_contact": None, "exam": "2026-11-05"}, "first_contact is required"),
    ("debrief", {"first_contact": "2026-11-01", "topics": None}, "topics is required"),
    ("debrief", {"now": None, "first_contact": "2026-11-01", "topics": []}, "now must not be null"),
    ("class", {**BASE, "exam": "next friday"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("class", {**BASE, "exam": "2026-02-30"}, "exam is not a valid date"),
    ("class", {**BASE, "exam": "20261105"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("class", {**BASE, "exam": "2026-W45-4"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("class", {**BASE, "exam": "2026-11-05 09:00"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("debrief", {"first_contact": "2026-11-01", "topics": [],
                 "sessions": [{"start": "2026-11-03", "end": "2026-11-03T23:30:00+02:00"}]},
     "sessions[0].start must include a time"),
    ("summary", {"first_contact": "2026-11-01",
                 "sessions": [{"start": "2026-11-03T20:00:00+02:00", "end": "2026-11-04"}]},
     "sessions[0].end must include a time"),
    ("class", b'{"now": "2026-10-17T09:00:00+03:00", "exam": "2026-11-05", "topics": [{"weight": 3}], '
              b'"timed": [' + b", ".join([b'{"weight": 1, "minutes": 4' + b"0" * 4299 + b"}"] * 3) + b"]}",
     "too large"),
    ("debrief", b'{"first_contact": "2026-11-01", "topics": [{"weight": 3}], '
                b'"timed": [' + b", ".join([b'{"weight": 1, "minutes": 4' + b"0" * 4299 + b"}"] * 3) + b"]}",
     "too large"),
    ("class", {**BASE, "now": "2026-10-17"}, "now must include a time"),
    ("class", {**BASE, "topics": topics(0)}, "between 1 and 3"),
    ("class", {**BASE, "topics": topics(3.5)}, "between 1 and 3"),
    ("class", {**BASE, "topics": topics(True)}, "must be a number"),
    ("class", {**BASE, "topics": [{"name": "x"}]}, "must be a number"),
    ("class", {**BASE, "timed": [{"weight": 4, "minutes": 10}]}, "between 1 and 3"),
    ("class", {**BASE, "timed": [{"weight": 1, "minutes": 0}]}, "must be positive"),
    ("class", {**BASE, "timed": [{"weight": 1, "minutes": -5}]}, "must be positive"),
    ("class", b'{"now": "2026-10-17T09:00:00+03:00", "topics": [], "timed": [{"weight": 1, "minutes": NaN}]}',
     "non-finite"),
    ("class", b'{"now": "2026-10-17T09:00:00+03:00", "topics": [], "timed": [{"weight": 1, "minutes": Infinity}]}',
     "non-finite"),
    ("class", b'{"now": "2026-10-17T09:00:00+03:00", "topics": [], "timed": [{"weight": 1, "minutes": 1e999}]}',
     "finite"),
    ("class", {**BASE, "exam": "2026-11-05T09:00:00"}, "with and without a UTC offset"),
    ("debrief", {"first_contact": "2026-11-01T09:00:00", "topics": [],
                 "sessions": [SESSION]}, "with and without a UTC offset"),
    ("debrief", {"first_contact": "2026-11-01", "topics": [],
                 "sessions": [{"start": SESSION["end"], "end": SESSION["start"]}]}, "ends before it starts"),
    ("summary", {"first_contact": "2026-11-01", "sessions": [{"start": SESSION["start"]}]},
     "sessions[0].end is required"),
    ("class", {**BASE, "exam": "2027-10-19T09:00:00+03:00"}, "more than 366 days away"),
])
def test_invalid_input_exits_2(cmd, payload, message):
    proc = run(cmd, payload)
    assert proc.returncode == 2
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("plan.py: ") and err.endswith("\n") and err.count("\n") == 1, err
    assert message in err
    assert "Traceback" not in err


def test_internal_error_exits_1_without_traceback(monkeypatch, capsys):
    import io

    def boom(data):
        raise ZeroDivisionError("bug")

    monkeypatch.setitem(plan.COMMANDS, "class", (boom, "test"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    assert plan.main(["class"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "plan.py: internal error (ZeroDivisionError)\n"


# --- I/O matrix: triage ---------------------------------------------------------

def qtype(name, marks=10, seen=1, papers=1, status="unseen"):
    return {"name": name, "marks": marks, "seen": seen, "papers": papers, "status": status}


def in_hours(h):
    return f"2026-10-17T{9 + h:02d}:00:00+03:00"


def names(out, key="drill"):
    return [t["name"] for t in out[key]]


def test_triage_rank():
    out = ok("triage", {"now": NOW, "exam": None,
                        "types": [qtype("B", 10, 1, 2), qtype("A", 20, 2, 2)]})
    assert names(out) == ["A", "B"]
    a, b = out["drill"]
    assert (a["weight"], a["minutes"], a["frequency"], a["pph"]) == (3, 75, 1, 16)
    assert (b["weight"], b["minutes"], b["frequency"], b["pph"]) == (2, 50, 0.5, 6)
    assert set(out) == {"drill", "skip", "budget_minutes", "basis", "line"}


def test_triage_shaky_ranks_first_with_half_minutes():
    out = ok("triage", {"now": NOW, "exam": None,
                        "types": [qtype("A"), qtype("B", status="shaky")]})
    assert names(out) == ["B", "A"]
    assert out["drill"][0]["minutes"] == 37.5


def test_triage_mastered_is_skipped():
    out = ok("triage", {"now": NOW, "exam": None,
                        "types": [qtype("A", status="mastered"), qtype("B")]})
    assert names(out) == ["B"]
    assert out["skip"] == [{"name": "A", "reason": "mastered"}]
    assert out["line"] == "Drilling: B. Skipping: A (mastered)."
    urgent = ok("triage", {"now": NOW, "exam": None, "class": "Urgent",
                           "types": [qtype("A", status="mastered"), qtype("B")]})
    assert urgent == out  # Urgent is the default


def test_triage_standard_includes_mastered():
    types = [qtype("A", 20, status="mastered"), qtype("B", 10, status="gap"), qtype("C", status="mastered")]
    out = ok("triage", {"now": NOW, "exam": None, "class": "Standard", "types": types})
    assert names(out) == ["A", "B", "C"] and out["skip"] == []  # ranked by pph like the rest
    assert out["line"] == "Drilling: A, B, C."
    only = ok("triage", {"now": NOW, "exam": None, "class": "Standard", "types": [qtype("A", status="mastered")]})
    assert names(only) == ["A"]



def test_triage_budget():
    out = ok("triage", {"now": NOW, "exam": in_hours(8),
                        "types": [qtype("A"), qtype("B"), qtype("C")]})
    assert out["budget_minutes"] == 160
    assert [t["minutes"] for t in out["drill"]] == [75, 75]
    assert names(out) == ["A", "B"]
    assert out["skip"] == [{"name": "C", "reason": "lower yield"}]
    assert out["line"] == "Drilling: A, B. Skipping: C (lower yield)."


def test_triage_floor_one():
    out = ok("triage", {"now": NOW, "exam": in_hours(3), "types": [qtype("A"), qtype("B")]})
    assert out["budget_minutes"] == 60
    assert names(out) == ["A"]
    assert out["skip"] == [{"name": "B", "reason": "lower yield"}]


def test_triage_stops_at_first_type_that_does_not_fit():
    # Budget 180: A 75 and B 75 fit (150); C would make 225, so drilling stops there.
    # D (weight 1, 25 min, lowest pph) would fit the remaining 30 min but is not packed in.
    types = [qtype("A", 30), qtype("B", 30), qtype("C", 30), qtype("D", 1)]
    out = ok("triage", {"now": NOW, "exam": in_hours(9), "types": types})
    assert out["budget_minutes"] == 180
    assert [t["minutes"] for t in out["drill"]] == [75, 75]
    assert names(out) == ["A", "B"]
    assert names(out, "skip") == ["C", "D"]


def test_triage_zero_marks_type():
    out = ok("triage", {"now": NOW, "exam": None, "types": [qtype("A", 10), qtype("B", 0)]})
    b = {t["name"]: t for t in out["drill"]}["B"]
    assert (b["weight"], b["minutes"], b["pph"]) == (1, 25, 0)
    assert names(out) == ["A", "B"]


def test_triage_skip_order():
    types = [qtype("M1", status="mastered"), qtype("A", 30), qtype("B", 15),
             qtype("M2", status="mastered"), qtype("C", 25)]
    # pph: A 24 (75 min), C 20 (75 min), B 18 (50 min); budget 60 -> only A.
    out = ok("triage", {"now": NOW, "exam": in_hours(3), "types": types})
    assert names(out) == ["A"]
    assert out["skip"] == [{"name": "C", "reason": "lower yield"}, {"name": "B", "reason": "lower yield"},
                           {"name": "M1", "reason": "mastered"}, {"name": "M2", "reason": "mastered"}]
    assert out["line"] == ("Drilling: A. Skipping: C (lower yield), B (lower yield), "
                           "M1 (mastered), M2 (mastered).")


def test_triage_no_papers_outline():
    out = ok("triage", {"now": NOW, "exam": None, "basis": "outline",
                        "types": [qtype("A", None, 0, 0), qtype("B", None, 0, 0)]})
    assert [(t["marks"], t["weight"], t["frequency"]) for t in out["drill"]] == [(1, 3, 1), (1, 3, 1)]
    assert names(out) == ["A", "B"]
    assert out["line"] == "Drilling: A, B. No past papers, so the forecast is weaker."
    assert out["basis"] == "outline"


def test_triage_null_marks_take_mean_of_known():
    out = ok("triage", {"now": NOW, "exam": None,
                        "types": [qtype("A", 20), qtype("B", None), qtype("C", 10)]})
    assert {t["name"]: t["marks"] for t in out["drill"]}["B"] == 15


def test_triage_exam_null_drills_all_non_mastered():
    types = [qtype(n) for n in "ABCDEFG"] + [qtype("M", status="mastered")]
    out = ok("triage", {"now": NOW, "exam": None, "types": types})
    assert names(out) == list("ABCDEFG")
    assert out["budget_minutes"] is None
    assert out["skip"] == [{"name": "M", "reason": "mastered"}]


def test_triage_date_only_exam_today_drills_top_only():
    out = ok("triage", {"now": "2026-11-05T07:00:00+02:00", "exam": "2026-11-05",
                        "types": [qtype("A", 5), qtype("B", 20)]})
    assert names(out) == ["B"]
    assert out["budget_minutes"] is None
    assert out["skip"] == [{"name": "A", "reason": "lower yield"}]


def test_triage_edge_cases():
    out = ok("triage", {"now": NOW, "exam": None, "types": []})
    assert out["drill"] == [] and out["line"] == "Nothing to drill: no question types."
    out = ok("triage", {"now": NOW, "exam": None, "types": [qtype("A", status="mastered")]})
    assert out["drill"] == []
    assert out["line"] == "Nothing to drill: every question type is mastered. Skipping: A (mastered)."
    out = ok("triage", {"now": NOW, "exam": None, "types": [qtype("A", 0), qtype("B", 0)]})
    assert [t["weight"] for t in out["drill"]] == [1, 1]
    assert ok("triage", {"now": NOW, "exam": None, "types": [{"name": "A"}]})["drill"][0]["frequency"] == 1


def test_triage_is_deterministic():
    payload = {"now": NOW, "exam": in_hours(8), "types": [qtype("A", 7, 1, 3), qtype("B", 3, 2, 3)]}
    assert run("triage", payload).stdout == run("triage", payload).stdout


TRIAGE = {"now": NOW, "exam": None}


@pytest.mark.parametrize("payload, message", [
    ({**TRIAGE, "types": [qtype("A", status="done")]}, "types[0].status must be one of"),
    ({**TRIAGE, "types": [qtype("A", -1)]}, "types[0].marks must be >= 0"),
    ({**TRIAGE, "types": [qtype("A"), qtype("B", seen=3, papers=2)]}, "types[1].seen must not exceed"),
    ({**TRIAGE, "types": [qtype("A", seen=1, papers=0)]}, "types[0].seen must not exceed"),
    ({**TRIAGE, "types": [qtype("A", seen=1.5, papers=2)]}, "types[0].seen must be a whole number"),
    ({**TRIAGE, "types": [qtype("A", papers=-1)]}, "types[0].papers must be a whole number"),
    ({**TRIAGE, "types": [qtype("A", "10")]}, "types[0].marks must be a number"),
    ({**TRIAGE, "types": [qtype("")]}, "types[0].name must be a non-empty string"),
    ({**TRIAGE, "types": [qtype("Heaps"), qtype(" heaps  ")]}, "types[1].name repeats"),
    ({**TRIAGE, "types": ["A"]}, "types[0] must be an object"),
    ({**TRIAGE}, "types is required"),
    ({**TRIAGE, "types": [], "basis": "slides"}, "basis must be one of"),
    ({**TRIAGE, "types": [], "class": "standard"}, "class must be one of"),
    ({"exam": None, "types": []}, "now is required"),
    ({"now": NOW, "exam": "2026-10-16", "types": []}, "exam is not in the future"),
])
def test_triage_invalid_input_exits_2(payload, message):
    proc = run("triage", payload)
    assert proc.returncode == 2
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("plan.py: ") and err.count("\n") == 1 and message in err, err
