---
name: mimir-setup
description: One-time full Mimir setup. Picks the learning folder, the course and teaching languages, and any exam dates already known.
disable-model-invocation: true
---

First read `../mimir-core-rules/SKILL.md` (beside this skill's folder) unless it is already loaded; it defines `<mimir>`.

Reads at start: `workspace.py root` output. Nothing else.

All workspace changes go through `python3 "<mimir>/scripts/workspace.py" <cmd>`. Pass its JSON on stdin with a quoted heredoc (`<<'EOF'`) so paths with spaces survive. It prints one JSON object with a ready-to-print `line`.

1. Run `root` with `{}`. If `setup_done` is set, say "Setup already done on <setup_done>. Your learning folder is <root>." and stop.
2. Say: "One-time setup. This may take a few minutes, and it will not be repeated."
3. Ask everything in one numbered message, then wait for one reply:
   1. Learning folder: currently `<root>`. Keep it, or give another path?
   2. Which language are your courses and exams in, and which language do you want explanations in?
   3. Exams you already know, each with its date and time (course code, exam, date, time; "Don't know" is fine for the time), or "none".
   For anything left unanswered, pick a default and declare it: keep the folder; teaching language = the language the student writes in; course language = the teaching language; no exam dates.
4. Apply the folder choice:
   - Kept: `init` with `{}`.
   - New path and `exists` was true: `relocate` with `{"to": "<path>"}`.
   - New path and `exists` was false: `init` with `{"root": "<path>"}`.
   - If relocate is refused, keep the current folder, run `init` with `{}`, and declare it.
   Print each returned `line`. If any other `init` or `relocate` call exits non-zero, show its stderr line and stop without editing the profile.
5. Edit `.state/profile.md` under the `root` from the last returned JSON, keeping the template's shape:
   - `course_language:` and `teaching_language:`.
   - First run `python3 "<mimir>/scripts/session.py" now` with `{}` on stdin once: `N` is its `now`.
   - One `| CODE | exam | <exam> |` row per known exam under `## Exam dates`, `<exam>` being its `exam` from `python3 "<mimir>/scripts/session.py" parse-date` with `{"now": "<N>", "phrase": "<the date and time as the student gave them>"}` (escape it as a JSON string; leave the time out when they don't know it). It accepts only `YYYY-MM-DD`, today, tomorrow, an English weekday name (today's own weekday means today) and "N days" or "in N days", each optionally with a time such as `12:30` or `2pm` before or after it ("12:30 tomorrow"). Its `exam` keeps the time when one was given, else it is the date alone. When it exits 2, ask for the date as YYYY-MM-DD and the time as HH:MM in the same setup exchange. Never do date arithmetic yourself. Replace `|` and newlines in cell values with spaces.
   - Last, `setup_done:` set to the `date` of that `session.py now` call.
6. Say: "Drop your course outline and past papers into `<root>/_inbox/`." Teaching can start right after.
