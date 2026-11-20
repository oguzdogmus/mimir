#!/usr/bin/env python3
"""Checker benchmark (#79): how well each host's answer-key checker catches planted errors.

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/checker_benchmark.py run --host claude|codex|antigravity --out DIR \
        [--plugin PLUGIN_DIR] [--codex-home CODEX_HOME] [--model M] [--effort E] [--parallel N]
    python3 tests/acceptance/checker_benchmark.py report DIR [DIR ...]

``run`` builds a fresh fixture course in ``DIR`` (``make_fixture.py`` plus the
set's ``files`` and ``notation``), submits the 60 questions of
``checker_benchmark.json`` through ``verify.py submit`` as 10 question sets of
6 (fixed shuffle), runs the host's checker once per evidence pack, settles
each reply through ``verify.py settle`` and scores the verdicts: planted
errors caught (any verdict other than ``correct``), clean questions wrongly
rejected, batches left unsettled (a reply without the pack token), seconds,
usage and, on Claude Code, cost per question. It writes ``DIR/results.json``
and prints the summary. ``report`` prints one Markdown table row per run.

The checker runs as the core rules dispatch it: Claude Code, the plugin's
``mimir:verifier`` agent from ``--plugin`` (lean, as ``drive.py`` runs it), on
the agent's own model and effort unless ``--model``/``--effort`` are given;
Codex, ``codex exec`` read-only with ``CODEX_HOME``, given the helper body and
the pack line; Antigravity, ``agy -p`` given the same message.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from drive import lean_claude_home
from speed_checks import VERIFIER_BODY

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SET_PATH = HERE / "checker_benchmark.json"
KINDS = ("general", "convention")
SET_SIZE = 6
SEED = 79
SESSION = "checker-benchmark"
TERM, COURSE = "2026-Fall", "CS301 Automata"


def load_set(path: Path) -> dict:
    """The benchmark set at ``path``: ``files``, ``notation`` and ``questions``, checked."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    seen = set()
    for q in data["questions"]:
        if q["id"] in seen:
            raise ValueError(f"question id {q['id']} appears twice")
        seen.add(q["id"])
        for field in ("topic", "question", "key", "sources"):
            if not q.get(field):
                raise ValueError(f"question {q['id']} has no {field}")
        planted = q["planted"]
        if planted is not None and (planted.get("kind") not in KINDS or not planted.get("error")):
            raise ValueError(f"question {q['id']}: a planted error needs a kind ({', '.join(KINDS)}) and an error")
    return data


def question_sets(questions: list[dict]) -> list[list[dict]]:
    """The questions in a fixed shuffled order, cut into question sets of at most SET_SIZE."""
    order = list(questions)
    random.Random(SEED).shuffle(order)
    return [order[i:i + SET_SIZE] for i in range(0, len(order), SET_SIZE)]


def _script(env: dict, script: str, command: str, data: dict) -> tuple[int, dict | str]:
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / script), command], input=json.dumps(data),
                          capture_output=True, text=True, env=env, check=False)
    return proc.returncode, (json.loads(proc.stdout) if proc.returncode == 0 else proc.stderr.strip())


def _must(env: dict, script: str, command: str, data: dict) -> dict:
    code, out = _script(env, script, command, data)
    if code != 0:
        raise RuntimeError(f"{script} {command} failed: {out}")
    return out


def build_fixture(out: Path, data: dict) -> tuple[dict, Path]:
    """The make_fixture.py course plus the set's files (registered as notes) and its notation
    in the course fingerprint. Returns (the env with the fixture HOME, the learning root)."""
    fixture = out / "fixture"
    proc = subprocess.run([sys.executable, str(HERE / "make_fixture.py"), "--out", str(fixture), "--axis", "support",
                           "--level", "method-first"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"make_fixture.py failed: {proc.stderr.strip()}")
    made = json.loads(proc.stdout)
    course_dir, env = Path(made["course_dir"]), {**os.environ, "HOME": made["home"]}
    index = course_dir / "INDEX.md"
    rows = []
    for rel, text in data["files"].items():
        (course_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (course_dir / rel).write_text(text, encoding="utf-8")
        rows.append(f"| {rel} | {TERM} | notes | 1 | text |")
    lines = index.read_text(encoding="utf-8").splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("| notes/cfg-languages.md")) + 1
    index.write_text("\n".join(lines[:at] + rows + lines[at:]) + "\n", encoding="utf-8")
    sources = list(data["files"])
    _must(env, "fingerprint.py", "write", {"term": TERM, "course": COURSE,
                                           "notation": [{"text": t, "sources": sources} for t in data["notation"]]})
    return env, Path(made["root"])


def _submit_payload(group: list[dict]) -> dict:
    return {"term": TERM, "course": COURSE, "session": SESSION, "questions": [
        {"item": f"bench:{q['id']}", "topic": q["topic"], "origin": "practice", "question": q["question"],
         "key": q["key"], "sources": [{"path": p} for p in q["sources"]]} for q in group]}


def score(rows: list[dict], batches: list[dict]) -> dict:
    """Catch rate and cost from the per-question rows and the per-batch checker runs."""
    planted = [r for r in rows if r["kind"]]
    clean = [r for r in rows if not r["kind"]]
    flagged = lambda r: r["verdict"] not in (None, "correct")  # noqa: E731
    by_kind = {k: {"planted": sum(r["kind"] == k for r in planted),
                   "caught": sum(r["kind"] == k and flagged(r) for r in planted)} for k in KINDS}
    n = len(rows) or 1
    costs = [b["cost_usd"] for b in batches]
    usage: dict[str, float] = {}
    for b in batches:
        for key, value in (b.get("usage") or {}).items():
            if isinstance(value, (int, float)):
                usage[key] = usage.get(key, 0) + value
    caught = sum(map(flagged, planted))
    return {"questions": len(rows), "planted": len(planted), "caught": caught,
            "catch_rate": round(100 * caught / len(planted), 1) if planted else None,
            "by_kind": by_kind, "clean": len(clean), "rejected": sum(map(flagged, clean)),
            "unsettled": sum(r["verdict"] is None for r in rows),
            "seconds_per_question": round(sum(b["seconds"] for b in batches) / n, 2),
            "cost_usd_per_question": None if None in costs or not costs else round(sum(costs) / n, 4),
            "usage_per_question": {k: round(v / n) for k, v in usage.items()}}


def run(out: Path, data: dict, checker: Callable[[Path], dict], parallel: int = 1) -> dict:
    """Submit every question through ``verify.py submit``, run ``checker`` on each evidence pack,
    settle each reply through ``verify.py settle`` and score the verdicts. ``checker(pack)``
    returns ``{"reply", "seconds", "usage", "cost_usd"}``. Writes ``out/results.json``."""
    out.mkdir(parents=True, exist_ok=False)
    env, _ = build_fixture(out, data)
    by_item = {f"bench:{q['id']}": q for q in data["questions"]}
    submitted = [_must(env, "verify.py", "submit", _submit_payload(group)) for group in question_sets(data["questions"])]
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        replies = list(pool.map(lambda s: checker(Path(s["pack"])), submitted))
    rows, batches = [], []
    for sub, rep in zip(submitted, replies):
        code, settled = _script(env, "verify.py", "settle", {"term": TERM, "course": COURSE, "session": SESSION,
                                                             "batch": sub["batch"], "checker": "independent",
                                                             "reply": rep["reply"]})
        verdicts = {q["item"]: q for q in settled["questions"]} if code == 0 else {}
        batches.append({"batch": sub["batch"], "seconds": rep["seconds"], "usage": rep.get("usage") or {},
                        "models": rep.get("models"),
                        "cost_usd": rep.get("cost_usd"), "settle": settled if code else settled["line"],
                        "reply": rep["reply"]})
        for q in sub["questions"]:
            src, v = by_item[q["item"]], verdicts.get(q["item"], {})
            rows.append({"id": src["id"], "batch": sub["batch"], "kind": (src["planted"] or {}).get("kind"),
                         "verdict": v.get("verdict"), "reason": v.get("reason")})
    result = {"summary": score(rows, batches), "rows": rows, "batches": batches}
    (out / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def host_cmd(host: str, pack: Path, plugin: Path | None = None, model: str | None = None,
             effort: str | None = None) -> list[str]:
    """The command that runs one host's checker on one evidence pack, as the dispatch recipe in the
    core rules does: Claude Code runs the plugin's ``mimir:verifier`` agent (its own model and effort
    unless overridden) with the one pack line; Codex and Antigravity get the helper body plus that line,
    the message a ``spawn_agent`` or ``define_subagent`` + ``invoke_subagent`` child starts from."""
    line = f"Check the evidence pack at {pack}."
    if host == "claude":
        cmd = ["claude", "-p", "--plugin-dir", str(plugin), "--agent", "mimir:verifier", "--strict-mcp-config",
               "--setting-sources", "project", "--output-format", "json"]
        cmd += ["--model", model] if model else []
        cmd += ["--effort", effort] if effort else []
        return cmd + [line]
    message = f"{VERIFIER_BODY.strip()}\n\n{line}"
    if host == "codex":
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "-s", "read-only"]
        cmd += ["-m", model] if model else []
        cmd += ["-c", f'model_reasoning_effort="{effort}"'] if effort else []
        return cmd + [message]
    if host == "antigravity":
        cmd = ["agy", "--output-format", "stream-json", "--dangerously-skip-permissions"]
        cmd += ["--model", model] if model else []
        cmd += ["--effort", effort] if effort else []
        return cmd + ["-p", message]  # -p takes the next word as the prompt
    raise ValueError(f"unknown host {host}")


def _events(stdout: str) -> list[dict]:
    out = []
    for raw in stdout.splitlines():
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def parse_output(host: str, stdout: str) -> dict:
    """``{"reply", "usage", "cost_usd"}`` from one checker run's stdout."""
    if host == "claude":
        data = json.loads(stdout)
        return {"reply": data.get("result") or "", "cost_usd": data.get("total_cost_usd"),
                "models": sorted(data.get("modelUsage") or {}),
                "usage": {k: v for k, v in (data.get("usage") or {}).items() if isinstance(v, (int, float))}}
    reply, usage = "", {}
    for ev in _events(stdout):
        if host == "codex":
            item = ev.get("item") or {}
            if ev.get("type") == "item.completed" and item.get("type") == "agent_message":
                reply = item.get("text", "")
            if ev.get("type") == "turn.completed":
                usage = ev.get("usage") or {}
        elif ev.get("event") == "result":
            reply = (ev.get("result") or {}).get("response", "")
            usage = (ev.get("result") or {}).get("usage") or {}
    return {"reply": reply, "cost_usd": None, "usage": usage}


def host_checker(host: str, codex_home: Path | None = None, **opts) -> Callable[[Path], dict]:
    """A checker for ``run``: one host process per evidence pack, in the fixture's learning root
    with the fixture's HOME (Claude Code lean, as ``drive.py`` runs it; Codex with ``codex_home``),
    timed by the wall clock."""
    lock = threading.Lock()

    def check(pack: Path) -> dict:
        root = pack.parents[4]
        env = {**os.environ, "HOME": str(root.parent / "home")}
        if host == "claude":
            with lock:  # packs are checked in parallel; the home is made once
                lean_claude_home(root.parent / "home")
        if host == "codex":
            env["CODEX_HOME"] = str(codex_home)
        start = time.monotonic()
        proc = subprocess.run(host_cmd(host, pack, **opts), cwd=root, env=env, capture_output=True, text=True,
                              timeout=1200, check=False)
        seconds = round(time.monotonic() - start, 1)
        try:
            parsed = parse_output(host, proc.stdout)
        except json.JSONDecodeError:
            parsed = {"reply": "", "cost_usd": None, "usage": {}}
        return {**parsed, "seconds": seconds, "exit": proc.returncode, "stderr": proc.stderr[-2000:]}
    return check


def report_row(label: str, s: dict) -> str:
    conv, gen = s["by_kind"]["convention"], s["by_kind"]["general"]
    cost = f"${s['cost_usd_per_question']:.4f}" if s["cost_usd_per_question"] is not None else "–"
    u = s["usage_per_question"]
    tokens = sum(v for k, v in u.items() if "output" not in k and "thinking" not in k)
    return (f"| {label} | {s['caught']}/{s['planted']} ({s['catch_rate']}%) | {gen['caught']}/{gen['planted']} | "
            f"{conv['caught']}/{conv['planted']} | {s['rejected']}/{s['clean']} | {s['unsettled']} | "
            f"{s['seconds_per_question']} s | {tokens:,} in / {sum(v for k, v in u.items() if 'output' in k or 'thinking' in k):,} out | {cost} |")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--host", required=True, choices=["claude", "codex", "antigravity"])
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--plugin", type=Path)
    r.add_argument("--codex-home", type=Path)
    r.add_argument("--model")
    r.add_argument("--effort")
    r.add_argument("--parallel", type=int, default=3)
    rep = sub.add_parser("report")
    rep.add_argument("dirs", nargs="+", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "report":
        print("| Run | Planted caught | General | Convention | Clean rejected | Unsettled | Time per question "
              "| Tokens per question | Cost per question |")
        print("|---|---|---|---|---|---|---|---|---|")
        for d in args.dirs:
            print(report_row(d.name, json.loads((d / "results.json").read_text(encoding="utf-8"))["summary"]))
        return 0
    if args.host == "claude" and not args.plugin:
        ap.error("--plugin is required for claude")
    if args.host == "codex" and not args.codex_home:
        ap.error("--codex-home is required for codex")
    opts = {"model": args.model, "effort": args.effort}
    if args.host == "claude":
        opts["plugin"] = args.plugin.resolve()
    checker = host_checker(args.host, codex_home=args.codex_home.resolve() if args.codex_home else None, **opts)
    result = run(args.out.resolve(), load_set(SET_PATH), checker, parallel=args.parallel)
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
