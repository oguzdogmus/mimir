"""Mimir visual builder, part 3: the machine a page's automata simulator runs.

Standard library only, Python 3.11+. ``parse_machine`` and ``parse_example`` check the ``machine`` and
``example`` fields of ``visual.py page`` (see its docstring); ``simulator_html`` and ``machine_data`` are the
simulator controls, the machine as a table and the simulator's JSON data that the page shell adds.
"""

from __future__ import annotations

import html

import verify
import workspace
from workspace import InputError

MACHINE_MAX_STATES = 60
MACHINE_MAX_TRANSITIONS = 400
STATE_NAME_MAX_CHARS = 20
MACHINE_MAX_SYMBOLS = 64         # symbols in one fed input
EXAMPLE_MAX_CHARS = 4000       # the example input, spaces included
MACHINE_MAX_CONFIGS = 256        # configurations followed at once (NFA/PDA)
MACHINE_MAX_STACK = 64           # PDA stack depth

_MACHINE_KINDS = ("dfa", "nfa", "pda", "tree")
_KIND_TEXT = {"dfa": "DFA", "nfa": "NFA", "pda": "PDA, accepting by final state",
              "tree": "tree: the input walks the labelled edges from the root"}


def _symbol(value, where: str, epsilon: bool) -> str:
    """One input or stack symbol: a single character that is not a space; "" is ε when allowed."""
    if isinstance(value, str) and value == "" and epsilon:
        return value
    if (not isinstance(value, str) or len(value) != 1 or value.isspace() or workspace.has_control(value)
            or ord(value) > 0xFFFF):
        also = ' or "" for ε' if epsilon else ""
        raise InputError(f"{where} must be one character that is not a space and not outside the Basic "
                         f"Multilingual Plane (e.g. not an emoji){also}: {workspace.short(value)}")
    return value


def _state(value, where: str, states: list[str]) -> str:
    name = verify._text(value, where, STATE_NAME_MAX_CHARS)
    if name not in states:
        raise InputError(f"{where}: {workspace.short(name)} is not one of machine.states")
    return name


def parse_machine(value) -> dict:
    """Check a machine and return it normalized (see the docstring)."""
    if not isinstance(value, dict):
        raise InputError("machine must be an object")
    verify._keys(value, {"kind", "states", "start", "accept", "transitions", "stack_start"}, "machine")
    kind = value.get("kind")
    if kind not in _MACHINE_KINDS:
        raise InputError(f"machine.kind must be one of {', '.join(_MACHINE_KINDS)}: {workspace.short(kind)}")
    pda = kind == "pda"
    raw_states = value.get("states")
    if not isinstance(raw_states, list) or not raw_states:
        raise InputError("machine.states is required (a non-empty list of state names)")
    if len(raw_states) > MACHINE_MAX_STATES:
        raise InputError(f"machine.states has {len(raw_states)} states; at most {MACHINE_MAX_STATES}")
    states: list[str] = []
    for i, item in enumerate(raw_states, 1):
        name = verify._text(item, f"machine.states[{i}]", STATE_NAME_MAX_CHARS)
        if name in states:
            raise InputError(f"machine.states[{i}]: {workspace.short(name)} is listed twice")
        states.append(name)
    if "start" not in value:
        raise InputError("machine.start is required")
    start = _state(value["start"], "machine.start", states)
    raw_accept = value.get("accept", [])
    if not isinstance(raw_accept, list):
        raise InputError("machine.accept must be a list of state names")
    accept: list[str] = []
    for i, item in enumerate(raw_accept, 1):
        name = _state(item, f"machine.accept[{i}]", states)
        if name in accept:
            raise InputError(f"machine.accept[{i}]: {workspace.short(name)} is listed twice")
        accept.append(name)
    if pda:
        if "stack_start" not in value:
            raise InputError("machine.stack_start is required for a pda (one stack symbol)")
        stack_start = _symbol(value["stack_start"], "machine.stack_start", epsilon=False)
    elif "stack_start" in value:
        raise InputError(f"machine.stack_start is only for a pda, not a {kind}")
    raw_moves = value.get("transitions")
    if not isinstance(raw_moves, list):
        raise InputError("machine.transitions is required (a list of moves)")
    if len(raw_moves) > MACHINE_MAX_TRANSITIONS:
        raise InputError(f"machine.transitions has {len(raw_moves)} moves; at most {MACHINE_MAX_TRANSITIONS}")
    moves, seen = [], set()
    for i, item in enumerate(raw_moves, 1):
        where = f"machine.transitions[{i}]"
        if not isinstance(item, dict):
            raise InputError(f"{where} must be an object {{from, read, to}}")
        for extra in ("pop", "push"):
            if extra in item and not pda:
                raise InputError(f"{where}.{extra} is only for a pda, not a {kind}")
        verify._keys(item, {"from", "read", "to", "pop", "push"}, where)
        for field in ("from", "read", "to"):
            if field not in item:
                raise InputError(f"{where}.{field} is required")
        move = {"from": _state(item["from"], f"{where}.from", states),
                "read": _symbol(item["read"], f"{where}.read", epsilon=kind in ("nfa", "pda")),
                "to": _state(item["to"], f"{where}.to", states)}
        if pda:
            move["pop"] = _symbol(item.get("pop", ""), f"{where}.pop", epsilon=True)
            push = item.get("push", "")
            if not isinstance(push, str) or len(push) > MACHINE_MAX_STACK:
                raise InputError(f"{where}.push must be a string of at most {MACHINE_MAX_STACK} stack symbols")
            for c in push:
                _symbol(c, f"{where}.push", epsilon=False)
            move["push"] = push
        if kind in ("dfa", "tree"):
            if (move["from"], move["read"]) in seen:
                raise InputError(f"{where}: a second move from {workspace.short(move['from'])} on "
                                 f"{workspace.short(move['read'])} (a {kind} has at most one)")
            seen.add((move["from"], move["read"]))
        moves.append(move)
    if kind == "tree":
        parents = {name: [m["from"] for m in moves if m["to"] == name] for name in states}
        if parents[start]:
            raise InputError(f"machine.transitions: the root {workspace.short(start)} of a tree has an incoming edge")
        for name in states:
            if name != start and len(parents[name]) != 1:
                raise InputError(f"machine.transitions: tree node {workspace.short(name)} has {len(parents[name])} "
                                 "incoming edges; every node but the root has exactly one")
        reached, queue = {start}, [start]
        while queue:
            here = queue.pop()
            for m in moves:
                if m["from"] == here and m["to"] not in reached:
                    reached.add(m["to"])
                    queue.append(m["to"])
        lost = [name for name in states if name not in reached]
        if lost:
            raise InputError(f"machine.transitions: tree node {workspace.short(lost[0])} cannot be reached "
                             "from the root")
    out = {"kind": kind, "states": states, "start": start, "accept": accept, "transitions": moves}
    if pda:
        out["stack_start"] = stack_start
    return out


def _machine_html(machine: dict) -> str:
    def cell(text: str) -> str:
        return f"<td>{html.escape(text) if text else 'ε'}</td>"

    pda = machine["kind"] == "pda"
    accept = ", ".join(machine["accept"]) or "none"
    facts = (f"Kind: {_KIND_TEXT[machine['kind']]}. Start state: {machine['start']}. "
             f"Accepting states: {accept}.")
    if pda:
        facts += f" Stack start symbol: {machine['stack_start']}; the first pushed symbol becomes the top."
    head = "<th scope=\"col\">From</th><th scope=\"col\">Read</th>"
    if pda:
        head += "<th scope=\"col\">Pop</th><th scope=\"col\">Push</th>"
    head += "<th scope=\"col\">To</th>"
    body = []
    for m in machine["transitions"]:
        cells = cell(m["from"]) + cell(m["read"])
        if pda:
            cells += cell(m["pop"]) + cell(m["push"])
        body.append(f"<tr>{cells}{cell(m['to'])}</tr>")
    if not body:
        body.append(f"<tr><td colspan=\"{5 if pda else 3}\">No moves.</td></tr>")
    return (f"<p>{html.escape(facts)}</p>\n<div class=\"table-wrap\"><table>\n<thead><tr>{head}</tr></thead>\n"
            "<tbody>\n" + "\n".join(body) + "\n</tbody>\n</table></div>")


def parse_example(data: dict) -> str:
    """The optional input the simulator starts with."""
    if data.get("example") is None:
        return ""
    example = verify._text(data["example"], "example", EXAMPLE_MAX_CHARS, required=False)
    symbols = sum(1 for c in example if not c.isspace())
    if symbols > MACHINE_MAX_SYMBOLS:
        raise InputError(f"example has {symbols} symbols; at most {MACHINE_MAX_SYMBOLS}")
    return example


def machine_data(machine: dict) -> dict:
    """The simulator's JSON data: the machine and its limits."""
    return {**machine, "max_configs": MACHINE_MAX_CONFIGS, "max_stack": MACHINE_MAX_STACK,
            "max_symbols": MACHINE_MAX_SYMBOLS}


def simulator_html(machine: dict, example: str) -> str:
    """The shell's simulator controls and the machine as a table, placed after the builder's body."""
    return (
        '\n<section class="sim" id="mimir-sim">\n<div id="mimir-sim-controls" hidden>\n'
        "<h2>Feed an input</h2>\n"
        f'<p><label for="mimir-sim-input">Input</label> <input type="text" id="mimir-sim-input" '
        f'value="{html.escape(example)}" autocomplete="off" spellcheck="false" '
        'aria-describedby="mimir-sim-hint"></p>\n'
        f'<p class="sim-hint" id="mimir-sim-hint">One symbol per character; spaces are ignored. '
        f"At most {MACHINE_MAX_SYMBOLS} symbols.</p>\n"
        '<p class="sim-buttons"><button type="button" id="mimir-sim-start">Start</button>'
        '<button type="button" id="mimir-sim-next">Next symbol</button>'
        '<button type="button" id="mimir-sim-back">Back</button></p>\n'
        '<p class="sim-hint">Enter in the input field starts; on the buttons, the right arrow reads the next '
        "symbol and the left arrow goes back. The current states are marked in the diagram.</p>\n"
        '<p id="mimir-sim-status" role="status" aria-live="polite"></p>\n'
        '<h3>Steps so far</h3>\n<ol id="mimir-sim-history"></ol>\n</div>\n'
        f'<details class="sim-machine"><summary>The machine</summary>\n{_machine_html(machine)}\n</details>\n'
        "</section>")
