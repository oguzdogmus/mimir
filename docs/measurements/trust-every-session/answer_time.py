#!/usr/bin/env python3
"""How long the student takes to answer a question, from Claude Code transcripts.

Usage: answer_time.py PROJECT_DIR [PROJECT_DIR ...] [--since DAY] [--until DAY]

Answer time = from the end of the tutor's turn to the next student message that
the tutor recorded with `session.py record`. A turn's end is its last assistant
row or tool-result row; hook and system rows are stamped later and do not count.
Prints numbers only. Student turns are deduplicated across forked sessions.
"""
import statistics as st

from common import base_parser, day, is_student_message, quantile, rows, session_files, ts


def read_turns(path):
    turns, current = [], None
    for row in rows(path):
        if row.get("isSidechain") or not row.get("timestamp"):
            continue
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        content, when = message.get("content"), ts(row["timestamp"])
        if row.get("type") == "user" and isinstance(content, str):
            if not is_student_message(row, content):
                continue
            current = {"start": when, "uuid": row.get("uuid"), "end": None, "record": False,
                       "chars": len(content), "verifier": False}
            turns.append(current)
        elif current is not None and (row.get("type") == "assistant"
                                      or (row.get("type") == "user" and isinstance(content, list))):
            current["end"] = when
            if row.get("type") == "assistant":
                for part in content or []:
                    if part.get("type") != "tool_use":
                        continue
                    inp = part.get("input") or {}
                    cmd = inp.get("command") or ""
                    if "session.py" in cmd and " record" in cmd:
                        current["record"] = True
                    if inp.get("subagent_type") == "mimir:verifier":
                        current["verifier"] = True
    return turns


def show(name, values):
    if not values:
        print(f"{name}: n=0")
        return
    print(f"{name}: n={len(values)} p10={quantile(values, .1):.0f}s p25={quantile(values, .25):.0f}s "
          f"median={st.median(values):.0f}s p75={quantile(values, .75):.0f}s p90={quantile(values, .9):.0f}s")


def main():
    args = base_parser(__doc__.splitlines()[0]).parse_args()
    since, until = day(args.since), day(args.until)
    seen, answers, any_message, chars, first_of_set = set(), [], [], [], []
    for path in session_files(args.projects):
        turns = read_turns(path)
        for previous, turn in zip(turns, turns[1:]):
            if turn["uuid"] in seen:
                continue
            seen.add(turn["uuid"])
            if turn["start"] < since or (until and turn["start"] >= until) or previous["end"] is None:
                continue
            gap = (turn["start"] - previous["end"]).total_seconds()
            if gap < 0 or gap > 3600:
                continue
            any_message.append(gap)
            if turn["record"]:
                answers.append(gap)
                chars.append(turn["chars"])
                if previous["verifier"]:
                    first_of_set.append(gap)
    show("student time before a message that was recorded as an answer", answers)
    show("  same, when the previous tutor turn ran a check (first question of a set)", first_of_set)
    show("student time before any message", any_message)
    for limit in (15, 30, 45, 60, 90, 120):
        share = 100 * sum(1 for g in answers if g < limit) / max(1, len(answers))
        share_first = 100 * sum(1 for g in first_of_set if g < limit) / max(1, len(first_of_set))
        print(f"  answers within {limit}s of the tutor finishing: all {share:.0f}% | first of a set {share_first:.0f}%")
    if chars:
        print("answer length in characters: median", st.median(chars), "p75", quantile(chars, .75))


if __name__ == "__main__":
    main()
