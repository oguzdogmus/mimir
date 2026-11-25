"""#101: base figures, grown on first use (run: uv run --with pytest pytest tests -q).

Driven from outside: JSON into fieldpack.py and visual.py, JSON and files out. Every figure here is
synthetic; a professor's real diagrams never enter the repo.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
FP = SCRIPTS / "fieldpack.py"
VISUAL = SCRIPTS / "visual.py"
WS = SCRIPTS / "workspace.py"
PACK = json.loads((ROOT_DIR / "tests" / "fixtures" / "field-pack-microbiology.json").read_text(encoding="utf-8"))
FIELD, FIGURE = PACK["field"], PACK["figure_kinds"][0]["name"]
TERM, COURSE, OTHER = "2026-Fall", "MICRO201 Bacteria", "MICRO305 Pathogens"
SUBJECT = "gram-negative-envelope"

PARTS = ('<g id="outer-membrane"><rect x="10" y="10" width="180" height="12" class="ink"/></g>'
         '<g id="peptidoglycan"><rect x="10" y="34" width="180" height="6" class="ink"/></g>'
         '<path id="inner-membrane" d="M 10 56 L 190 56" class="ink"/>')
BASE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120" role="img">'
        "<title>Gram-negative envelope</title>"
        "<desc>From outside in: the outer membrane, a thin peptidoglycan layer, the inner membrane.</desc>"
        f"{PARTS}</svg>")
PASS = "1 | pass | thin peptidoglycan layer under an outer membrane\noverall | pass | every item passes\n"
FAIL = "1 | fail | the peptidoglycan layer is as thick as the membranes\noverall | fail | item 1 fails\n"


# --- fixtures and helpers ----------------------------------------------------------

@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows ignores HOME
    return home


@pytest.fixture
def root(home):
    run_ok(WS, home, "init", {})
    run_ok(FP, home, "save", PACK)
    for course in (COURSE, OTHER):
        run_ok(WS, home, "course", {"term": TERM, "course": course})
        run_ok(FP, home, "link", {"term": TERM, "course": course, "field": FIELD})
    return home / "learning"


def _run(script: Path, home: Path, cmd: str, payload) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), cmd], input=json.dumps(payload).encode(),
                          capture_output=True, env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)})


def run_ok(script: Path, home: Path, cmd: str, payload) -> dict:
    proc = _run(script, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b"" and proc.stdout.count(b"\n") == 1
    out = json.loads(proc.stdout)
    assert isinstance(out["line"], str) and out["line"]
    return out


def run_fails(script: Path, home: Path, cmd: str, payload, needle: str = "") -> str:
    proc = _run(script, home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith(f"{script.name}: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def built(home: Path, svg: str = BASE, name: str = f"base-{SUBJECT}", course: str = COURSE) -> Path:
    """A candidate built by the shell, as the base figure builder builds it."""
    return Path(run_ok(VISUAL, home, "svg", {"term": TERM, "course": course, "name": name, "svg": svg})["path"])


def save(path: Path, reply: str = PASS, subject: str = SUBJECT) -> dict:
    return {"field": FIELD, "subject": subject, "figure": FIGURE, "path": str(path), "reply": reply}


def pack_base(root: Path, subject: str = SUBJECT) -> Path:
    return root / ".state" / "field-packs" / FIELD / "base-figures" / f"{subject}.svg"


def snapshot(root: Path) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            out[str(p)] = p.read_bytes() if p.is_file() else None
    return out


# --- save-base ----------------------------------------------------------------------

def test_a_built_figure_the_checker_passed_is_saved_in_its_pack_without_the_shell_tokens(home, root):
    """#101: saved only after the checker passes it; stored as the figure itself, without the 300 KB of tokens."""
    out = run_ok(FP, home, "save-base", save(built(home)))
    target = pack_base(root)
    assert out["path"] == str(target) and out["subject"] == SUBJECT and out["field"] == FIELD
    assert target.read_text(encoding="utf-8") == BASE
    assert out["parts"] == ["outer-membrane", "peptidoglycan", "inner-membrane"]
    assert SUBJECT in out["line"]


@pytest.mark.parametrize(("svg", "needle"), [
    (BASE.replace('<g id="peptidoglycan">', "<g>"), "belongs to no part: give it or its group a stable part id"),
    (BASE.replace('id="inner-membrane"', 'id="Inner_Membrane"'), "is not a stable part id"),
    (BASE.replace('id="inner-membrane"', 'id="sk-inner"'), "is reserved for the page"),
    (BASE.replace(PARTS, ""), "the base figure has no parts"),
])
def test_a_figure_without_stable_part_ids_is_refused_and_not_saved(home, root, svg, needle):
    """#101: every drawn shape belongs to a part with a stable id, or the figure is not saved."""
    path = built(home, svg)
    before = snapshot(root)
    err = run_fails(FP, home, "save-base", save(path), needle)
    assert str(path) in err
    assert snapshot(root) == before


def test_a_figure_that_fails_the_shell_svg_checks_is_refused_and_not_saved(home, root):
    """#101: a built candidate changed after the build is checked again, exactly as visual.py svg checks it."""
    path = built(home)
    path.write_text(path.read_text(encoding="utf-8").replace("</desc>", '</desc><image href="https://x.test/a.png"/>'),
                    encoding="utf-8")
    before = snapshot(root)
    run_fails(FP, home, "save-base", save(path), "element <image> is not allowed")
    assert snapshot(root) == before


def test_a_figure_the_shell_did_not_build_is_refused(home, root, tmp_path):
    raw = tmp_path / "raw.svg"
    raw.write_text(BASE, encoding="utf-8")
    run_fails(FP, home, "save-base", save(raw), "is not an SVG built by visual.py svg")
    assert not pack_base(root).parent.exists()


@pytest.mark.parametrize(("reply", "needle"), [
    (FAIL, "Figure check failed: 1 of 1 checklist item fail (1)"),
    ("1 | pass | fine\n", "no overall verdict line"),
    ("", "Figure check failed: 1 of 1 checklist item fail (1)"),
])
def test_a_figure_that_fails_its_checklist_is_refused_and_not_saved(home, root, reply, needle):
    """#101: saved only when every checklist item passes; the next need of the subject tries again."""
    path = built(home)
    before = snapshot(root)
    err = run_fails(FP, home, "save-base", save(path, reply), needle)
    assert f"the base figure {SUBJECT} is not saved" in err
    assert snapshot(root) == before
    run_ok(FP, home, "save-base", save(path))  # a later passing check saves it


def test_a_subject_with_a_base_figure_is_not_saved_again(home, root):
    path = built(home)
    run_ok(FP, home, "save-base", save(path))
    before = snapshot(root)
    run_fails(FP, home, "save-base", save(path), f"already has a base figure {SUBJECT}")
    assert snapshot(root) == before


@pytest.mark.parametrize(("change", "needle"), [
    ({"subject": "Human Heart"}, "subject must be lowercase letters"),
    ({"subject": "a" * 41}, "at most 40 characters"),
    ({"field": "civil-engineering"}, "no field pack 'civil-engineering'"),
    ({"figure": "truss"}, "figure 'truss' is not one of the figure kinds"),
    ({"path": "relative.svg"}, "path must be the absolute path of an .svg file"),
    ({"extra": 1}, "unknown field 'extra'"),
])
def test_save_base_refuses_bad_input_naming_the_field(home, root, change, needle):
    run_fails(FP, home, "save-base", {**save(built(home)), **change}, needle)
    assert not pack_base(root).parent.exists()


# --- find-base and the professor's diagrams ------------------------------------------

PROFESSOR = BASE.replace("Gram-negative envelope</title>", "Gram-negative envelope, as in lecture 3</title>").replace(
    'width="180" height="12"', 'width="180" height="16"')


def find(subject: str = SUBJECT, course: str = COURSE) -> dict:
    return {"term": TERM, "course": course, "subject": subject}


def professor_diagram(root: Path, svg: str = PROFESSOR, course: str = COURSE) -> Path:
    slides = root / TERM / course / "slides"
    slides.mkdir(exist_ok=True)
    path = slides / "envelope.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def local(path: Path, subject: str = SUBJECT) -> dict:
    return {"term": TERM, "course": COURSE, "subject": subject, "path": str(path)}


def test_a_subject_with_no_base_figure_is_missing(home, root):
    out = run_ok(FP, home, "find-base", find())
    assert out["status"] == "missing" and out["subject"] == SUBJECT and out["path"] is None
    assert SUBJECT in out["line"]


def test_a_saved_base_figure_is_found_for_every_course_of_its_field(home, root):
    run_ok(FP, home, "save-base", save(built(home)))
    for course in (COURSE, OTHER):
        out = run_ok(FP, home, "find-base", find(course=course))
        assert out["status"] == "found" and out["source"] == "pack" and out["field"] == FIELD
        assert out["path"] == str(pack_base(root))
        assert out["parts"] == ["outer-membrane", "peptidoglycan", "inner-membrane"]


def test_a_professors_diagram_is_the_courses_base_figure_before_the_packs_and_stays_in_the_course(home, root):
    """#101: the professor wins for that course only; the diagram never leaves the course folder."""
    run_ok(FP, home, "save-base", save(built(home)))
    store = snapshot(root / ".state")
    other = snapshot(root / TERM / OTHER)
    out = run_ok(FP, home, "save-course-base", local(professor_diagram(root)))
    target = root / TERM / COURSE / ".state" / "base-figures" / f"{SUBJECT}.svg"
    assert out["path"] == str(target) and target.read_text(encoding="utf-8") == PROFESSOR
    assert snapshot(root / ".state") == store and snapshot(root / TERM / OTHER) == other

    mine = run_ok(FP, home, "find-base", find())
    assert mine["status"] == "found" and mine["source"] == "course" and mine["field"] is None
    assert mine["path"] == str(target)
    theirs = run_ok(FP, home, "find-base", find(course=OTHER))
    assert theirs["source"] == "pack" and theirs["path"] == str(pack_base(root))


def test_a_professors_diagram_is_used_even_when_the_pack_has_no_base_figure(home, root):
    run_ok(FP, home, "save-course-base", local(professor_diagram(root)))
    assert run_ok(FP, home, "find-base", find())["source"] == "course"
    assert run_ok(FP, home, "find-base", find(course=OTHER))["status"] == "missing"


def test_a_diagram_from_outside_the_course_folder_is_refused(home, root, tmp_path):
    outside = tmp_path / "envelope.svg"
    outside.write_text(PROFESSOR, encoding="utf-8")
    elsewhere = professor_diagram(root, course=OTHER)
    for path in (outside, elsewhere):
        run_fails(FP, home, "save-course-base", local(path), "must be inside the course folder")
    assert not (root / TERM / COURSE / ".state" / "base-figures").exists()


def test_a_professors_diagram_without_stable_part_ids_is_refused(home, root):
    path = professor_diagram(root, PROFESSOR.replace('<g id="peptidoglycan">', "<g>"))
    run_fails(FP, home, "save-course-base", local(path), "belongs to no part")
    assert not (root / TERM / COURSE / ".state" / "base-figures").exists()


def test_a_damaged_stored_base_figure_is_refused_naming_its_file(home, root):
    run_ok(FP, home, "save-base", save(built(home)))
    pack_base(root).write_text(BASE.replace('id="inner-membrane"', ""), encoding="utf-8")
    err = run_fails(FP, home, "find-base", find(), "belongs to no part")
    assert str(pack_base(root)) in err and "damaged" in err


# --- reuse: a later build starts from the base figure --------------------------------

LABELS = ('<path class="leader" d="M 150 16 L 150 88"/><circle class="anchor" cx="150" cy="16" r="2"/>'
          '<text x="100" y="106" text-anchor="middle">Outer membrane</text>')
REUSE = BASE.replace("</svg>", LABELS + "</svg>")


def reuse(svg: str = REUSE, course: str = COURSE, base: str = SUBJECT) -> dict:
    return {"term": TERM, "course": course, "name": "envelope-labelled", "svg": svg, "base": base}


def figure_in_page(svg: str) -> dict:
    inline = svg.replace(' xmlns="http://www.w3.org/2000/svg"', "")
    body = f'<header class="head"><h1>The envelope</h1></header><figure>{inline}</figure>'
    return {"term": TERM, "course": COURSE, "name": "envelope-steps", "title": "The envelope", "body": body,
            "base": SUBJECT}


@pytest.fixture
def saved(home, root):
    run_ok(FP, home, "save-base", save(built(home)))
    return pack_base(root)


def out_file(root: Path, name: str, ext: str = "svg", course: str = COURSE) -> Path:
    return root / TERM / course / ".state" / "out" / f"{name}.{ext}"


def test_inputs_for_a_subject_hand_the_builder_its_base_figure(home, saved):
    out = run_ok(VISUAL, home, "inputs", {"term": TERM, "course": COURSE, "subject": SUBJECT})
    assert out["base"] == {"subject": SUBJECT, "source": "pack", "field": FIELD, "path": str(saved),
                           "parts": ["outer-membrane", "peptidoglycan", "inner-membrane"]}
    assert out["line"].endswith(f"base figure {SUBJECT} from the field pack {FIELD}.")


def test_inputs_for_a_subject_with_no_base_figure_say_so(home, root):
    out = run_ok(VISUAL, home, "inputs", {"term": TERM, "course": COURSE, "subject": SUBJECT})
    assert out["base"] is None
    assert out["line"].endswith(f"no base figure {SUBJECT} yet.")


def test_a_reuse_that_keeps_every_part_and_adds_labels_and_leaders_is_built(home, root, saved):
    """#101: a later build keeps the base figure's part ids and geometry and only adds labels and leaders."""
    out = run_ok(VISUAL, home, "svg", reuse())
    assert out["path"] == str(out_file(root, "envelope-labelled"))


def test_a_reuse_page_with_steps_and_highlights_is_built(home, root, saved):
    """#101: steps wrap parts and highlights mark them; the parts themselves stay as they are."""
    stepped = BASE.replace('<g id="outer-membrane">', '<g data-step="1"><g id="outer-membrane">').replace(
        '<g id="peptidoglycan">', '</g><g data-step="2"><g id="peptidoglycan">').replace(
        '<path id="inner-membrane" d="M 10 56 L 190 56" class="ink"/>',
        '</g><path data-step="3" class="ink wash" id="inner-membrane" d="M 10 56 L 190 56"/>').replace(
        "</svg>", '<path class="mark-loop" data-highlight="2" pathLength="1" d="M 6 30 L 194 30 L 194 44 L 6 44 Z"/>'
                  + LABELS + "</svg>")
    out = run_ok(VISUAL, home, "page", figure_in_page(stepped))
    assert out["path"] == str(out_file(root, "envelope-steps", "html"))


@pytest.mark.parametrize(("svg", "needle"), [
    (REUSE.replace('width="180" height="6"', 'width="180" height="9"'), "part 'peptidoglycan' changed"),
    (REUSE.replace('d="M 10 56 L 190 56"', 'd="M 10 58 L 190 58"'), "part 'inner-membrane' changed"),
    (REUSE.replace('<path id="inner-membrane" d="M 10 56 L 190 56" class="ink"/>', ""),
     "part 'inner-membrane' is missing"),
    (REUSE.replace('<g id="outer-membrane">', '<g transform="translate(0 4)"><g id="outer-membrane">').replace(
        '<g id="peptidoglycan">', '</g><g id="peptidoglycan">'), "part 'outer-membrane' changed"),
    (REUSE.replace('<g id="peptidoglycan">', '<g id="peptidoglycan"><circle cx="40" cy="37" r="2"/>'),
     "part 'peptidoglycan' changed"),
    (REUSE.replace('viewBox="0 0 200 120"', 'viewBox="0 0 240 120"'), "viewBox"),
    (REUSE.replace("</svg>", '<rect x="20" y="70" width="40" height="10" class="ink"/></svg>'),
     "only labels, leader lines and highlights"),
])
def test_a_reuse_that_redraws_the_base_figure_is_refused_and_writes_nothing(home, root, saved, svg, needle):
    """#101: later builders never redraw a base figure's parts."""
    run_fails(VISUAL, home, "svg", reuse(svg), needle)
    assert not out_file(root, "envelope-labelled").exists()


def test_a_reuse_page_that_redraws_a_part_is_refused(home, root, saved):
    changed = REUSE.replace('d="M 10 56 L 190 56"', 'd="M 10 60 L 190 60"')
    run_fails(VISUAL, home, "page", figure_in_page(changed), "base: base figure part 'inner-membrane' changed")
    run_fails(VISUAL, home, "page", figure_in_page(SVG_FREE), "no inline <svg> holds the base figure")
    assert not out_file(root, "envelope-steps", "html").exists()


SVG_FREE = ('<svg viewBox="0 0 100 40" role="img"><title>Other</title><desc>A line.</desc>'
            '<line x1="5" y1="20" x2="95" y2="20" class="ink"/></svg>')


def test_a_reuse_of_a_subject_with_no_base_figure_is_refused(home, root):
    run_fails(VISUAL, home, "svg", reuse(), f"base: no base figure {SUBJECT} for {COURSE}")
    run_fails(VISUAL, home, "svg", reuse(base="Heart!"), "base must be lowercase letters")


def test_a_course_with_its_professors_diagram_builds_from_that_not_the_packs(home, root, saved):
    """#101: the professor's diagram is the base for that course; other courses keep the pack's."""
    run_ok(FP, home, "save-course-base", local(professor_diagram(root)))
    run_fails(VISUAL, home, "svg", reuse(), "part 'outer-membrane' changed")
    run_ok(VISUAL, home, "svg", reuse(PROFESSOR.replace("</svg>", LABELS + "</svg>")))
    run_ok(VISUAL, home, "svg", reuse(course=OTHER))


# --- the dispatch and helper text ----------------------------------------------------
# First need: the student's build returns at once; the base figure grows in the background, is checked
# in the foreground when it arrives and saved only on a pass. Later needs start from it.

def _read(rel: str) -> str:
    return (ROOT_DIR / rel).read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def _front(rel: str) -> dict:
    _, head, _ = _read(rel).split("---", 2)
    return dict(line.split(": ", 1) for line in head.strip().splitlines())


BUILDER = "helpers/base-figure-builder.md"


def test_the_base_figure_builder_is_a_registered_helper_on_the_stronger_model():
    front = _front(BUILDER)
    assert front["name"] == "base-figure-builder"
    assert front["model"] == "opus" and front["tools"] == "Bash"
    assert front["description"].endswith("Dispatched by Mimir skills; not for direct use.")
    assert f"./{BUILDER}" in json.loads(_read(".claude-plugin/plugin.json"))["agents"]
    assert "mimir:base-figure-builder" in _read("docs/agents/plugin-from-worktree.md")


def test_the_base_figure_builder_draws_parts_with_stable_ids_through_the_shell_and_never_opens_them():
    body = _read(BUILDER)
    given = _section(body, "Input")
    for key in ("`script`", "`term`", "`course`", "`subject`", "`figure`"):
        assert key in given, key
    assert '"$(dirname "$(dirname "<script>")")/reference/house-style.md"' in body
    assert "inputs" in body and "stable part id" in body and "no labels" in body.lower()
    assert "`base-<subject>`" in body and "never `open`" in body
    assert "Built <path>." in _section(body, "Reply")


def test_core_rules_start_the_base_figure_builder_in_the_background_and_the_figure_checker_in_the_foreground():
    dispatch = _section(_read("reference/core-rules.md"), "Base figure dispatch")
    background = dispatch.index("`mimir:base-figure-builder`")
    assert dispatch.index("`run_in_background: true`") > background
    checker = dispatch.index("`mimir:figure-checker`")
    assert dispatch.index("`run_in_background: false`") > checker
    assert "`spawn_agent`" in dispatch and "`define_subagent`" in dispatch and "no independent agent" in dispatch
    assert "never waits" in dispatch and "foreground" in dispatch


def test_the_first_need_builds_at_once_and_saves_a_base_figure_only_after_the_checker_passes_it():
    text = _section(_read("reference/notation.md"), "Base figures")
    find, builder = text.index("`fieldpack.py find-base`"), text.index("`mimir:visual-builder`")
    background, brief = text.index("Base figure dispatch"), text.index("`figurecheck.py brief`")
    checker, save_ = text.index("`mimir:figure-checker`"), text.index("`fieldpack.py save-base`")
    assert find < builder < background < brief < checker < save_
    assert "without waiting" in text and "`subject`" in text
    assert "not saved" in text and "tries again" in text


def test_a_professors_diagram_is_saved_only_for_its_course_and_never_leaves_it():
    text = _section(_read("reference/notation.md"), "Base figures")
    assert "`fieldpack.py save-course-base`" in text
    assert "never leaves the course folder" in text and "never" in text and "commit" in text


def test_the_builder_starts_from_the_base_figure_and_never_redraws_its_parts():
    body = _read("helpers/visual-builder.md")
    given = _section(body, "Input")
    assert "`subject`" in given
    start = _section(body, "Start from a base figure")
    assert '"subject"' in start and "`base`" in start and 'cat "<path>"' in start
    assert "never redraw" in start
    for added in ("labels", "steps", "highlights", "leader lines"):
        assert added in start, added
    assert '"base": "<subject>"' in start
