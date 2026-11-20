#!/usr/bin/env python3
"""Count the speed rules of #77 and the checker rule of #78 in a Claude Code acceptance run.

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/speed_checks.py RUN_DIR

RUN_DIR is a ``drive.py`` run folder; its raw host events are
``RUN_DIR/events/turn-N.jsonl``. Only the tutor's own steps count (events of
a subagent, which carry a ``parent_tool_use_id``, are skipped). Per turn:

* **J** a turn with a ``session.py record`` call (an answer turn) writes text
  before its first tool call: the feedback comes first.
* **K** a turn with a ``verify.py submit`` call writes text before its first
  submit call and before its first checker dispatch. The report quotes the
  last text before the submit, so the tester can confirm it is the set's
  first practice question (or the explanation, the recipe or the first real
  question).
* **L** at most 2 checker dispatches in a turn (one batch per question set
  plus at most one recheck batch), and at most 6 questions in any submit call.
* **M** no checker dispatch in the background: neither ``run_in_background``
  true on the ``Agent`` call nor ``is_backgrounded`` (or ``is_background``) true
  when its task starts.
* **N** every ``verify.py settle`` call follows a checker dispatch made in the
  same turn after the previous settle call: no batch is settled without a
  checker call (#23).

A checker dispatch is an ``Agent`` (or ``Task``) call with ``subagent_type``
``mimir:verifier``. Prints one line per finding and a ``J K L M N`` summary;
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
        if ev.get("type") == "system" and ev.get("subtype") == "task_started" and (ev.get("is_background") or ev.get("is_backgrounded")):
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


def is_submit(step: tuple) -> bool:
    """A ``verify.py submit`` call: it prepares a question set for its check."""
    return bool(re.search(r"verify\.py\"?\s+submit\b", _command(step)))


def is_settle(step: tuple) -> bool:
    return bool(re.search(r"verify\.py\"?\s+settle\b", _command(step)))


def is_record(step: tuple) -> bool:
    return bool(re.search(r"session\.py\"?\s+record\b", _command(step)))


def is_dispatch(step: tuple) -> bool:
    return step[0] == "tool" and step[1] in ("Agent", "Task") and step[2].get("subagent_type") == "mimir:verifier"


def submit_questions(step: tuple) -> int:
    """How many questions a submit call sends: the ``questions`` list of its JSON input."""
    command = _command(step)
    start = command.find("{")
    end = command.rfind("}")
    try:
        return len(json.loads(command[start:end + 1]).get("questions", []))
    except (ValueError, AttributeError):
        return len(re.findall(r'"item"\s*:', command))


def check_turn(events: list[dict]) -> dict[str, list[str]]:
    """Findings per check (``J``, ``K``, ``L``, ``M``) for one turn; an empty list is a pass.
    ``K`` also carries ``ok:`` lines quoting the text before each turn's first submit call."""
    seq, background = steps(events)
    found: dict[str, list[str]] = {"J": [], "K": [], "L": [], "M": [], "N": []}
    tools = [i for i, s in enumerate(seq) if s[0] == "tool"]
    if any(is_record(s) for s in seq) and tools and tools[0] == 0:
        found["J"].append(f"answer turn starts with a tool call ({seq[0][1]}) before any text")
    submits = [i for i, s in enumerate(seq) if is_submit(s)]
    dispatches = [i for i, s in enumerate(seq) if is_dispatch(s)]
    if submits or dispatches:
        first = min(submits + dispatches)
        texts = [s[1] for s in seq[:first] if s[0] == "text"]
        if not texts:
            found["K"].append("no text before the first submit call or checker dispatch")
        else:
            found.setdefault("K_ok", []).append(" ".join(texts[-1].split())[:120])
    if len(dispatches) > MAX_DISPATCHES:
        found["L"].append(f"{len(dispatches)} checker dispatches in one turn (at most {MAX_DISPATCHES})")
    for i in submits:
        if submit_questions(seq[i]) > MAX_SET:
            found["L"].append(f"a submit call with {submit_questions(seq[i])} questions (a set holds at most {MAX_SET})")
    for i in dispatches:
        if seq[i][2].get("run_in_background") is True or seq[i][3] in background:
            found["M"].append("checker dispatched in the background")
    since = -1
    for i in (i for i, s in enumerate(seq) if is_settle(s)):
        if not any(since < d < i for d in dispatches):
            found["N"].append("a batch settled without a checker dispatch since the previous settle")
        since = i
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
            print(f"{path.stem} K ok, text before the submit: {line}")
        for check, lines in found.items():
            for line in lines:
                failed.add(check)
                print(f"{path.stem} {check} FAIL: {line}")
    print(" ".join(f"{c} {'FAIL' if c in failed else 'PASS'}" for c in "JKLMN"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
