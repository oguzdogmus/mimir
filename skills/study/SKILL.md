---
description: Run a Mimir study session for a course in the student's learning folder - exam date intake, delivery class, "previously on" recap, a timed teaching episode on the next exam topic (explanation ladder in the professor's notation, Socratic questions, attempt-first, disguise drills), and a cliffhanger for next time. Use when a student wants to study, prepare or get help for an exam in a course with its outline, slides or past papers, e.g. "exam Friday, help".
---

Load `mimir:core-rules` first.

Then Read `${CLAUDE_PLUGIN_ROOT}/skills/study/references/session.md` and follow it exactly. It runs the whole session: course and exam from `scripts/session.py`, the class line from `plan.py`, the episode, and the close.

- Every date, clock and class decision comes from `session.py` output or a `date` call. Never compute a date or an elapsed time yourself.
- At session start read nothing but what `session.md` names: no `mastery.md`, `fingerprint.md`, `forecast.md` or `logs/` reads before the episode. The profile is read once, at episode start, for the languages, the dial preference and the rung hints.
- No bulk review sets, no homework.
