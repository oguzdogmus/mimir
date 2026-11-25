#!/usr/bin/env python3
"""Blind test pages (#102): every field pack's test page built by a fresh builder and checked.

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/blind_test_pages.py run --home HOME --plugin PLUGIN_DIR --out DIR \
        [--builder-model M] [--checker-model M] [--parallel N]
    python3 tests/acceptance/blind_test_pages.py report DIR [DIR ...]
    python3 tests/acceptance/blind_test_pages.py compare BEFORE_DIR AFTER_DIR

``run`` finds every field pack in the workspace of ``HOME`` (``fieldpack.py
list``) and, per pack, makes a fresh fixture workspace in ``DIR/<field>/``
that holds only that pack (saved again through ``fieldpack.py save``) and one
course linked to it. It builds the pack's test page there with a fresh
builder, the plugin's ``mimir:visual-builder`` given the helper's inputs and
the pack's ``test_page`` content, timed by the wall clock. It then checks the
built page with a fresh ``mimir:figure-checker`` given the brief from
``figurecheck.py brief`` and reads its reply through ``figurecheck.py read``.
Both agents run lean (as ``drive.py`` runs Claude Code) on their own model
unless ``--builder-model``/``--checker-model`` are given. Every script and the
house style guide come from ``PLUGIN_DIR``, so a run measures that plugin's
guide. Measured as in #87: build time per page and checklist errors. It writes
``DIR/results.json`` (``plugin`` and one row per pack: ``field``, ``figure``,
``build_seconds``, ``built``, ``items``, ``errors``, ``failed``,
``failed_rules``, ``check_seconds``, ``cost_usd``, the replies) and prints one
Markdown row per pack. A page the builder did not build is reported "not
built" and is not checked.

``report`` prints those rows for one or more runs. ``compare`` prints, per
pack, the checklist errors of two runs and the failed rules the later run
gained or lost; run it after a change to the core house style guide against
the last run (RELEASE.md).

The test content is the packs' synthetic ``test_page``; no course material
is read. The source workspace is only listed and read, never written.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from checker_benchmark import parse_output
from drive import lean_claude_home

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TERM = "2026-Fall"
NAME = "test-page"
KIND = "page"
TIMEOUT = 1800


def _script(scripts: Path, home: Path, script: str, command: str, data: dict) -> dict:
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    proc = subprocess.run([sys.executable, str(scripts / script), command], input=json.dumps(data),
                          capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{script} {command} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def find_packs(scripts: Path, home: Path) -> list[dict]:
    """Every field pack in the workspace of ``home``, as stored, sorted by field."""
    listed = _script(scripts, home, "fieldpack.py", "list", {})["packs"]
    return [json.loads(Path(p["path"]).read_text(encoding="utf-8")) for p in listed]


def _fixture(scripts: Path, base: Path, pack: dict) -> dict:
    """A fresh workspace in ``base`` holding only ``pack`` and one course linked to it."""
    home = base / "home"
    home.mkdir(parents=True)
    course = f"Test page {pack['field']}"
    _script(scripts, home, "workspace.py", "init", {})
    _script(scripts, home, "fieldpack.py", "save", pack)
    made = _script(scripts, home, "workspace.py", "course", {"term": TERM, "course": course})
    _script(scripts, home, "fieldpack.py", "link", {"term": TERM, "course": course, "field": pack["field"]})
    return {"home": home, "root": Path(made["root"]), "course": course, "course_dir": Path(made["course_dir"])}


def run_pack(out: Path, scripts: Path, pack: dict, builder: Callable[[dict], dict],
             checker: Callable[[str, dict], dict]) -> dict:
    """Build one pack's test page in a fresh fixture with ``builder`` and check it with ``checker``."""
    fx = _fixture(scripts, out / pack["field"], pack)
    page = pack["test_page"]
    kind = next(k["kind"] for k in pack["figure_kinds"] if k["name"] == page["figure"])
    env = {**os.environ, "HOME": str(fx["home"]), "USERPROFILE": str(fx["home"])}
    job = {"script": str(scripts / "visual.py"), "term": TERM, "course": fx["course"], "name": NAME, "kind": KIND,
           "figure": page["figure"], "figure_kind": kind, "content": page["content"], "env": env,
           "cwd": fx["root"]}
    built = builder(job)
    path = fx["course_dir"] / ".state" / "out" / f"{NAME}.html"
    row = {"field": pack["field"], "figure": page["figure"], "build_seconds": built["seconds"],
           "build_reply": built["reply"], "built": str(path) if path.is_file() else None,
           "models": sorted(set(built.get("models") or [])), "cost_usd": built.get("cost_usd")}
    if row["built"] is None:
        return {**row, "items": None, "errors": None, "failed": None, "failed_rules": None, "check_seconds": None,
                "overall": None, "check_reply": None}
    brief = _script(scripts, fx["home"], "figurecheck.py", "brief",
                    {"field": pack["field"], "figure": page["figure"], "path": str(path)})
    checked = checker(brief["brief"], job)
    read = _script(scripts, fx["home"], "figurecheck.py", "read",
                   {"field": pack["field"], "figure": page["figure"], "reply": checked["reply"]})
    costs = [row["cost_usd"], checked.get("cost_usd")]
    return {**row, "items": len(read["items"]), "errors": len(read["failed"]), "failed": read["failed"],
            "failed_rules": [i["rule"] for i in read["items"] if i["verdict"] != "pass"],
            "overall": read["overall"], "check_seconds": checked["seconds"], "check_reply": checked["reply"],
            "models": sorted(set(row["models"]) | set(checked.get("models") or [])),
            "cost_usd": None if None in costs else round(sum(costs), 4)}


def _agent_cmd(plugin: Path, agent: str, model: str | None) -> list[str]:
    cmd = ["claude", "-p", "--plugin-dir", str(plugin), "--agent", agent, "--strict-mcp-config",
           "--setting-sources", "project", "--output-format", "json"]
    return cmd + (["--model", model] if model else [])


def builder_cmd(plugin: Path, job: dict, model: str | None = None) -> list[str]:
    """The fresh builder for one test page: the plugin's ``mimir:visual-builder`` (its own model unless
    overridden) given the helper's inputs and the test content, as ``reference/notation.md`` dispatches it.
    The one place the builder's dispatch is written; change it here when the helper's inputs change."""
    prompt = "\n".join([f"script: {job['script']}", f"term: {job['term']}", f"course: {job['course']}",
                        f"name: {job['name']}", f"kind: {job['kind']}", "",
                        f"Figure kind: {job['figure']} ({job['figure_kind']})", "Content:", job["content"]])
    return _agent_cmd(plugin, "mimir:visual-builder", model) + ["--allowedTools", "Bash", prompt]


def checker_cmd(plugin: Path, brief: str, model: str | None = None) -> list[str]:
    """The plugin's ``mimir:figure-checker`` (its own model unless overridden) with the brief as its prompt."""
    return _agent_cmd(plugin, "mimir:figure-checker", model) + [brief]


def _host(cmd: list[str], job: dict) -> dict:
    """One lean Claude Code process in the job's fixture HOME, timed by the wall clock. No display is
    passed, so the builder's ``open`` step opens no browser on Linux."""
    env = {k: v for k, v in job["env"].items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    lean_claude_home(Path(env["HOME"]))
    start = time.monotonic()
    proc = subprocess.run(cmd, cwd=job["cwd"], env=env, capture_output=True, text=True, timeout=TIMEOUT,
                          check=False)
    seconds = round(time.monotonic() - start, 1)
    try:
        parsed = parse_output("claude", proc.stdout)
    except json.JSONDecodeError:
        parsed = {"reply": "", "cost_usd": None, "usage": {}, "models": []}
    return {**parsed, "seconds": seconds, "exit": proc.returncode, "stderr": proc.stderr[-2000:]}


def host_builder(plugin: Path, model: str | None = None) -> Callable[[dict], dict]:
    return lambda job: _host(builder_cmd(plugin, job, model), job)


def host_checker(plugin: Path, model: str | None = None) -> Callable[[str, dict], dict]:
    return lambda brief, job: _host(checker_cmd(plugin, brief, model), job)


NOT_BUILT = "not built"


def _failures(row: dict | None) -> list[str]:
    if row is None:
        return []
    return [NOT_BUILT] if row["built"] is None else row["failed_rules"]


def _errors(row: dict | None) -> int | str | None:
    if row is None:
        return None
    return NOT_BUILT if row["built"] is None else row["errors"]


def compare(before: dict, after: dict) -> list[dict]:
    """Per pack of either run: its checklist errors before and after (None when absent, "not built") and
    the failed rules it gained (``new``) and lost (``gone``), matched by rule text. A page that is no
    longer built counts as the new failure "not built"."""
    old = {r["field"]: r for r in before["packs"]}
    new = {r["field"]: r for r in after["packs"]}
    rows = []
    for field in sorted(old.keys() | new.keys()):
        was, now = old.get(field), new.get(field)
        lost, gained = _failures(was), _failures(now)
        rows.append({"field": field, "before": _errors(was), "after": _errors(now),
                     "new": [r for r in gained if r not in lost] if was else [],
                     "gone": [r for r in lost if r not in gained] if now else []})
    return rows


def _cell(value: object) -> str:
    return "–" if value is None else str(value)


def compare_row(row: dict) -> str:
    return (f"| {row['field']} | {_cell(row['before'])} | {_cell(row['after'])} | "
            f"{'; '.join(row['new']) or '–'} | {'; '.join(row['gone']) or '–'} |")


def report_row(label: str, row: dict) -> str:
    cost = "–" if row["cost_usd"] is None else f"${row['cost_usd']:.4f}"
    if row["built"] is None:
        errors, failed, check = NOT_BUILT, "–", "–"
    else:
        errors = f"{row['errors']}/{row['items']}"
        failed = ", ".join(map(str, row["failed"])) or "–"
        check = f"{row['check_seconds']} s"
    return (f"| {label} | {row['field']} | {row['figure']} | {row['build_seconds']} s | {errors} | {failed} "
            f"| {check} | {cost} |")


def run(out: Path, home: Path, builder: Callable[[dict], dict], checker: Callable[[str, dict], dict],
        plugin: Path = REPO, parallel: int = 1) -> dict:
    """Run every pack's test page from the workspace of ``home``. Writes ``out/results.json``."""
    scripts = plugin / "scripts"
    packs = find_packs(scripts, home)
    if not packs:
        raise ValueError(f"no field pack in the workspace of {home}")
    out.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        rows = list(pool.map(lambda p: run_pack(out, scripts, p, builder, checker), packs))
    result = {"plugin": str(plugin), "packs": rows}
    (out / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def _results(folder: Path) -> dict:
    return json.loads((folder / "results.json").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--home", required=True, type=Path)
    r.add_argument("--plugin", required=True, type=Path)
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--builder-model")
    r.add_argument("--checker-model")
    r.add_argument("--parallel", type=int, default=3)
    rep = sub.add_parser("report")
    rep.add_argument("dirs", nargs="+", type=Path)
    cmp = sub.add_parser("compare")
    cmp.add_argument("before", type=Path)
    cmp.add_argument("after", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "report":
        print("| Run | Pack | Figure | Build time | Checklist errors | Failed items | Check time | Cost |")
        print("|---|---|---|---|---|---|---|---|")
        for d in args.dirs:
            for row in _results(d)["packs"]:
                print(report_row(d.name, row))
        return 0
    if args.cmd == "compare":
        print("| Pack | Errors before | Errors after | New failures | Gone |")
        print("|---|---|---|---|---|")
        for row in compare(_results(args.before), _results(args.after)):
            print(compare_row(row))
        return 0
    plugin = args.plugin.resolve()
    result = run(args.out.resolve(), args.home.resolve(), host_builder(plugin, args.builder_model),
                 host_checker(plugin, args.checker_model), plugin=plugin, parallel=args.parallel)
    for row in result["packs"]:
        print(report_row(args.out.name, row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
