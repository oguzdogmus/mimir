"""Boundary tests for scripts/verify.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import ast
import datetime
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
VF = SCRIPTS / "verify.py"
WS = SCRIPTS / "workspace.py"

sys.path.insert(0, str(SCRIPTS))
import ingest  # noqa: E402
import verify  # noqa: E402

TERM, COURSE = "2026-Fall", "CS201 Theory"
PRACTICE = "[practice, not from a real paper]"
OCR = "[real, from photo/scan, wording may be off]"
ROWS = [("past-papers/2024-final.pdf", "past-papers", "4", "text"),
        ("past-papers/photo.jpg", "past-papers", "1", "ocr"),
        ("past-papers/nopages.pdf", "past-papers", "", "text"),
        ("slides/s1.pdf", "slides", "5", "text"),
        ("slides/scan.pdf", "slides", "5", "ocr"),
        ("outline/outline.pdf", "outline", "2", "text"),
        ("notes/summary.pdf", "notes", "3", "text"),
        ("past-papers/a|b.pdf", "past-papers", "2", "text")]


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


@pytest.fixture
def cdir(home, root):
    return course(home, root, rows=ROWS)


def _run(script: Path, home: Path, cmd: str, payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(script), cmd], input=stdin, capture_output=True,
                          env={**os.environ, "HOME": str(home)})


def ok(home: Path, payload) -> dict:
    proc = _run(VF, home, "gate", payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b"" and proc.stdout.count(b"\n") == 1
    out = json.loads(proc.stdout)
    assert isinstance(out["line"], str) and out["line"]
    return out


def fails(home: Path, payload, needle: str = "", cmd: str = "gate") -> str:
    proc = _run(VF, home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("verify.py: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def ws_ok(home: Path, cmd: str, payload) -> dict:
    proc = _run(WS, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    return json.loads(proc.stdout)


def course(home: Path, root: Path, name: str = COURSE, rows=()) -> Path:
    """A course tree whose INDEX registry holds ``rows`` of (path, role, pages, fidelity)."""
    ws_ok(home, "course", {"term": TERM, "course": name})
    cdir = root / TERM / name
    index = cdir / "INDEX.md"
    lines = index.read_text().splitlines()
    at = lines.index("## Topics") - 1
    lines[at:at] = [f"| {p.replace('|', chr(92) + '|')} | {TERM} | {r} | {n} | {f} |" for p, r, n, f in rows]
    index.write_text("\n".join(lines) + "\n")
    return cdir


def gate(*items) -> dict:
    return {"term": TERM, "course": COURSE, "items": list(items)}


def one(home: Path, item: dict) -> dict:
    return ok(home, gate(item))["results"][0]


def practice(**kw) -> dict:
    return {"topic": "DFA minimisation", "origin": "practice", **kw}


def real(source="past-papers/2024-final.pdf", page=3, **kw) -> dict:
    return {"topic": "Pumping lemma", "origin": "real", "source": source, "page": page, **kw}


def dated(home: Path, payload) -> tuple[dict, set[str]]:
    """Gate output plus the dates seen just before and after the call (a run may cross midnight)."""
    before = datetime.date.today().isoformat()
    out = ok(home, payload)
    return out, {before, datetime.date.today().isoformat()}


def same_on_a_day(lines: list[str], days: set[str], *expected: str) -> bool:
    """True when ``lines`` equal ``expected`` (with ``{day}`` filled in) for one of ``days``."""
    return any(lines == [e.format(day=d) for e in expected] for d in days)
COMPARE = {"path": "past-papers/2024-final.pdf", "page": 3, "question": "Q4"}


def snapshot(root: Path) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            out[str(p)] = (os.readlink(p) if p.is_symlink() else
                           (p.read_bytes(), p.stat().st_mtime_ns) if p.is_file() else None)
    return out


# --- constants and shared registry ---------------------------------------------------

def test_constants_are_the_spec_values():
    assert verify.VERIFIER_RETRIES == 1


def test_registry_reads_role_pages_fidelity(cdir):
    rows = ingest.registry(cdir / "INDEX.md")
    assert rows["past-papers/2024-final.pdf"] == ("past-papers", 4, "text")
    assert rows["past-papers/nopages.pdf"] == ("past-papers", None, "text")
    assert rows["slides/scan.pdf"] == ("slides", 5, "ocr")
    assert rows["past-papers/a|b.pdf"] == ("past-papers", 2, "text")
    assert ingest.registry(cdir / "missing.md") == {}


def test_registry_lowercases_role_and_rejects_non_positive_pages(home, root):
    cdir = course(home, root, rows=[("past-papers/A.pdf", "Past-Papers", "0", "TEXT"),
                                    ("slides/b.pdf", "SLIDES", "007", "ocr"),
                                    ("slides/c.pdf", "slides", "-3", "text"),
                                    ("slides/d.pdf", "slides", "2.5", "text"),
                                    ("slides/e.pdf", "slides", "x", "text")])
    rows = ingest.registry(cdir / "INDEX.md")
    assert rows["past-papers/A.pdf"] == ("past-papers", None, "text")
    assert rows["slides/b.pdf"] == ("slides", None, "ocr")
    assert all(rows[f"slides/{n}.pdf"][1] is None for n in "cde")


def test_uppercase_role_still_counts_as_past_paper(home, root):
    course(home, root, rows=[("past-papers/A.pdf", "Past-Papers", "0", "text")])
    assert one(home, real(source="past-papers/A.pdf", page=9))["label"] == "[real: past-papers/A.pdf, p.9]"


def test_registry_refuses_non_utf8(cdir):
    (cdir / "INDEX.md").write_bytes(b"\xff\xfe broken")
    with pytest.raises(ingest.InputError, match="not valid UTF-8"):
        ingest.registry(cdir / "INDEX.md")


# --- matrix: labels and decisions ----------------------------------------------------

def test_practice_unverified_needs_verify(home, cdir):
    out = ok(home, gate(practice()))
    r = out["results"][0]
    assert r == {"n": 1, "topic": "DFA minimisation", "origin": "practice", "label": PRACTICE,
                 "needs_verification": True, "decision": "verify", "counts_for_mastery": False}
    assert out["verify"] == [1] and out["retry"] == [] and out["disagreements"] == []
    assert out["course_dir"] == str(cdir)
    assert out["line"] == "Gate: 1 item, 1 to verify."


@pytest.mark.parametrize("path,page", [("slides/s1.pdf", 2), ("outline/outline.pdf", 2),
                                       ("past-papers/2024-final.pdf", 4), ("past-papers/nopages.pdf", 99)])
def test_cited_text_quote_shows_without_verification(home, cdir, path, page):
    r = one(home, practice(quote={"path": path, "page": page}))
    assert r["decision"] == "show" and r["needs_verification"] is False and r["counts_for_mastery"] is True
    assert r["label"] == PRACTICE


@pytest.mark.parametrize("quote", [{"path": "slides/scan.pdf", "page": 2},        # ocr row
                                   {"path": "past-papers/photo.jpg", "page": 1},  # ocr row
                                   {"path": "notes/summary.pdf", "page": 1},      # not professor material
                                   {"path": "slides/missing.pdf", "page": 1},     # unindexed
                                   {"path": "slides/s1.pdf", "page": 6}])         # past the end
def test_other_quotes_still_need_verification(home, cdir, quote):
    r = one(home, practice(quote=quote))
    assert r["decision"] == "verify" and r["needs_verification"] is True


def test_real_text_label(home, cdir):
    r = one(home, real(question="Q2"))
    assert r["label"] == "[real: past-papers/2024-final.pdf, p.3]"
    assert "original" not in r and r["decision"] == "verify"


def test_real_ocr_label_and_original(home, cdir):
    r = one(home, real(source="past-papers/photo.jpg", page=1))
    assert r["label"] == OCR
    assert r["original"] == {"path": str(cdir / "past-papers" / "photo.jpg"), "page": 1}


def test_real_without_known_pages_accepts_any_page(home, cdir):
    assert one(home, real(source="past-papers/nopages.pdf", page=40))["label"] == \
        "[real: past-papers/nopages.pdf, p.40]"


def test_pipe_in_registry_path(home, cdir):
    assert one(home, real(source="past-papers/a|b.pdf", page=2))["label"] == "[real: past-papers/a|b.pdf, p.2]"


def test_one_non_correct_is_retry(home, cdir):
    out = ok(home, gate(practice(verdicts=["wrong"]), practice(verdicts=["source-conflict"])))
    assert [r["decision"] for r in out["results"]] == ["retry", "retry"]
    assert out["retry"] == [1, 2] and out["verify"] == [] and out["disagreements"] == []


@pytest.mark.parametrize("verdicts", [["correct"], ["wrong", "correct"], ["ambiguous", "correct"]])
def test_last_correct_shows(home, cdir, verdicts):
    r = one(home, practice(verdicts=verdicts))
    assert r["decision"] == "show" and r["counts_for_mastery"] is True and "flag" not in r


def test_disputed_twice_with_compare_is_flagged(home, cdir):
    out, days = dated(home, gate(practice(), practice(verdicts=["wrong", "ambiguous"], compare=COMPARE,
                                                      dispute="step 3")))
    r = out["results"][1]
    assert r["decision"] == "flagged" and r["counts_for_mastery"] is False
    assert r["flag"] == "⚠ my checker disagrees on step 3, compare with `past-papers/2024-final.pdf` p.3 Q4"
    assert same_on_a_day(out["disagreements"], days, "- {day} item 2 (DFA minimisation): flagged, checker said "
                         "ambiguous, compare past-papers/2024-final.pdf p.3 Q4")
    assert out["line"] == "Gate: 2 items, 1 to verify, 1 flagged."


def test_flag_without_dispute_or_question(home, cdir):
    out, days = dated(home, gate(practice(verdicts=["wrong", "wrong"], compare={"path": "slides/s1.pdf", "page": 5})))
    assert out["results"][0]["flag"] == "⚠ my checker disagrees on this answer, compare with `slides/s1.pdf` p.5"
    assert same_on_a_day(out["disagreements"], days,
                         "- {day} item 1 (DFA minimisation): flagged, checker said wrong, compare slides/s1.pdf p.5")


@pytest.mark.parametrize("extra", [{}, {"compare": {"path": "slides/missing.pdf", "page": 1}},
                                   {"compare": {"path": "slides/s1.pdf", "page": 6}}])
def test_no_reference_is_dropped(home, cdir, extra):
    out, days = dated(home, gate(practice(verdicts=["wrong", "wrong"], **extra)))
    r = out["results"][0]
    assert r["decision"] == "dropped" and r["counts_for_mastery"] is False and "flag" not in r
    assert same_on_a_day(out["disagreements"], days, "- {day} item 1 (DFA minimisation): dropped, checker said wrong")
    assert out["line"] == "Gate: 1 item, 1 dropped."


def test_verdicts_apply_to_quote_items(home, cdir):
    quote = {"path": "slides/s1.pdf", "page": 2}
    assert one(home, practice(quote=quote, verdicts=["wrong"]))["decision"] == "retry"
    assert one(home, practice(quote=quote, verdicts=["wrong", "wrong"]))["decision"] == "dropped"
    assert one(home, practice(quote=quote, verdicts=[]))["decision"] == "show"


def test_empty_verdicts_is_no_verdicts(home, cdir):
    assert one(home, practice(verdicts=[]))["decision"] == "verify"


def test_mixed_batch_numbers_and_line(home, cdir):
    out = ok(home, gate(practice(), practice(quote={"path": "slides/s1.pdf", "page": 1}),
                        real(verdicts=["wrong"]), practice(verdicts=["wrong", "correct"]),
                        practice(verdicts=["ambiguous", "wrong"])))
    assert [r["n"] for r in out["results"]] == [1, 2, 3, 4, 5]
    assert out["verify"] == [1] and out["retry"] == [3]
    assert out["line"] == "Gate: 5 items, 2 to show, 1 to verify, 1 to retry, 1 dropped."
    assert len(out["disagreements"]) == 1 and "item 5 " in out["disagreements"][0]


UNSAFE = [("/etc/passwd", "past-papers", "4", "text"),
          ("past-papers/../../outside.pdf", "past-papers", "4", "text"),
          ("../CS999 Other/past-papers/x.pdf", "past-papers", "4", "text"),
          ("past-papers/link.pdf", "past-papers", "4", "text")]


@pytest.fixture
def unsafe(home, root, tmp_path):
    cdir = course(home, root, rows=ROWS + UNSAFE)
    (tmp_path / "outside.pdf").write_bytes(b"%PDF-1.7")
    (cdir / "past-papers" / "link.pdf").symlink_to(tmp_path / "outside.pdf")
    return cdir


@pytest.mark.parametrize("path", [p for p, *_ in UNSAFE])
def test_registry_paths_outside_the_course_count_as_no_row(home, unsafe, path):
    fails(home, gate(real(source=path, page=1)), "items[1].source")
    assert one(home, practice(quote={"path": path, "page": 1}))["decision"] == "verify"
    r = one(home, practice(verdicts=["wrong", "wrong"], compare={"path": path, "page": 1}))
    assert r["decision"] == "dropped" and "flag" not in r


def test_inside_paths_still_work_next_to_unsafe_rows(home, unsafe):
    assert one(home, real())["label"] == "[real: past-papers/2024-final.pdf, p.3]"


# --- matrix: bad input ----------------------------------------------------------------

@pytest.mark.parametrize("item,needle", [
    (real(source="slides/s1.pdf", page=1), "items[1].source"),
    (real(source="past-papers/unindexed.pdf"), "items[1].source"),
    (real(source="notes/summary.pdf", page=1), "items[1].source"),
    (real(page=5), "items[1].page"),
    (real(page=0), "items[1].page"),
    (real(page=True), "items[1].page"),
    (real(page="3"), "items[1].page"),
    ({"topic": "t", "origin": "real", "page": 1}, "items[1].source"),
    ({"topic": "t", "origin": "real", "source": "past-papers/2024-final.pdf"}, "items[1].page"),
    (practice(verdicts=["wrong", "wrong", "wrong"]), "items[1].verdicts"),
    (practice(verdicts=["correct", "wrong"]), "items[1].verdicts[2]"),
    (practice(verdicts=["maybe"]), "items[1].verdicts[1]"),
    (practice(verdicts="wrong"), "items[1].verdicts"),
    (practice(source="past-papers/2024-final.pdf"), "items[1].source"),
    (practice(page=3), "items[1].page"),
    (practice(question="Q2"), "items[1].question"),
    ({"topic": "t", "origin": "generated"}, "items[1].origin"),
    ({"topic": "t"}, "items[1].origin"),
    ({"origin": "practice"}, "items[1].topic"),
    (practice(topic=""), "items[1].topic"),
    (practice(topic="x" * 121), "items[1].topic"),
    (practice(topic="two\nlines"), "items[1].topic"),
    (practice(topic="bell\x07"), "items[1].topic"),
    (real(question="Q" * 41), "items[1].question"),
    (practice(dispute="d" * 121), "items[1].dispute"),
    (practice(dispute=3), "items[1].dispute"),
    (practice(label="[real: x, p.1]"), "items[1]: unknown field"),
    (practice(quote={"path": "slides/s1.pdf"}), "items[1].quote.page"),
    (practice(quote={"page": 1}), "items[1].quote.path"),
    (practice(quote={"path": "slides/s1.pdf", "page": 1, "question": "Q1"}), "items[1].quote: unknown field"),
    (practice(quote="slides/s1.pdf p.1"), "items[1].quote"),
    (practice(compare={"path": "slides/s1.pdf", "page": -1}), "items[1].compare.page"),
    (practice(compare={"path": "slides/s1.pdf", "page": 1, "question": "Q" * 41}), "items[1].compare.question"),
    (practice(compare={"path": "slides/s1.pdf", "page": 1, "x": 1}), "items[1].compare: unknown field"),
    ("not an object", "items[1]"),
])
def test_bad_items_exit_2_naming_the_field(home, cdir, item, needle):
    fails(home, gate(item), needle)


def test_error_names_the_right_item_number(home, cdir):
    fails(home, gate(practice(), practice(), real(source="slides/s1.pdf", page=1)), "items[3].source")


@pytest.mark.parametrize("payload,needle", [
    ({"term": TERM, "course": COURSE}, "items is required"),
    ({"term": TERM, "course": COURSE, "items": []}, "items is required"),
    ({"term": TERM, "course": COURSE, "items": {}}, "items is required"),
    ({"term": TERM, "course": COURSE, "items": [practice()], "extra": 1}, "unknown field"),
    ({"term": "Fall", "course": COURSE, "items": [practice()]}, "term"),
    ({"term": TERM, "course": "../x", "items": [practice()]}, "course"),
    ({"term": TERM, "course": "Other 101", "items": [practice()]}, "no course folder"),
])
def test_bad_payload(home, cdir, payload, needle):
    fails(home, payload, needle)


def test_requires_workspace(home):
    fails(home, gate(practice()), "no workspace")


@pytest.mark.parametrize("which", ["term", "course", "state"])
def test_symlinked_folders_refused(home, root, tmp_path, which):
    cdir = course(home, root, rows=ROWS)
    elsewhere = tmp_path / "elsewhere"
    target = {"term": root / TERM, "course": cdir, "state": cdir / ".state"}[which]
    target.rename(elsewhere)
    target.symlink_to(elsewhere)
    fails(home, gate(practice()), "is a symlink")


def test_non_utf8_index_refused(home, cdir):
    (cdir / "INDEX.md").write_bytes(b"\xff\xfe broken")
    fails(home, gate(practice()), "not valid UTF-8")


def test_missing_index_has_no_rows(home, cdir):
    (cdir / "INDEX.md").unlink()
    assert one(home, practice())["decision"] == "verify"
    fails(home, gate(real()), "items[1].source")
    assert not (cdir / "INDEX.md").exists()


def test_writes_nothing(home, root, cdir):
    (cdir / "INDEX.md").write_text((cdir / "INDEX.md").read_text().replace("## Registry\n", "## registry\n\n"))
    before = snapshot(root)
    ok(home, gate(practice(), real(), real(source="past-papers/photo.jpg", page=1),
                  practice(verdicts=["wrong", "wrong"], compare=COMPARE),
                  practice(verdicts=["wrong", "wrong"])))
    fails(home, gate(real(source="slides/s1.pdf", page=1)))
    assert snapshot(root) == before


# --- contract ----------------------------------------------------------------------

@pytest.mark.parametrize("raw", [b"", b"not json", b"[1]", b"\xff\xfe", b'"x"'])
def test_bad_json_exits_2(home, cdir, raw):
    fails(home, raw)


@pytest.mark.parametrize("argv", [["check"], [], ["gate", "extra"]])
def test_usage_errors_are_one_line(home, argv):
    proc = subprocess.run([sys.executable, str(VF), *argv], input=b"{}", capture_output=True,
                          env={**os.environ, "HOME": str(home)})
    assert proc.returncode == 2 and proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("verify.py: ") and err.count("\n") == 1, err


def test_help_still_works():
    proc = subprocess.run([sys.executable, str(VF), "-h"], capture_output=True)
    assert proc.returncode == 0 and b"gate" in proc.stdout


def test_internal_error_exits_1(home, monkeypatch, capsys):
    def boom(data):
        raise KeyError("bug")

    monkeypatch.setitem(verify.COMMANDS, "gate", (boom, "x"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    assert verify.main(["gate"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "verify.py: internal error (KeyError)\n"


def test_stdlib_plus_workspace_and_ingest_only():
    tree = ast.parse(VF.read_text())
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            tops.add(node.module.split(".")[0])
    assert {"workspace", "ingest"} <= tops
    assert tops - {"workspace", "ingest"} <= set(sys.stdlib_module_names) | {"__future__"}, tops
