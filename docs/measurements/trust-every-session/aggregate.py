#!/usr/bin/env python3
"""Aggregate Mimir latency over Claude Code session JSONLs (dev analysis only, prints numbers only).

Usage: aggregate.py SESSION.jsonl [SESSION.jsonl ...]

Model step  = time from the previous event (student message or tool result) to the next
              assistant event that ends a step (a tool call or the turn's last text).
Verify cycle = from the start of the model step that issues the gate call before a
               verifier dispatch, to the end of the gate call after it.
"""
import datetime as dt
import glob
import json
import os
import statistics as st
import sys


def ts(row):
    t = row.get("timestamp")
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None


def load(path):
    out = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def content(row):
    msg = row.get("message")
    return msg.get("content") if isinstance(msg, dict) else None


def q(values, p):
    values = sorted(values)
    if not values:
        return float("nan")
    k = (len(values) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def describe(name, values, unit="s"):
    if not values:
        print(f"  {name}: n=0")
        return
    print(f"  {name}: n={len(values)} median={st.median(values):.1f}{unit} p25={q(values, .25):.1f} "
          f"p75={q(values, .75):.1f} p90={q(values, .9):.1f} max={max(values):.1f}")


def kind_of(cmd):
    cmd = cmd or ""
    for key in ("verify.py gate", "session.py record", "session.py now", "session.py start", "session.py check",
                "session.py triage", "session.py close", "session.py prefs", "session.py pref-event",
                "session.py progress", "session.py gauge", "session.py scope", "pdftext.py", "visual.py"):
        if key in cmd:
            return key
    return "other-bash"


def analyse(path, acc):
    rows = [r for r in load(path) if not r.get("isSidechain")]
    uses = {}
    events = []  # (when, kind, payload)
    for r in rows:
        t, c, when = r.get("type"), content(r), ts(r)
        if when is None:
            continue
        if t == "user":
            if isinstance(c, str):
                if r.get("isMeta") or "<task-notification" in c or c.startswith("<system-reminder") \
                        or "<local-command" in c or "<command-name>/compact" in c \
                        or c.startswith("This session is being continued") or c.startswith("[Request interrupted"):
                    events.append((when, "meta", None))
                else:
                    events.append((when, "student", None))
            elif isinstance(c, list):
                texts = [p for p in c if p.get("type") == "text"]
                results = [p for p in c if p.get("type") == "tool_result"]
                for p in results:
                    u = uses.get(p.get("tool_use_id"))
                    if u:
                        u["end"] = when
                        cc = p.get("content")
                        if isinstance(cc, list):
                            cc = " ".join(x.get("text", "") for x in cc if isinstance(x, dict))
                        u["async"] = "Async agent launched" in str(cc)
                    events.append((when, "result", u))
                if texts and not results:
                    joined = " ".join(p.get("text", "") for p in texts)
                    if r.get("isMeta") or "<task-notification" in joined or "[Request interrupted" in joined:
                        events.append((when, "meta", None))
                    else:
                        events.append((when, "student", None))
        elif t == "assistant":
            for p in c or []:
                if p.get("type") == "text" and p.get("text", "").strip():
                    events.append((when, "text", len(p["text"])))
                elif p.get("type") == "tool_use":
                    inp = p.get("input", {})
                    u = dict(name=p["name"], start=when, end=None, cmd=inp.get("command") or "",
                             sub=inp.get("subagent_type"), bg=inp.get("run_in_background"), async_=False,
                             inlen=len(json.dumps(inp)))
                    u["kind"] = (("agent:" + str(u["sub"])) if p["name"] in ("Agent", "Task")
                                 else kind_of(u["cmd"]) if p["name"] == "Bash" else p["name"])
                    uses[p["id"]] = u
                    events.append((when, "tool", u))

    # split into student turns
    turns, cur = [], None
    for ev in events:
        if ev[1] == "student":
            cur = [ev]
            turns.append(cur)
        elif cur is not None:
            cur.append(ev)

    for turn in turns:
        start = turn[0][0]
        texts = [e for e in turn if e[1] == "text"]
        tools = [e[2] for e in turn if e[1] == "tool"]
        if not texts:
            continue
        first_text = (texts[0][0] - start).total_seconds()
        wall = (texts[-1][0] - start).total_seconds()
        if wall > 900:      # steering / queue artefacts and API stalls: skip as outliers
            acc["skipped_long"] += 1
            continue
        kinds = [u["kind"] for u in tools]
        has_verifier = any(k == "agent:mimir:verifier" for k in kinds)
        has_record = "session.py record" in kinds
        has_gate = "verify.py gate" in kinds
        # model steps: gap from previous boundary to each tool call start
        prev = start
        for e in turn[1:]:
            if e[1] == "tool":
                acc["step"].append((e[0] - prev).total_seconds())
                acc["step_by_kind"].setdefault(e[2]["kind"], []).append((e[0] - prev).total_seconds())
            if e[1] == "result" and e[2] is not None and e[2]["end"]:
                prev = e[0]
            if e[1] == "meta":
                prev = e[0]
        acc["tools_per_turn"].append(len(tools))
        if has_verifier:
            acc["verify_turn_wall"].append(wall)
            acc["verify_turn_first"].append(first_text)
            acc["verify_turn_tools"].append(len(tools))
            # the cycle: first gate before the verifier ... the gate after it
            idx = [i for i, e in enumerate(turn) if e[1] == "tool" and e[2]["kind"] == "agent:mimir:verifier"]
            for i in idx:
                agent = turn[i][2]
                if agent["end"]:
                    acc["agent_tool_s"].append((agent["end"] - agent["start"]).total_seconds())
                acc["agent_async"].append(bool(agent.get("async")))
                acc["agent_bg_flag"].append(agent["bg"])
                acc["agent_prompt_chars"].append(agent["inlen"])
                before = [e for e in turn[:i] if e[1] == "tool" and e[2]["kind"] == "verify.py gate"]
                after = [e for e in turn[i + 1:] if e[1] == "tool" and e[2]["kind"] == "verify.py gate"]
                if before and after and after[0][2]["end"]:
                    gate_before = before[-1]
                    # start of the model step that produced the gate call
                    j = turn.index(gate_before)
                    step_start = start
                    for e in turn[:j]:
                        if e[1] in ("result", "meta"):
                            step_start = e[0]
                    cycle = (after[0][2]["end"] - step_start).total_seconds()
                    acc["cycle"].append(cycle)
                    if agent["end"]:
                        acc["cycle_non_agent"].append(cycle - (agent["end"] - agent["start"]).total_seconds())
                    acc["gate_in_chars"].append(gate_before[2]["inlen"])
                    acc["gate_in_chars"].append(after[0][2]["inlen"])
        elif has_record and not has_gate:
            acc["plain_turn_wall"].append(wall)
            acc["plain_turn_first"].append(first_text)
            acc["plain_turn_tools"].append(len(tools))
        elif not tools:
            acc["notool_turn_wall"].append(wall)

    # subagents
    base = path[:-len(".jsonl")]
    for f in glob.glob(os.path.join(base, "subagents", "agent-*.jsonl")):
        srows = load(f)
        meta = f[:-len(".jsonl")] + ".meta.json"
        atype = None
        if os.path.exists(meta):
            try:
                atype = json.load(open(meta, encoding="utf-8")).get("agentType")
            except Exception:
                pass
        first_user = next((content(r) for r in srows if r.get("type") == "user"), "")
        if isinstance(first_user, list):
            first_user = " ".join(p.get("text", "") for p in first_user if p.get("type") == "text")
        times = [ts(r) for r in srows if ts(r)]
        tool_names, seen, out_tok = [], set(), 0
        for r in srows:
            if r.get("type") != "assistant":
                continue
            m = r.get("message") or {}
            if m.get("id") not in seen:
                seen.add(m.get("id"))
                out_tok += (m.get("usage") or {}).get("output_tokens", 0)
            for p in content(r) or []:
                if p.get("type") == "tool_use":
                    tool_names.append(p["name"])
        is_verifier = (atype == "mimir:verifier") or ("verdict" in str(first_user).lower() and "answer key" in str(first_user).lower()) \
            or "check answer keys" in json.dumps(srows[:3])[:6000]
        if atype and atype != "mimir:verifier":
            is_verifier = False
        if not is_verifier or not times:
            acc["other_sub"] += 1
            continue
        acc["sub_dur"].append((max(times) - min(times)).total_seconds())
        acc["sub_tools"].append(len(tool_names))
        acc["sub_turns"].append(len(seen))
        acc["sub_out"].append(out_tok)
        acc["sub_prompt_chars"].append(len(str(first_user)))
        acc["sub_models"].add(next(((r.get("message") or {}).get("model") for r in srows if r.get("type") == "assistant"), None))


def main():
    acc = dict(step=[], step_by_kind={}, tools_per_turn=[], verify_turn_wall=[], verify_turn_first=[], verify_turn_tools=[],
               agent_tool_s=[], agent_async=[], agent_bg_flag=[], agent_prompt_chars=[], cycle=[], cycle_non_agent=[],
               gate_in_chars=[], plain_turn_wall=[], plain_turn_first=[], plain_turn_tools=[], notool_turn_wall=[],
               sub_dur=[], sub_tools=[], sub_turns=[], sub_out=[], sub_prompt_chars=[], sub_models=set(), other_sub=0,
               skipped_long=0)
    for path in sys.argv[1:]:
        analyse(path, acc)
    print(f"sessions={len(sys.argv) - 1} skipped_long_turns={acc['skipped_long']}")
    print("Main-agent model step (wait before each tool call):")
    describe("all steps", acc["step"])
    for k, v in sorted(acc["step_by_kind"].items(), key=lambda kv: -len(kv[1])):
        if len(v) >= 5:
            describe(f"step before {k}", v)
    print("Turns:")
    describe("tools per turn", acc["tools_per_turn"], "")
    describe("no-tool turn wall", acc["notool_turn_wall"])
    describe("plain answer turn (record, no gate) wall", acc["plain_turn_wall"])
    describe("plain answer turn tools", acc["plain_turn_tools"], "")
    describe("verify turn wall (student msg -> last text)", acc["verify_turn_wall"])
    describe("verify turn time to first text", acc["verify_turn_first"])
    describe("verify turn tools", acc["verify_turn_tools"], "")
    print("Verify cycle (gate -> verifier -> gate):")
    describe("cycle total", acc["cycle"])
    describe("cycle minus agent wait", acc["cycle_non_agent"])
    describe("Agent tool call duration (parent side)", acc["agent_tool_s"])
    describe("gate call input size", acc["gate_in_chars"], " chars")
    describe("Agent prompt size", acc["agent_prompt_chars"], " chars")
    n = len(acc["agent_async"])
    print(f"  verifier dispatches: {n}, async-launched: {sum(acc['agent_async'])}, run_in_background flags: "
          f"{ {str(k): acc['agent_bg_flag'].count(k) for k in set(acc['agent_bg_flag'])} }")
    print("Verifier subagent (its own transcript):")
    describe("duration", acc["sub_dur"])
    describe("tool calls", acc["sub_tools"], "")
    describe("model turns", acc["sub_turns"], "")
    describe("output tokens", acc["sub_out"], "")
    zero = sum(1 for t in acc["sub_tools"] if t == 0)
    print(f"  verifier runs with ZERO tool calls (never opened a source): {zero} of {len(acc['sub_tools'])}")
    print(f"  models: {acc['sub_models']}  (other subagent files skipped: {acc['other_sub']})")


if __name__ == "__main__":
    main()
