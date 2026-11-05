"""Boundary tests for scripts/plan.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
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


# --- I/O matrix: class ---------------------------------------------------------

CLASS_KEYS = {"class", "reason", "hours_to_exam", "days_to_exam", "line"}


def test_calm():
    out = ok("class", {"now": NOW, "exam": "2026-11-05"})
    assert out["class"] == "Standard"
    assert out["reason"] == "calm"
    assert out["days_to_exam"] == 19
    assert out["line"] == "Standard delivery: exam in 19 days"
    assert set(out) == CLASS_KEYS


def test_long_route_far_from_exam_stays_standard():
    # A huge route 3 days out used to switch to Urgent ("route"); only exam proximity decides now.
    out = ok("class", {"now": NOW, "exam": "2026-10-20T09:00:00+03:00",
                       "topics": [{"name": f"t{i}", "weight": 3} for i in range(40)],
                       "timed": [{"weight": 1, "minutes": 500}] * 3})
    assert (out["class"], out["reason"]) == ("Standard", "calm")
    assert out["line"] == "Standard delivery: exam in 3 days"
    assert set(out) == CLASS_KEYS


def test_floor_exactly_48h_empty_route():
    out = ok("class", {"now": NOW, "exam": "2026-10-19T09:00:00+03:00"})
    assert (out["class"], out["reason"]) == ("Urgent", "floor")
    assert out["line"] == "Urgent delivery: exam in 48 hours"
    assert out["hours_to_exam"] == 48


def test_floor_plus_one_minute_is_standard():
    out = ok("class", {"now": NOW, "exam": "2026-10-19T09:01:00+03:00"})
    assert (out["class"], out["reason"]) == ("Standard", "calm")
    assert out["line"] == "Standard delivery: exam in 2 days"


def test_floor_47_5_hours_rounds_to_48():
    out = ok("class", {"now": NOW, "exam": "2026-10-19T08:30:00+03:00"})
    assert out["hours_to_exam"] == 47.5
    assert out["line"] == "Urgent delivery: exam in 48 hours"


def test_floor_30_hours_and_under_one_hour():
    out = ok("class", {"now": NOW, "exam": "2026-10-18T15:00:00+03:00"})
    assert out["line"] == "Urgent delivery: exam in 30 hours"
    out = ok("class", {"now": NOW, "exam": "2026-10-17T09:59:00+03:00"})
    assert out["line"] == "Urgent delivery: exam in under 1 hour"
    out = ok("class", {"now": NOW, "exam": "2026-10-17T10:00:00+03:00"})
    assert out["line"] == "Urgent delivery: exam in 1 hour"


def test_unknown_date():
    out = ok("class", {"now": NOW, "exam": None})
    assert (out["class"], out["reason"]) == ("Standard", "unknown")
    assert out["line"] == "Standard delivery: exam date unknown"
    assert out["hours_to_exam"] is None and out["days_to_exam"] is None


def test_exam_today_date_only():
    payload = {"now": "2026-11-05T07:00:00+02:00", "exam": "2026-11-05"}
    out = ok("class", payload)
    assert (out["class"], out["reason"]) == ("Urgent", "today")
    assert out["line"] == "Urgent delivery: exam today"
    assert out["hours_to_exam"] is None          # exam time unknown
    assert out["days_to_exam"] == 0


def test_date_only_exam_earlier_day_is_midnight():
    out = ok("class", {"now": "2026-11-03T12:00:00+02:00", "exam": "2026-11-05"})
    assert out["hours_to_exam"] == 36
    assert out["reason"] == "floor"


@pytest.mark.parametrize("payload", [
    {"now": "2026-11-05T09:00:00+02:00", "exam": "2026-11-05T09:00:00+02:00"},
    {"now": "2026-11-05T10:00:00+02:00", "exam": "2026-11-05T09:00:00+02:00"},
    {"now": "2026-11-06T00:00:00+02:00", "exam": "2026-11-05"},
])
def test_past_exam(payload):
    proc = run("class", payload)
    assert proc.returncode == 2
    assert proc.stdout == b""
    assert proc.stderr.decode() == "plan.py: exam is not in the future\n"


def test_horizon():
    proc = run("class", {"now": NOW, "exam": "2027-10-19T09:00:00+03:00"})  # 367 days
    assert proc.returncode == 2
    assert b"366 days" in proc.stderr
    assert proc.stdout == b""
    out = ok("class", {"now": NOW, "exam": "2027-10-18T09:00:00+03:00"})  # 366 days
    assert out["days_to_exam"] == 366


def test_null_now():
    proc = run("class", {"now": None, "exam": "2026-11-05"})
    assert proc.returncode == 2 and proc.stdout == b""
    assert proc.stderr.decode() == "plan.py: now is required\n"


# --- No learning-time forecasts ---------------------------------------------------

def test_delay_subcommand_is_gone():
    proc = run("delay", {"now": NOW, "exam": "2026-11-05", "topics": topics(1)})
    assert proc.returncode == 2
    assert proc.stdout == b""
    assert b"invalid choice: 'delay'" in proc.stderr


# --- Debrief ---------------------------------------------------------------------

SESSION = {"start": "2026-11-03T20:00:00+02:00", "end": "2026-11-03T23:30:00+02:00"}


DEBRIEF_KEYS = {"actual_minutes", "actual_hours", "session_count", "days_before_exam", "line"}


def test_debrief_reports_actual_hours_only():
    out = ok("debrief", {"first_contact": "2026-11-03T20:00:00+02:00", "exam": "2026-11-05",
                         "topics": topics(2, 3, 1), "sessions": [SESSION]})
    assert set(out) == DEBRIEF_KEYS
    assert out["actual_minutes"] == 210 and out["actual_hours"] == 3.5
    assert out["session_count"] == 1
    assert out["days_before_exam"] == 2
    assert out["line"] == "Cram bill: 3.5 h studied in 1 session. First contact: 2 days before the exam."


def test_debrief_no_sessions():
    out = ok("debrief", {"first_contact": "2026-11-04", "exam": "2026-11-05"})
    assert set(out) == DEBRIEF_KEYS
    assert (out["actual_minutes"], out["session_count"]) == (0, 0)
    assert out["line"] == "Cram bill: no study sessions logged. First contact: 1 day before the exam."


def test_debrief_null_exam():
    out = ok("debrief", {"first_contact": "2026-11-04", "exam": None, "sessions": [SESSION]})
    assert out["days_before_exam"] is None
    assert out["line"] == "Cram bill: 3.5 h studied in 1 session."


def test_debrief_now_offset_moves_calendar_day():
    out = ok("debrief", {"now": "2026-11-04T01:00:00+03:00",
                         "first_contact": "2026-11-03T23:30:00+00:00",   # Nov 4 02:30 at +03:00
                         "exam": "2026-11-05"})
    assert out["days_before_exam"] == 1


def test_debrief_short_session_minutes():
    out = ok("debrief", {"first_contact": "2026-11-05", "exam": "2026-11-05",
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
    out = ok("class", {"now": "2026-10-18T01:00:00+03:00", "exam": "2026-10-19T23:30:00+00:00"})
    assert out["days_to_exam"] == 2
    assert out["hours_to_exam"] == 49.5


def test_naive_datetimes_are_accepted_together():
    out = ok("class", {"now": "2026-10-17T09:00:00", "exam": "2026-11-05"})
    assert out["days_to_exam"] == 19


# --- Determinism -------------------------------------------------------------------

@pytest.mark.parametrize("cmd,payload", [
    ("class", {"now": NOW, "exam": "2026-11-05"}),
    ("debrief", {"first_contact": "2026-11-03", "exam": "2026-11-05", "sessions": [SESSION]}),
    ("summary", {"course": "CS201", "first_contact": "2026-11-03", "exam": "2026-11-05",
                 "sessions": [SESSION]}),
])
def test_byte_identical_rerun(cmd, payload):
    first, second = run(cmd, payload), run(cmd, payload)
    assert first.returncode == 0
    assert first.stdout == second.stdout


# --- Exit-2 rules -------------------------------------------------------------------

BASE = {"now": NOW, "exam": "2026-11-05"}


@pytest.mark.parametrize("cmd,payload,message", [
    ("class", b"{not json", "not valid JSON"),
    ("class", b"[1, 2]", "one JSON object"),
    ("class", b'{"now": "\xff"}', "not valid UTF-8"),
    ("class", b"[" * 100_000, "too deeply nested"),
    ("class", {"exam": "2026-11-05"}, "now is required"),
    ("debrief", {"exam": "2026-11-05"}, "first_contact is required"),
    ("summary", {"first_contact": None, "exam": "2026-11-05"}, "first_contact is required"),
    ("debrief", {"now": None, "first_contact": "2026-11-01"}, "now must not be null"),
    ("class", {**BASE, "exam": "next friday"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("class", {**BASE, "exam": "2026-02-30"}, "exam is not a valid date"),
    ("class", {**BASE, "exam": "20261105"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("class", {**BASE, "exam": "2026-W45-4"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("class", {**BASE, "exam": "2026-11-05 09:00"}, "exam must be YYYY-MM-DD or an ISO datetime"),
    ("debrief", {"first_contact": "2026-11-01",
                 "sessions": [{"start": "2026-11-03", "end": "2026-11-03T23:30:00+02:00"}]},
     "sessions[0].start must include a time"),
    ("summary", {"first_contact": "2026-11-01",
                 "sessions": [{"start": "2026-11-03T20:00:00+02:00", "end": "2026-11-04"}]},
     "sessions[0].end must include a time"),
    ("class", {**BASE, "now": "2026-10-17"}, "now must include a time"),
    ("class", {**BASE, "exam": "2026-11-05T09:00:00"}, "with and without a UTC offset"),
    ("debrief", {"first_contact": "2026-11-01T09:00:00",
                 "sessions": [SESSION]}, "with and without a UTC offset"),
    ("debrief", {"first_contact": "2026-11-01",
                 "sessions": [{"start": SESSION["end"], "end": SESSION["start"]}]}, "ends before it starts"),
    ("summary", {"first_contact": "2026-11-01", "sessions": [{"start": SESSION["start"]}]},
     "sessions[0].end is required"),
    ("class", {**BASE, "exam": "2027-10-19T09:00:00+03:00"}, "more than 366 days away"),
    ("triage", b'{"now": "2026-10-17T09:00:00+03:00", "types": [{"name": "A", "marks": NaN}]}', "non-finite"),
    ("triage", b'{"now": "2026-10-17T09:00:00+03:00", "types": [{"name": "A", "marks": Infinity}]}',
     "non-finite"),
    ("triage", b'{"now": "2026-10-17T09:00:00+03:00", "types": [{"name": "A", "marks": 1e999}]}', "finite"),
    ("triage", b'{"types": [{"name": "A", "marks": 1' + b"0" * 4000 + b'}]}', "too large"),
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


def test_triage_rows_rank_every_type_by_marks_times_frequency():
    out = ok("triage", {"types": [qtype("B", 10, 1, 2), qtype("A", 20, 2, 2, "gap"), qtype("C", 8, 3, 3, "shaky")]})
    assert out["rows"] == [
        {"name": "A", "marks": 20, "marks_source": "printed", "frequency": "2 of 2 papers",
         "decision": "drill", "reason": "gap"},
        {"name": "C", "marks": 8, "marks_source": "printed", "frequency": "3 of 3 papers",
         "decision": "drill", "reason": "shaky"},
        {"name": "B", "marks": 10, "marks_source": "printed", "frequency": "1 of 2 papers",
         "decision": "drill", "reason": "not studied yet"},
    ]
    assert out["drill"] == ["A", "C", "B"]
    assert out["line"] == "Ranked by marks × how often each type appeared in past papers."
    assert set(out) == {"rows", "drill", "basis", "line"}


def rows(out):
    return [(r["name"], r["decision"], r["reason"]) for r in out["rows"]]


def test_triage_ties_keep_input_order_and_shaky_gets_no_time_bonus():
    out = ok("triage", {"types": [qtype("A"), qtype("B", status="shaky"), qtype("C", 20, 1, 2)]})
    assert out["drill"] == ["A", "B", "C"]


def test_triage_mastered_is_skipped_but_still_listed():
    out = ok("triage", {"types": [qtype("A", 30, status="mastered"), qtype("B")]})
    assert rows(out) == [("B", "drill", "not studied yet"), ("A", "skip", "mastered")]
    assert out["drill"] == ["B"]
    urgent = ok("triage", {"class": "Urgent", "types": [qtype("A", 30, status="mastered"), qtype("B")]})
    assert urgent == out  # Urgent is the default


def test_triage_standard_includes_mastered():
    types = [qtype("A", 20, status="mastered"), qtype("B", 10, status="gap"), qtype("C", status="mastered")]
    out = ok("triage", {"class": "Standard", "types": types})
    assert rows(out) == [("A", "drill", "mastered: revision"), ("B", "drill", "gap"),
                         ("C", "drill", "mastered: revision")]


def test_triage_cuts_nothing_however_close_the_exam():
    # Eight question types three hours before the exam (and on a date-only exam day):
    # no minutes budget, no floor of one, no stop at the first type that does not fit.
    types = [qtype(n, 30 - i) for i, n in enumerate("ABCDEFGH")]
    expected = ok("triage", {"types": types})
    assert expected["drill"] == list("ABCDEFGH")
    assert [r["decision"] for r in expected["rows"]] == ["drill"] * 8
    for when in ({"now": NOW, "exam": in_hours(3)}, {"now": "2026-11-05T07:00:00+02:00", "exam": "2026-11-05"},
                 {"now": NOW, "exam": None}):
        assert ok("triage", {**when, "types": types}) == expected


def test_triage_zero_marks_type_ranks_last_but_is_drilled():
    out = ok("triage", {"types": [qtype("A", 0), qtype("B", 10)]})
    assert rows(out) == [("B", "drill", "not studied yet"), ("A", "drill", "not studied yet")]


def test_triage_skipped_mastered_types_come_after_every_drilled_type():
    types = [qtype("M1", 50, status="mastered"), qtype("A", 30), qtype("B", 15),
             qtype("M2", 40, status="mastered"), qtype("C", 25)]
    out = ok("triage", {"types": types})
    assert [r["name"] for r in out["rows"]] == ["A", "C", "B", "M1", "M2"]
    assert out["drill"] == ["A", "C", "B"]


def test_triage_no_papers_outline_names_no_statistics():
    out = ok("triage", {"basis": "outline", "types": [qtype("A", None, 0, 0), qtype("B", None, 0, 0)]})
    assert [(r["marks"], r["marks_source"], r["frequency"]) for r in out["rows"]] == [
        (1, "estimated", None), (1, "estimated", None)]
    assert out["drill"] == ["A", "B"]
    assert out["line"] == "No past papers: ranked from the course outline, without paper statistics."
    assert out["basis"] == "outline"


def test_triage_null_marks_take_mean_of_known_and_unknown_frequency_counts_as_one():
    out = ok("triage", {"types": [qtype("A", 20, 1, 4), qtype("B", None, 0, 0), qtype("C", 10, 1, 1)]})
    by_name = {r["name"]: r for r in out["rows"]}
    assert (by_name["B"]["marks"], by_name["B"]["marks_source"], by_name["B"]["frequency"]) == (15, "estimated", None)
    assert by_name["A"]["frequency"] == "1 of 4 papers" and by_name["C"]["frequency"] == "1 of 1 paper"
    assert out["drill"] == ["B", "C", "A"]  # 15 x 1, 10 x 1, 20 x 1/4


def test_triage_edge_cases():
    out = ok("triage", {"types": []})
    assert out["rows"] == [] and out["drill"] == [] and out["line"] == "Nothing to drill: no question types."
    out = ok("triage", {"types": [qtype("A", status="mastered")]})
    assert out["drill"] == [] and rows(out) == [("A", "skip", "mastered")]
    assert out["line"] == "Nothing to drill: every question type is mastered."
    only = ok("triage", {"types": [{"name": "A"}]})["rows"]
    assert only == [{"name": "A", "marks": 1, "marks_source": "estimated", "frequency": None,
                     "decision": "drill", "reason": "not studied yet"}]


def test_triage_marks_near_the_float_limit_still_rank():
    out = ok("triage", {"types": [qtype("A", 1.7e308, 1, 3), qtype("B", None, 0, 0)]})
    assert out["drill"] == ["B", "A"]  # B's estimate is A's marks, at frequency 1
    assert out["rows"][0]["marks"] == out["rows"][1]["marks"] == 17 * 10 ** 307


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
])
def test_triage_invalid_input_exits_2(payload, message):
    proc = run("triage", payload)
    assert proc.returncode == 2
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("plan.py: ") and err.count("\n") == 1 and message in err, err
