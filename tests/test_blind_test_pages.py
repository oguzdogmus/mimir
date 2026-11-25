"""The blind test page run (#102): every field pack's test page built and checked
(tests/acceptance/blind_test_pages.py). No host builder or checker is called here."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "acceptance"))
import blind_test_pages as btp  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

MEDICINE = {
    "field": "medicine", "title": "Medicine",
    "figures": [{"name": "anatomical section", "kind": "depiction"}],
    "conventions": [], "recipes": [],
    "checklists": [{"figure": "anatomical section", "rules": [
        {"rule": "The aorta arches over the pulmonary trunk.", "source": "Gray's Anatomy, 42nd ed., ch. 57"},
        {"rule": "The inferior vena cava enters the right atrium from below.", "source": "Gray's Anatomy, 42nd ed."},
        {"rule": "The left ventricle wall is clearly thicker than the right.", "source": "OpenStax A&P 2e, 19.1"},
    ]}],
    "test_page": {"figure": "anatomical section", "content": "How the heart pumps blood: a frontal section."},
}
TRANSLATION = {
    "field": "translation-studies", "title": "Translation studies",
    "figures": [{"name": "aligned table", "kind": "formal notation"}],
    "conventions": [], "recipes": [],
    "checklists": [{"figure": "aligned table", "rules": [
        {"rule": "The source text column is left of the target text column.", "source": "Munday, 4th ed."},
    ]}],
    "test_page": {"figure": "aligned table", "content": "Three procedures of Vinay and Darbelnet, English to French."},
}


def _script(home: Path, script: str, cmd: str, payload: dict) -> dict:
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), cmd], input=json.dumps(payload),
                          capture_output=True, text=True, env={**os.environ, "HOME": str(home),
                                                               "USERPROFILE": str(home)})
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture
def source(tmp_path):
    """A student's HOME whose workspace holds the two synthetic packs."""
    home = tmp_path / "student"
    home.mkdir()
    _script(home, "workspace.py", "init", {})
    for pack in (MEDICINE, TRANSLATION):
        _script(home, "fieldpack.py", "save", pack)
    return home


def page_builder(job: dict) -> dict:
    """A stand-in builder that builds a small page through the job's visual.py, as the helper does."""
    payload = {"term": job["term"], "course": job["course"], "name": job["name"], "title": "Test page",
               "body": "<h1>Test page</h1><svg viewBox=\"0 0 10 10\" role=\"img\"><title>x</title><desc>y</desc></svg>"}
    proc = subprocess.run([sys.executable, job["script"], job["kind"]], input=json.dumps(payload),
                          capture_output=True, text=True, env=job["env"])
    assert proc.returncode == 0, proc.stderr
    return {"reply": json.loads(proc.stdout)["line"], "seconds": 200.0, "cost_usd": 0.4, "models": ["sonnet"]}


def failing_checker(fails: dict) -> callable:
    """A stand-in checker failing the given item numbers per figure."""
    def check(brief: str, job: dict) -> dict:
        figure = brief.split("Figure: ", 1)[1].split(" (", 1)[0]
        count = brief.count("\n") - 3
        bad = fails.get(figure, ())
        lines = [f"{n} | {'fail' if n in bad else 'pass'} | stand-in" for n in range(1, count + 1)]
        lines.append(f"overall | {'fail' if bad else 'pass'} | stand-in")
        return {"reply": "\n".join(lines), "seconds": 30.0, "cost_usd": 0.1, "models": ["opus"]}
    return check


def test_a_run_builds_and_checks_every_packs_test_page_and_reports_time_and_errors(source, tmp_path):
    jobs = []

    def builder(job):
        jobs.append(job)
        return page_builder(job)

    result = btp.run(tmp_path / "run", source, builder, failing_checker({"anatomical section": (2, 3)}))
    rows = {r["field"]: r for r in result["packs"]}
    assert sorted(rows) == ["medicine", "translation-studies"]
    med = rows["medicine"]
    assert (med["figure"], med["items"], med["errors"], med["failed"]) == ("anatomical section", 3, 2, [2, 3])
    assert med["failed_rules"] == ["The inferior vena cava enters the right atrium from below.",
                                   "The left ventricle wall is clearly thicker than the right."]
    assert med["build_seconds"] == 200.0 and med["check_seconds"] == 30.0 and med["cost_usd"] == pytest.approx(0.5)
    assert Path(med["built"]).is_file() and Path(med["built"]).name == "test-page.html"
    assert (rows["translation-studies"]["errors"], rows["translation-studies"]["failed"]) == (0, [])
    assert sorted(j["content"] for j in jobs) == sorted(p["test_page"]["content"] for p in (MEDICINE, TRANSLATION))
    assert json.loads((tmp_path / "run" / "results.json").read_text())["packs"] == result["packs"]


def test_a_page_that_was_not_built_is_reported_with_the_builders_reply_and_is_not_checked(source, tmp_path):
    checked = []

    def broken(job):
        return {"reply": "visual.py: body: element <img> is not allowed", "seconds": 90.0, "cost_usd": 0.2,
                "exit": 0, "stderr": "warning"}

    def checker(brief, job):
        checked.append(brief)
        return failing_checker({})(brief, job)

    rows = btp.run(tmp_path / "run", source, broken, checker)["packs"]
    assert checked == []
    assert all(r["built"] is None and r["errors"] is None for r in rows)
    assert rows[0]["build_reply"] == "visual.py: body: element <img> is not allowed"
    assert (rows[0]["build_seconds"], rows[0]["build_exit"], rows[0]["build_stderr"]) == (90.0, 0, "warning")


JOB = {"script": "/p/mimir/scripts/visual.py", "term": "2026-Fall", "course": "Test page medicine",
       "name": "test-page", "kind": "page", "figure": "anatomical section", "figure_kind": "depiction",
       "content": "How the heart pumps blood:\na frontal section."}


def test_the_builder_is_the_plugin_agent_given_the_helpers_inputs_and_the_test_content():
    cmd = btp.builder_cmd(Path("/p/mimir"), JOB, model="opus")
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--agent") + 1] == "mimir:visual-builder"
    assert cmd[cmd.index("--plugin-dir") + 1] == str(Path("/p/mimir"))
    assert "--allowedTools=Bash" in cmd  # the helper's one tool; the = form, as --allowedTools takes many values
    assert cmd[cmd.index("--model") + 1] == "opus"
    prompt = cmd[-1]
    for line in ("script: /p/mimir/scripts/visual.py", "term: 2026-Fall", "course: Test page medicine",
                 "name: test-page", "kind: page", "Figure: anatomical section (depiction)",
                 "How the heart pumps blood:\na frontal section."):
        assert line in prompt
    assert "--model" not in btp.builder_cmd(Path("/p/mimir"), JOB)  # the agent's own model


def test_the_checker_is_the_figure_checker_agent_with_only_the_brief_as_its_prompt():
    cmd = btp.checker_cmd(Path("/p/mimir"), "Figure: /x/test-page.html\nChecklist:\n1. a\n")
    assert cmd[cmd.index("--agent") + 1] == "mimir:figure-checker"
    assert "--allowedTools" not in cmd and "--model" not in cmd
    assert cmd[-1] == "Figure: /x/test-page.html\nChecklist:\n1. a\n"


ROW = {"field": "medicine", "figure": "anatomical section", "build_seconds": 212.4, "built": "/x/test-page.html",
       "items": 11, "errors": 3, "failed": [4, 6, 8], "failed_rules": ["LV wall", "IVC from below", "aorta arch"],
       "check_seconds": 41.0, "cost_usd": 0.6123}


def test_report_row_shows_build_time_and_checklist_errors_per_pack():
    assert btp.report_row("base", ROW) == ("| base | medicine | anatomical section | 212.4 s | 3/11 | 4, 6, 8 "
                                           "| 41.0 s | $0.6123 |")
    clean = {**ROW, "errors": 0, "failed": [], "failed_rules": [], "cost_usd": None}
    assert btp.report_row("base", clean).endswith("| 0/11 | – | 41.0 s | – |")
    unbuilt = {**ROW, "built": None, "items": None, "errors": None, "failed": None, "failed_rules": None,
               "check_seconds": None}
    assert btp.report_row("base", unbuilt) == ("| base | medicine | anatomical section | 212.4 s | not built | – "
                                               "| – | $0.6123 |")


def test_compare_names_the_checklist_errors_each_pack_gained_or_lost_since_the_last_run():
    before = {"packs": [{**ROW, "errors": 1, "failed": [4], "failed_rules": ["LV wall"]},
                        {**ROW, "field": "law", "errors": 0, "failed": [], "failed_rules": []}]}
    after = {"packs": [ROW, {**ROW, "field": "law", "built": None, "errors": None, "failed": None,
                             "failed_rules": None},
                       {**ROW, "field": "music", "errors": 0, "failed": [], "failed_rules": []}]}
    rows = {r["field"]: r for r in btp.compare(before, after)}
    assert rows["medicine"] == {"field": "medicine", "before": 1, "after": 3,
                                "new": ["IVC from below", "aorta arch"], "gone": []}
    assert rows["law"] == {"field": "law", "before": 0, "after": "not built", "new": ["not built"], "gone": []}
    assert rows["music"] == {"field": "music", "before": None, "after": 0, "new": [], "gone": []}
    assert btp.compare_row(rows["medicine"]) == "| medicine | 1 | 3 | IVC from below; aorta arch | – |"
    assert btp.compare_row(rows["music"]) == "| music | – | 0 | – | – |"
    assert btp.compare_row(rows["law"]) == "| law | 0 | not built | not built | – |"


def test_report_and_compare_print_markdown_tables_from_the_runs_results(tmp_path, capsys):
    for name, row in (("base", {**ROW, "errors": 1, "failed": [4], "failed_rules": ["LV wall"]}), ("broken", ROW)):
        (tmp_path / name).mkdir()
        (tmp_path / name / "results.json").write_text(json.dumps({"packs": [row]}))
    assert btp.main(["report", str(tmp_path / "base"), str(tmp_path / "broken")]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("| Run | Pack | Figure | Build time | Checklist errors |")
    assert lines[2].startswith("| base | medicine |") and lines[3].startswith("| broken | medicine |")
    assert btp.main(["compare", str(tmp_path / "base"), str(tmp_path / "broken")]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "| Pack | Errors before | Errors after | New failures | Gone |"
    assert lines[2] == "| medicine | 1 | 3 | IVC from below; aorta arch | – |"


def test_a_workspace_without_field_packs_is_refused(tmp_path):
    home = tmp_path / "student"
    home.mkdir()
    _script(home, "workspace.py", "init", {})
    with pytest.raises(ValueError, match="no field pack"):
        btp.run(tmp_path / "run", home, page_builder, failing_checker({}))
    assert not (tmp_path / "run").exists()
