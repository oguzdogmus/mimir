---
name: mimir-study
description: Run a Mimir study session for a course in the student's learning folder - exam date intake, delivery class, "previously on" recap, a timed teaching episode on the next exam topic (explanation ladder in the professor's notation, Socratic questions, attempt-first, disguise drills), and a cliffhanger for next time. Close to the exam it switches to Urgent cargo - triage of question types by points per hour and answer-first drilling on real past-paper questions - and works even with no workspace from one attached past-paper photo. Use when a student wants to study, prepare or get help for an exam in a course with its outline, slides or past papers, e.g. "exam Friday, help" or "exam tomorrow, help" with a photo.
---

First read `../mimir-core-rules/SKILL.md` (beside this skill's folder) unless it is already loaded; it defines `<mimir>`.

Then Read `<mimir>/skills/mimir-study/references/session.md` and follow it exactly. It runs the whole session: course and exam from `scripts/session.py`, the class line from `plan.py`, the episode, and the close. An Urgent session, and a first contact with no workspace but an attached file, continue in `references/urgent.md` as `session.md` says.

- Every date, clock and class decision comes from `session.py` output (`session.py now` for the clock). Never compute a date or an elapsed time yourself.
- At session start read nothing but what `session.md` names: no `mastery.md`, `fingerprint.md`, `forecast.md` or `logs/` reads before the episode (Urgent cargo reads `fingerprint.md` and `mastery.md` topics as `urgent.md` §2 says). The profile is read once, at episode start, for the languages, the dial preference and the rung hints.
- No bulk review sets, no homework.
