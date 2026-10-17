"""Boundary tests for scripts/fingerprint.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
FP = SCRIPTS / "fingerprint.py"
WS = SCRIPTS / "workspace.py"
TEMPLATES = ROOT_DIR / "assets" / "templates"

sys.path.insert(0, str(SCRIPTS))
import fingerprint  # noqa: E402
import workspace  # noqa: E402

OLD, NEW, COURSE = "2026-Fall", "2027-Spring", "CS201 Theory"


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
    proc = _run(FP, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b"" and proc.stdout.count(b"\n") == 1
    out = json.loads(proc.stdout)
    assert isinstance(out["line"], str) and out["line"]
    return out


def fails(home: Path, cmd: str, payload, needle: str = "") -> str:
    proc = _run(FP, home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("fingerprint.py: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def ws_ok(home: Path, cmd: str, payload) -> dict:
    proc = _run(WS, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    return json.loads(proc.stdout)


def course(home: Path, root: Path, term: str = OLD, name: str = COURSE, rows=()) -> Path:
    """A course tree whose INDEX registry holds ``rows`` of (path, role, fidelity)."""
    ws_ok(home, "course", {"term": term, "course": name})
    cdir = root / term / name
    index = cdir / "INDEX.md"
    lines = index.read_text().splitlines()
    at = lines.index("## Topics") - 1
    lines[at:at] = [f"| {p.replace('|', chr(92) + '|')} | {term} | {r} | 3 | {f} |" for p, r, f in rows]
    index.write_text("\n".join(lines) + "\n")
    return cdir


def fp_text(cdir: Path) -> str:
    return (cdir / ".state" / "fingerprint.md").read_text()


def bullets(cdir: Path) -> list[str]:
    return [l for l in fp_text(cdir).splitlines() if l.startswith("- ")]


def table(cdir: Path) -> list[str]:
    return [l for l in fp_text(cdir).splitlines() if l.startswith("|")][2:]


def key(cdir: Path, name: str) -> str:
    return next(l for l in fp_text(cdir).splitlines() if l.startswith(f"{name}:"))


def snapshot(root: Path) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            out[str(p)] = os.readlink(p) if p.is_symlink() else (p.read_bytes() if p.is_file() else None)
    return out


PAPERS = [("past-papers/ocr.pdf", "past-papers", "ocr"), ("past-papers/text.pdf", "past-papers", "text"),
          ("past-papers/p3.pdf", "past-papers", "text"), ("slides/s1.pdf", "slides", "text"),
          ("notes/photo.jpg", "notes", "ocr")]


def write(term=OLD, **kw) -> dict:
    return {"term": term, "course": COURSE, **kw}


# --- template ----------------------------------------------------------------------

def test_template_has_prior_term_after_professor():
    keys = [l.split(":")[0] for l in (TEMPLATES / "fingerprint.md").read_text().splitlines()
            if l.split(":")[0] in ("label", "professor", "prior_term")]
    assert keys == ["label", "professor", "prior_term"]
    inst = workspace.instance_template((TEMPLATES / "fingerprint.md").read_text()).splitlines()
    assert inst[3:6] == ["label:", "professor:", "prior_term:"]
    assert "(source: <file>; <file>)" in (TEMPLATES / "fingerprint.md").read_text()


def test_constants_are_the_spec_values():
    assert fingerprint.FINGERPRINT_MAX_LINES == 60
    assert fingerprint.ENTRY_MAX_CHARS == 160


# --- write: markers and frequency --------------------------------------------------

def test_ocr_paper_entry_is_tentative(root, home):
    cdir = course(home, root, rows=PAPERS)
    out = ok(home, "write", write(notation=[{"text": "Uses := for definitions", "sources": ["past-papers/ocr.pdf"]}]))
    assert bullets(cdir) == ["- Uses := for definitions (source: past-papers/ocr.pdf) (tentative)"]
    assert out["tentative"] == 1 and out["label"] == "current term"
    assert key(cdir, "label") == "label: current term"


@pytest.mark.parametrize("extra", ["past-papers/text.pdf", "debrief 2027-01-20", "slides/s1.pdf"])
def test_text_or_debrief_source_confirms(root, home, extra):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(phrasing=[{"text": "Says 'show' for proofs", "sources": ["past-papers/ocr.pdf", extra]}]))
    assert bullets(cdir) == [f"- Says 'show' for proofs (source: past-papers/ocr.pdf; {extra})"]


def test_ocr_notes_only_is_tentative(root, home):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(disguises=[{"text": "Reversed direction", "sources": ["notes/photo.jpg", "notes/photo.jpg"]}]))
    assert bullets(cdir) == ["- Reversed direction (source: notes/photo.jpg) (tentative)"]  # duplicates merged


def test_question_types_frequency_and_escaping(root, home):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(question_types=[
        {"type": "a|b", "sources": ["past-papers/ocr.pdf", "past-papers/text.pdf", "slides/s1.pdf"], "marks": "20|25"},
        {"type": "DFA design", "sources": ["past-papers/p3.pdf"], "marks": "10"}]))
    assert table(cdir) == [
        "| a\\|b (source: past-papers/ocr.pdf; past-papers/text.pdf; slides/s1.pdf) | 2 of 3 papers | 20\\|25 |",
        "| DFA design (source: past-papers/p3.pdf) | 1 of 3 papers | 10 |"]


def test_debrief_counts_as_a_paper_and_slides_only_gives_dash(root, home):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(question_types=[{"type": "Proof", "sources": ["debrief 2027-01-20"], "marks": "30"}]))
    assert table(cdir) == ["| Proof (source: debrief 2027-01-20) | 1 of 1 papers | 30 |"]
    ok(home, "write", write(question_types=[{"type": "Proof", "sources": ["slides/s1.pdf"]}]))
    assert table(cdir) == ["| Proof (source: slides/s1.pdf) | - |  |"]


def test_markers_are_never_input(root, home):
    course(home, root, rows=PAPERS)
    fails(home, "write", write(notation=[{"text": "x", "sources": ["past-papers/ocr.pdf"], "tentative": False}]),
          "unknown field")
    fails(home, "write", write(question_types=[{"type": "x", "sources": ["past-papers/ocr.pdf"],
                                                "frequency": "3 of 3"}]), "unknown field")


def test_render_shape(root, home):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(notation=[{"text": "n", "sources": ["slides/s1.pdf"]}],
                            question_types=[{"type": "t", "sources": ["past-papers/p3.pdf"], "marks": "5"}]))
    template_comment = (TEMPLATES / "fingerprint.md").read_text().splitlines()[0]
    assert fp_text(cdir).splitlines() == [
        template_comment, "# Fingerprint", "", "label: current term", "professor:", "prior_term:", "",
        "## Notation", "- n (source: slides/s1.pdf)", "", "## Phrasing", "", "## Disguise types", "",
        "## Question types", "| type | frequency | marks |", "|---|---|---|",
        "| t (source: past-papers/p3.pdf) | 1 of 1 papers | 5 |"]


def test_empty_write_matches_fresh_instance_shape(root, home):
    cdir = course(home, root)
    fresh = fp_text(cdir)
    ok(home, "write", write())
    assert fp_text(cdir) == fresh.replace("label:\n", "label: current term\n")


def test_professor_kept_set_or_unknown_and_prior_term_kept(root, home):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(professor="Dr. Ayse Kaya"))
    assert key(cdir, "professor") == "professor: Dr. Ayse Kaya"
    ok(home, "write", write())
    assert key(cdir, "professor") == "professor: Dr. Ayse Kaya"
    ok(home, "write", write(professor=""))
    assert key(cdir, "professor") == "professor: unknown"
    path = cdir / ".state" / "fingerprint.md"
    path.write_text(path.read_text().replace("prior_term:", "prior_term: 2025-Fall/CS201 Theory, another "
                                                           "professor's papers"))
    ok(home, "write", write(notation=[{"text": "n", "sources": ["slides/s1.pdf"]}]))
    assert key(cdir, "prior_term") == "prior_term: 2025-Fall/CS201 Theory, another professor's papers"
    assert key(cdir, "label") == "label: current term"


def test_write_restores_missing_fingerprint(root, home):
    cdir = course(home, root, rows=PAPERS)
    (cdir / ".state" / "fingerprint.md").unlink()
    ok(home, "write", write(notation=[{"text": "n", "sources": ["slides/s1.pdf"]}]))
    assert bullets(cdir) == ["- n (source: slides/s1.pdf)"]


# --- write: cap and bad input ------------------------------------------------------

def _entries(n: int) -> list[dict]:
    return [{"text": f"entry {i}", "sources": ["slides/s1.pdf"]} for i in range(n)]


def test_cap_at_60_passes(root, home):
    cdir = course(home, root, rows=PAPERS)
    out = ok(home, "write", write(notation=_entries(44)))
    assert out["lines"] == 60 and len(fp_text(cdir).splitlines()) == 60


def test_over_cap_exits_2_with_count_and_file_unchanged(root, home):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(notation=_entries(3)))
    before = fp_text(cdir)
    fails(home, "write", write(notation=_entries(45)), "would be 61 lines, over the 60-line cap")
    assert fp_text(cdir) == before


@pytest.mark.parametrize("payload, needle", [
    (write(notation=[{"text": "x", "sources": ["past-papers/nope.pdf"]}]), "notation[1].sources[1]"),
    (write(phrasing=[{"text": "x", "sources": ["slides/s1.pdf", "prior-term:past-papers/text.pdf"]}]),
     "phrasing[1].sources[2]"),
    (write(disguises=[{"text": "x", "sources": ["debrief 2027-02-30"]}]), "disguises[1].sources[1]"),
    (write(disguises=[{"text": "x", "sources": ["/abs/past-papers/text.pdf"]}]), "disguises[1].sources[1]"),
    (write(question_types=[{"type": "x", "sources": ["slides/s1.pdf"]}, {"type": "y", "sources": ["s.pdf"]}]),
     "question_types[2].sources[1]"),
    (write(notation=[{"text": "x", "sources": []}]), "notation[1].sources is required"),
    (write(notation=[{"text": "x"}]), "notation[1].sources is required"),
    (write(notation=[{"text": "", "sources": ["slides/s1.pdf"]}]), "notation[1].text is required"),
    (write(notation=[{"text": "a\nb", "sources": ["slides/s1.pdf"]}]), "one line"),
    (write(notation=[{"text": "x" * 161, "sources": ["slides/s1.pdf"]}]), "longer than 160"),
    (write(question_types=[{"type": "t", "sources": ["slides/s1.pdf"], "marks": "m" * 161}]), "longer than 160"),
    (write(professor="P" * 161), "longer than 160"),
    (write(professor="a\tb"), "one line"),
    (write(notation={"text": "x"}), "notation must be a list"),
    (write(notation=["x"]), "notation[1] must be an object"),
    (write(extra=1), "unknown field"),
    ({"term": "Fall", "course": COURSE}, "term must be"),
    ({"term": OLD, "course": "Nope"}, "no course folder"),
])
def test_bad_write_input_changes_nothing(root, home, payload, needle):
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(notation=[{"text": "keep", "sources": ["slides/s1.pdf"]}]))
    before = snapshot(root)
    fails(home, "write", payload, needle)
    assert snapshot(root) == before
    assert bullets(cdir) == ["- keep (source: slides/s1.pdf)"]


def test_pipe_in_registry_path_matches(root, home):
    cdir = course(home, root, rows=[("past-papers/a|b.pdf", "past-papers", "text")])
    ok(home, "write", write(notation=[{"text": "n", "sources": ["past-papers/a|b.pdf"]}]))
    assert bullets(cdir) == ["- n (source: past-papers/a|b.pdf)"]


def test_index_is_never_changed(root, home):
    cdir = course(home, root, rows=PAPERS)
    index = cdir / "INDEX.md"
    index.write_text("# INDEX\n\n## Registry\n| past-papers/text.pdf | 2026-Fall | past-papers | 3 | text |\n")
    before = index.read_bytes()
    ok(home, "write", write(notation=[{"text": "n", "sources": ["past-papers/text.pdf"]}]))
    assert index.read_bytes() == before


# --- retake ------------------------------------------------------------------------

def retake(professor: str, prior_term: str = OLD, term: str = NEW, prior_course: str = COURSE) -> dict:
    return {"term": term, "course": COURSE, "prior_term": prior_term, "prior_course": prior_course,
            "professor": professor}


@pytest.fixture
def prior(root, home) -> Path:
    cdir = course(home, root, rows=PAPERS)
    ok(home, "write", write(professor="dr ayse kaya", notation=[
        {"text": "Uses := for definitions", "sources": ["past-papers/text.pdf"]},
        {"text": "Sigma for alphabets", "sources": ["past-papers/ocr.pdf"]}]))
    return cdir


def test_same_professor_links_relative_and_carries(root, home, prior):
    out = ok(home, "retake", retake("Dr. Ayse  Kaya"))
    new = root / NEW / COURSE
    link = new / ".state" / "prior-term"
    assert link.is_symlink() and not os.path.isabs(os.readlink(link))
    assert link.resolve() == (prior / ".state").resolve()
    assert out["same_professor"] is True and out["assumed"] is False and out["carry"] is True
    assert out["prior_fingerprint"] == str(prior / ".state" / "fingerprint.md")
    assert key(new, "prior_term") == "prior_term: 2026-Fall/CS201 Theory, same professor"
    assert key(new, "professor") == "professor: Dr. Ayse  Kaya"
    assert "Same professor" in out["line"] and "prior term" in out["line"]
    assert (new / "INDEX.md").is_file()  # course built
    # carried entries: prior-term sources validate against the prior INDEX and get (prior term)
    w = ok(home, "write", write(NEW, notation=[
        {"text": "Uses := for definitions", "sources": ["prior-term:past-papers/text.pdf"]},
        {"text": "Sigma for alphabets", "sources": ["prior-term:past-papers/ocr.pdf"]}]))
    assert bullets(new) == ["- Uses := for definitions (source: prior-term:past-papers/text.pdf) (prior term)",
                            "- Sigma for alphabets (source: prior-term:past-papers/ocr.pdf) (tentative) (prior term)"]
    assert key(new, "label") == "label: prior term (2026-Fall)" and w["label"] == "prior term (2026-Fall)"
    assert key(new, "prior_term") == "prior_term: 2026-Fall/CS201 Theory, same professor"


def test_carried_entry_confirmed_this_term_drops_prior_marker(root, home, prior):
    ok(home, "retake", retake(""))
    new = course(home, root, term=NEW, rows=[("past-papers/2027.pdf", "past-papers", "text")])
    ok(home, "write", write(NEW, question_types=[
        {"type": "Proof", "sources": ["prior-term:past-papers/ocr.pdf", "past-papers/2027.pdf"], "marks": "20"},
        {"type": "DFA", "sources": ["prior-term:past-papers/p3.pdf"], "marks": "10"}]))
    assert table(new) == [
        "| Proof (source: prior-term:past-papers/ocr.pdf; past-papers/2027.pdf) | 2 of 3 papers | 20 |",
        "| DFA (source: prior-term:past-papers/p3.pdf) (prior term) | 1 of 3 papers | 10 |"]
    assert key(new, "label") == "label: prior term (2026-Fall)"
    ok(home, "write", write(NEW, question_types=[{"type": "Proof", "sources": ["past-papers/2027.pdf"]}]))
    assert key(new, "label") == "label: current term"


def test_other_professor(root, home, prior):
    out = ok(home, "retake", retake("Prof. John Smith"))
    new = root / NEW / COURSE
    assert out["same_professor"] is False and out["carry"] is False and out["assumed"] is False
    assert key(new, "prior_term") == "prior_term: 2026-Fall/CS201 Theory, another professor's papers"
    assert key(new, "professor") == "professor: Prof. John Smith"
    assert "another professor's papers" in out["line"]
    assert (new / ".state" / "prior-term").is_symlink()
    fails(home, "write", write(NEW, notation=[{"text": "x", "sources": ["prior-term:past-papers/text.pdf"]}]),
          "notation[1].sources[1]")


def test_no_name_assumes_same_professor(root, home, prior):
    out = ok(home, "retake", retake(""))
    new = root / NEW / COURSE
    assert out["same_professor"] is True and out["assumed"] is True and out["carry"] is True
    assert "assuming the same professor" in out["line"]
    assert key(new, "prior_term") == "prior_term: 2026-Fall/CS201 Theory, same professor (assumed)"
    assert key(new, "professor") == "professor: dr ayse kaya"  # the prior's name


def test_unknown_prior_professor_assumes_same(root, home):
    course(home, root, rows=PAPERS)
    out = ok(home, "retake", retake("Dr. New"))
    assert out["same_professor"] is True and out["assumed"] is True
    assert out["carry"] is False  # the prior fingerprint has no entries
    assert "Carrying" not in out["line"]
    assert key(root / NEW / COURSE, "professor") == "professor: Dr. New"
    assert "has no professor name" in out["line"]


def test_no_name_anywhere_writes_unknown(root, home):
    course(home, root)
    (root / OLD / COURSE / ".state" / "fingerprint.md").unlink()
    out = ok(home, "retake", retake(""))
    assert out["assumed"] is True and out["carry"] is False and out["prior_fingerprint"] is None
    assert key(root / NEW / COURSE, "professor") == "professor: unknown"


@pytest.mark.parametrize("first", ["Prof. John Smith", "Dr Ayse Kaya", ""])
def test_rerun_without_name_keeps_decision(root, home, prior, first):
    first_out = ok(home, "retake", retake(first))
    new = root / NEW / COURSE
    before = fp_text(new)
    out = ok(home, "retake", retake(""))
    assert fp_text(new) == before
    assert (out["same_professor"], out["assumed"]) == (first_out["same_professor"], first_out["assumed"])
    assert out["carry"] is False and "Carrying" not in out["line"]  # nothing new to carry on a rerun


def test_rerun_with_name_redecides_and_keeps_entries(root, home, prior):
    ok(home, "retake", retake(""))
    new = root / NEW / COURSE
    ok(home, "write", write(NEW, notation=[{"text": "x", "sources": ["prior-term:past-papers/text.pdf"]}]))
    out = ok(home, "retake", retake("Dr. Ayse Kaya"))
    assert out["assumed"] is False and out["same_professor"] is True
    assert key(new, "prior_term") == "prior_term: 2026-Fall/CS201 Theory, same professor"
    assert bullets(new) == ["- x (source: prior-term:past-papers/text.pdf) (prior term)"]


def test_retake_into_existing_course_without_prior_term_line(root, home, prior):
    new = course(home, root, term=NEW)
    path = new / ".state" / "fingerprint.md"
    path.write_text("\n".join(l for l in path.read_text().splitlines() if not l.startswith("prior_term")) + "\n")
    ok(home, "retake", retake("Dr. Ayse Kaya"))
    lines = fp_text(new).splitlines()
    assert lines[lines.index("professor: Dr. Ayse Kaya") + 1] == \
        "prior_term: 2026-Fall/CS201 Theory, same professor"


def test_link_survives_relocate(root, home, prior, tmp_path):
    ok(home, "retake", retake(""))
    target = tmp_path / "elsewhere" / "uni"
    ws_ok(home, "relocate", {"to": str(target)})
    link = target / NEW / COURSE / ".state" / "prior-term"
    assert link.is_symlink() and (link / "fingerprint.md").is_file()
    assert link.resolve() == (target / OLD / COURSE / ".state").resolve()


def test_retake_never_writes_through_link(root, home, prior):
    before = snapshot(prior)
    ok(home, "retake", retake("Dr. Ayse Kaya"))
    ok(home, "retake", retake(""))
    ok(home, "write", write(NEW, notation=[{"text": "x", "sources": ["prior-term:past-papers/text.pdf"]}]))
    assert snapshot(prior) == before


@pytest.mark.parametrize("setup, payload, needle", [
    (None, retake("x", prior_term=NEW), "same term"),
    (None, retake("x", prior_term="2025-Fall"), "no prior course folder"),
    (None, retake("x", prior_course="MA101 Calc"), "no prior course folder"),
    ("no_state", retake("x"), "no .state/"),
    ("foreign_link", retake("x"), "already exists and is not a link"),
    ("foreign_dir", retake("x"), "already exists and is not a link"),
    ("abs_link", retake("x"), "already exists and is not a link"),
    ("symlink_prior", retake("x"), "is a symlink"),
    ("symlink_course", retake("x"), "is a symlink"),
    (None, {k: v for k, v in retake("x").items() if k != "professor"}, "professor is required"),
    (None, retake("a\nb"), "one line"),
    (None, retake("x", prior_term="Fall"), "prior_term must be"),
    (None, {**retake("x"), "extra": 1}, "unknown field"),
])
def test_retake_conflicts_change_nothing(root, home, prior, tmp_path, setup, payload, needle):
    new_state = root / NEW / COURSE / ".state"
    if setup == "no_state":
        course(home, root, term=OLD, name="MA101 Calc")
        import shutil
        shutil.rmtree(root / OLD / "MA101 Calc" / ".state")
        payload = {**payload, "prior_course": "MA101 Calc"}
    elif setup in ("foreign_link", "foreign_dir", "abs_link"):
        course(home, root, term=NEW)
        other = course(home, root, term="2025-Fall")
        if setup == "foreign_link":
            (new_state / "prior-term").symlink_to(os.path.relpath(other / ".state", new_state))
        elif setup == "foreign_dir":
            (new_state / "prior-term").mkdir()
        else:
            (new_state / "prior-term").symlink_to(prior / ".state")
    elif setup == "symlink_prior":
        real = tmp_path / "real-course"
        real.mkdir()
        (real / ".state").mkdir()
        (root / OLD / "Linked").symlink_to(real)
        payload = {**payload, "prior_course": "Linked"}
    elif setup == "symlink_course":
        (root / NEW).mkdir()
        real = tmp_path / "real-new"
        real.mkdir()
        (root / NEW / COURSE).symlink_to(real)
    before = snapshot(root)
    fails(home, "retake", payload, needle)
    assert snapshot(root) == before


def test_retake_keeps_existing_link(root, home, prior):
    ok(home, "retake", retake("Dr. Ayse Kaya"))
    link = root / NEW / COURSE / ".state" / "prior-term"
    before = os.lstat(link).st_ino
    ok(home, "retake", retake("Dr. Ayse Kaya"))
    assert os.lstat(link).st_ino == before


# --- contract ----------------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["write", "retake"])
def test_requires_workspace(home, cmd):
    payload = write() if cmd == "write" else retake("")
    fails(home, cmd, payload, "no workspace")


@pytest.mark.parametrize("cmd", ["write", "retake"])
@pytest.mark.parametrize("raw", [b"", b"not json", b"[1]", b"\xff\xfe", b'"x"'])
def test_bad_json_exits_2(root, home, cmd, raw):
    fails(home, cmd, raw)


@pytest.mark.parametrize("argv", [["carry"], [], ["write", "extra"]])
def test_usage_errors_are_one_line(home, argv):
    proc = subprocess.run([sys.executable, str(FP), *argv], input=b"{}", capture_output=True,
                          env={**os.environ, "HOME": str(home)})
    assert proc.returncode == 2 and proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("fingerprint.py: ") and err.count("\n") == 1, err


def test_help_still_works():
    proc = subprocess.run([sys.executable, str(FP), "-h"], capture_output=True)
    assert proc.returncode == 0 and b"write" in proc.stdout and b"retake" in proc.stdout


def test_internal_error_exits_1(home, monkeypatch, capsys):
    def boom(data):
        raise KeyError("bug")

    monkeypatch.setitem(fingerprint.COMMANDS, "write", (boom, "x"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    assert fingerprint.main(["write"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "fingerprint.py: internal error (KeyError)\n"


def test_non_utf8_fingerprint_refused(root, home):
    cdir = course(home, root, rows=PAPERS)
    path = cdir / ".state" / "fingerprint.md"
    path.write_bytes(b"\xff\xfe broken")
    fails(home, "write", write(), "not valid UTF-8")
    assert path.read_bytes() == b"\xff\xfe broken"


def test_symlinked_course_refused_for_write(root, home, tmp_path):
    cdir = course(home, root, name="Real")
    (root / OLD / COURSE).symlink_to(cdir)
    fails(home, "write", write(), "is a symlink")


def test_stdlib_plus_workspace_and_ingest_only():
    tree = ast.parse(FP.read_text())
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            tops.add(node.module.split(".")[0])
    assert {"workspace", "ingest"} <= tops
    assert tops - {"workspace", "ingest"} <= set(sys.stdlib_module_names) | {"__future__"}, tops


# --- review fixes ------------------------------------------------------------------

def test_retake_rolls_back_everything_on_failure(root, home, prior, monkeypatch, capsys):
    before = snapshot(root)

    def broken(path, text):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(fingerprint.ingest, "_write_atomic", broken)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(retake("Dr. Ayse Kaya")).encode())))
    assert fingerprint.main(["retake"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith("fingerprint.py: filesystem error")
    assert snapshot(root) == before
    assert not (root / NEW).exists()


def test_retake_rollback_keeps_an_existing_course(root, home, prior, monkeypatch, capsys):
    new = course(home, root, term=NEW)
    before = snapshot(root)
    monkeypatch.setattr(fingerprint.ingest, "_write_atomic",
                        lambda path, text: (_ for _ in ()).throw(OSError(13, "Permission denied")))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(retake("")).encode())))
    assert fingerprint.main(["retake"]) == 2
    capsys.readouterr()
    assert snapshot(root) == before and not (new / ".state" / "prior-term").is_symlink()


@pytest.mark.parametrize("cmd", ["write", "retake"])
def test_symlinked_fingerprint_refused(root, home, prior, tmp_path, cmd):
    new = course(home, root, term=NEW)
    if cmd == "write":
        ok(home, "retake", retake(""))
    path = new / ".state" / "fingerprint.md"
    real = tmp_path / "elsewhere.md"
    real.write_text("outside\n")
    path.unlink()
    path.symlink_to(real)
    before = snapshot(root)
    fails(home, cmd, write(NEW) if cmd == "write" else retake("Dr. Ayse Kaya"), "is a symlink")
    assert snapshot(root) == before and real.read_text() == "outside\n"
    assert os.readlink(path) == str(real)


@pytest.mark.parametrize("prior_term, needle", [("2027-spring", "same term"), ("2028-Fall", "later than"),
                                                ("2028-Spring", "later than")])
def test_retake_refuses_same_or_later_term(root, home, prior, prior_term, needle):
    course(home, root, term=prior_term)
    before = snapshot(root)
    fails(home, "retake", retake("x", prior_term=prior_term), needle)
    assert snapshot(root) == before


def test_retake_same_year_other_word_allowed(root, home):
    course(home, root, term="2027-Fall")
    out = ok(home, "retake", retake("", prior_term="2027-Fall", term="2027-Spring"))
    assert out["same_professor"] is True


@pytest.mark.parametrize("given", ["unknown", " Unknown. "])
def test_retake_unknown_input_counts_as_no_name(root, home, prior, given):
    out = ok(home, "retake", retake(given))
    assert out["assumed"] is True and out["professor"] == "dr ayse kaya"


def test_retake_uses_professor_already_named_in_course(root, home, prior):
    new = course(home, root, term=NEW)
    ok(home, "write", write(NEW, professor="Prof. John Smith"))
    out = ok(home, "retake", retake(""))
    assert out["same_professor"] is False and out["assumed"] is False and out["carry"] is False
    assert key(new, "professor") == "professor: Prof. John Smith"
    assert key(new, "prior_term") == "prior_term: 2026-Fall/CS201 Theory, another professor's papers"


def test_carry_only_when_new_or_newly_same(root, home, prior):
    first = ok(home, "retake", retake("Prof. John Smith"))
    assert first["carry"] is False
    switched = ok(home, "retake", retake("Dr. Ayse Kaya"))  # decision changes to same: carry now
    assert switched["carry"] is True and "Carrying" in switched["line"]
    again = ok(home, "retake", retake("Dr. Ayse Kaya"))  # already same: nothing new
    assert again["carry"] is False and "Carrying" not in again["line"]


def test_carry_counts_question_type_rows(root, home):
    course(home, root, rows=PAPERS)
    ok(home, "write", write(question_types=[{"type": "Proof", "sources": ["past-papers/text.pdf"]}]))
    assert ok(home, "retake", retake(""))["carry"] is True


@pytest.mark.parametrize("field, value, needle", [
    ("text", "Uses := (tentative)", "notation[1].text contains the reserved marker"),
    ("text", "x (source: past-papers/text.pdf)", "notation[1].text contains the reserved marker"),
    ("text", "x (Prior Term)", "notation[1].text contains the reserved marker"),
])
def test_write_rejects_reserved_markers_in_text(root, home, field, value, needle):
    course(home, root, rows=PAPERS)
    fails(home, "write", write(notation=[{field: value, "sources": ["slides/s1.pdf"]}]), needle)


@pytest.mark.parametrize("row, needle", [
    ({"type": "Proof (prior term)", "sources": ["slides/s1.pdf"]}, "question_types[1].type"),
    ({"type": "Proof", "sources": ["slides/s1.pdf"], "marks": "20 (tentative)"}, "question_types[1].marks"),
])
def test_write_rejects_reserved_markers_in_rows(root, home, row, needle):
    course(home, root, rows=PAPERS)
    fails(home, "write", write(question_types=[row]), needle)


@pytest.mark.parametrize("damage", ["missing", "elsewhere", "absolute_ok"])
def test_prior_term_sources_need_the_link(root, home, prior, damage):
    ok(home, "retake", retake("Dr. Ayse Kaya"))
    link = root / NEW / COURSE / ".state" / "prior-term"
    link.unlink()
    payload = write(NEW, notation=[{"text": "x", "sources": ["prior-term:past-papers/text.pdf"]}])
    if damage == "absolute_ok":  # an absolute link to the right place still resolves there
        link.symlink_to(prior / ".state")
        ok(home, "write", payload)
        return
    if damage == "elsewhere":
        other = course(home, root, term="2025-Fall")
        link.symlink_to(os.path.relpath(other / ".state", link.parent))
    fails(home, "write", payload, "notation[1].sources[1]")
