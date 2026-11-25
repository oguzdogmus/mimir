"""Boundary tests for scripts/fieldpack.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
FP = SCRIPTS / "fieldpack.py"
WS = SCRIPTS / "workspace.py"

sys.path.insert(0, str(SCRIPTS))
import fieldpack  # noqa: E402 -- read for its limits only; behaviour is driven through the CLI

TERM, COURSE = "2026-Fall", "MED101 Physiology"

PACK = {
    "field": "medicine",
    "title": "Medicine",
    "figures": [
        {"name": "anatomical section", "kind": "depiction"},
        {"name": "ECG trace", "kind": "plot"},
    ],
    "conventions": [
        {"rule": "Draw the body in anatomical position; the patient's right is on the viewer's left.",
         "source": "Gray's Anatomy, 42nd ed., ch. 1"},
        {"rule": "Arteries are red, veins are blue.", "source": "Netter, Atlas of Human Anatomy, 8th ed."},
    ],
    "recipes": [
        {"figure": "ECG trace", "rule": "25 mm/s on the time axis, 10 mm/mV on the voltage axis.",
         "source": "AHA/ACCF/HRS recommendations for the standardization of the ECG, 2007"},
    ],
    "checklists": [
        {"figure": "anatomical section", "rules": [
            {"rule": "The aorta arches over the pulmonary trunk.", "source": "Gray's Anatomy, 42nd ed., ch. 57"},
            {"rule": "The inferior vena cava enters the right atrium from below.",
             "source": "Gray's Anatomy, 42nd ed., ch. 57"},
        ]},
        {"figure": "ECG trace", "rules": [
            {"rule": "P wave, QRS complex and T wave appear in that order.", "source": "Guyton and Hall, 14th ed."},
        ]},
    ],
    "test_page": {"figure": "anatomical section",
                  "content": "How the heart pumps blood: a frontal section with the four chambers,\n"
                             "the valves and the great vessels, labelled."},
}


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows ignores HOME
    return home


@pytest.fixture
def root(home):
    ws_ok(home, "init", {})
    return home / "learning"


@pytest.fixture
def course(home, root):
    ws_ok(home, "course", {"term": TERM, "course": COURSE})
    return root / TERM / COURSE


def _run(script: Path, home: Path, cmd: str, payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(script), cmd], input=stdin, capture_output=True,
                          env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)})


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
    assert err.startswith("fieldpack.py: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def ws_ok(home: Path, cmd: str, payload) -> dict:
    proc = _run(WS, home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    return json.loads(proc.stdout)


def snapshot(root: Path) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            out[str(p)] = p.read_bytes() if p.is_file() else None
    return out


def pack(**changes) -> dict:
    p = copy.deepcopy(PACK)
    p.update(changes)
    return p


# --- save and list -------------------------------------------------------------------

def test_a_valid_pack_is_saved_in_the_workspace_store_and_listed(home, root):
    out = ok(home, "save", PACK)
    path = root / ".state" / "field-packs" / "medicine" / "pack.json"
    assert out["path"] == str(path) and out["field"] == "medicine"
    assert json.loads(path.read_text(encoding="utf-8")) == PACK
    assert "Medicine" in out["line"]

    listed = ok(home, "list", {})
    assert listed["packs"] == [{"field": "medicine", "title": "Medicine", "path": str(path),
                                "figures": ["anatomical section", "ECG trace"]}]


def _without_source(section: str):
    def change(p):
        if section == "checklists":
            del p["checklists"][0]["rules"][1]["source"]
        else:
            p[section][0]["source"] = " "
    return change


def _unmapped_kind(p):
    p["figures"][1]["kind"] = "chart"


def _no_checklist(p):
    p["figures"].append({"name": "histology slide", "kind": "depiction"})


def _over_cap(p):
    p["conventions"] = [{"rule": f"Rule {n}: " + "x" * 140, "source": "Gray's Anatomy"} for n in range(200)]


@pytest.mark.parametrize("change, needle", [
    (_unmapped_kind, "figures[2].kind must be one of depiction, formal notation, plot, own sketch"),
    (_without_source("conventions"), "conventions[1].source is required"),
    (_without_source("recipes"), "recipes[1].source is required"),
    (_without_source("checklists"), "checklists[1].rules[2].source is required"),
    (_no_checklist, "figures[3] 'histology slide' has no accuracy checklist"),
    (_over_cap, f"over the {fieldpack.MAX_PACK_CHARS}-character cap"),
])
def test_a_bad_pack_is_refused_with_a_field_named_error_and_nothing_is_written(home, root, change, needle):
    bad = pack()
    change(bad)
    before = snapshot(root)
    fails(home, "save", bad, needle)
    assert snapshot(root) == before


def test_a_pack_is_written_once_per_field(home, root):
    ok(home, "save", PACK)
    before = snapshot(root)
    fails(home, "save", pack(title="Medicine again"), "field pack 'medicine' already exists")
    assert snapshot(root) == before


def test_save_leaves_only_the_pack_file_in_the_pack_folder(home, root):
    ok(home, "save", PACK)
    assert sorted(p.name for p in (root / ".state" / "field-packs" / "medicine").iterdir()) == ["pack.json"]


def test_save_refuses_a_symlinked_store(home, root, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / ".state" / "field-packs").symlink_to(elsewhere, target_is_directory=True)
    fails(home, "save", PACK, "is a symlink")
    assert list(elsewhere.iterdir()) == []


def test_every_command_needs_a_workspace(home):
    fails(home, "save", PACK, "no workspace at")
    fails(home, "list", {}, "no workspace at")


@pytest.mark.parametrize("payload, where", [
    (pack(title="T" * (fieldpack.TITLE_MAX_CHARS + 1)), "title"),
    (pack(figures=[{"name": "n" * (fieldpack.TITLE_MAX_CHARS + 1), "kind": "plot"}]), "figures[1].name"),
])
def test_a_title_or_figure_name_over_the_limit_is_refused(home, root, payload, where):
    fails(home, "save", payload, f"{where} has {fieldpack.TITLE_MAX_CHARS + 1} characters, over the "
                                 f"{fieldpack.TITLE_MAX_CHARS}-character limit")


def test_the_researcher_is_told_the_stores_own_limits():
    """The field researcher's limits follow from the store's constants, so the two never drift apart."""
    text = (ROOT_DIR / "helpers" / "field-researcher.md").read_text(encoding="utf-8")
    assert f"one line of at most {fieldpack.TEXT_MAX_CHARS} characters" in text
    assert f"the title and each figure name at most {fieldpack.TITLE_MAX_CHARS} characters" in text
    assert f"`test_page.content` at most {fieldpack.CONTENT_MAX_CHARS} characters" in text
    assert f"the stored pack at most {fieldpack.MAX_PACK_CHARS} characters" in text


@pytest.mark.parametrize("payload, needle", [
    (pack(field="Civil Engineering"), "field must be lowercase letters and digits joined by single hyphens"),
    (pack(colour="red"), "unknown field 'colour'"),
    (pack(test_page={"figure": "brain scan", "content": "x"}), "test_page.figure 'brain scan' is not one of"),
    (pack(test_page={"figure": "ECG trace"}), "test_page.content is required"),
    (pack(figures=[]), "figures is required"),
    ({**{k: v for k, v in PACK.items() if k != "figures"}, "figure_kinds": PACK["figures"]},
     "unknown field 'figure_kinds'"),  # the old name, kept by no alias
])
def test_save_refuses_a_malformed_pack(home, root, payload, needle):
    before = snapshot(root)
    fails(home, "save", payload, needle)
    assert snapshot(root) == before


ENGINEERING = pack(field="civil-engineering", title="Civil engineering",
                   figures=[{"name": "free-body diagram", "kind": "formal notation"}], recipes=[],
                   checklists=[{"figure": "free-body diagram", "rules": [
                       {"rule": "Every support is replaced by its reaction forces.",
                        "source": "Hibbeler, Engineering Mechanics: Statics, 14th ed., ch. 5"}]}],
                   test_page={"figure": "free-body diagram", "content": "A simply supported beam with one point load."})


def test_list_reports_every_pack_sorted_by_field(home, root):
    assert ok(home, "list", {})["packs"] == []
    ok(home, "save", PACK)
    ok(home, "save", ENGINEERING)
    out = ok(home, "list", {})
    assert [p["field"] for p in out["packs"]] == ["civil-engineering", "medicine"]
    assert out["packs"][0]["figures"] == ["free-body diagram"]
    assert out["line"] == "2 field packs: civil-engineering, medicine."


def test_list_refuses_a_damaged_pack_naming_its_file(home, root):
    ok(home, "save", PACK)
    path = root / ".state" / "field-packs" / "medicine" / "pack.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    del stored["conventions"][0]["source"]
    path.write_text(json.dumps(stored), encoding="utf-8")
    err = fails(home, "list", {}, str(path))
    assert "conventions[1].source is required" in err


def test_list_refuses_a_pack_folder_without_its_pack(home, root):
    (root / ".state" / "field-packs" / "biology").mkdir(parents=True)
    fails(home, "list", {}, "pack.json")


# --- link and report -----------------------------------------------------------------

def link(field: str) -> dict:
    return {"term": TERM, "course": COURSE, "field": field}


def test_a_course_links_one_or_two_packs_and_a_third_is_refused(home, root, course):
    biology = pack(field="biology", title="Biology")
    for p in (PACK, ENGINEERING, biology):
        ok(home, "save", p)
    record = course / ".state" / "field-packs.json"

    out = ok(home, "link", link("medicine"))
    assert out["packs"] == ["medicine"] and out["path"] == str(record)
    assert json.loads(record.read_text(encoding="utf-8")) == {"packs": ["medicine"]}

    out = ok(home, "link", link("civil-engineering"))
    assert out["packs"] == ["medicine", "civil-engineering"]

    before = snapshot(root)
    fails(home, "link", link("biology"), "already uses 2 field packs (medicine, civil-engineering)")
    assert snapshot(root) == before


def test_linking_a_pack_twice_changes_nothing(home, root, course):
    ok(home, "save", PACK)
    ok(home, "link", link("medicine"))
    before = snapshot(root)
    out = ok(home, "link", link("medicine"))
    assert out["packs"] == ["medicine"] and out["added"] is False
    assert snapshot(root) == before


def test_a_link_to_a_pack_that_does_not_exist_is_refused(home, root, course):
    before = snapshot(root)
    fails(home, "link", link("medicine"), "no field pack 'medicine'")
    assert snapshot(root) == before


def test_a_link_needs_an_existing_course(home, root):
    ok(home, "save", PACK)
    before = snapshot(root)
    fails(home, "link", link("medicine"), "no course folder at")
    assert snapshot(root) == before


def test_report_returns_a_course_s_linked_packs(home, root, course):
    ok(home, "save", PACK)
    ok(home, "save", ENGINEERING)
    ok(home, "link", link("civil-engineering"))
    ok(home, "link", link("medicine"))
    out = ok(home, "report", {"term": TERM, "course": COURSE})
    store = root / ".state" / "field-packs"
    assert out["status"] == "linked"
    assert out["packs"] == [
        {"field": "civil-engineering", "title": "Civil engineering",
         "path": str(store / "civil-engineering" / "pack.json")},
        {"field": "medicine", "title": "Medicine", "path": str(store / "medicine" / "pack.json")},
    ]
    assert out["course_dir"] == str(course)


def test_report_tells_a_course_without_a_pack_apart_from_an_error(home, root, course):
    ok(home, "save", PACK)
    out = ok(home, "report", {"term": TERM, "course": COURSE})
    assert out["status"] == "none" and out["packs"] == []
    assert out["line"] == f"{COURSE} has no field pack yet."


def test_report_refuses_a_link_to_a_pack_that_is_gone(home, root, course):
    ok(home, "save", PACK)
    ok(home, "link", link("medicine"))
    (root / ".state" / "field-packs" / "medicine" / "pack.json").unlink()
    fails(home, "report", {"term": TERM, "course": COURSE}, "no field pack 'medicine'")


def test_report_refuses_a_damaged_link_record(home, root, course):
    (course / ".state" / "field-packs.json").write_text('{"packs": ["a", "b", "c"]}', encoding="utf-8")
    fails(home, "report", {"term": TERM, "course": COURSE}, "field-packs.json is damaged")


def test_report_needs_an_existing_course(home, root):
    fails(home, "report", {"term": TERM, "course": COURSE}, "no course folder at")


# --- match (#98) ---------------------------------------------------------------------

def match(field: str, course: str = COURSE, **extra) -> dict:
    return {"term": TERM, "course": course, "field": field, **extra}


def test_match_links_a_course_to_the_existing_pack_of_its_field_without_research(home, root, course):
    """#98: a second course in a field reuses that field's pack; nothing is researched."""
    ok(home, "save", PACK)
    out = ok(home, "match", match("medicine", topics=["Cardiac cycle"]))
    assert out["status"] == "linked" and out["added"] is True and out["packs"] == ["medicine"]
    assert "brief" not in out
    assert ok(home, "report", {"term": TERM, "course": COURSE})["packs"][0]["field"] == "medicine"
    assert out["line"] == f"{COURSE} now uses the field pack medicine."


def test_match_on_a_field_without_a_pack_returns_the_researcher_brief_and_writes_nothing(home, root, course):
    """#98: the brief is the researcher's whole input, built only from the field name and topic names."""
    before = snapshot(root)
    out = ok(home, "match", match("human-anatomy", topics=["Cardiac cycle", " Heart valves "]))
    assert out["status"] == "research" and out["packs"] == [] and out["added"] is False
    assert out["brief"] == {"field": "human-anatomy", "topics": ["Cardiac cycle", "Heart valves"]}
    assert out["line"] == "No field pack human-anatomy yet; researching it in the background."
    assert snapshot(root) == before


def test_match_refuses_research_for_a_course_that_already_uses_two_packs(home, root, course):
    ok(home, "save", PACK)
    ok(home, "save", ENGINEERING)
    ok(home, "link", link("medicine"))
    ok(home, "link", link("civil-engineering"))
    before = snapshot(root)
    fails(home, "match", match("translation-studies"), "already uses 2 field packs (medicine, civil-engineering)")
    assert snapshot(root) == before


@pytest.mark.parametrize("payload, needle", [
    (match("human-anatomy", topics="Cardiac cycle"), "topics must be a list of at most 20 topic names"),
    (match("human-anatomy", topics=[f"Topic {n}" for n in range(21)]), "topics must be a list of at most 20"),
    (match("human-anatomy", topics=["x" * 121]), "topics[1] has 121 characters, over the 120-character limit"),
    (match("human-anatomy", topics=["Cardiac\ncycle"]), "topics[1] must be one line"),
    (match("human-anatomy", notes="Week 3 slides"), "unknown field 'notes'"),
    (match("Human Anatomy"), "field must be lowercase letters and digits"),
    (match("human-anatomy", course="ANAT999 Missing"), "no course folder at"),
])
def test_match_refuses_bad_input_and_writes_nothing(home, root, course, payload, needle):
    before = snapshot(root)
    fails(home, "match", payload, needle)
    assert snapshot(root) == before


def test_after_research_saves_the_pack_match_links_the_waiting_course(home, root, course):
    """#98: ingest matches again when the background research finishes, which links the course."""
    assert ok(home, "match", match("medicine", topics=["Cardiac cycle"]))["status"] == "research"
    ok(home, "save", PACK)  # what the field researcher does
    out = ok(home, "match", match("medicine", topics=["Cardiac cycle"]))
    assert out["status"] == "linked" and out["added"] is True
    again = ok(home, "match", match("medicine"))
    assert again["status"] == "linked" and again["added"] is False
    assert again["line"] == f"{COURSE} already uses the field pack medicine."


# --- glossary ------------------------------------------------------------------------

def test_the_glossary_names_field_packs_and_base_figures():
    text = (ROOT_DIR / "GLOSSARY.md").read_text(encoding="utf-8")
    assert "**Field pack**:" in text and "**Base figure**:" in text
    assert "**Field notes**:" not in text  # #103: renamed, field conventions live in field packs
    recipes = text.split("**Cross-field recipes**:", 1)[1].split("\n\n", 1)[0]
    assert "field pack" in recipes and "when a real case shows the need" not in recipes
