#!/usr/bin/env python3
"""Per-student-turn latency timeline of a Claude Code session JSONL (dev analysis only).

Usage: timeline.py SESSION.jsonl [--detail]
Prints, per student message: wall time until the tutor's last text, time to the
first student-visible text, every tool call with its duration, and for Agent
calls the subagent's own tool count and model turns.
"""
import datetime as dt
import glob
import json
import os
import sys


def ts(row):
    t = row.get("timestamp")
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None


def load(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def content(row):
    msg = row.get("message")
    if not isinstance(msg, dict):
        return None
    return msg.get("content")


def sub_stats(session_path):
    """agent id -> dict(first, last, tools, turns, names) from subagents/*.jsonl."""
    base = session_path[:-len(".jsonl")]
    stats = {}
    for f in glob.glob(os.path.join(base, "subagents", "agent-*.jsonl")):
        rows = load(f)
        times = [ts(r) for r in rows if ts(r)]
        tools, turns, names, out_tok = 0, 0, [], 0
        seen_msg = set()
        for r in rows:
            if r.get("type") != "assistant":
                continue
            mid = (r.get("message") or {}).get("id")
            if mid not in seen_msg:
                seen_msg.add(mid)
                turns += 1
                out_tok += ((r.get("message") or {}).get("usage") or {}).get("output_tokens", 0)
            for p in content(r) or []:
                if p.get("type") == "tool_use":
                    tools += 1
                    inp = p.get("input", {})
                    names.append(p["name"] + ":" + (inp.get("command") or inp.get("file_path") or inp.get("pattern") or "")[:70].replace("\n", " "))
        aid = os.path.basename(f)[len("agent-"):-len(".jsonl")]
        stats[aid] = dict(first=min(times) if times else None, last=max(times) if times else None,
                          tools=tools, turns=turns, names=names, out=out_tok,
                          model=next(((r.get("message") or {}).get("model") for r in rows if r.get("type") == "assistant"), None))
    return stats


def main():
    path = sys.argv[1]
    detail = "--detail" in sys.argv
    rows = load(path)
    subs = sub_stats(path)
    # student turns: user rows with string content (or text-only list) that are not tool results / meta
    turns = []
    cur = None
    uses = {}
    for r in rows:
        if r.get("isSidechain"):
            continue
        t = r.get("type")
        c = content(r)
        when = ts(r)
        if t == "user":
            is_student = isinstance(c, str) and not r.get("isMeta")
            if isinstance(c, list) and c and all(p.get("type") == "text" for p in c) and not r.get("isMeta"):
                is_student = True
            text = c if isinstance(c, str) else " ".join(p.get("text", "") for p in c if p.get("type") == "text") if isinstance(c, list) else ""
            if is_student and ("<task-notification" in text or "<system-reminder" in text[:40]):
                # background agent finished: not a student message
                if cur is not None:
                    cur["events"].append((when, "NOTIFY", text[:60].replace("\n", " ")))
                continue
            if is_student:
                cur = dict(start=when, text=text[:70].replace("\n", " "), events=[], first_text=None, last_text=None)
                turns.append(cur)
                continue
            if isinstance(c, list) and cur is not None:
                for p in c:
                    if p.get("type") == "tool_result":
                        u = uses.get(p.get("tool_use_id"))
                        if u:
                            u["end"] = when
                            cc = p.get("content")
                            if isinstance(cc, list):
                                cc = " ".join(x.get("text", "") for x in cc if isinstance(x, dict))
                            u["result"] = str(cc)[:90].replace("\n", " ")
        elif t == "assistant" and cur is not None:
            for p in c or []:
                if p.get("type") == "text" and p.get("text", "").strip():
                    if cur["first_text"] is None:
                        cur["first_text"] = when
                    cur["last_text"] = when
                    cur["events"].append((when, "TEXT", p["text"][:70].replace("\n", " ")))
                elif p.get("type") == "tool_use":
                    inp = p.get("input", {})
                    label = inp.get("command") or inp.get("file_path") or inp.get("skill") or inp.get("subagent_type") or ""
                    u = dict(name=p["name"], start=when, end=None, label=str(label)[:80].replace("\n", " "),
                             bg=inp.get("run_in_background"), result="")
                    uses[p["id"]] = u
                    cur["events"].append((when, "TOOL", u))
    total_wall = 0.0
    for i, tn in enumerate(turns, 1):
        end = tn["last_text"] or tn["start"]
        wall = (end - tn["start"]).total_seconds()
        first = (tn["first_text"] - tn["start"]).total_seconds() if tn["first_text"] else float("nan")
        tools = [e[2] for e in tn["events"] if e[1] == "TOOL"]
        tool_time = sum((u["end"] - u["start"]).total_seconds() for u in tools if u["end"])
        agents = [u for u in tools if u["name"] in ("Agent", "Task")]
        agent_time = sum((u["end"] - u["start"]).total_seconds() for u in agents if u["end"])
        total_wall += wall
        print(f"T{i:<2} wall={wall:6.1f}s first_text={first:6.1f}s tools={len(tools):2d} tool_s={tool_time:6.1f} "
              f"agents={len(agents)} agent_s={agent_time:6.1f} model_s={wall - tool_time:6.1f} | {tn['text']}")
        if detail:
            for when, kind, v in tn["events"]:
                off = (when - tn["start"]).total_seconds()
                if kind == "TOOL":
                    d = (v["end"] - v["start"]).total_seconds() if v["end"] else float("nan")
                    print(f"      +{off:6.1f}s {v['name']:<6} {d:6.1f}s bg={v['bg']} {v['label']} -> {v['result'][:70]}")
                else:
                    print(f"      +{off:6.1f}s {kind:<6} {v}")
    print(f"TOTAL wall {total_wall:.0f}s over {len(turns)} student turns")
    for aid, s in subs.items():
        d = (s["last"] - s["first"]).total_seconds() if s["first"] else float("nan")
        print(f"  subagent {aid[:8]} model={s['model']} dur={d:.1f}s model_turns={s['turns']} tools={s['tools']} out_tok={s['out']}")
        if detail:
            for n in s["names"]:
                print("       -", n)


if __name__ == "__main__":
    main()
