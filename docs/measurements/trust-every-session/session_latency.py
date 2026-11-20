#!/usr/bin/env python3
"""Latency of real Mimir study sessions from Claude Code transcripts.

Usage: session_latency.py PROJECT_DIR [PROJECT_DIR ...] [--since DAY] [--until DAY]

Prints numbers only. Student turns are deduplicated across forked sessions.
Model step   = time from the previous event (student message or tool result) to the next tool call.
Verify cycle = from the start of the model step that issues the gate call before a
               checker dispatch, to the end of the gate call after it.
Verdict words are counted over all sessions, not only since --since.
"""
import collections
import json
import re

from common import base_parser, day, describe, is_student_message, rows, session_files, ts


def call_kind(inp):
    cmd = inp.get("command") or ""
    if inp.get("subagent_type") == "mimir:verifier":
        return "verifier"
    if "verify.py gate" in cmd:
        return "gate"
    if "session.py record" in cmd:
        return "record"
    if ("/scripts/" in cmd and ".py" in cmd) or "mimir" in json.dumps(inp)[:400]:
        return "mimir"
    return "tool"


def read_turns(path):
    """Student turns of one session file, each with its ordered events."""
    current, uses, turns = None, {}, []
    for row in rows(path):
        if row.get("isSidechain") or not row.get("timestamp"):
            continue
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        content, when = message.get("content"), ts(row["timestamp"])
        if row.get("type") == "user":
            if isinstance(content, str):
                if not is_student_message(row, content, slash_commands=True):
                    if current:
                        current["ev"].append((when, "meta", None))
                    continue
                current = {"start": when, "ev": [], "uuid": row.get("uuid")}
                turns.append(current)
            elif isinstance(content, list) and current is not None:
                for part in content:
                    if part.get("type") != "tool_result":
                        continue
                    use = uses.get(part.get("tool_use_id"))
                    if use:
                        use["end"] = when
                        out = part.get("content")
                        if isinstance(out, list):
                            out = " ".join(x.get("text", "") for x in out if isinstance(x, dict))
                        use["out"] = str(out)
                    current["ev"].append((when, "result", use))
        elif row.get("type") == "assistant" and current is not None:
            for part in content or []:
                if part.get("type") == "text" and part.get("text", "").strip():
                    current["ev"].append((when, "text", None))
                elif part.get("type") == "tool_use":
                    use = {"kind": call_kind(part.get("input") or {}), "start": when, "end": None, "out": ""}
                    uses[part["id"]] = use
                    current["ev"].append((when, "tool", use))
    return turns


def main():
    args = base_parser(__doc__.splitlines()[0]).parse_args()
    since, until = day(args.since), day(args.until)
    files = session_files(args.projects)
    seen, acc = set(), collections.defaultdict(list)
    verdict_words = collections.Counter()
    dispatches = background = counted = 0
    for path in files:
        turns = read_turns(path)
        # a file is a Mimir session if it ever ran a Mimir script
        is_mimir = any(e[1] == "tool" and e[2]["kind"] != "tool" for t in turns for e in t["ev"])
        for turn in turns:
            if turn["uuid"] in seen or (until and turn["start"] >= until):
                continue
            seen.add(turn["uuid"])
            texts = [e for e in turn["ev"] if e[1] == "text"]
            tools = [e[2] for e in turn["ev"] if e[1] == "tool"]
            for use in tools:
                if use["kind"] == "verifier":
                    for _, word in re.findall(r"^\s*(\d+)\s*\|\s*([a-zA-Z\-]+)\s*\|", use["out"], flags=re.M):
                        verdict_words[word.lower()] += 1
            if turn["start"] < since or not texts or not is_mimir:
                continue
            wall = (texts[-1][0] - turn["start"]).total_seconds()
            first = (texts[0][0] - turn["start"]).total_seconds()
            if wall > 900 or wall < 0:
                acc["skipped"].append(wall)
                continue
            counted += 1
            kinds = [use["kind"] for use in tools]
            previous = turn["start"]
            for event in turn["ev"]:
                if event[1] == "tool":
                    acc["step"].append((event[0] - previous).total_seconds())
                if event[1] in ("result", "meta"):
                    previous = event[0]
            if "verifier" in kinds:
                acc["verify_wall"].append(wall)
                acc["verify_first"].append(first)
                acc["verify_tools"].append(len(tools))
                events = turn["ev"]
                for i, event in enumerate(events):
                    if event[1] != "tool" or event[2]["kind"] != "verifier":
                        continue
                    agent = event[2]
                    dispatches += 1
                    background += "Async agent launched" in agent["out"]
                    if agent["end"]:
                        acc["agent"].append((agent["end"] - agent["start"]).total_seconds())
                    before = [x for x in events[:i] if x[1] == "tool" and x[2]["kind"] == "gate"]
                    after = [x for x in events[i + 1:] if x[1] == "tool" and x[2]["kind"] == "gate"]
                    if before and after and after[0][2]["end"] and agent["end"]:
                        step_start = turn["start"]
                        for x in events[:events.index(before[-1])]:
                            if x[1] in ("result", "meta"):
                                step_start = x[0]
                        cycle = (after[0][2]["end"] - step_start).total_seconds()
                        acc["cycle"].append(cycle)
                        acc["cycle_nonagent"].append(cycle - (agent["end"] - agent["start"]).total_seconds())
            elif "record" in kinds and "gate" not in kinds:
                acc["record_wall"].append(wall)
                acc["record_first"].append(first)
                acc["record_tools"].append(len(tools))
            elif not tools:
                acc["notool_wall"].append(wall)
            else:
                acc["other_wall"].append(wall)

    print(f"files={len(files)} unique student turns in Mimir sessions since {args.since}: {counted} "
          f"(skipped outliers {len(acc['skipped'])})")
    describe("model step before a tool call", acc["step"])
    describe("dialogue turn, no tools (reply complete)", acc["notool_wall"])
    describe("answer turn, record only (reply complete)", acc["record_wall"])
    describe("  time to first text", acc["record_first"])
    describe("  tools in it", acc["record_tools"], "")
    describe("turn with a checker dispatch: student message to last text", acc["verify_wall"])
    describe("  time to first text", acc["verify_first"])
    describe("  tools in it", acc["verify_tools"], "")
    describe("verify cycle gate, checker, gate", acc["cycle"])
    describe("  of which not the subagent", acc["cycle_nonagent"])
    describe("  subagent call (parent side)", acc["agent"])
    describe("other tool turns (start, triage, visuals, close ...)", acc["other_wall"])
    shares = ("notool_wall", "record_wall", "verify_wall", "other_wall")
    total = sum(sum(acc[k]) for k in shares)
    for k in shares:
        if total:
            print(f"  share {k:<12} {100 * sum(acc[k]) / total:5.1f}%  ({len(acc[k])} turns, {sum(acc[k]):.0f} s)")
    if total:
        print(f"  verify cycles: {sum(acc['cycle']):.0f} s = {100 * sum(acc['cycle']) / total:.1f}% of tutor wall time; "
              f"dispatches {dispatches}, in the background {background}")
    print("verdict words over all sessions:", verdict_words.most_common())


if __name__ == "__main__":
    main()
