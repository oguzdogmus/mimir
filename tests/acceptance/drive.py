#!/usr/bin/env python3
"""Send one student message to a Mimir host session and print the tutor's reply.

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/drive.py --run DIR --host claude|codex|antigravity --plugin PLUGIN_DIR \
        [--codex-home CODEX_HOME] [--agy-home AGY_HOME] "student message"

DIR is a folder from ``make_fixture.py``. The first call starts a new host
session in ``DIR/learning`` with ``HOME=DIR/home``; later calls resume it (the
session id is kept in ``DIR/session_id``). Claude Code runs lean, with
``--plugin-dir PLUGIN_DIR`` and nothing else: no MCP connectors, no user
settings, plugins, skills or hooks (a fresh ``~/.claude`` with only the
login), on ``--model`` (default sonnet); Codex runs with ``CODEX_HOME`` (a home where
Mimir is installed from PLUGIN_DIR); Antigravity runs ``agy -p`` with
``--add-dir PLUGIN_DIR`` (the installed plugin folder) and ``DIR/home/.gemini``
linked to ``AGY_HOME/.gemini`` (a home where Mimir is installed with ``agy
plugin install``). All three run without permission prompts, so use them only
on a fixture folder.

Each turn appends the student message, the tool calls (one line each) and
the tutor's reply to ``DIR/transcript.md``, saves the raw host events as
``DIR/events/turn-N.jsonl`` and prints the reply. On Antigravity it also copies
the conversation's full transcript to ``DIR/events/agy-transcript-full.jsonl``:
agy's stream leaves out a ``define_subagent`` call's system prompt and tool
switches, which check G needs. Antigravity's usage line and seconds are totals
for the conversation so far, not for the turn.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from speed_checks import FULL_TRANSCRIPT, antigravity_definitions, antigravity_steps, from_verifier

TIMEOUT = 1800


def short(value: object, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def lean_claude_home(home: Path) -> None:
    """A fresh ``home/.claude`` holding only the login, so none of the user's own
    skills, plugins, hooks or memory load into the host."""
    (home / ".claude").mkdir(exist_ok=True)
    creds = home / ".claude" / ".credentials.json"
    if not creds.exists():
        creds.symlink_to(Path.home() / ".claude" / ".credentials.json")
    if not (home / ".claude.json").exists() and (Path.home() / ".claude.json").exists():
        (home / ".claude.json").write_bytes((Path.home() / ".claude.json").read_bytes())


def claude_cmd(args, session: str | None) -> list[str]:
    # Lean host: only Mimir. No MCP connectors (their tool lists are large and change
    # while they connect, which voids the prompt cache) and no user settings, plugins or hooks.
    cmd = ["claude", "-p", "--plugin-dir", str(args.plugin), "--dangerously-skip-permissions",
           "--strict-mcp-config", "--setting-sources", "project", "--model", args.model,
           "--output-format", "stream-json", "--verbose"]
    if session:
        cmd += ["--resume", session]
    return cmd + [args.message]


def codex_cmd(args, session: str | None) -> list[str]:
    base = ["codex", "exec"]
    if session:
        base += ["resume", session]
    return base + ["--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox", "--json", args.message]


def agy_cmd(args, session: str | None) -> list[str]:
    # The plugin folder is added to the workspace, as the README's launch command does.
    cmd = ["agy", "--add-dir", str(args.plugin), "--dangerously-skip-permissions", "--output-format", "stream-json"]
    if args.model:
        cmd += ["--model", args.model]
    if session:
        cmd += ["--conversation", session]
    return cmd + ["-p", args.message]  # -p takes the next word as the prompt


def parse_antigravity(lines: list[dict], definitions: dict | None = None) -> tuple[str | None, list[str], str]:
    """``definitions``: the conversation's ``define_subagent`` arguments by name, from its full
    transcript (agy's stream leaves out the system prompt and the tool switches)."""
    session, tools, texts = None, [], []
    for ev in lines:
        session = ev.get("conversation_id") or (ev.get("result") or {}).get("conversation_id") or session
    for step in antigravity_steps(lines):
        if step[0] == "text":
            texts.append(step[1])
            continue
        _, name, inp, _ = step
        if name == "run_command":
            tools.append(f"run_command: {short(inp['command'])}")
        elif name == "define_subagent":
            inp = {**inp, **(definitions or {}).get(inp.get("name"), {})}
            tools.append(f"define_subagent name={inp.get('name')} from_verifier={from_verifier(inp.get('system_prompt', ''))} "
                         f"write={inp.get('enable_write_tools')} mcp={inp.get('enable_mcp_tools')} "
                         f"subagents={inp.get('enable_subagent_tools')}")
        elif name == "invoke_subagent":
            tools.append(f"invoke_subagent type={inp.get('TypeName')}: {short(inp.get('prompt', ''))}")
        else:
            tools.append(f"{name}: {short(inp)}")
    for ev in lines:
        if ev.get("event") == "result":
            r = ev.get("result") or {}
            u = r.get("usage") or {}
            tools.append(f"usage: input={u.get('input_tokens', 0)} cache_read={u.get('cache_read_tokens', 0)} "
                         f"out={u.get('output_tokens', 0)} thinking={u.get('thinking_tokens', 0)} "
                         f"seconds={r.get('duration_seconds')}")
    return session, tools, "\n\n".join(texts)


def parse_claude(lines: list[dict]) -> tuple[str | None, list[str], str]:
    session, tools, texts = None, [], []
    for ev in lines:
        session = ev.get("session_id") or session
        if ev.get("type") == "assistant" and not ev.get("parent_tool_use_id"):
            for part in ev.get("message", {}).get("content", []):
                if part.get("type") == "text" and part.get("text", "").strip():
                    texts.append(part["text"])
                if part.get("type") == "tool_use":
                    inp = part.get("input", {})
                    name = part.get("name")
                    if name in ("Agent", "Task"):
                        tools.append(f"{name} subagent_type={inp.get('subagent_type')} "
                                     f"run_in_background={inp.get('run_in_background')}: "
                                     f"{short(inp.get('description') or inp.get('prompt'))}")
                    else:
                        tools.append(f"{name}: {short(inp.get('command') or inp.get('file_path') or inp.get('skill') or inp)}")
        if ev.get("type") == "result":
            u = ev.get("usage") or {}
            tools.append(f"usage: cache_write={u.get('cache_creation_input_tokens', 0)} "
                         f"cache_read={u.get('cache_read_input_tokens', 0)} out={u.get('output_tokens', 0)} "
                         f"cost_usd={ev.get('total_cost_usd')}")
    # Every text the tutor wrote this turn, in order: the class line often comes first.
    return session, tools, "\n\n".join(texts)


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
    ap.add_argument("--host", required=True, choices=["claude", "codex", "antigravity"])
    ap.add_argument("--plugin", required=True, type=Path)
    ap.add_argument("--codex-home", type=Path)
    ap.add_argument("--agy-home", type=Path, help="Antigravity: a HOME whose .gemini has Mimir installed")
    ap.add_argument("--model", help="host model (Claude Code default sonnet, opus costs more; others: the host default)")
    ap.add_argument("message")
    args = ap.parse_args()
    run = args.run.resolve()
    home, learning = run / "home", run / "learning"
    if not (home / ".config" / "mimir" / "root").is_file():
        sys.exit(f"drive: {run} is not a make_fixture.py folder")
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    if args.host == "claude":
        lean_claude_home(home)
        args.model = args.model or "sonnet"
    elif args.host == "codex":
        if not args.codex_home:
            sys.exit("drive: --codex-home is required for codex")
        env["CODEX_HOME"] = str(args.codex_home.resolve())
    else:
        # Antigravity keeps its config, plugins and conversations in ~/.gemini: link the
        # installed home's, so the fixture's HOME (and its learning-root pointer) stays.
        if not args.agy_home or not (args.agy_home / ".gemini").is_dir():
            sys.exit("drive: --agy-home must be a HOME with Mimir installed (agy plugin install)")
        gemini = home / ".gemini"
        if not gemini.exists():
            gemini.symlink_to((args.agy_home / ".gemini").resolve())

    id_file = run / "session_id"
    session = id_file.read_text().strip() if id_file.exists() else None
    cmd = {"claude": claude_cmd, "codex": codex_cmd, "antigravity": agy_cmd}[args.host](args, session)
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
    if args.host == "antigravity":
        conversation = session or next((ev.get("conversation_id") for ev in lines if ev.get("conversation_id")), None)
        full = home / ".gemini" / "antigravity-cli" / "brain" / str(conversation) / ".system_generated" / "logs" / "transcript_full.jsonl"
        if conversation and full.is_file():
            (events_dir / FULL_TRANSCRIPT).write_bytes(full.read_bytes())
        new_session, tools, reply = parse_antigravity(lines, antigravity_definitions(events_dir / FULL_TRANSCRIPT))
    else:
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
