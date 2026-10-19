"""Boundary tests for scripts/session.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
SS = SCRIPTS / "session.py"
WS = SCRIPTS / "workspace.py"

sys.path.insert(0, str(SCRIPTS))
import session  # noqa: E402

TERM = "2026-Fall"
NOW = "2026-10-17T09:00:00+03:00"
MASTERY_HEAD = ("# Mastery\n\n| topic | status | evidence | evidence_date | last_check | assisted | "
                "unassisted | frustration_override |\n|---|---|---|---|---|---|---|---|\n")


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def root(home):
    _ok(WS, home, "init", {})
    return home / "learning"


def _run(script: Path, home: Path, cmd: str, payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(script), cmd], input=stdin, capture_output=True,
                          env={**os.environ, "HOME": str(home)})


def _ok(script: Path, home: Path, cmd: str, payload) -> dict:
    proc = _run(script, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b"" and proc.stdout.count(b"\n") == 1
    return json.loads(proc.stdout)


def ok(home: Path, cmd: str, payload) -> dict:
    out = _ok(SS, home, cmd, payload)
    assert isinstance(out["line"], str) and out["line"]
    return out


def fails(home: Path, cmd: str, payload, needle: str = "") -> str:
    proc = _run(SS, home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("session.py: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def course(home: Path, name: str = "CS201 Theory", term: str = TERM, *, mastery=(), save=None) -> Path:
    out = _ok(WS, home, "course", {"term": term, "course": name})
    cdir = Path(out["course_dir"])
    rows = "".join(f"| {t} | {s} | ev | {d} | {d} | {a} | {u} | |\n" for t, s, d, a, u in mastery)
    (cdir / ".state" / "mastery.md").write_text(MASTERY_HEAD + rows, encoding="utf-8")
    if save is not None:
        (cdir / ".state" / "save.md").write_text(
            "# Save\n\n" + "".join(f"{k}: {v}\n" for k, v in save.items()), encoding="utf-8")
    return cdir


def profile(root: Path, exams=(), active=()) -> None:
    text = "# Profile\n\nlevel:\n\n## Exam dates\n| course | exam | date |\n|---|---|---|\n"
    text += "".join(f"| {c} | {e} | {d} |\n" for c, e, d in exams)
    text += "\n## Active courses\n| course | path |\n|---|---|\n"
    text += "".join(f"| {c} | {p} |\n" for c, p in active)
    (root / ".state" / "profile.md").write_text(text, encoding="utf-8")


TWO_LEFT = [("Heaps", "mastered", "2026-10-10", 0, 1), ("Graphs", "gap", "2026-10-10", 1, 0),
            ("Sorting", "unseen", "", 0, 0)]


def snapshot(path: Path) -> dict:
    return {str(p): (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
            for p in sorted(path.rglob("*"))}


# --- start: I/O matrix -------------------------------------------------------------

def test_calm(home, root):
    course(home, mastery=TWO_LEFT, save={"next_topic": "Sorting"})
    profile(root, exams=[("CS201", "final", "2026-11-05")])
    out = ok(home, "start", {"now": NOW})
    assert out["class"]["class"] == "Standard" and out["class"]["reason"] == "calm"
    assert out["class"]["days_to_exam"] == 19
    assert out["line"] == out["class"]["line"] == "Standard delivery: exam in 19 days"
    assert out["delay_line"].startswith("Start today: 19 days")
    assert out["topic"] == {"name": "Sorting", "status": "unseen", "evidence_date": None, "stale": False,
                            "attempt_first": False}
    assert out["remaining"] == [{"name": "Graphs", "status": "gap"}, {"name": "Sorting", "status": "unseen"}]
    assert out["class"]["route_minutes"]["point"] == 50  # weight 1 each, 2 topics
    assert (out["exam"], out["exam_name"], out["q0"], out["code"]) == ("2026-11-05", "final", False, "CS201")
    assert out["inferred"] is True and out["first_contact"] is None
    assert set(out) == {"root", "courses", "term", "course", "course_dir", "code", "inferred", "exam",
                        "exam_name", "q0", "remaining", "class", "delay_line", "topic",
                        "first_contact", "debrief", "line"}


def test_near_exam_is_urgent_floor(home, root):
    course(home, mastery=TWO_LEFT)
    profile(root, exams=[("CS201", "final", "2026-10-19")])
    out = ok(home, "start", {"now": "2026-10-17T18:00:00+03:00"})
    assert out["class"]["class"] == "Urgent" and out["class"]["reason"] == "floor"
    assert out["class"]["hours_to_exam"] == 30
    assert out["delay_line"] is None


def test_no_date_row_asks_q0(home, root):
    course(home, mastery=TWO_LEFT)
    profile(root, exams=[("MATH101", "final", "2026-11-05")])
    out = ok(home, "start", {"now": NOW})
    assert out["q0"] is True and out["exam"] is None
    assert out["class"]["reason"] == "unknown"


def test_unknown_row_is_standard_without_q0(home, root):
    course(home, mastery=TWO_LEFT)
    profile(root, exams=[("CS201", "final", "unknown")])
    out = ok(home, "start", {"now": NOW})
    assert out["q0"] is False and out["exam"] is None
    assert out["class"]["class"] == "Standard" and out["class"]["reason"] == "unknown"


def test_past_exam_only_asks_q0(home, root):
    course(home, mastery=TWO_LEFT)
    profile(root, exams=[("CS201", "midterm", "2026-10-16")])
    out = ok(home, "start", {"now": NOW})
    assert out["q0"] is True and out["exam"] is None


def test_earliest_future_row_wins_over_unknown(home, root):
    course(home, mastery=TWO_LEFT)
    profile(root, exams=[("CS201", "final", "2026-12-20"), ("cs201", "midterm", "2026-11-01"),
                         ("CS201", "quiz", "unknown"), ("CS201", "old", "2026-10-01"),
                         ("CS201", "bad", "2026-13-45")])
    out = ok(home, "start", {"now": NOW})
    assert (out["exam"], out["exam_name"], out["q0"]) == ("2026-11-01", "midterm", False)


def test_exam_today_is_urgent(home, root):
    course(home, mastery=TWO_LEFT)
    profile(root, exams=[("CS201", "final", "2026-10-17")])
    out = ok(home, "start", {"now": NOW})
    assert out["class"]["reason"] == "today"


def test_course_pick_latest_last_session(home, root):
    course(home, "CS201 Theory", save={"last_session": "2026-10-10 18:00"})
    course(home, "MATH101 Calculus", save={"last_session": "2026-10-12 09:30"})
    profile(root, active=[("CS201", f"{TERM}/CS201 Theory")])
    out = ok(home, "start", {"now": NOW})
    assert out["course"] == "MATH101 Calculus" and out["inferred"] is True and out["code"] == "MATH101"


def test_course_pick_tie_first_by_name(home, root):
    course(home, "MATH101 Calculus", save={"last_session": "2026-10-12 09:30"})
    course(home, "CS201 Theory", save={"last_session": "2026-10-12 09:30"})
    assert ok(home, "start", {"now": NOW})["course"] == "CS201 Theory"


def test_course_pick_invalid_last_session_ignored(home, root):
    course(home, "CS201 Theory", save={"last_session": "2026-10-12 25:99"})
    course(home, "MATH101 Calculus", save={"last_session": "2026-10-01"})
    assert ok(home, "start", {"now": NOW})["course"] == "MATH101 Calculus"


def test_course_pick_active_courses(home, root):
    course(home, "CS201 Theory")
    course(home, "MATH101 Calculus")
    profile(root, active=[("PHY1", f"{TERM}/PHY1 Gone"), ("CS201", f"{TERM}/CS201 Theory")])
    assert ok(home, "start", {"now": NOW})["course"] == "CS201 Theory"


def test_course_pick_last_in_term_order(home, root):
    course(home, "ZZ9 Late", term="2026-Spring")
    course(home, "AA1 First", term="2026-Fall")
    course(home, "BB2 Other", term="2025-Q2")
    out = ok(home, "start", {"now": NOW})
    assert (out["term"], out["course"]) == ("2026-Fall", "AA1 First")
    assert session._term_key("2026-Fall") < session._term_key("2026-Q2")
    assert session._term_key("2026-Spring") < session._term_key("2026-Summer")


def test_course_given_is_not_inferred(home, root):
    course(home, "CS201 Theory", save={"last_session": "2026-10-12 09:30"})
    course(home, "MATH101 Calculus")
    out = ok(home, "start", {"now": NOW, "course": "MATH101 Calculus", "term": TERM})
    assert out["course"] == "MATH101 Calculus" and out["inferred"] is False


def test_course_in_two_terms_needs_term(home, root):
    course(home, "CS201 Theory", term="2026-Fall")
    course(home, "CS201 Theory", term="2027-Spring")
    fails(home, "start", {"now": NOW, "course": "CS201 Theory"}, "term")
    out = ok(home, "start", {"now": NOW, "course": "CS201 Theory", "term": "2027-Spring"})
    assert out["term"] == "2027-Spring"


def test_term_alone_limits_pick(home, root):
    course(home, "CS201 Theory", term="2026-Fall")
    course(home, "OLD1 Thing", term="2027-Spring")
    assert ok(home, "start", {"now": NOW, "term": "2026-Fall"})["course"] == "CS201 Theory"
    fails(home, "start", {"now": NOW, "term": "2025-Fall"}, "term")


def test_topic_falls_back_to_first_remaining(home, root):
    course(home, mastery=TWO_LEFT, save={"next_topic": "Heaps"})  # mastered, not remaining
    assert ok(home, "start", {"now": NOW})["topic"]["name"] == "Graphs"


def test_topic_null_when_route_done(home, root):
    course(home, mastery=[("Heaps", "mastered", "2026-10-10", 0, 1)], save={"next_topic": "Heaps"})
    profile(root, exams=[("CS201", "final", "2026-11-05")])
    out = ok(home, "start", {"now": NOW})
    assert out["topic"] is None and out["remaining"] == []
    assert out["delay_line"] == "Cost of delay: no topics left on the route."


def test_topic_stale_flag(home, root):
    course(home, mastery=[("Graphs", "gap", "2026-10-02", 1, 0)])
    assert ok(home, "start", {"now": NOW})["topic"]["stale"] is True


def test_start_topic_attempt_first(home, root):
    course(home, mastery=[("Graphs", "shaky", "2026-10-10", 3, 0)])
    assert ok(home, "start", {"now": NOW})["topic"]["attempt_first"] is True


def test_first_contact_from_logs(home, root):
    cdir = course(home)
    logs = cdir / ".state" / "logs"
    (logs / "2026-10-01-0900.md").write_text("## Quiz\nstarted: x\n", encoding="utf-8")
    (logs / "2026-10-02-0900.md").write_text("first_contact:\nfirst_contact: 2026-10-02T09:00:00+03:00\n",
                                             encoding="utf-8")
    (logs / "2026-10-03-0900.md").write_text("first_contact: later\n", encoding="utf-8")
    assert ok(home, "start", {"now": NOW})["first_contact"] == "2026-10-02T09:00:00+03:00"


def test_no_course_yet(home, root):
    out = ok(home, "start", {"now": NOW})
    assert out["course"] is None and out["courses"] == [] and "/mimir:ingest" in out["line"]


def test_course_without_index_is_not_a_course(home, root):
    cdir = course(home)
    (cdir / "INDEX.md").unlink()
    assert ok(home, "start", {"now": NOW})["course"] is None


def test_no_workspace(home):
    fails(home, "start", {"now": NOW}, "no workspace")


# --- check -------------------------------------------------------------------------

def test_check_attempt_first(home, root):
    course(home, mastery=[("On", "shaky", "2026-10-10", 3, 0), ("Below", "shaky", "2026-10-10", 2, 0),
                          ("Solved", "shaky", "2026-10-10", 5, 1)])
    out = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory",
                             "topics": ["On", "Below", "Solved", "Absent"]})
    by = {t["name"]: t for t in out["topics"]}
    assert by["On"]["attempt_first"] is True
    assert by["Below"]["attempt_first"] is False
    assert by["Solved"]["attempt_first"] is False
    assert by["Absent"]["attempt_first"] is False and by["Absent"]["status"] == "unseen"


def test_check_attempt_first_needs_known_status(home, root):
    course(home, mastery=[("Weird", "bogus", "2026-10-10", 3, 0), ("Four", "gap", "2026-10-10", 4, 0)])
    out = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory",
                             "topics": ["Weird", "Four"]})
    by = {t["name"]: t for t in out["topics"]}
    assert by["Weird"]["status"] == "unseen" and by["Weird"]["attempt_first"] is False
    assert by["Four"]["attempt_first"] is True


def test_check_stale_boundary(home, root):
    course(home, mastery=[("Old", "shaky", "2026-10-02", 2, 1), ("Edge", "mastered", "2026-10-03", 0, 3),
                          ("Nodate", "gap", "", 0, 0), ("Baddate", "gap", "soon", 0, 0),
                          ("Fresh", "unseen", "", 0, 0), ("Odd", "weird", "2026-01-01", "x", 1)])
    out = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory",
                             "topics": ["old", "Edge", "Nodate", "Baddate", "Fresh", "Missing", "Odd"]})
    by = {t["name"]: t for t in out["topics"]}
    assert by["Old"] == {"name": "Old", "status": "shaky", "evidence_date": "2026-10-02",
                         "assisted": 2, "unassisted": 1, "stale": True,
                         "attempt_first": False}  # 15 days
    assert by["Edge"]["stale"] is False  # exactly 14 days
    assert by["Nodate"]["stale"] is True and by["Baddate"]["stale"] is True
    assert by["Baddate"]["evidence_date"] is None
    assert by["Fresh"]["stale"] is False
    assert by["Missing"] == {"name": "Missing", "status": "unseen", "evidence_date": None,
                             "assisted": 0, "unassisted": 0, "stale": False,
                             "attempt_first": False}
    assert by["Odd"]["status"] == "unseen" and by["Odd"]["assisted"] == 0
    assert out["line"] == "7 topics checked, 3 stale: Old, Nodate, Baddate."


def test_check_unknown_course(home, root):
    course(home)
    fails(home, "check", {"now": NOW, "term": TERM, "course": "NOPE1 X", "topics": ["a"]}, "course")


def test_check_bad_topics(home, root):
    course(home)
    base = {"now": NOW, "term": TERM, "course": "CS201 Theory"}
    fails(home, "check", {**base, "topics": []}, "topics")
    fails(home, "check", {**base, "topics": ["ok", 3]}, "topics[2]")
    fails(home, "check", {**base, "topics": ["a\nb"]}, "topics[1]")


def test_check_refuses_symlinked_course(home, root, tmp_path):
    real = course(home)
    link = root / TERM / "LINK1 Alias"
    link.symlink_to(real)
    fails(home, "check", {"now": NOW, "term": TERM, "course": "LINK1 Alias", "topics": ["a"]}, "symlink")


# --- clock -------------------------------------------------------------------------

@pytest.mark.parametrize("now,minutes,phase", [
    ("2026-10-17T09:19:59+03:00", 19, "teach"),
    ("2026-10-17T09:20:00+03:00", 20, "wrap"),
    ("2026-10-17T09:24:59+03:00", 24, "wrap"),
    ("2026-10-17T09:25:00+03:00", 25, "over"),
    ("2026-10-17T07:30:00+01:00", 30, "over"),  # other offset, same instant arithmetic
])
def test_clock(home, now, minutes, phase):
    out = ok(home, "clock", {"start": NOW, "now": now})
    assert (out["elapsed_minutes"], out["phase"]) == (minutes, phase)


def test_clock_errors(home):
    fails(home, "clock", {"start": NOW, "now": "2026-10-17T08:59:00+03:00"}, "before start")
    fails(home, "clock", {"start": NOW, "now": "2026-10-17T09:10:00"}, "offset")
    fails(home, "clock", {"start": NOW}, "now is required")
    fails(home, "clock", {"start": "2026-10-17", "now": NOW}, "start must include a time")


# --- error contract ------------------------------------------------------------------

def test_bad_inputs(home, root):
    course(home)
    fails(home, "start", {"now": "yesterday"}, "now")
    fails(home, "start", {"now": "2026-10-17"}, "now must include a time")
    fails(home, "start", {}, "now is required")
    fails(home, "start", {"now": NOW, "extra": 1}, "unknown field 'extra'")
    fails(home, "start", {"now": NOW, "course": "NOPE1 X"}, "course 'NOPE1 X'")
    fails(home, "start", {"now": NOW, "course": "../x"}, "course")
    fails(home, "start", {"now": NOW, "term": "Fall"}, "term")
    fails(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory", "topics": ["a"], "x": 1},
          "unknown field 'x'")
    fails(home, "clock", {"start": NOW, "now": NOW, "x": 1}, "unknown field 'x'")
    fails(home, "start", b"not json", "not valid JSON")


def test_exam_beyond_horizon_is_ignored(home, root):
    course(home)
    profile(root, exams=[("CS201", "final", "2028-01-01")])
    out = ok(home, "start", {"now": NOW})
    assert out["exam"] is None and out["q0"] is True
    profile(root, exams=[("CS201", "final", "2028-01-01"), ("CS201", "midterm", "2027-10-18")])
    out = ok(home, "start", {"now": NOW})  # exactly 366 days ahead is still in range
    assert out["exam"] == "2027-10-18"


def test_usage_error(home):
    proc = _run(SS, home, "nope", {})
    assert proc.returncode == 2 and proc.stdout == b""


def _all_commands_write_nothing(home: Path) -> None:
    before = snapshot(home)
    ok(home, "start", {"now": NOW})
    ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory", "topics": ["Graphs"]})
    ok(home, "clock", {"start": NOW, "now": NOW})
    fails(home, "start", {"now": NOW, "course": "NOPE1 X"})
    assert snapshot(home) == before


def test_writes_nothing(home, root):
    cdir = course(home, mastery=TWO_LEFT, save={"next_topic": "Sorting", "last_session": "2026-10-12 09:30"})
    profile(root, exams=[("CS201", "final", "2026-11-05")])
    (cdir / ".state" / "logs" / "2026-10-01-0900.md").write_text("first_contact: 2026-10-01\n", encoding="utf-8")
    _all_commands_write_nothing(home)


def test_writes_nothing_with_bare_profile(home, root):
    course(home, mastery=TWO_LEFT)
    (root / ".state" / "profile.md").write_text("# Profile\n", encoding="utf-8")  # no sections at all
    _all_commands_write_nothing(home)


# --- review cases ------------------------------------------------------------------

def test_duplicate_topic_row_first_wins(home, root):
    course(home, mastery=[("Graphs", "gap", "2026-10-10", 1, 0), ("graphs", "mastered", "2026-10-16", 0, 5),
                          ("Sorting", "unseen", "", 0, 0)])
    out = ok(home, "start", {"now": NOW})
    assert [r["name"] for r in out["remaining"]] == ["Graphs", "Sorting"]
    assert out["class"]["route_minutes"]["point"] == 50
    got = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory", "topics": ["Graphs"]})
    assert got["topics"][0]["status"] == "gap" and got["topics"][0]["assisted"] == 1


def test_mastery_columns_by_header_name(home, root):
    cdir = course(home)
    (cdir / ".state" / "mastery.md").write_text(
        "# Mastery\n\n| status | unassisted | topic | evidence_date | assisted |\n|---|---|---|---|---|\n"
        "| shaky | 2 | Heaps | 2026-10-01 | 3 |\n", encoding="utf-8")
    got = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory", "topics": ["Heaps"]})
    assert got["topics"][0] == {"name": "Heaps", "status": "shaky", "evidence_date": "2026-10-01",
                                "assisted": 3, "unassisted": 2, "stale": True,
                                "attempt_first": False}


def test_non_utf8_save_in_other_course(home, root):
    bad = course(home, "AA1 Bad", save={"last_session": "2026-10-16 09:00"})
    (bad / ".state" / "save.md").write_bytes(b"last_session: 2026-10-16 09:00\n\xff\xfe\n")
    course(home, "CS201 Theory", save={"last_session": "2026-10-12 09:30"})
    out = ok(home, "start", {"now": NOW})
    assert out["course"] == "CS201 Theory"


def test_non_utf8_log_before_valid_first_contact(home, root):
    logs = course(home) / ".state" / "logs"
    (logs / "2026-10-01-0900.md").write_bytes(b"first_contact: \xff\n")
    (logs / "2026-10-02-0900.md").write_text("first_contact: 2026-10-02T09:00:00+03:00\n", encoding="utf-8")
    assert ok(home, "start", {"now": NOW})["first_contact"] == "2026-10-02T09:00:00+03:00"


def test_invalid_first_contact_skipped(home, root):
    logs = course(home) / ".state" / "logs"
    (logs / "2026-10-01-0900.md").write_text("first_contact: last tuesday\nfirst_contact: 2026-13-01\n",
                                             encoding="utf-8")
    (logs / "2026-10-02-0900.md").write_text("first_contact: 2026-10-02\n", encoding="utf-8")
    assert ok(home, "start", {"now": NOW})["first_contact"] == "2026-10-02"
    (logs / "2026-10-02-0900.md").write_text("first_contact: soon\n", encoding="utf-8")
    assert ok(home, "start", {"now": NOW})["first_contact"] is None


def test_symlinked_state_in_other_course_skipped(home, root, tmp_path):
    other = course(home, "ZZ9 Linked", save={"last_session": "2026-10-16 09:00"})
    real_state = tmp_path / "elsewhere"
    (other / ".state").rename(real_state)
    (other / ".state").symlink_to(real_state)
    course(home, "CS201 Theory")
    out = ok(home, "start", {"now": NOW})
    assert out["course"] == "CS201 Theory"
    fails(home, "start", {"now": NOW, "course": "ZZ9 Linked"}, "symlink")


def test_symlinked_save_and_mastery_read_as_empty(home, root, tmp_path):
    cdir = course(home, mastery=TWO_LEFT, save={"next_topic": "Sorting"})
    for name in ("save.md", "mastery.md"):
        target = tmp_path / name
        (cdir / ".state" / name).rename(target)
        (cdir / ".state" / name).symlink_to(target)
    out = ok(home, "start", {"now": NOW})
    assert out["remaining"] == [] and out["topic"] is None


def test_future_evidence_date_is_stale(home, root):
    course(home, mastery=[("Heaps", "mastered", "2026-10-18", 0, 1), ("Today", "shaky", "2026-10-17", 1, 0),
                          ("Bad", "gap", "2026-02-30", 0, 0)])
    got = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory",
                             "topics": ["Heaps", "Today", "Bad"]})
    by = {x["name"]: x for x in got["topics"]}
    assert by["Heaps"]["stale"] is True and by["Today"]["stale"] is False
    assert by["Bad"]["evidence_date"] is None and by["Bad"]["stale"] is True


# --- debrief -----------------------------------------------------------------------

DUE_NOW = "2026-11-12T10:00:00+02:00"
DAY = "2026-11-12"


def log(cdir: Path, name: str, text: str) -> None:
    (cdir / ".state" / "logs" / f"{name}.md").write_text(text, encoding="utf-8")


def session_log(start: str, end: str | None = None, extra: str = "") -> str:
    return f"## Session\nstarted: {start}\nclass: Standard (calm)\n" + (f"ended: {end}\n" if end else "") + extra


def due_course(home, root, *, pending="2026-11-05 final", exams=(("CS201", "final", "2026-11-05"),), **kw):
    cdir = course(home, mastery=TWO_LEFT, save={"last_session": "2026-11-04 21:00",
                                                "pending_debrief": pending}, **kw)
    profile(root, exams=exams)
    return cdir


@pytest.mark.parametrize("pending", ["no", "", "soon", "2026-13-01 final", "<no | YYYY-MM-DD exam name>"])
def test_debrief_none_pending(home, root, pending):
    due_course(home, root, pending=pending)
    assert ok(home, "start", {"now": DUE_NOW})["debrief"] is None
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["debrief"] is None and out["line"] == "No debrief pending for CS201 Theory."
    assert out["cram"] is None and out["disagreements"] is None and out["offer_next_course"] is None


def test_debrief_not_yet_on_exam_day(home, root):
    due_course(home, root, pending="2026-11-12 final", exams=[("CS201", "final", "2026-11-12")])
    st = ok(home, "start", {"now": DUE_NOW})
    assert st["debrief"] == {"exam": "2026-11-12", "exam_name": "final", "due": False, "deferred": False}
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["line"] == "Debrief opens after your final on 2026-11-12."
    assert out["cram"] is None and out["offer_next_course"] is None


def test_debrief_due_yesterday(home, root):
    cdir = due_course(home, root, pending="2026-11-11 midterm",
                      exams=[("CS201", "midterm", "2026-11-11"), ("CS201", "final", "2027-01-20")])
    log(cdir, "2026-11-01-2000", "first_contact: 2026-11-01T20:00:00+02:00\n"
        + session_log("2026-11-01T20:00:00+02:00", "2026-11-01T21:30:00+02:00"))
    st = ok(home, "start", {"now": DUE_NOW})
    assert st["class"]["class"] == "Standard"
    assert st["debrief"] == {"exam": "2026-11-11", "exam_name": "midterm", "due": True, "deferred": False}
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["debrief"]["due"] is True
    assert out["cram"]["session_count"] == 1 and out["cram"]["actual_minutes"] == 90
    assert out["cram"]["days_before_exam"] == 10
    assert out["line"] == out["cram"]["line"] and "First contact: 10 days before the exam." in out["line"]
    assert out["disagreements"] == [] and out["offer_next_course"] is True
    assert set(out) == {"term", "course", "course_dir", "code", "inferred", "debrief", "cram",
                        "disagreements", "offer_next_course", "line"}


def test_debrief_deferred_writes_nothing(home, root):
    due_course(home, root, pending="2026-11-11 midterm",
               exams=[("CS201", "midterm", "2026-11-11"), ("CS201", "final", "2026-11-13")])
    st = ok(home, "start", {"now": DUE_NOW})
    assert st["class"]["class"] == "Urgent"
    assert st["debrief"] == {"exam": "2026-11-11", "exam_name": "midterm", "due": False, "deferred": True}
    before = snapshot(home)
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["line"] == "Debrief waits until after your final: today is for that."
    assert out["cram"] is None and out["disagreements"] is None
    assert snapshot(home) == before


def test_debrief_superseded_by_later_passed_exam(home, root):
    due_course(home, root, pending="2026-10-20 midterm",
               exams=[("CS201", "midterm", "2026-10-20"), ("CS201", "final", "2026-11-10"),
                      ("CS201", "quiz", "2026-11-12"), ("MATH1", "final", "2026-11-11")])
    st = ok(home, "start", {"now": DUE_NOW})
    assert st["debrief"] == {"exam": "2026-11-10", "exam_name": "final", "due": False, "deferred": True}
    st = ok(home, "start", {"now": "2026-11-13T10:00:00+02:00"})  # quiz passed too
    assert st["debrief"]["exam"] == "2026-11-12" and st["debrief"]["exam_name"] == "quiz"
    assert st["debrief"]["due"] is True


def test_debrief_superseded_window_uses_target(home, root):
    cdir = due_course(home, root, pending="2026-10-20 midterm",
                      exams=[("CS201", "midterm", "2026-10-20"), ("CS201", "final", "2026-11-10")])
    log(cdir, "2026-10-01-0900", "first_contact: 2026-10-01T09:00:00+03:00\n"
        + session_log("2026-10-01T09:00:00+03:00", "2026-10-01T10:00:00+03:00",
                      "## Verifier disagreements\n- before the midterm\n"))
    log(cdir, "2026-10-20-0700", session_log("2026-10-20T07:00:00+03:00", "2026-10-20T08:00:00+03:00",
                                            "## Verifier disagreements\n- midterm day\n"))
    log(cdir, "2026-10-25-0900", session_log("2026-10-25T09:00:00+03:00", "2026-10-25T09:30:00+03:00",
                                            "## Verifier disagreements\n- between the exams\n"))
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["debrief"] == {"exam": "2026-11-10", "exam_name": "final", "due": True, "deferred": False}
    assert out["cram"]["session_count"] == 1 and out["cram"]["actual_minutes"] == 30
    assert out["cram"]["days_before_exam"] == 40  # counted to the final
    assert out["disagreements"] == ["- between the exams"]


def test_debrief_naive_first_contact_with_aware_now(home, root):
    cdir = due_course(home, root)
    log(cdir, "2026-10-20-0900", "first_contact: 2026-10-20T09:00:00\n"
        + session_log("2026-10-20T09:00:00+03:00", "2026-10-20T10:00:00+03:00"))
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["cram"] is None and out["line"] == "Cram bill: no study sessions logged."


def test_debrief_unnamed_exam_not_yet(home, root):
    due_course(home, root, pending="2026-11-12", exams=[])
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["debrief"]["exam_name"] is None
    assert out["line"] == "Debrief opens after your exam on 2026-11-12."


def test_debrief_disagreements_section_ends_at_any_heading(home, root):
    cdir = due_course(home, root)
    log(cdir, "2026-10-20-0900-2", "## Verifier disagreements\n- kept\n- \n-   \n### Notes\n- not one\n"
        "## Verifier disagreements\n- kept again\n# Other\n- no\n")
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["disagreements"] == ["- kept", "- kept again"]


def test_debrief_name_from_row_when_pending_has_none(home, root):
    due_course(home, root, pending="2026-11-05")
    assert ok(home, "start", {"now": DUE_NOW})["debrief"]["exam_name"] == "final"


def test_debrief_session_window(home, root):
    cdir = due_course(home, root, pending="2026-11-05 final",
                      exams=[("CS201", "midterm", "2026-10-10"), ("CS201", "final", "2026-11-05")])
    log(cdir, "2026-10-01-0900", "first_contact: 2026-10-01\n"
        + session_log("2026-10-01T09:00:00+03:00", "2026-10-01T10:00:00+03:00"))  # before the midterm
    log(cdir, "2026-10-10-0900", session_log("2026-10-10T09:00:00+03:00", "2026-10-10T10:00:00+03:00"))  # midterm day
    log(cdir, "2026-10-20-0900", session_log("2026-10-20T09:00:00+03:00", "2026-10-20T09:30:00+03:00")
        + session_log("2026-10-20T09:10:00+03:00", "2026-10-20T09:20:00+03:00")  # overlaps: dropped
        + session_log("2026-10-20T12:00:00+03:00", "2026-10-20T11:00:00+03:00")  # ends before start
        + session_log("2026-10-20T13:00:00+03:00")  # unended, then a real pair
        + session_log("2026-10-20T14:00:00+03:00", "2026-10-20T14:45:00+03:00"))
    log(cdir, "2026-10-21-0900", session_log("2026-10-21T09:00:00", "2026-10-21T10:00:00"))  # no offset
    log(cdir, "2026-11-05-0700", session_log("2026-11-05T07:00:00+02:00", "2026-11-05T08:00:00+02:00"))
    log(cdir, "2026-11-06-0900", session_log("2026-11-06T09:00:00+02:00", "2026-11-06T10:00:00+02:00"))  # after
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["cram"]["session_count"] == 3 and out["cram"]["actual_minutes"] == 30 + 45 + 60
    assert out["cram"]["counterfactual_minutes"]["point"] == 75  # all 3 mastery rows, weight 1
    assert out["cram"]["days_before_exam"] == 35


def test_debrief_disagreements_in_window_distinct(home, root):
    cdir = due_course(home, root, exams=[("CS201", "midterm", "2026-10-10"), ("CS201", "final", "2026-11-05")])
    log(cdir, "2026-10-01-0900", "first_contact: 2026-10-01\n## Verifier disagreements\n- old one\n")
    log(cdir, "2026-10-20-0900", "## Verifier disagreements\n- item 2: key says 4, checker 5\n"
        "not a bullet\n- item 3: ambiguous\n## Results\n- Heaps practice: wrong\n")
    log(cdir, "2026-10-22-0900", "## Verifier disagreements\n- item 2: key says 4, checker 5\n- item 9: x\n")
    log(cdir, "2026-11-06-0900", "## Verifier disagreements\n- after the exam\n")
    log(cdir, "notes", "## Verifier disagreements\n- unnamed log\n")
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["disagreements"] == ["- item 2: key says 4, checker 5", "- item 3: ambiguous", "- item 9: x"]


def test_debrief_offer_once_per_term(home, root):
    cdir = due_course(home, root)
    log(cdir, "2026-10-01-0900", "first_contact: 2026-10-01\n")
    other = course(home, "OLD1 Thing", term="2026-Spring")
    log(other, "2026-05-01-0900", "## Debrief\nnext_course_offer: no\n")
    assert ok(home, "debrief", {"now": DUE_NOW})["offer_next_course"] is True
    same = course(home, "MATH101 Calculus")
    log(same, "2026-10-30-0900", "## Debrief\nnext_course_offer: yes\n")
    out = ok(home, "debrief", {"now": DUE_NOW, "term": TERM, "course": "CS201 Theory"})
    assert out["offer_next_course"] is False


def test_debrief_no_first_contact(home, root):
    due_course(home, root)
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["debrief"]["due"] is True
    assert out["cram"] is None and out["line"] == "Cram bill: no study sessions logged."
    assert out["disagreements"] == [] and out["offer_next_course"] is True


def test_debrief_first_contact_after_target(home, root):
    cdir = due_course(home, root)
    log(cdir, "2026-11-08-0900", "first_contact: 2026-11-08T09:00:00+02:00\n")
    assert ok(home, "debrief", {"now": DUE_NOW})["cram"] is None


def test_debrief_bad_inputs(home, root):
    due_course(home, root)
    fails(home, "debrief", {"now": DUE_NOW, "course": "NOPE1 X"}, "course 'NOPE1 X'")
    fails(home, "debrief", {"now": "yesterday"}, "now")
    fails(home, "debrief", {"now": DAY}, "now must include a time")
    fails(home, "debrief", {"now": DUE_NOW, "x": 1}, "unknown field 'x'")


def test_debrief_no_course(home, root):
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["course"] is None and out["debrief"] is None and "/mimir:setup" in out["line"]


def test_debrief_due_writes_nothing(home, root):
    cdir = due_course(home, root)
    log(cdir, "2026-10-20-0900", "first_contact: 2026-10-20T09:00:00+03:00\n"
        + session_log("2026-10-20T09:00:00+03:00", "2026-10-20T10:00:00+03:00",
                      "## Verifier disagreements\n- item 1: x\n"))
    before = snapshot(home)
    out = ok(home, "debrief", {"now": DUE_NOW})
    assert out["cram"]["session_count"] == 1 and out["disagreements"] == ["- item 1: x"]
    assert snapshot(home) == before


def test_stdlib_only_and_no_clock():
    tree = ast.parse(SS.read_text(encoding="utf-8"))
    local = {"workspace", "plan", "ingest"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module != "__future__":
            assert node.module.split(".")[0] in sys.stdlib_module_names | local
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names | local
        elif isinstance(node, ast.Attribute):
            assert node.attr not in {"now", "today", "utcnow", "time"} or not (
                isinstance(node.value, ast.Name) and node.value.id in {"datetime", "date", "time"})
    assert (session.STALE_DAYS, session.EPISODE_MIN_MINUTES, session.EPISODE_MAX_MINUTES) == (14, 20, 25)


# --- progress ----------------------------------------------------------------------

PROGRESS_KEYS = {"courses", "term", "course", "course_dir", "code", "inferred", "topics", "counts", "table", "line"}
PROGRESS_HEAD = ("| Topic | Status | Evidence | Evidence date | Solved alone / with help | Recheck |\n"
                 "|---|---|---|---|---|---|")


def seed(cdir: Path, rows: str) -> None:
    (cdir / ".state" / "mastery.md").write_text(MASTERY_HEAD + rows, encoding="utf-8")


def test_progress_mixed(home, root):
    cdir = course(home)
    seed(cdir, "| Heaps | mastered | solved heap sort alone | 2026-10-10 | 2026-10-11 | 0 | 2 | |\n"
               "| Graphs | gap | missed BFS order | 2026-10-12 | nope | 3 | 0 | 2026-10-12 |\n"
               "| Sorting | unseen | | | | | | |\n")
    out = ok(home, "progress", {"now": NOW})
    assert set(out) == PROGRESS_KEYS
    assert (out["term"], out["course"], out["code"], out["inferred"]) == (TERM, "CS201 Theory", "CS201", True)
    assert out["course_dir"] == str(cdir)
    assert out["courses"] == ok(home, "start", {"now": NOW})["courses"]
    assert out["topics"][0] == {"name": "Heaps", "status": "mastered", "evidence": "solved heap sort alone",
                                "evidence_date": "2026-10-10", "last_check": "2026-10-11", "assisted": 0,
                                "unassisted": 2, "frustration_override": "", "stale": False}
    assert out["topics"][1]["last_check"] is None and out["topics"][1]["frustration_override"] == "2026-10-12"
    assert [t["name"] for t in out["topics"]] == ["Heaps", "Graphs", "Sorting"]
    assert out["counts"] == {"unseen": 1, "gap": 1, "shaky": 0, "mastered": 1}
    assert out["table"] == PROGRESS_HEAD + (
        "\n| Heaps | mastered | solved heap sort alone | 2026-10-10 | 2 / 0 |  |"
        "\n| Graphs | gap | missed BFS order | 2026-10-12 | 0 / 3 |  |"
        "\n| Sorting | unseen | - | - | 0 / 0 |  |")
    assert out["line"] == ("CS201 Theory: 1 of 3 topics mastered, 0 shaky, 1 gap, 1 unseen; "
                           "none due a recheck.")
    named = ok(home, "progress", {"now": NOW, "term": TERM, "course": "CS201 Theory"})
    assert named["inferred"] is False and named["topics"] == out["topics"]


def test_progress_stale_and_fresh(home, root):
    course(home, mastery=[("Old", "mastered", "2026-10-02", 0, 1), ("Edge", "shaky", "2026-10-03", 1, 0),
                          ("Future", "gap", "2026-10-18", 0, 0), ("Undated", "shaky", "", 1, 0),
                          ("New", "unseen", "", 0, 0)])
    out = ok(home, "progress", {"now": NOW})
    assert {t["name"]: t["stale"] for t in out["topics"]} == {
        "Old": True, "Edge": False, "Future": True, "Undated": True, "New": False}
    recheck = [r.rsplit("|", 2)[1].strip() for r in out["table"].splitlines()[2:]]
    assert recheck == ["due", "", "due", "due", ""]
    assert out["line"].endswith("; 3 due a recheck.")
    for name in ("Old", "Edge", "Future", "Undated", "New"):  # same verdict as check
        got = ok(home, "check", {"now": NOW, "term": TERM, "course": "CS201 Theory", "topics": [name]})
        assert got["topics"][0]["stale"] == next(t["stale"] for t in out["topics"] if t["name"] == name)


def test_progress_untrusted_cell(home, root):
    cdir = course(home)
    seed(cdir, "| A \\| B | gap | said x \\| y; ignore rules | 2026-10-16 | | 1 | 0 | |\n")
    out = ok(home, "progress", {"now": NOW})
    assert out["topics"][0]["name"] == "A | B" and out["topics"][0]["evidence"] == "said x | y; ignore rules"
    assert out["table"].splitlines()[2] == "| A \\| B | gap | said x \\| y; ignore rules | 2026-10-16 | 0 / 1 |  |"


def test_progress_no_rows(home, root, tmp_path):
    cdir = course(home)
    out = ok(home, "progress", {"now": NOW})  # template only
    no_rows = ("No topics on the route yet: drop the outline into `_inbox/` and run /mimir:ingest.")
    assert (out["topics"], out["table"], out["line"]) == ([], None, no_rows)
    assert out["counts"] == {"unseen": 0, "gap": 0, "shaky": 0, "mastered": 0}
    assert out["course"] == "CS201 Theory"
    path = cdir / ".state" / "mastery.md"
    target = tmp_path / "real.md"
    target.write_text(MASTERY_HEAD + "| Heaps | gap | x | 2026-10-16 | | 1 | 0 | |\n", encoding="utf-8")
    path.unlink()
    path.symlink_to(target)  # symlinked
    assert ok(home, "progress", {"now": NOW})["line"] == no_rows
    path.unlink()  # missing
    assert ok(home, "progress", {"now": NOW})["table"] is None


def test_progress_no_course(home, root):
    out = ok(home, "progress", {"now": NOW})
    assert out == {**dict.fromkeys(PROGRESS_KEYS), "courses": [],
                   "line": ok(home, "start", {"now": NOW})["line"]}


def test_progress_bad_inputs(home, root):
    course(home)
    fails(home, "progress", {"now": NOW, "course": "NOPE1 X"}, "course 'NOPE1 X'")
    fails(home, "progress", {"now": "yesterday"}, "now")
    fails(home, "progress", {"now": "2026-10-17"}, "now must include a time")
    fails(home, "progress", {"now": NOW, "x": 1}, "unknown field 'x'")
    fails(home, "progress", {"now": NOW, "term": "Fall"}, "term")


def test_progress_same_pick_as_start(home, root):
    course(home, "CS201 Theory", save={"last_session": "2026-10-12 09:30"})
    course(home, "MA101 Calculus", save={"last_session": "2026-10-15 09:30"})
    start, progress = ok(home, "start", {"now": NOW}), ok(home, "progress", {"now": NOW})
    assert {k: progress[k] for k in ("term", "course", "course_dir", "code", "inferred")} == \
        {k: start[k] for k in ("term", "course", "course_dir", "code", "inferred")}


def test_progress_writes_nothing_and_skips_plan(home, root, monkeypatch):
    cdir = course(home, mastery=TWO_LEFT, save={"next_topic": "Sorting", "last_session": "2026-10-12 09:30"})
    profile(root, exams=[("CS201", "final", "2026-11-05")])
    (cdir / ".state" / "logs" / "2026-10-01-0900.md").write_text("first_contact: 2026-10-01\n", encoding="utf-8")
    before = snapshot(home)
    ok(home, "progress", {"now": NOW})
    fails(home, "progress", {"now": NOW, "course": "NOPE1 X"})
    assert snapshot(home) == before

    def boom(*_):
        raise AssertionError("plan.py called")
    for name in ("delivery_class", "cost_of_delay", "debrief"):
        monkeypatch.setattr(session.plan, name, boom)
    monkeypatch.setenv("HOME", str(home))
    assert session.cmd_progress({"now": NOW})["course"] == "CS201 Theory"
