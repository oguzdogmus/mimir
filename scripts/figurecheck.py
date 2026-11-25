#!/usr/bin/env python3
"""Mimir figure check: the figure checker's brief, and its reply read into verdicts.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py`` and ``fieldpack.py`` (same folder). Run as::

    python3 figurecheck.py <brief|read>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Both need a workspace whose field pack store holds the pack named
(see ``fieldpack.py``). This script writes nothing and checks no figure
itself: the figure checker helper (``helpers/figure-checker.md``) does that,
dispatched as a fresh agent with the brief as its whole input.

Subcommands and examples
------------------------
brief -- the figure checker's input for one built figure.
    in : {"field": "medicine", "figure": "anatomical section",
          "path": "/abs/heart.html"}
    out: {"field": "medicine", "figure": "anatomical section", "kind":
          "depiction", "path": "/abs/heart.html", "items": [{"n": 1,
          "rule": "..."}], "brief": "...", "line": "Figure check brief:
          3 checklist items for anatomical section."}
    ``figure`` names one of the pack's figures, ignoring case. ``path``
    is the absolute path of an existing ``.svg`` or ``.html`` file, not a
    symlink. ``brief`` is the text to dispatch: the check token, the figure's
    path, the pack's figure with its figure kind and that figure's
    checklist, numbered from 1, without sources. Nothing else from the pack
    goes in. The check token is the first TOKEN_CHARS hex digits of a SHA-256
    over the figure file's bytes, the field, the figure with its kind and the
    checklist: the same file and checklist always give the same token, any
    change to either a new one.

read -- the figure checker's reply as one verdict per checklist item.
    in : {"field": "medicine", "figure": "anatomical section",
          "path": "/abs/heart.html", "reply": "<check token>\\n1 | fail |
          ...\\n2 | pass | ...\\noverall | fail | ..."}
    out: {"field": "medicine", "figure": "anatomical section", "items":
          [{"n": 1, "rule": "...", "verdict": "fail", "reason": "..."}],
          "overall": "fail", "failed": [1], "line": "Figure check failed:
          1 of 3 checklist items fail (1)."}
    ``path`` is the figure the reply is about, as ``brief`` takes it. The
    reply must hold a line with just the check token of that file and
    checklist (backticks and asterisks around it are ignored), as the answer
    key checker's reply holds its pack token (``verify.py settle``); a reply
    without it, or with another file's token, exits 2. Only the lines after
    the token line count: ``N | verdict | reason`` per checklist item and
    ``overall | verdict | reason``; the verdict is one of VERDICTS, in any
    case. Other lines (prose, fences) are ignored, the first line for each
    item counts, and the reason is made one line. Read fails closed: an item
    with no line reads as ``fail`` "no reply line", an unknown verdict word as
    ``fail``. ``overall`` is "pass" only when every item passes and the reply's
    overall line says pass; ``failed`` lists the failing item numbers.

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``figurecheck.py: <message>``) and
nothing on stdout. An unexpected internal error exits 1 with
``figurecheck.py: internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import fieldpack
import ingest
import verify
import workspace
from workspace import InputError, check_keys, refuse_symlinks, short

FIGURE_SUFFIXES = (".svg", ".html")
VERDICTS = ("pass", "fail")
TOKEN_CHARS = 12


def _checklist(data: dict) -> tuple[str, dict, list[dict]]:
    """(field, the pack's figure entry, numbered items) for the input's field and figure."""
    field = fieldpack.parse_field(data)
    _, pack = fieldpack.load_pack(ingest._workspace_root(), field)
    name = data.get("figure")
    if not isinstance(name, str) or not name.strip():
        raise InputError("figure is required (one of the pack's figures)")
    figure = next((f for f in pack["figures"] if f["name"].casefold() == name.strip().casefold()), None)
    if figure is None:
        names = ", ".join(f["name"] for f in pack["figures"])
        raise InputError(f"figure {short(name)} is not one of the figures of {field} ({names})")
    rules = next(c["rules"] for c in pack["checklists"] if c["figure"] == figure["name"])
    return field, figure, [{"n": n, "rule": r["rule"]} for n, r in enumerate(rules, 1)]


def _figure_path(data: dict) -> Path:
    value = data.get("path")
    if not isinstance(value, str) or not value:
        raise InputError("path is required (the absolute path of the built figure)")
    path = Path(value)
    if not path.is_absolute():
        raise InputError(f"path must be absolute: {short(value)}")
    if path.suffix.lower() not in FIGURE_SUFFIXES:
        raise InputError(f"path must be an {' or '.join(FIGURE_SUFFIXES)} file: {short(value)}")
    refuse_symlinks(path, field="path")
    if not path.is_file():
        raise InputError(f"path {path} is not a file")
    return path


def check_token(path: Path, field: str, figure: dict, items: list[dict]) -> str:
    """The token that ties a checker's reply to the figure file and the checklist it was briefed on."""
    digest = hashlib.sha256(path.read_bytes())
    for value in (field, figure["name"], figure["kind"], *(i["rule"] for i in items)):
        digest.update(b"\0" + value.encode("utf-8"))
    return digest.hexdigest()[:TOKEN_CHARS]


def cmd_brief(data: dict) -> dict:
    check_keys(data, {"field", "figure", "path"})
    field, figure, items = _checklist(data)
    path = _figure_path(data)
    lines = [f"Check token: {check_token(path, field, figure, items)}", f"File: {path}",
             f"Figure: {figure['name']} ({figure['kind']})", "Checklist:"]
    lines += [f"{i['n']}. {i['rule']}" for i in items]
    count = f"{len(items)} checklist item{'' if len(items) == 1 else 's'}"
    return {"field": field, "figure": figure["name"], "kind": figure["kind"], "path": str(path), "items": items,
            "brief": "\n".join(lines) + "\n", "line": f"Figure check brief: {count} for {figure['name']}."}


def _reply_lines(reply: str, token: str, path: Path) -> dict[str, tuple[str, str]]:
    """{N or "overall": (verdict word, reason)} from the lines after the one holding just ``token``."""
    lines = reply.splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip().strip("`*").strip() == token), None)
    if first is None:
        raise InputError(f"reply: the reply has no line with the check token of {path} and its checklist; "
                         "dispatch the figure checker with the brief for this file and pass its reply unchanged")
    found = {}
    for line in lines[first + 1:]:
        parts = [p.strip() for p in line.strip().strip("`").split("|", 2)]
        if len(parts) == 3 and parts[0].casefold() not in found:
            found[parts[0].casefold()] = (parts[1].casefold(), parts[2])
    return found


def cmd_read(data: dict) -> dict:
    check_keys(data, {"field", "figure", "path", "reply"})
    field, figure, items = _checklist(data)
    if not isinstance(data.get("reply"), str):
        raise InputError("reply is required (the figure checker's reply text)")
    path = _figure_path(data)
    found = _reply_lines(data["reply"], check_token(path, field, figure, items), path)
    results = []
    for item in items:
        verdict, reason = found.get(str(item["n"]), ("fail", "no reply line"))
        if verdict not in VERDICTS:
            verdict, reason = "fail", f"unknown verdict {short(verdict)}"
        results.append({**item, "verdict": verdict, "reason": verify._one_line(reason)})
    failed = [r["n"] for r in results if r["verdict"] != "pass"]
    said = found.get("overall", (None, ""))[0]
    count = f"{len(items)} checklist item{'' if len(items) == 1 else 's'}"
    if failed:
        line = f"Figure check failed: {len(failed)} of {count} fail ({', '.join(map(str, failed))})."
    elif said is None:
        line = "Figure check failed: every checklist item passes, but the reply has no overall verdict line."
    elif said != "pass":
        word = said if said in VERDICTS else short(said)
        line = f"Figure check failed: every checklist item passes, but the reply's overall verdict is {word}."
    else:
        line = f"Figure check passed: all {count} pass."
    return {"field": field, "figure": figure["name"], "items": results,
            "overall": "pass" if not failed and said == "pass" else "fail", "failed": failed, "line": line}


COMMANDS = {
    "brief": (cmd_brief, "the figure checker's input for one built figure"),
    "read": (cmd_read, "the figure checker's reply as one verdict per checklist item and an overall verdict"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("figurecheck.py",
                             ("Mimir figure check. Subcommands: brief, read. Reads one JSON object on stdin and "
                              "prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
