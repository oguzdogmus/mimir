#!/usr/bin/env python3
"""What each answer-key checker run read, and how large its batch was.

Usage: checker_reads.py PROJECT_DIR [PROJECT_DIR ...] [--until DAY] [--detail]

A call opens a named source when the file it targets has its name in the
dispatch prompt. Every other call (a search, a `--help`, a file the tutor did
not name) counts as "other". Prints numbers only; --detail also prints the
calls and the reply of every run with a verdict other than `correct`, which
shows course content.
"""
import collections
import os
import re
import statistics as st

from common import base_parser, checker_runs, day

SOURCE_FILE = re.compile(r"[^\s\"'`/\\]+\.(?:pdf|md|txt|png|jpe?g|pptx|docx)\b", re.I)
IGNORED_TOOLS = {"SubagentHandback"}      # host bookkeeping, not a read


def targets(name, inp):
    """File names a call targets; empty for a call that opens no course file."""
    if name == "Bash":
        cmd = inp.get("command", "")
        path = re.search(r'"path"\s*:\s*\\?"([^"\\]+)', cmd)
        if path:
            return [os.path.basename(path.group(1))]
        return [] if "--help" in cmd else SOURCE_FILE.findall(cmd)
    if name == "Read":
        return [os.path.basename(inp.get("file_path") or "")]
    return []


def main():
    parser = base_parser(__doc__.splitlines()[0])
    parser.add_argument("--detail", action="store_true", help="print the runs with a verdict other than correct")
    args = parser.parse_args()
    stats, tool_names, labels = collections.Counter(), collections.Counter(), collections.Counter()
    batch_sizes, calls_per_run, other_per_run, non_correct = [], [], [], []
    for path, prompt, calls, final in checker_runs(args.projects, day(args.until)):
        calls = [(name, inp) for name, inp in calls if name not in IGNORED_TOOLS]
        stats["runs"] += 1
        verdicts = re.findall(r"^\s*(\d+)\s*\|\s*([a-zA-Z\-]+)\s*\|", final, flags=re.M)
        fake_real = re.findall(r"^\s*\d+\s*\|\s*[a-zA-Z\-]+\s*\|\s*(?:fake-real\s+)?(yes|no)\s*\|", final, flags=re.M | re.I)
        stats["reply lines"] += len(verdicts)
        stats["fake-real yes"] += sum(1 for cell in fake_real if cell.lower() == "yes")
        for _, word in verdicts:
            stats[f"verdict {word.lower()}"] += 1
        batch_sizes.append(len(verdicts))
        labels["practice"] += len(re.findall(r"\[practice", prompt))
        labels["real, text label"] += len(re.findall(r"\[real: ", prompt))
        labels["real, from scan"] += len(re.findall(r"\[real, from photo/scan", prompt))
        named = other = 0
        for name, inp in calls:
            tool_names[name] += 1
            found = [t for t in targets(name, inp) if t]
            if found and all(t in prompt for t in found):
                named += 1
            else:
                other += 1
                stats["other calls"] += 1
                stats["other calls that are --help"] += name == "Bash" and "--help" in inp.get("command", "")
        calls_per_run.append(len(calls))
        if not named:
            stats["runs that opened no named source"] += 1
        if not calls:
            stats["runs with no call at all"] += 1
        if named and not other:
            stats["runs that opened named sources only"] += 1
        if other:
            stats["runs with a call that is not a named source"] += 1
            other_per_run.append(other)
        if any(word.lower() != "correct" for _, word in verdicts):
            non_correct.append((path, calls, final))

    for key, value in sorted(stats.items()):
        print(f"{key}: {value}")
    print("tool names over all runs:", tool_names.most_common())
    print("labels in the dispatch prompts:", dict(labels))
    if batch_sizes:
        print("batch size (reply lines per run): median=%s mean=%.1f max=%s; runs of 1: %d, of 20 or more: %d" % (
            st.median(batch_sizes), st.mean(batch_sizes), max(batch_sizes),
            sum(1 for b in batch_sizes if b == 1), sum(1 for b in batch_sizes if b >= 20)))
        print("batch size histogram:", sorted(collections.Counter(batch_sizes).items()))
        print("calls per run: median=%s mean=%.1f max=%s" % (
            st.median(calls_per_run), st.mean(calls_per_run), max(calls_per_run)))
    print("other calls per run, runs with any:", sorted(other_per_run))
    print("runs with a verdict other than correct:", len(non_correct))
    if args.detail:
        for path, calls, final in non_correct:
            print("RUN", os.path.basename(path))
            for name, inp in calls:
                print("  call", name, (inp.get("file_path") or inp.get("pattern") or inp.get("command") or "")[:160])
            print("  reply:", final[:900].replace("\n", "\n    "))


if __name__ == "__main__":
    main()
