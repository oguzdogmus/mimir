#!/usr/bin/env python3
"""Build one isolated acceptance-run folder for the teaching-level runs (#44).

Dev-only, standard library, Python 3.11+. Not part of CI. Usage::

    python3 tests/acceptance/make_fixture.py --out DIR --axis support --level try-first

DIR (must not exist) gets:

* ``home/``: a stand-in HOME whose ``.config/mimir/root`` points at
  ``DIR/learning``, so Mimir's scripts never touch the real learning folder.
  Run the host's shell commands with ``HOME=DIR/home``.
* ``learning/``: a finished setup with one course, ``2026-Fall/CS301 Automata``,
  built through Mimir's own scripts: a midterm three weeks ahead (Standard
  delivery), two unseen topics, a notes file with the shared task and four
  more questions, an earlier session log (so it is not a first contact and
  the knowledge gauge is done), the what's-new line already seen, and all
  three teaching settings saved as explicit: the axis under test at
  ``--level``, the other two at their defaults. Explicit axes are never
  probed, so no probe trial changes a level mid-run.

Prints one JSON object: the paths, the levels and ``session.py start``'s
class line, which must say Standard.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
TERM, COURSE, CODE = "2026-Fall", "CS301 Automata", "CS301"
TOPIC = "Languages of context-free grammars"
NEXT_TOPIC = "Closure properties of context-free languages"
DEFAULTS = {"support": "method-first", "frequency": "key decisions", "depth": "why"}
LEVELS = {
    "support": ["example-first", "method-first", "try-first"],
    "frequency": ["checks only", "key decisions", "every step"],
    "depth": ["next step", "why", "what-if"],
}

NOTES = f"""# {TOPIC}

A context-free grammar generates a language: every string of terminals that
can be derived from the start symbol. To describe that language in set
notation, look at what one application of each recursive rule adds on each
side, what the base case adds, and how many times the recursive rule can be
applied (zero or more times unless a rule forces at least one).

## Practice questions

1. Describe in set notation the language of S → aSc | b.
2. Describe in set notation the language of S → aaSb | c.
3. Describe in set notation the language of S → aSbb | ε.
4. Describe in set notation the language of S → aSa | bSb | c.
5. Give a grammar for {{aⁿbᵐ | n ≥ 1, m ≥ 0}}.

## Answers

1. {{aⁿbcⁿ | n ≥ 0}}
2. {{a²ⁿcbⁿ | n ≥ 0}}
3. {{aⁿb²ⁿ | n ≥ 0}}
4. {{wcwᴿ | w ∈ {{a, b}}*}}
5. S → aA, A → aA | B, B → bB | ε
"""


def run(script: str, cmd: str, data: dict, env: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), cmd],
        input=json.dumps(data), capture_output=True, text=True, env=env, check=False,
    )
    if proc.returncode != 0:
        sys.exit(f"make_fixture: {script} {cmd} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--axis", required=True, choices=sorted(LEVELS))
    ap.add_argument("--level", required=True)
    args = ap.parse_args()
    if args.level not in LEVELS[args.axis]:
        ap.error(f"--level for {args.axis} is one of: {', '.join(LEVELS[args.axis])}")
    out = args.out.resolve()
    if out.exists():
        ap.error(f"{out} already exists")

    home, root = out / "home", out / "learning"
    write(home / ".config" / "mimir" / "root", f"{root}\n")
    env = {**os.environ, "HOME": str(home)}

    now = run("session.py", "now", {}, env)
    today = dt.date.fromisoformat(now["date"])
    exam = f"{today + dt.timedelta(days=21)} 10:00"
    earlier = dt.datetime.fromisoformat(now["now"]) - dt.timedelta(days=3)
    earlier = earlier.replace(hour=18, minute=0, second=0, microsecond=0)

    course_dir = Path(run("workspace.py", "course", {"term": TERM, "course": COURSE}, env)["course_dir"])

    write(root / ".state" / "profile.md", f"""<!-- Mimir profile. Always loaded. Cap: 50 lines (forecast record 1 line). -->
# Profile

level: 2nd-year undergraduate
course_language: English
teaching_language: English
setup_done: {earlier.date()}

## Exam dates
| course | exam | date |
|---|---|---|
| {CODE} | midterm | {exam} |

## Active courses
| course | path |
|---|---|
| {CODE} | {TERM}/{COURSE} |
""")
    write(course_dir / "notes" / "cfg-languages.md", NOTES)
    write(course_dir / "INDEX.md", f"""<!-- Mimir course INDEX. Always loaded for the active course. One line per file or topic. Read first. -->
# INDEX

## Registry
| path | term | role | pages | fidelity |
|---|---|---|---|---|
| notes/cfg-languages.md | {TERM} | notes | 1 | text |

## Topics
| topic | file#anchor |
|---|---|
| {TOPIC} | notes/cfg-languages.md#{TOPIC.lower().replace(' ', '-')} |
| {NEXT_TOPIC} | notes/cfg-languages.md |
""")
    write(course_dir / ".state" / "mastery.md", f"""<!-- Mimir mastery. One line per topic, no prose. Status: unseen | gap | shaky | mastered. -->
# Mastery

| topic | status | evidence | evidence_date | last_check | assisted | unassisted | frustration_override |
|---|---|---|---|---|---|---|---|
| {TOPIC} | unseen | | | | 0 | 0 | |
| {NEXT_TOPIC} | unseen | | | | 0 | 0 | |
""")
    stamp = earlier.isoformat()
    write(course_dir / ".state" / "save.md", f"""<!-- Mimir save. Always loaded for the active course. Cap: 30 lines. -->
# Save

current_topic:
next_topic: {TOPIC}
cliffhanger:
resolution:
last_class: Standard
last_session: {earlier.strftime('%Y-%m-%d %H:%M')}
status: on-track
pending_debrief: no

## Previously on
- Set up CS301 and filed the grammar notes.
""")
    write(course_dir / ".state" / "logs" / f"{earlier.strftime('%Y-%m-%d-%H%M')}.md", f"""## Session
started: {stamp}
class: Standard (exam date, calm)
first_contact: {stamp}
gauge_done: {stamp}
ended: {(earlier + dt.timedelta(minutes=20)).isoformat()}
""")

    levels = {**DEFAULTS, args.axis: args.level}
    for axis, level in levels.items():
        run("session.py", "pref-event", {"event": "explicit", "axis": axis, "level": level,
                                          "wording": f"acceptance run: {level}"}, env)
    run("session.py", "pref-event", {"event": "whats-new-seen"}, env)

    start = run("session.py", "start", {"now": now["now"]}, env)
    if start["class"]["class"] != "Standard" or start["gauge"]["done"] is not True:
        sys.exit(f"make_fixture: expected Standard with the gauge done, got {start['line']}")
    print(json.dumps({
        "out": str(out), "home": str(home), "root": str(root), "course_dir": str(course_dir),
        "axis": args.axis, "level": args.level, "levels": levels,
        "topic": start["topic"]["name"], "line": start["line"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
