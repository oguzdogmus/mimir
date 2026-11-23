#!/usr/bin/env python3
"""Probe for a script-side real-paper label check.

Usage: label_anchor_probe.py PROJECT_DIR [PROJECT_DIR ...] --learning-root DIR [--until DAY]

For every real question that a tutor sent to the checker, compare the question
text as the tutor worded it with the text of the cited page (and the page after
it) from `scripts/pdftext.py`, and report the longest run of words they share.
Prints numbers only.
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys
import unicodedata

from common import base_parser, checker_runs, day

PDFTEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts", "pdftext.py")


def words(text):
    return re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", text).lower())


def page_text(path, first, last):
    """Text of pages first..last, '' for pages without a text layer, None when unreadable."""
    try:
        out = subprocess.run([sys.executable, PDFTEXT, "pages"], capture_output=True, timeout=60,
                             input=json.dumps({"path": path, "first": first, "last": last}).encode())
        if out.returncode != 0:
            return None
        text = json.loads(out.stdout).get("text")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if isinstance(text, list):
        text = " ".join(str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in text)
    return text or ""


def longest_shared_run(question, page):
    positions = collections.defaultdict(list)
    for i, word in enumerate(page):
        positions[word].append(i)
    longest = 0
    for i, word in enumerate(question):
        for j in positions.get(word, ()):
            k = 0
            while i + k < len(question) and j + k < len(page) and question[i + k] == page[j + k]:
                k += 1
            longest = max(longest, k)
    return longest


def real_questions(prompt):
    """(source, page, question text) for each real question of a dispatch prompt."""
    for label in re.finditer(r"\[real: (.+?), p\.(\d+)\]", prompt):
        rest = prompt[label.end():label.end() + 2500]
        following = re.search(r"\n\s*(?:Item\s+\d+|\d+\s*[|.)—-])", rest)
        block = rest[:following.start()] if following else rest
        question = re.search(r"Question\s*:?\s*(.*?)(?:\n\s*(?:Answer key|Key|Answer)\b|\Z)", block, flags=re.S | re.I)
        yield label.group(1), int(label.group(2)), (question.group(1) if question else block).strip()


def main():
    parser = base_parser(__doc__.splitlines()[0])
    parser.add_argument("--learning-root", required=True, help="the learning folder, for example ~/Learning")
    args = parser.parse_args()
    root = os.path.expanduser(args.learning_root)
    found = [q for _, prompt, _, _ in checker_runs(args.projects, day(args.until)) for q in real_questions(prompt)]
    unique = {}
    for source, page, question in found:
        unique.setdefault((source, page, question[:80]), (source, page, question))
    result, runs, cache = collections.Counter(), [], {}
    for source, page, question in unique.values():
        hits = glob.glob(os.path.join(root, "*", "*", glob.escape(source)))
        if not hits:
            result["file not found"] += 1
            continue
        key = (hits[0], page)
        if key not in cache:
            cache[key] = page_text(hits[0], max(1, page), page + 1)
        text = cache[key]
        if text is None:
            result["page unreadable"] += 1
            continue
        page_words, question_words = words(text), words(question)
        if len(page_words) < 20:
            result["page has no text layer"] += 1
            continue
        if len(question_words) < 8:
            result["question text too short to probe"] += 1
            continue
        longest = longest_shared_run(question_words, page_words)
        runs.append(longest)
        result["probed"] += 1
        for n in (4, 6, 8, 12):
            if longest >= n:
                result[f"shares a run of {n} or more words"] += 1
    print("real questions in checker prompts:", len(found), "unique:", len(unique))
    print(dict(result))
    if runs:
        runs.sort()
        print("longest shared word run per question: min", runs[0], "p25", runs[len(runs) // 4],
              "median", runs[len(runs) // 2], "max", runs[-1])


if __name__ == "__main__":
    main()
