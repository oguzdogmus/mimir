---
name: mimir-study
description: Run a Mimir study session for a course: a short lesson on the next exam topic with practice questions or, close to the exam, drilling on real past-paper questions. Use when the student wants to study or prepare for an exam, e.g. "exam Friday, help", even with only a photo of a past paper.
---

First read `../mimir-core-rules/SKILL.md` (beside this skill's folder) unless it is already loaded; it defines `<mimir>`.

Then Read `<mimir>/skills/mimir-study/references/session.md` and follow it exactly. It runs the whole session: course and exam from `scripts/session.py`, the class line from `plan.py`, the episode, and the close. An Urgent session, and a first contact with no workspace but an attached file, continue in `references/urgent.md` as `session.md` says.

- Every date, clock and class decision comes from `session.py` output (`session.py now` for the clock). Never compute a date or an elapsed time yourself.
- Reads at start: only what `session.md` names, nothing else: no `mastery.md`, `fingerprint.md`, `forecast.md` or `logs/` reads before the episode (Urgent cargo reads `fingerprint.md` and `mastery.md` topics as `urgent.md` §2 says). The profile is read once, at episode start, for the languages, the dial preference and the rung hints.
- No bulk review sets, no homework.
