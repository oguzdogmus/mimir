#!/usr/bin/env python3
"""Count the speed rules of #77 in a Claude Code acceptance run.

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/speed_checks.py RUN_DIR

RUN_DIR is a ``drive.py`` run folder; its raw host events are
``RUN_DIR/events/turn-N.jsonl``. Only the tutor's own steps count (events of
a subagent, which carry a ``parent_tool_use_id``, are skipped). Per turn:

* **J** a turn with a ``session.py record`` call (an answer turn) writes text
  before its first tool call: the feedback comes first.
* **K** a turn with a ``verify.py gate`` call writes text before its first
  gate call and before its first checker dispatch. The report quotes the last
  text before the gate, so the tester can confirm it is the set's first
  practice question (or the explanation, the recipe or the wait line).
* **L** at most 2 checker dispatches in a turn (one batch per question set
  plus at most one recheck batch), and at most 6 items in any gate call.
* **M** no checker dispatch in the background: neither ``run_in_background``
  true on the ``Agent`` call nor ``is_background`` true when its task starts.

A checker dispatch is an ``Agent`` (or ``Task``) call with ``subagent_type``
``mimir:verifier``. Prints one line per finding and a ``J K L M`` summary;
exits 0 when every check passes, else 1.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MAX_SET = 6
MAX_DISPATCHES = 2


def steps(events: list[dict]) -> tuple[list[tuple], set[str]]:
    """The tutor's own steps in order, ``("text", str)`` or ``("tool", name, input, id)``,
    and the ids of tool calls whose task started in the background."""
    out, background = [], set()
    for ev in events:
        if ev.get("type") == "system" and ev.get("subtype") == "task_started" and ev.get("is_background"):
            background.add(ev.get("tool_use_id"))
        if ev.get("type") != "assistant" or ev.get("parent_tool_use_id"):
            continue
        for part in ev.get("message", {}).get("content", []):
            if part.get("type") == "text" and part.get("text", "").strip():
                out.append(("text", part["text"]))
            elif part.get("type") == "tool_use":
                out.append(("tool", part.get("name"), part.get("input") or {}, part.get("id")))
    return out, background


def _command(step: tuple) -> str:
    return step[2].get("command", "") if step[0] == "tool" and step[1] == "Bash" else ""


def is_gate(step: tuple) -> bool:
    return bool(re.search(r"verify\.py\"?\s+gate\b", _command(step)))


def is_record(step: tuple) -> bool:
    return bool(re.search(r"session\.py\"?\s+record\b", _command(step)))


def is_dispatch(step: tuple) -> bool:
    return step[0] == "tool" and step[1] in ("Agent", "Task") and step[2].get("subagent_type") == "mimir:verifier"


def gate_items(step: tuple) -> int:
    """How many items a gate call sends: the ``items`` list of its JSON input."""
    command = _command(step)
    start = command.find("{")
    end = command.rfind("}")
    try:
        return len(json.loads(command[start:end + 1]).get("items", []))
    except (ValueError, AttributeError):
        return len(re.findall(r'"topic"\s*:', command))


def check_turn(events: list[dict]) -> dict[str, list[str]]:
    """Findings per check (``J``, ``K``, ``L``, ``M``) for one turn; an empty list is a pass.
    ``K`` also carries ``ok:`` lines quoting the text before each turn's first gate call."""
    seq, background = steps(events)
    found: dict[str, list[str]] = {"J": [], "K": [], "L": [], "M": []}
    tools = [i for i, s in enumerate(seq) if s[0] == "tool"]
    if any(is_record(s) for s in seq) and tools and tools[0] == 0:
        found["J"].append(f"answer turn starts with a tool call ({seq[0][1]}) before any text")
    gates = [i for i, s in enumerate(seq) if is_gate(s)]
    dispatches = [i for i, s in enumerate(seq) if is_dispatch(s)]
    if gates or dispatches:
        first = min(gates + dispatches)
        texts = [s[1] for s in seq[:first] if s[0] == "text"]
        if not texts:
            found["K"].append("no text before the first gate call or checker dispatch")
        else:
            found.setdefault("K_ok", []).append(" ".join(texts[-1].split())[:120])
    if len(dispatches) > MAX_DISPATCHES:
        found["L"].append(f"{len(dispatches)} checker dispatches in one turn (at most {MAX_DISPATCHES})")
    for i in gates:
        if gate_items(seq[i]) > MAX_SET:
            found["L"].append(f"a gate call with {gate_items(seq[i])} items (a set holds at most {MAX_SET})")
    for i in dispatches:
        if seq[i][2].get("run_in_background") is True or seq[i][3] in background:
            found["M"].append("checker dispatched in the background")
    return found


def load(path: Path) -> list[dict]:
    events = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return events


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.exit("usage: speed_checks.py RUN_DIR")
    turns = sorted((Path(argv[0]) / "events").glob("turn-*.jsonl"), key=lambda p: int(p.stem.split("-")[1]))
    if not turns:
        sys.exit(f"speed_checks: no events in {argv[0]}")
    failed = set()
    for path in turns:
        found = check_turn(load(path))
        for line in found.pop("K_ok", []):
            print(f"{path.stem} K ok, text before the gate: {line}")
        for check, lines in found.items():
            for line in lines:
                failed.add(check)
                print(f"{path.stem} {check} FAIL: {line}")
    print(" ".join(f"{c} {'FAIL' if c in failed else 'PASS'}" for c in "JKLM"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
