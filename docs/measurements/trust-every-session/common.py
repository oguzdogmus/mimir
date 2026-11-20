"""Shared helpers for the trust-every-session measurements.

Dev analysis only, standard library. The scripts read Claude Code session
transcripts (JSONL, one timestamped row per message block) and print numbers,
never transcript text. A row's timestamp marks the moment its block was
complete, so time to the first token cannot be measured.
"""
import argparse
import datetime as dt
import glob
import json
import os
import statistics as st


def base_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("projects", nargs="+",
                        help="Claude Code project folders that hold the study transcripts, "
                             "for example ~/.claude/projects/-home-me-Learning")
    parser.add_argument("--since", default="2026-11-01",
                        help="first day counted for latency, YYYY-MM-DD in UTC (default 2026-11-01)")
    parser.add_argument("--until", default=None,
                        help="first day not counted, YYYY-MM-DD in UTC (default: no limit)")
    return parser


def day(text):
    return dt.datetime.fromisoformat(text).replace(tzinfo=dt.timezone.utc) if text else None


def ts(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def rows(path):
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def session_files(projects):
    """Session transcripts of the given project folders, in one stable order."""
    return sorted(f for d in projects for f in glob.glob(os.path.join(os.path.expanduser(d), "*.jsonl")))


def is_student_message(row, content, slash_commands=False):
    """True for a message the student typed; False for host and hook rows.

    A slash command (it starts a session) counts only with slash_commands; /compact never counts.
    """
    if row.get("isMeta") or not isinstance(content, str):
        return False
    if "<task-notification" in content or content.startswith(("<local", "[Request", "This session is being")):
        return False
    return "<command-name>/compact" not in content if slash_commands else "<command-name>" not in content


def checker_runs(projects, until=None):
    """Yield (path, prompt, calls, final_text) for each distinct mimir:verifier run.

    Forked sessions copy their subagent runs, so runs are deduplicated by prompt.
    """
    metas = sorted(m for d in projects
                   for m in glob.glob(os.path.join(os.path.expanduser(d), "*", "subagents", "agent-*.meta.json")))
    seen = set()
    for meta in metas:
        try:
            with open(meta, encoding="utf-8") as handle:
                agent_type = str(json.load(handle).get("agentType", ""))
        except (OSError, ValueError):
            continue
        if "verifier" not in agent_type:
            continue
        path = meta[:-len(".meta.json")] + ".jsonl"
        prompt, calls, final, started = None, [], "", None
        for row in rows(path):
            message = row.get("message") if isinstance(row.get("message"), dict) else {}
            content = message.get("content")
            if started is None and row.get("timestamp"):
                started = ts(row["timestamp"])
            if row.get("type") == "user" and prompt is None:
                prompt = content if isinstance(content, str) else " ".join(
                    part.get("text", "") for part in content or [] if isinstance(part, dict))
            elif row.get("type") == "assistant":
                for part in content or []:
                    if part.get("type") == "tool_use":
                        calls.append((part.get("name"), part.get("input") or {}))
                    elif part.get("type") == "text" and part.get("text", "").strip():
                        final = part["text"]
        if not prompt or (until and started and started >= until):
            continue
        key = hash(prompt)
        if key in seen:
            continue
        seen.add(key)
        yield path, prompt, calls, final


def quantile(values, p):
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def describe(name, values, unit="s"):
    if not values:
        print(f"  {name}: n=0")
        return
    print(f"  {name}: n={len(values)} median={st.median(values):.1f}{unit} p25={quantile(values, .25):.1f} "
          f"p75={quantile(values, .75):.1f} p90={quantile(values, .9):.1f}")
