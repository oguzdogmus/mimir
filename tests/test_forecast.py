"""Boundary tests for scripts/forecast.py (run: uv run --with pytest pytest tests -q)."""

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
FC = SCRIPTS / "forecast.py"
WS = SCRIPTS / "workspace.py"

sys.path.insert(0, str(SCRIPTS))
import forecast  # noqa: E402

TERM, COURSE, OTHER = "2026-Fall", "CS201 Theory", "MA101 Calculus"
PAPERS = [("past-papers/p1.pdf", "past-papers", "text"), ("past-papers/p2.pdf", "past-papers", "ocr"),
          ("past-papers/p3.pdf", "past-papers", "text"), ("past-papers/p4.pdf", "past-papers", "text"),
          ("past-papers/a|b.pdf", "past-papers", "text"), ("outline/outline.pdf", "outline", "text"),
          ("slides/s1.pdf", "slides", "text")]


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def root(home):
    ws_ok(home, "init", {})
    return home / "learning"


def _run(script: Path, home: Path, cmd: str, payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(script), cmd], input=stdin, capture_output=True,
                          env={**os.environ, "HOME": str(home)})


def ok(home: Path, cmd: str, payload) -> dict:
    proc = _run(FC, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b"" and proc.stdout.count(b"\n") == 1
    out = json.loads(proc.stdout)
    assert isinstance(out["line"], str) and out["line"]
    return out


def fails(home: Path, cmd: str, payload, needle: str = "") -> str:
    proc = _run(FC, home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("forecast.py: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def ws_ok(home: Path, cmd: str, payload) -> dict:
    proc = _run(WS, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    return json.loads(proc.stdout)


def course(home: Path, root: Path, name: str = COURSE, rows=PAPERS) -> Path:
    ws_ok(home, "course", {"term": TERM, "course": name})
    cdir = root / TERM / name
    index = cdir / "INDEX.md"
    lines = index.read_text().splitlines()
    at = lines.index("## Topics") - 1
    lines[at:at] = [f"| {p.replace('|', chr(92) + '|')} | {TERM} | {r} | 3 | {f} |" for p, r, f in rows]
    index.write_text("\n".join(lines) + "\n")
    return cdir


def snapshot(root: Path) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            out[str(p)] = os.readlink(p) if p.is_symlink() else (p.read_bytes() if p.is_file() else None)
    return out


def topics(n: int, sources=("outline/outline.pdf",)) -> list[dict]:
    return [{"topic": f"Topic {i}", "evidence": f"Evidence {i}", "sources": list(sources)} for i in range(1, n + 1)]


def write(name=COURSE, exam="2026-11-05", exam_name="final", date="2026-10-19", **kw) -> dict:
    return {"term": TERM, "course": name, "date": date, "exam": exam, "exam_name": exam_name,
            "topics": topics(3), **kw}


def score(hits, name=COURSE, exam="2026-11-05", exam_name="final", date="2026-11-12") -> dict:
    return {"term": TERM, "course": name, "date": date, "exam": exam, "exam_name": exam_name, "hits": hits}


def fc_text(cdir: Path) -> str:
    return (cdir / ".state" / "forecast.md").read_text()


def headings(cdir: Path) -> list[str]:
    return [l for l in fc_text(cdir).splitlines() if l.startswith("## ")]


def profile_line(root: Path) -> str:
    return next(l for l in (root / ".state" / "profile.md").read_text().splitlines()
                if l.startswith("forecast_record:"))


# --- constants and confidence -------------------------------------------------------

def test_constants_are_the_spec_values():
    assert (forecast.MAX_TOPICS, forecast.TOP_N, forecast.ENTRY_MAX_CHARS) == (10, 5, 160)
    assert forecast.LABEL == "[forecast, not a guarantee]"


@pytest.mark.parametrize("n, want", [
    (0, "low - No past papers or debriefs to go on, only the outline and slides, so this is a rough guess."),
    (1, "low - Only one paper to go on, so this is a rough guess."),
    (2, "medium - Based on 2 papers; more papers would sharpen it."),
    (3, "medium - Based on 3 papers; more papers would sharpen it."),
    (4, "high - Based on 4 papers."),
    (7, "high - Based on 7 papers.")])
def test_confidence_bands(n, want):
    assert forecast.confidence(n) == want


# --- write ----------------------------------------------------------------------------

def test_one_paper_low_confidence_block_first(root, home):
    cdir = course(home, root)
    ts = [{"topic": "Pumping lemma", "evidence": "20 marks on the final",
           "sources": ["past-papers/p1.pdf", "outline/outline.pdf"]},
          {"topic": "Regular expressions", "evidence": "Outline week 9", "sources": ["outline/outline.pdf"]},
          {"topic": "DFA minimisation", "evidence": "Both", "sources": ["past-papers/p1.pdf"]}]
    out = ok(home, "write", write(topics=ts))
    assert out["confidence"] == "low - Only one paper to go on, so this is a rough guess."
    assert out["papers"] == 1 and out["replaced"] is False and out["record_line"] is None
    assert out["label"] == "[forecast, not a guarantee]"
    assert [t["rank"] for t in out["topics"]] == [1, 2, 3]
    lines = fc_text(cdir).splitlines()
    assert lines[0].startswith("<!--") and lines[1] == "# Forecast"
    at = lines.index("## 2026-11-05 final")
    assert lines[at:at + 11] == [
        "## 2026-11-05 final", "date: 2026-10-19", "label: [forecast, not a guarantee]",
        "confidence: low - Only one paper to go on, so this is a rough guess.", "hit_rate: pending", "",
        "| rank | topic | evidence |", "|---|---|---|",
        "| 1 | Pumping lemma | 20 marks on the final (source: past-papers/p1.pdf; outline/outline.pdf) |",
        "| 2 | Regular expressions | Outline week 9 (source: outline/outline.pdf) |",
        "| 3 | DFA minimisation | Both (source: past-papers/p1.pdf) |"]
    assert out["forecast"] == str(cdir / ".state" / "forecast.md")
    assert "3 topics, low confidence" in out["line"]


def test_new_block_goes_first(root, home):
    cdir = course(home, root)
    ok(home, "write", write(exam="2026-11-05", exam_name="midterm"))
    ok(home, "write", write(exam="2027-01-10", exam_name="final"))
    assert headings(cdir) == ["## 2027-01-10 final", "## 2026-11-05 midterm"]


def test_confidence_counts_distinct_papers_and_debriefs(root, home):
    course(home, root)
    ts = [{"topic": "A", "evidence": "e", "sources": ["past-papers/p1.pdf", "past-papers/p2.pdf"]},
          {"topic": "B", "evidence": "e", "sources": ["past-papers/p1.pdf", "slides/s1.pdf"]}]
    assert ok(home, "write", write(topics=ts))["confidence"].startswith("medium - Based on 2 papers")
    ts.append({"topic": "C", "evidence": "e", "sources": ["debrief 2026-06-01", "past-papers/p3.pdf"]})
    assert ok(home, "write", write(topics=ts))["confidence"] == "high - Based on 4 papers."
    assert ok(home, "write", write(topics=topics(2)))["confidence"].startswith("low - No past papers")


def test_rewrite_pending_replaces_block(root, home):
    cdir = course(home, root)
    ok(home, "write", write(exam_name="midterm", exam="2026-10-30"))
    ok(home, "write", write(topics=topics(2)))
    out = ok(home, "write", write(exam_name="Final", topics=topics(4)))
    assert out["replaced"] is True
    assert headings(cdir) == ["## 2026-11-05 Final", "## 2026-10-30 midterm"]
    assert fc_text(cdir).count("| 4 | Topic 4 |") == 1


def test_scored_rewrite_exits_2(root, home):
    cdir = course(home, root)
    ok(home, "write", write())
    ok(home, "score", score([1]))
    before = snapshot(root)
    fails(home, "write", write(), "already scored")
    assert snapshot(root) == before
    assert headings(cdir) == ["## 2026-11-05 final"]


def test_pipes_are_escaped(root, home):
    cdir = course(home, root)
    ts = [{"topic": "A|B", "evidence": "x | y", "sources": ["past-papers/a|b.pdf"]}]
    ok(home, "write", write(topics=ts))
    assert "| 1 | A\\|B | x \\| y (source: past-papers/a\\|b.pdf) |" in fc_text(cdir)


def test_bad_source_names_field_and_writes_nothing(root, home):
    course(home, root)
    before = snapshot(root)
    ts = topics(2) + [{"topic": "X", "evidence": "e", "sources": ["past-papers/missing.pdf"]}]
    fails(home, "write", write(topics=ts), "topics[3].sources[1]")
    fails(home, "write", write(topics=[{"topic": "X", "evidence": "e", "sources": ["prior-term:x.pdf"]}]),
          "topics[1].sources[1]")
    fails(home, "write", write(topics=[{"topic": "X", "evidence": "e", "sources": ["debrief 2026-02-30"]}]),
          "not a valid debrief date")
    fails(home, "write", write(topics=[{"topic": "X", "evidence": "e", "sources": []}]), "topics[1].sources")
    assert snapshot(root) == before


@pytest.mark.parametrize("patch, needle", [
    ({"topics": []}, "topics is required"),
    ({"topics": topics(11)}, "over the 10-topic cap"),
    ({"topics": [{"topic": "A", "evidence": "e", "sources": ["slides/s1.pdf"]},
                 {"topic": " a ", "evidence": "e", "sources": ["slides/s1.pdf"]}]}, "distinct"),
    ({"topics": [{"topic": "A\nB", "evidence": "e", "sources": ["slides/s1.pdf"]}]}, "topics[1].topic"),
    ({"topics": [{"topic": "A" * 161, "evidence": "e", "sources": ["slides/s1.pdf"]}]}, "160"),
    ({"topics": [{"topic": "A", "evidence": "x (source: y)", "sources": ["slides/s1.pdf"]}]}, "reserved"),
    ({"topics": [{"topic": "A", "evidence": "", "sources": ["slides/s1.pdf"]}]}, "evidence is required"),
    ({"topics": [{"topic": "A", "evidence": "e", "sources": ["slides/s1.pdf"], "x": 1}]}, "x"),
    ({"exam": "2026-13-01"}, "exam"),
    ({"exam": "Nov 5"}, "exam"),
    ({"date": None}, "date"),
    ({"exam_name": ""}, "exam_name"),
    ({"exam_name": "final (tentative)"}, "reserved"),
    ({"exam": "2026-10-18"}, "before date"),
    ({"confidence": "high"}, "confidence"),
])
def test_write_input_errors(root, home, patch, needle):
    course(home, root)
    before = snapshot(root)
    fails(home, "write", {**write(), **patch}, needle)
    assert snapshot(root) == before


def test_write_needs_course_and_workspace(home, root):
    fails(home, "write", write(), "no course folder")
    real = course(home, root, name="Real")
    (root / TERM / COURSE).symlink_to(real)
    fails(home, "write", write(), "symlink")


def test_symlinked_forecast_refused(root, home, tmp_path):
    cdir = course(home, root)
    target = tmp_path / "elsewhere.md"
    target.write_text("x\n")
    fcp = cdir / ".state" / "forecast.md"
    fcp.unlink()
    fcp.symlink_to(target)
    fails(home, "write", write(), "symlink")
    assert target.read_text() == "x\n"


def test_prior_term_source_follows_fingerprint_rules(root, home):
    prior = root / "2026-Spring" / COURSE
    ws_ok(home, "course", {"term": "2026-Spring", "course": COURSE})
    index = prior / "INDEX.md"
    lines = index.read_text().splitlines()
    at = lines.index("## Topics") - 1
    lines[at:at] = ["| past-papers/old.pdf | 2026-Spring | past-papers | 3 | text |"]
    index.write_text("\n".join(lines) + "\n")
    course(home, root)
    proc = _run(SCRIPTS / "fingerprint.py", home, "retake",
                {"term": TERM, "course": COURSE, "prior_term": "2026-Spring", "prior_course": COURSE,
                 "professor": ""})
    assert proc.returncode == 0, proc.stderr.decode()
    ts = [{"topic": "A", "evidence": "e", "sources": ["prior-term:past-papers/old.pdf"]}]
    out = ok(home, "write", write(topics=ts))
    assert out["papers"] == 1 and out["topics"][0]["sources"] == ["prior-term:past-papers/old.pdf"]


# --- score ----------------------------------------------------------------------------

def test_score_five_topics(root, home):
    cdir = course(home, root)
    ok(home, "write", write(topics=topics(5)))
    out = ok(home, "score", score([1, 3, 4]))
    assert out["hit_rate"] == "3 of 5" and (out["hits"], out["of"]) == (3, 5)
    assert "hit_rate: 3 of 5 (scored 2026-11-12)" in fc_text(cdir).splitlines()
    assert "hit_rate: pending" not in fc_text(cdir)
    assert profile_line(root) == "forecast_record: 3 of 5 across 1 forecast"
    assert out["record"] == {"hits": 3, "of": 5, "forecasts": 1}
    assert out["record_line"] == "Past forecasts: 3 of 5 top topics appeared, across 1 forecast."


def test_score_short_list_and_top_five_cap(root, home):
    course(home, root)
    ok(home, "write", write(topics=topics(3)))
    assert ok(home, "score", score([2]))["hit_rate"] == "1 of 3"
    ok(home, "write", write(exam="2027-01-10", topics=topics(8)))
    assert ok(home, "score", score([], exam="2027-01-10", date="2027-01-20"))["hit_rate"] == "0 of 5"
    assert profile_line(root) == "forecast_record: 1 of 8 across 2 forecasts"


def test_rescore_overwrites_without_double_counting(root, home):
    cdir = course(home, root)
    ok(home, "write", write(topics=topics(5)))
    ok(home, "score", score([1]))
    ok(home, "score", score([1, 2], date="2026-11-13"))
    assert fc_text(cdir).count("hit_rate:") == 1
    assert "hit_rate: 2 of 5 (scored 2026-11-13)" in fc_text(cdir)
    assert profile_line(root) == "forecast_record: 2 of 5 across 1 forecast"


def test_two_courses_sum_and_record_line_in_next_write(root, home):
    course(home, root)
    course(home, root, name=OTHER)
    ok(home, "write", write(topics=topics(5)))
    ok(home, "write", write(name=OTHER, topics=topics(5)))
    ok(home, "score", score([1, 2, 3]))
    out = ok(home, "score", score([1, 2, 3, 4], name=OTHER))
    assert out["record"] == {"hits": 7, "of": 10, "forecasts": 2}
    assert profile_line(root) == "forecast_record: 7 of 10 across 2 forecasts"
    nxt = ok(home, "write", write(exam="2027-01-10"))
    assert nxt["record_line"] == "Past forecasts: 7 of 10 top topics appeared, across 2 forecasts."


def test_record_skips_symlinked_courses(root, home):
    course(home, root)
    ok(home, "write", write(topics=topics(5)))
    ok(home, "score", score([1, 2]))
    (root / "2027-Spring").mkdir()
    (root / "2027-Spring" / COURSE).symlink_to(root / TERM / COURSE)
    ok(home, "write", write(exam="2027-01-10"))
    assert ok(home, "score", score([1], exam="2027-01-10", date="2027-01-20"))["record"] == \
        {"hits": 3, "of": 8, "forecasts": 2}


def test_profile_line_added_when_missing(root, home):
    course(home, root)
    prof = root / ".state" / "profile.md"
    prof.write_text("\n".join(l for l in prof.read_text().splitlines()
                              if not l.startswith(("forecast_record:", "## Forecast record"))) + "\n")
    ok(home, "write", write())
    ok(home, "score", score([1]))
    lines = prof.read_text().splitlines()
    assert lines[-2:] == ["## Forecast record", "forecast_record: 1 of 3 across 1 forecast"]
    prof.write_text(prof.read_text().replace("forecast_record: 1 of 3 across 1 forecast\n", ""))
    ok(home, "score", score([1, 2]))
    lines = prof.read_text().splitlines()
    assert lines.count("## Forecast record") == 1
    assert lines[lines.index("## Forecast record") + 1] == "forecast_record: 2 of 3 across 1 forecast"


@pytest.mark.parametrize("hits, needle", [
    ([6], "hits[1]"), ([4], "from 1 to 3"), ([0], "hits[1]"), ([1, 1], "more than once"),
    ([True], "hits[1]"), (["1"], "hits[1]"), (None, "hits is required")])
def test_bad_hits(root, home, hits, needle):
    course(home, root)
    ok(home, "write", write(topics=topics(3)))
    before = snapshot(root)
    fails(home, "score", score(hits), needle)
    assert snapshot(root) == before


def test_rank_six_refused_on_long_list(root, home):
    course(home, root)
    ok(home, "write", write(topics=topics(8)))
    fails(home, "score", score([6]), "from 1 to 5")


def test_score_without_block_exits_2(root, home):
    course(home, root)
    before = snapshot(root)
    fails(home, "score", score([1]), "no forecast")
    assert snapshot(root) == before
    ok(home, "write", write())
    before = snapshot(root)
    fails(home, "score", score([1], exam_name="midterm"), "no forecast")
    assert snapshot(root) == before


def test_score_restores_forecast_when_profile_write_fails(root, home, monkeypatch):
    cdir = course(home, root)
    ok(home, "write", write())
    before = fc_text(cdir)
    real = forecast.ingest._write_atomic

    def flaky(path, text):
        if path.name == "profile.md":
            raise OSError(28, "No space left on device")
        real(path, text)

    monkeypatch.setattr(forecast.ingest, "_write_atomic", flaky)
    with pytest.raises(OSError):
        forecast.cmd_score(score([1]))
    assert fc_text(cdir) == before


def test_score_reraises_original_error_when_restore_fails(root, home, monkeypatch):
    course(home, root)
    ok(home, "write", write())
    real = forecast.ingest._write_atomic
    calls = []

    def flaky(path, text):
        calls.append(path.name)
        if path.name == "profile.md":
            raise OSError(28, "No space left on device")
        if len(calls) > 1:
            raise OSError(13, "Permission denied")
        real(path, text)

    monkeypatch.setattr(forecast.ingest, "_write_atomic", flaky)
    with pytest.raises(OSError) as info:
        forecast.cmd_score(score([1]))
    assert info.value.errno == 28
    assert calls == ["forecast.md", "profile.md", "forecast.md"]


def test_write_error_after_validation_creates_nothing(root, home):
    """A missing .state/ is not rebuilt when the write is refused."""
    cdir = course(home, root)
    (cdir / ".state" / "forecast.md").unlink()
    before = snapshot(root)
    fails(home, "write", write(topics=[{"topic": "X", "evidence": "e", "sources": ["nope.pdf"]}]), "nope.pdf")
    assert snapshot(root) == before


def test_score_date_before_exam_exits_2(root, home):
    course(home, root)
    ok(home, "write", write())
    before = snapshot(root)
    fails(home, "score", score([1], date="2026-11-04"), "before exam")
    assert snapshot(root) == before
    assert ok(home, "score", score([1], date="2026-11-05"))["hit_rate"] == "1 of 3"


@pytest.mark.parametrize("value", ["", "3 of 5 maybe", "of 5", "6 of 5", "3 of 0", "3 of 5 (scored soon)"])
def test_malformed_hit_rate_is_pending(root, home, value):
    cdir = course(home, root)
    ok(home, "write", write())
    fcp = cdir / ".state" / "forecast.md"
    fcp.write_text(fcp.read_text().replace("hit_rate: pending", f"hit_rate: {value}".rstrip()))
    assert forecast.record(root) == (0, 0, 0)
    out = ok(home, "write", write(topics=topics(2)))
    assert out["replaced"] is True and out["record_line"] is None
    assert headings(cdir) == ["## 2026-11-05 final"] and "hit_rate: pending" in fc_text(cdir)


def test_scored_suffix_counts():
    assert forecast._scored(["## x", "hit_rate: 3 of 5 (scored 2026-11-12)"]) == (3, 5)
    assert forecast._scored(["## x", "hit_rate: 3 of 5"]) == (3, 5)


def test_profile_record_replaced_only_in_its_section(root, home):
    course(home, root)
    prof = root / ".state" / "profile.md"
    prof.write_text(prof.read_text().replace("dial_preference:", "dial_preference:\nforecast_record: stray"))
    ok(home, "write", write())
    ok(home, "score", score([1]))
    lines = prof.read_text().splitlines()
    assert "forecast_record: stray" in lines
    assert lines[lines.index("## Forecast record") + 1] == "forecast_record: 1 of 3 across 1 forecast"
    assert sum(l.startswith("forecast_record:") for l in lines) == 2


def test_symlinked_root_state_refused(root, home, tmp_path):
    course(home, root)
    ok(home, "write", write())
    real_state = tmp_path / "real-state"
    (root / ".state").rename(real_state)
    (root / ".state").symlink_to(real_state)
    before = (real_state / "profile.md").read_text()
    fails(home, "score", score([1]), "symlink")
    assert (real_state / "profile.md").read_text() == before


def test_non_utf8_forecast_elsewhere_is_skipped(root, home):
    course(home, root)
    other = course(home, root, name=OTHER)
    (other / ".state" / "forecast.md").write_bytes(b"\xff\xfe## 2026-11-05 final\nhit_rate: 5 of 5\n")
    ok(home, "write", write(topics=topics(5)))
    out = ok(home, "score", score([1, 2]))
    assert out["record"] == {"hits": 2, "of": 5, "forecasts": 1}
    nxt = ok(home, "write", write(exam="2027-01-10"))
    assert nxt["record_line"] == "Past forecasts: 2 of 5 top topics appeared, across 1 forecast."


def test_score_matches_exam_name_ignoring_case_and_spaces(root, home):
    cdir = course(home, root)
    ok(home, "write", write(exam_name="Final  Exam"))
    out = ok(home, "score", score([1], exam_name="  FINAL exam "))
    assert out["hit_rate"] == "1 of 3"
    assert "hit_rate: 1 of 3 (scored 2026-11-12)" in fc_text(cdir)


# --- module hygiene -------------------------------------------------------------------

def test_stdlib_plus_siblings_only_and_no_clock():
    tree = ast.parse(FC.read_text(encoding="utf-8"))
    local = {"workspace", "ingest", "fingerprint"}
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            tops.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            assert node.attr not in {"now", "today", "utcnow", "time"} or not (
                isinstance(node.value, ast.Name) and node.value.id in {"datetime", "date", "time"})
    assert tops - local <= set(sys.stdlib_module_names) | {"__future__"}, tops


def test_fingerprint_sources_are_reused_not_copied():
    text = FC.read_text(encoding="utf-8")
    assert "fingerprint._sources(" in text and "fingerprint.source_context(" in text
    assert "_DEBRIEF" not in text and "registry(" not in text


def test_plugin_json_lists_every_skill_folder():
    manifest = json.loads((ROOT_DIR / ".claude-plugin" / "plugin.json").read_text())
    folders = {f"./skills/{d.name}" for d in (ROOT_DIR / "skills").iterdir() if (d / "SKILL.md").is_file()}
    assert len(manifest["skills"]) == len(set(manifest["skills"]))
    assert set(manifest["skills"]) == folders


def test_write_failure_in_record_creates_and_writes_nothing(root, home, monkeypatch):
    cdir = course(home, root)
    (cdir / ".state" / "forecast.md").unlink()
    before = snapshot(root)

    def broken(*args, **kwargs):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(forecast, "record", broken)
    with pytest.raises(OSError):
        forecast.cmd_write(write())
    assert snapshot(root) == before
