#!/usr/bin/env python3
"""Send one student message to a Mimir host session and print the tutor's reply.

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/drive.py --run DIR --host claude|codex --plugin PLUGIN_DIR \
        [--codex-home CODEX_HOME] "student message"

DIR is a folder from ``make_fixture.py``. The first call starts a new host
session in ``DIR/learning`` with ``HOME=DIR/home``; later calls resume it (the
session id is kept in ``DIR/session_id``). Claude Code runs with
``--plugin-dir PLUGIN_DIR``; Codex runs with ``CODEX_HOME`` (a home where
Mimir is installed from PLUGIN_DIR). Both run without permission prompts, so
use them only on a fixture folder.

Each turn appends the student message, the tool calls (one line each) and
the tutor's reply to ``DIR/transcript.md``, saves the raw host events as
``DIR/events/turn-N.jsonl`` and prints the reply.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

TIMEOUT = 1800


def short(value: object, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def claude_cmd(args, session: str | None) -> list[str]:
    cmd = ["claude", "-p", "--plugin-dir", str(args.plugin), "--dangerously-skip-permissions",
           "--output-format", "stream-json", "--verbose"]
    if session:
        cmd += ["--resume", session]
    return cmd + [args.message]


def codex_cmd(args, session: str | None) -> list[str]:
    base = ["codex", "exec"]
    if session:
        base += ["resume", session]
    return base + ["--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox", "--json", args.message]


def parse_claude(lines: list[dict]) -> tuple[str | None, list[str], str]:
    session, tools, reply = None, [], ""
    for ev in lines:
        session = ev.get("session_id") or session
        if ev.get("type") == "assistant":
            for part in ev.get("message", {}).get("content", []):
                if part.get("type") == "tool_use":
                    inp = part.get("input", {})
                    name = part.get("name")
                    if name in ("Agent", "Task"):
                        tools.append(f"{name} subagent_type={inp.get('subagent_type')}: {short(inp.get('description') or inp.get('prompt'))}")
                    else:
                        tools.append(f"{name}: {short(inp.get('command') or inp.get('file_path') or inp.get('skill') or inp)}")
        if ev.get("type") == "result":
            reply = ev.get("result") or ""
    return session, tools, reply


def parse_codex(lines: list[dict]) -> tuple[str | None, list[str], str]:
    session, tools, replies = None, [], []
    # Every agent message of the turn, in order: the class line often comes before the lesson.
    for ev in lines:
        if ev.get("type") == "thread.started":
            session = ev.get("thread_id")
        item = ev.get("item") or {}
        if ev.get("type") != "item.completed":
            continue
        kind = item.get("type")
        if kind == "agent_message":
            replies.append(item.get("text", ""))
        elif kind == "command_execution":
            tools.append(f"command: {short(item.get('command'))}")
        elif kind not in ("reasoning",):
            tools.append(f"{kind}: {short({k: v for k, v in item.items() if k not in ('id', 'type')})}")
    return session, tools, "\n\n".join(r for r in replies if r.strip())


def codex_spawns(codex_home: Path, session: str, seen: int) -> tuple[list[str], int]:
    """New spawn_agent calls in the parent rollout, with how much context each child got."""
    found = []
    for rollout in sorted((codex_home / "sessions").rglob(f"rollout-*{session}.jsonl")):
        for raw in rollout.read_text(encoding="utf-8").splitlines():
            if '"spawn_agent"' not in raw or '"arguments"' not in raw:
                continue
            try:
                payload = json.loads(raw).get("payload", {})
                spawn = json.loads(payload.get("arguments", "{}"))
            except (json.JSONDecodeError, AttributeError):
                continue
            if payload.get("name") == "spawn_agent":
                found.append(f"spawn_agent task_name={spawn.get('task_name')} fork_turns={spawn.get('fork_turns', 'none')} "
                             f"agent_type={spawn.get('agent_type')}")
    return found[seen:], len(found)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--host", required=True, choices=["claude", "codex"])
    ap.add_argument("--plugin", required=True, type=Path)
    ap.add_argument("--codex-home", type=Path)
    ap.add_argument("message")
    args = ap.parse_args()
    run = args.run.resolve()
    home, learning = run / "home", run / "learning"
    if not (home / ".config" / "mimir" / "root").is_file():
        sys.exit(f"drive: {run} is not a make_fixture.py folder")
    env = {**os.environ, "HOME": str(home)}
    if args.host == "claude":
        for name in (".claude", ".claude.json"):
            real, fake = Path.home() / name, home / name
            if real.exists() and not fake.exists():
                if real.is_dir():
                    fake.symlink_to(real)
                else:
                    fake.write_bytes(real.read_bytes())
    else:
        if not args.codex_home:
            sys.exit("drive: --codex-home is required for codex")
        env["CODEX_HOME"] = str(args.codex_home.resolve())

    id_file = run / "session_id"
    session = id_file.read_text().strip() if id_file.exists() else None
    cmd = claude_cmd(args, session) if args.host == "claude" else codex_cmd(args, session)
    proc = subprocess.run(cmd, cwd=learning, env=env, capture_output=True, text=True, timeout=TIMEOUT, check=False)

    events_dir = run / "events"
    events_dir.mkdir(exist_ok=True)
    turn = len(list(events_dir.glob("turn-*.jsonl"))) + 1
    (events_dir / f"turn-{turn}.jsonl").write_text(proc.stdout + ("\n# stderr\n" + proc.stderr if proc.stderr else ""), encoding="utf-8")
    lines = []
    for raw in proc.stdout.splitlines():
        try:
            lines.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    new_session, tools, reply = (parse_claude if args.host == "claude" else parse_codex)(lines)
    if new_session and not session:
        id_file.write_text(new_session + "\n")
    if args.host == "codex" and (session or new_session):
        count_file = run / "spawn_count"
        seen = int(count_file.read_text()) if count_file.exists() else 0
        spawns, total = codex_spawns(Path(env["CODEX_HOME"]), session or new_session, seen)
        count_file.write_text(str(total))
        tools += spawns
    if proc.returncode != 0 and not reply:
        reply = f"(host exited {proc.returncode}: {short(proc.stderr, 400)})"

    with (run / "transcript.md").open("a", encoding="utf-8") as fh:
        fh.write(f"\n## Turn {turn}\n\n**Student:** {args.message}\n\n")
        if tools:
            fh.write("Tool calls:\n" + "".join(f"- {t}\n" for t in tools) + "\n")
        fh.write(f"**Tutor:**\n\n{reply}\n")
    print(reply)
    if tools:
        print("\n[tool calls this turn: " + "; ".join(t.split(":")[0] for t in tools) + "]")


if __name__ == "__main__":
    main()
