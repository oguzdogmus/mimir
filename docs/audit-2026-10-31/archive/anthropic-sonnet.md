# Original report: anthropic-sonnet

Source: <t3-thread://v2/4c5bcb11-81b0-41c1-95df-d92fe94a74a7/thread:delegated-task:command%3Amcp%3A135b902e-d7b3-42f5-997f-5cb0739fa9c2%3Adelegate-task%3A643d250e-4b96-44a2-a36d-f7b3bf967bb1>

Historical agent report, not a new verification. Findings may overlap or disagree; use the consolidated findings and accepted decisions for implementation.

Review done, nothing modified. I did not read every reference file in full: `teaching.md`, `urgent.md`, `verifier.md` and `visual-builder.md` were only skimmed or sampled. I did not open the templates. Every `<script>.py <cmd>` named in the skills exists in `scripts/`.

**Correction to the brief:** all 12 skills have a `description`. `mimir-help`, `mimir-ingest` and `mimir-setup` carry `disable-model-invocation: true`, so they are meant to be manual-only. The description problems are about overlap and wording (items 3 and 6), not missing fields.

1. **Core rules contradict the study skill on session-start reads.**
   - Finding: core-rules says session start reads `profile.md`, `save.md` and `INDEX.md`. `mimir-study` says to read nothing beyond what `session.md` names. `session.md` §1 step 8 reads only `save.md`, and the profile is read later, at episode start. `INDEX.md` is not read at start at all.
   - Location: `skills/mimir-core-rules/SKILL.md:63`; `skills/mimir-study/SKILL.md` (the "At session start read nothing…" bullet); `references/session.md` §1 step 8 and §4.
   - Impact: Medium. Effort: Trivial.
   - Fix: reword core-rules to "Memory a skill may load at start; each skill lists what it actually reads", or list the study exception there.
   - Evidence: "Session start reads only: `<root>/.state/profile.md`, `<course>/.state/save.md`, and `<course>/INDEX.md`" against "Read nothing else yet: not `mastery.md`…".

2. **The question budget omits questions the skills actually ask.**
   - Finding: the budget allows teaching questions "only through" the Socratic dial, the stale recheck and the "I know this" checks. It does not name the cliffhanger, the practice and disguise-drill items, the quiz items, or the `mimir-ingest` "Reply ok" table. The ingest table is listed, but the others are not.
   - Location: `skills/mimir-core-rules/SKILL.md:24-26`; `session.md` §3 step 4 and §5.
   - Impact: Medium. Effort: Trivial.
   - Fix: add one line, "Items shown by quiz, drill or study episodes and the cliffhanger are content, not questions under this budget."
   - Evidence: "Teaching questions only through: the Socratic dial, the one-question stale recheck…".

3. **Trigger overlap between `mimir-quiz`, `mimir-past-questions` and `mimir-study`.**
   - Finding: the quiz description ends "…its exam topics or past papers", which is what `mimir-past-questions` exists for. The study description is about 700 characters and uses internal jargon ("Urgent cargo", "disguise drills"). It never says the skill is the default for "teach me / help me study X".
   - Location: `skills/mimir-quiz/SKILL.md:3`; `skills/mimir-study/SKILL.md:3`.
   - Impact: Medium. Effort: Trivial.
   - Fix: drop "or past papers" from the quiz description and add "for real past-paper drills use mimir-past-questions". Cut the study description to about 300 characters in plain words, with the "exam Friday, help" example kept.
   - Evidence: "Use when the student asks to be quizzed or tested on a course, its exam topics or past papers."

4. **The course-resolution and "no course" boilerplate is copied across at least 6 files.**
   - Finding: the "names a course … rerun `start` with term/course" paragraph and the "No course to X yet: run `mimir-setup`…" messages are repeated in debrief, forecast, plan, progress, `session.md` and quiz. The copies will drift, and the rerun rules already differ slightly by skill.
   - Location: `mimir-plan` step 2, `mimir-forecast` step 2, `mimir-progress` step 2, `mimir-debrief` step 2, `session.md` §1 step 3.
   - Impact: Medium. Effort: Small.
   - Fix: move one "Resolve the course" block into core-rules, or a `references/course-resolve.md`. Each skill then says "do §Resolve; no-course message: '<verb> …'".
   - Evidence: the string "named course that matches no" appears in 5 files.

5. **Command-name rewriting is ambiguous for hard-coded messages.**
   - Finding: core-rules says to write `/mimir:mimir-setup` in Claude Code and `$mimir-setup` in Codex. It scopes the rewrite to script `line`s ("rewriting those names is the only change you make to a verbatim line"). The skills' fixed strings use the bare name, for example "run `mimir-setup`, then… `mimir-ingest`". It is unclear whether those get rewritten. `mimir-help` handles this explicitly; the other skills don't.
   - Location: `skills/mimir-core-rules/SKILL.md:13`; the "No course…" lines in plan, forecast, progress, past-questions and `session.md`.
   - Impact: Medium. Effort: Trivial.
   - Fix: add "Any command name in text you say to the student is written per this rule, including fixed strings in skills."
   - Evidence: "When you tell the student to run one, write it the way this tool invokes skills…".

6. **Frontmatter keys are Claude-specific and the manual-only skills are unprotected elsewhere.**
   - Finding: `disable-model-invocation`, `user-invocable`, `argument-hint` and `model: haiku` are Claude Code keys. Codex and Antigravity may ignore them. The `mimir-help`, `mimir-ingest` and `mimir-setup` descriptions then act as normal triggers. The `mimir-help` description ("Tells the student which Mimir command fits…") would trigger on generic "help". The `mimir-ingest` and `mimir-setup` descriptions have no "Use only when…" guard like the others.
   - Location: `skills/mimir-help/SKILL.md:3-6`; `skills/mimir-ingest/SKILL.md:3`; `skills/mimir-setup/SKILL.md:3`.
   - Impact: Medium. Effort: Trivial.
   - Fix: add "Use only when the student asks to set up, or invokes this command by name." to each of the three descriptions. Add "only when the student asks which Mimir command to use" to `mimir-help`.
   - Evidence: "description: Mimir command router. Tells the student which Mimir command fits their situation, then stops."

7. **Cross-file references by step number are brittle.**
   - Finding: skills point into other files by step or section number. Renumbering any one of them breaks the callers silently.
     - `mimir-quiz` step 7: "Its steps 1–5 are this skill's steps 7–11".
     - `mimir-past-questions` step 5: "urgent.md §2 steps 1–3".
     - `session.md` §1 step 9: "run its flow from its step 3" in debrief.
     - `session.md` also points to `urgent.md` §1–§4.
   - Location: `skills/mimir-quiz/SKILL.md:23`; `skills/mimir-past-questions/SKILL.md` (steps 5 and 7); `session.md` step 9.
   - Impact: Low. Effort: Small.
   - Fix: give the target steps stable names ("Triage", "Gate and verify", "Debrief body") and refer to those. Add a release-check grep that every "§N" or "step N" cross-reference still resolves.
   - Evidence: "Its steps 1–5 are this skill's steps 7–11".

8. **Edge cases are unspecified in forecast, progress and the `mimir-help` tables.**
   - Finding:
     - `mimir-forecast` step 5 says nothing for a course with no past papers, no outline, or a missing `fingerprint.md`. It would still rank topics and write a forecast from nothing.
     - `mimir-progress` handles `table` null, but it does not say what to tell the student when mastery is empty (only unseen topics).
     - `mimir-help` duplicates every command's purpose in two tables. Those will drift from the skill descriptions.
   - Location: `skills/mimir-forecast/SKILL.md` step 5; `skills/mimir-progress/SKILL.md` step 4; `skills/mimir-help/SKILL.md` (both tables).
   - Impact: Low–Medium. Effort: Small.
   - Fix: in forecast, "No `outline` and no `past-papers` row: say 'Not enough material to forecast…' and stop." In progress, add one line for the all-unseen case. In `mimir-help`, keep the situation table and cut the first table to command names plus "see its description".
   - Evidence: forecast step 5, "Read `INDEX.md`, `fingerprint.md`, and the `outline` and `past-papers` registry files…", has no empty branch.

**Minor, no action needed:** core-rules lines 12, 16 and 46 run over 600 characters each and are hard to maintain. Splitting each into bullets would help. Because every skill loads this file first, it is also the file where drift costs the most.
