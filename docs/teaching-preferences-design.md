# Teaching preferences — design interview

Status: design complete and implemented under issue #30. Records the agreed intentions from the design conversation; the skills and the script docstrings hold the exact shipped behavior.

Naming: this design uses **Standard** and **Urgent**, the delivery class names in the shipped code. Earlier drafts said "Normal" for Standard. The shipped skills and scripts call the teaching preference **teaching settings** and a preference probe a **probe trial** (`GLOSSARY.md`); this document keeps its interview wording.

## Agreed direction

- One global teaching preference carries across every course; no course overrides. It governs Standard teaching in study sessions only. Quiz and past-question sessions keep their current behavior.
- Urgent bypasses all three preference axes and does not update saved preferences, accumulate preference evidence, or run preference probes. Cramming behavior never influences later Standard sessions.
- Standard sessions held within 48 hours of an exam also contribute no preference evidence and run no probes, so exam stress does not shape lasting preferences. Every course's exams count. A date-only exam counts when its day is at most two calendar days after today, since some moment of that day is within 48 hours (the conservative reading). A running trial is paused in such a session: teaching uses the saved levels, and the trial continues at the next eligible session.
- Three independent axes: support, guiding-question frequency and guiding-question depth. Each axis has three named levels (below). Named behavior contracts and examples provide consistency across models; vague decimal instructions are insufficient.
- Frequency follows key decisions (defined under Level examples), not mechanical question counts.
- A request to ask fewer questions changes guiding-question frequency only; preserve support and depth unless the student also requests changes to those axes.
- Guiding-question depth is a preference, not a prohibition on temporary help: a student who prefers why/what-if questions may receive a simple next-step question to locate confusion, without changing the saved preference.
- Method-first support explains how to solve the problem before the student tries. Example-first support fully solves a separate example, then gives a fresh application question. Neither reveals the answer to an active student question unless requested.
- Temporary difficulty gets temporary help. Wrong answers, including repeated wrong answers, never by themselves lower any saved teaching preference. Simplify the current teaching when needed; lasting preference changes require evidence about the student's preferred interaction style, not their performance.
- Explicit lasting requests such as "always explain first" change the relevant saved preference immediately, without requiring repeated evidence or a probe. Preserve the student's words; do not probe in contradiction to that instruction until the student revises it. Other axes remain independently adaptable.
- A request scoped to one course or subject ("for math, always show an example first") is stored as a global preference, since there are no course overrides, and the agent says so in one line.
- Distinguish preference provenance: default, sampler, learned, explicit standing instruction, or legacy. Default, sampler, learned and legacy values remain probeable; explicit values are not. Temporary requests do not create standing instructions. Ambiguous wording changes the immediate response without creating a permanent probe restriction. An isolated answer request is honoured immediately without changing any preference.
- Announce lasting changes briefly. Temporary assistance stays unobtrusive.

## Axis levels

Each axis has three named levels. A change moves one level at a time; a move between adjacent levels is one **transition**. Defaults are the middle column.

| Axis | More guided | Default | More independent |
|---|---|---|---|
| Support | example-first | method-first | try-first |
| Guiding-question frequency | checks only | key decisions | every step |
| Guiding-question depth | next step | why | what-if |

- Probes only move one level toward the right-hand column (more Socratic).
- Moves toward the left happen only by explicit request. One exception offers the choice instead of making it: when the frustration answer-giving step (see Existing mechanics) fires in two separate Standard sessions, ask once, "Want fewer questions from now on?" A yes is an explicit request; a no or no answer changes nothing.
- Each level has one "does" example and one "must not" line, and "key decision" and "comfortable engagement" have concrete examples (see Level examples).

## Level examples

Shared task for every example: "Describe in set notation the language of S → aSc | b."

### Support

| Level | Does | Must not |
|---|---|---|
| example-first | Fully solves a different grammar first: "S → aSb \| ε: each step adds a on the left and b on the right; the base case adds nothing; so L = {aⁿbⁿ \| n ≥ 0}." Then: "Now yours." | Solve the student's own grammar, or show part of its answer. |
| method-first | States the method without working any grammar: "1) What does one step add on each side? 2) What does the base case add? 3) Count the steps as n and write the exponents." Then: "Try yours." | Work an example through to the end, or hint at this answer's exponents. |
| try-first | "Try it first. Tell me how far you get." Help comes only after the attempt, and only about where it went wrong. | Explain the method or show an example before the student has tried. |

All support levels: once the student is working on the question, its answer is shown only on request.

### Guiding-question frequency

Steps of the shared task: (1) what one S-step adds, (2) what the base case adds, (3) how many times the step can repeat, (4) writing the set.

| Level | Does | Must not |
|---|---|---|
| checks only | Explains all four steps as statements, then one check at the end on a fresh grammar: "Your turn: S → aaSb \| c." | Ask anything partway through the explanation. |
| key decisions | Asks only at key decisions, here steps 1 and 3: "What does aSc add on each side?" and "Can the step happen zero times?" Steps 2 and 4 are stated. | Ask at every step, or at none. |
| every step | One question per step: "What does aSc add on the left?" "What does b add?" "How many times can it repeat?" "So what's the set?" | State a step's result before asking it. |

A **key decision** is a step where a plausible wrong choice gives a different final answer.

### Guiding-question depth

Depth is the kind of question asked at a moment chosen by the frequency level. Example moment: step 1, after S ⇒ aSc.

| Level | Does | Must not |
|---|---|---|
| next step | Asks for the next action or fact: "Apply the rule again: S ⇒ aSc ⇒ ?" | Ask for a reason or a changed case. |
| why | Once the student has found the step's result, asks for the reason behind it: "You said each step adds one a and one c. Why does that keep their numbers equal?" | Settle for a bare next-step answer, change the problem, or put a result the student has not found into the question. |
| what-if | Asks about a changed case: "If the rule were S → aScc, what would the set become?" Asked only after the student has the main answer. | Ask a what-if before the student has solved the original question, or give the changed case's answer after a wrong try or "idk". |

Any depth level may drop to a next-step question for the moment, to locate confusion, without changing the saved level.

### Comfortable engagement

A probe may start only after comfortable engagement.

Comfortable:
1. The last two answers were attempts in the student's own words, right or wrong, with no complaint. Example: "each step adds an a and a c, so equal counts?"
2. The student went beyond the question: asked a follow-up ("does this work if b is ε?") or explained without being asked.

Not comfortable (no probe for now):
1. Any frustration signal in the last few messages: "just tell me", "idk" twice, all caps, "this is pointless".
2. Several one-word replies in a row after explanations ("ok", "k", "sure"), or the student said they're tired, rushed or confused.

## Probes

- A probe is a **trial**: one transition on one axis, applied naturally and without announcing a calibration exercise. Once started, the trial behavior continues in each following eligible Standard session until it is adopted or rejected. Continuing an active trial uses that session's one probe.
- At most one active trial across all courses, and at most one probe per Standard session, started only after comfortable engagement.
- Positive evidence: the student willingly explains reasoning or explores a follow-up. Brief answers are neutral. Correctness alone is neither acceptance nor rejection. Do not routinely interrupt teaching to ask whether the student liked a probe.
- Adopt the transition after positive evidence in two different Standard sessions held on different calendar days. Neutral sessions neither count nor reset. A single answer never changes the saved preference.
- Pushback rejects the trial: revert immediately and reset its positive evidence.
- Rejection counts belong to one specific transition, not to the axis. After the first rejection of a transition, skip the next eligible Standard session before trying it again; after the second, skip the next two; after the third, stop. Rejecting less explanation does not block a separate trial of more frequent questions. Urgent sessions and sessions within 48 hours of an exam do not advance this schedule. An explicit request may reopen a stopped transition.

## Setup sampler

- Offer once during setup, with an explicit skip option; never offer again after setup.
- If setup is interrupted, preserve completed sampler choices and resume the remaining demonstrations when setup resumes. An explicit skip ends the sampler, retaining completed choices and using defaults for unanswered axes; it is not offered again.
- Explain the consequence of skipping: use the default levels while continuing to adapt through study.
- Use quick everyday demonstrations, one choice at a time, to explore each axis separately.
- Finish with a brief tentative preference summary and continue without an extra confirmation step.
- The sampler only fills axes still at their default. It never overwrites an explicit, learned or legacy value.
- Existing users with completed setup keep that status. Missing teaching preferences use the defaults and adapt through Standard sessions; do not reopen setup or automatically launch the sampler.
- Do not confuse this optional sampler with the knowledge gauge.

## Ownership of behavior and state

- Skill Markdown defines behavior contracts, examples and adaptation rules.
- A small script validates and persists structured preference state in its own global file, separate from the always-loaded profile.
- The agent interprets conversational evidence; the script does not infer frustration.
- Stored state is closed and enumerable, with no free-text evidence notes:
  - per axis: level, provenance, and for explicit values the student's wording;
  - the one active trial: axis, from-level, to-level, and the session IDs that gave positive evidence;
  - per transition: rejection count and the next eligible Standard-session index;
  - a global counter of eligible Standard sessions.
- A **session** is one `started:` record in a course log. For preference evidence, two sessions must also fall on different calendar days.
- Persisted state survives a change of agent or conversation. Never record personality guesses or mood labels.

## Existing mechanics: fate of each

- **Delivery choice.** This design replaces the core rule "the exam date is the only mode input; the student never picks a mode" (`skills/mimir-core-rules/SKILL.md`). Exam proximity sets the default class; the student may choose Standard despite proximity or ask to cram earlier. The class line states the reason, e.g. "Urgent: exam within 48 hours" or "Standard: you asked".
- **Lasting delivery override.** Saved for one exam only and expires when that exam passes. Without an explicit lasting request, a delivery choice lasts for the current session and delivery is reassessed at the next.
- **`dial_preference`.** An existing value becomes the "checks only" frequency level with provenance `legacy`, so it stays probeable.
- **Frustration override.** Keeps its in-session behavior: one smaller step, then the answer, and the topic stays shaky (the `frustration_override` mastery column remains as mastery evidence). It no longer writes `dial_preference` or says "Fewer questions from now on." Its second occurrence in a separate session triggers the one-time question above.
- **Explanation ladder.** The support level picks the starting rung: example-first starts at the worked-example rung, method-first at the notation rung. Mastery-driven `attempt_first` overrides the support level for that topic. `## Rung hints` retire; the support axis replaces them. Existing rows are ignored, not converted and not deleted: a rung hint records what worked after an explanation failed, which is performance evidence, so it never sets a preference. Support starts at its default.
- **Standard retries.** Unlimited trial-and-error attempts with Socratic guidance; honour requests for the answer. Record the first wrong answer once; a later right answer after guidance records as assisted.
- **Question labels.** Real past-paper, flagged, OCR and tentative items keep their gate label on every item. Only plain practice items are declared once per session instead of labelled individually.

## Transition for existing users

- Existing courses get the knowledge gauge once (see Knowledge gauge). Existing `dial_preference` and `## Rung hints` follow Existing mechanics.
- At the first study session after the update, say one short line, once: "New: sessions run until you say 'end session'. You can also ask to cram or to study normally." A global seen marker stops it repeating. An existing user is one with evidence of use before the update: setup is done, or some course has a session log (a lazy setup leaves no `setup_done`). New users never hear it: setup marks it seen when there is no such evidence, and so does every first study session. No longer what's-new list; the other changes explain themselves when they happen.
- Existing date-only exam rows are not asked about in bulk. The two-day rule in Exam dates and times asks for each exam's time before it matters.

## Study flow

- Study sessions end only at the student's request. When a planned list or route runs out, say so and offer more; do not close.
- Feedback and the next appropriate question normally share one message; pause for clarification or a continue/move-on decision.

### Knowledge gauge

- **Standard:** announced and automatic in the first Standard session of each course that has no gauge-done marker. The marker is per course and is set when the gauge finishes, so the gauge never runs twice. Existing courses (which already have `first_contact`) have no marker, so they get the gauge once at their next Standard session. The gauge covers only `unseen` topics and skips any topic with recorded evidence (gap, shaky or mastered). A course with no topics yet (no outline, slides or past papers) gets no gauge and its marker stays unset; the gauge runs at the first session that has topics. Never gauge from the course name or general knowledge: answer keys must be checkable against course files.
- **Urgent:** at the start of every Urgent session, offer a mastery gauge before drilling. Run it only if the student accepts; otherwise start drilling. The same offer applies to the Urgent branch of `mimir-past-questions`, defined once in the core rules.
- Focus the gauge on the highest-priority question types rather than surveying the whole course. Use fresh questions before showing any recipe or worked answer, to measure what the student can already solve alone.
- Gauge answers record as unassisted solves through the existing recorder. The existing mastery rule (two distinct unassisted solves, on separate days or with a real past-paper question) already prevents one right answer from marking a topic mastered.
- When the gauge shows a question type is already solvable, skip its recipe and focus drilling on weaker types, while allowing further practice on request.
- The gauge assesses knowledge, not teaching preferences, and contributes no preference evidence.
- **First-ever onboarding order:** setup (with the optional sampler), then the exam-date question, then the gauge in the first study session.

### Urgent

- **Opening order:** class line, then the gauge offer, then the triage table, then drilling. In a lazy setup the class line stays the first thing said.
- Recipe, then a fresh similar application question. After a wrong answer, correction and a fresh similar question rather than retrying the same question.
- When verified past-paper frequency is available, cite it when explaining topic priority or the decision to keep drilling, such as "this appeared in 9 of 11 papers". Without past papers, prioritize using announced exam scope, syllabus and lecture emphasis and state that basis instead; never invent paper statistics.
- **Continue-or-move-on check.** Count unsuccessful attempts per question type, in total across the session, not only in a row. Wrong answers, "idk", "skip" and "just tell me" are unsuccessful. A right answer after a hint is a success but does not reset the count. When the count reaches three, state real past-paper frequency when known and ask whether to continue or move on. Choosing "continue" resets the count to zero. An item the answer-key gate drops is not an attempt.

## Exam dates and times

- When an exam is added, ask for its date and time together; "don't know" is accepted for the time. Store the time when given.
- When an exam is within two days and its time is still unknown, ask for the time once more.
- When the date is known but the time is unknown, default to Urgent if the exam is today or tomorrow, label the time unknown, and never show an hourly countdown.
- When a date-only exam is today, ask whether it is still ahead before drilling.
- Default to Urgent within 48 hours of the actual exam time.

## Exam scope

Issue #45 (part 2 of #29). Settled in a short follow-up interview.

- **Storage.** When the student states a scope ("the midterm covers sessions 1–19"), the agent resolves it once into a list of in-scope question types and topics, using the course's session notes and syllabus. It shows the list ("In scope: … Out: …") and the student confirms or edits it. The confirmed list is saved with the exam, together with the student's original words, and used unchanged in every later session. The agent never reinterprets the sentence on its own.
- **Out-of-scope types.** Listed at the bottom of the triage table, marked "not on this exam", and never drilled, gauged or used for recipes unless the student asks. They stay visible so a wrong scope list is easy to spot.
- **Capture.** Asked when the exam is added, together with its date and time ("What does it cover? 'don't know' is fine"). At setup the course has no files yet, so the student's words are noted by course code and the first study session of the course runs the show-and-confirm step with them. A lazy setup does not ask. If still unknown when the exam is within two days, asked once more in the same question as the missing time. When the syllabus or outline states an exam's coverage, the agent proposes that list for confirmation. The student may give or change the scope at any time; a change goes through the same show-and-confirm step.
- **Unknown scope.** Every question type is ranked as before and nothing is marked. No guessing from paper names (they are unreliable: a file of finals may not say so).
- **Standard study.** The scope of the next exam also orders the Standard route: in-scope topics first, out-of-scope topics last, marked "not on your next exam". Nothing is removed and the student may pick any topic. After that exam passes, the next exam's scope (or none) applies.
- **New material.** A question type that appears after the scope was confirmed is ranked normally with a "not checked" mark. At the next session the agent asks once, in one line: "New question type 'X' was found. Is it on your <exam>?" The answer updates the saved list.
- **Unsure.** A "don't know" to that question saves the name as unsure: it is not asked again and is ranked normally with the same "not checked" mark as a new type.
- **Date changes.** The scope is saved with the exam's date and name. When the exam's date or time changes but its course and name stay, the saved scope follows it: a saved scope whose date no exam row of that name has any more belongs to the moved exam, and the next save moves it to the new date. A passed exam whose row stays keeps its own scope.

## Learning-time forecasts

- Remove prescriptive learning-time forecasts, including daily-minute estimates and cost-of-delay claims. The reported OOP session recommended 1–3 minutes daily across 62 days despite substantial unresolved gaps. Course, student and topic differences make these estimates misleading.
- Remove the route-learning-time estimate as an Urgent trigger. Urgent depends on actual exam proximity or an explicit request to cram.
- `mimir-plan`'s cost-of-delay output is retired.
- Debrief's cram bill keeps the hours actually studied and drops the counterfactual estimate of what the route should have taken.
- Urgent triage ranks question types by marks × past-paper frequency and cuts nothing for a minutes budget. Student-ended sessions and the continue-or-move-on check replace the cut-off. The minute-based constants (`EPISODE_MINUTES`, `URGENT_STUDY_SHARE`, points per hour) lose their role in triage.
- Actual observed session durations remain historical evidence, not promises of future learning speed.

## Tunable heuristics

These numbers are product rules of thumb, not evidence-based, and may change after real use: the 48-hour Urgent window (inherited from `URGENT_FLOOR_HOURS`), three unsuccessful attempts, two sessions for adoption, the skip-one / skip-two / stop rejection schedule, and at most one probe per session.

## Sampler trial findings

A single simulated conversation with Opus captured example-first support for unfamiliar material, few interruptions and why/what-if follow-ups. This establishes feasibility only, not validation across students or models.

The frequency comparison also changed how much solution was disclosed, confounding the choice. Future demonstrations should isolate the relevant axis. The closing demonstration previewed a later follow-up and added an unnecessary readiness question; keep one active question and wait.

## Acceptance test: levels on two models

Run once the behavior is built. Not a design question.

1. Test course: a small fixture course with the shared task "Describe in set notation the language of S → aSc | b" as a topic, plus 4–5 questions so a set can run out.
2. One level per run: set one axis to the level under test and keep the other two at their defaults. Nine runs per model.
3. Models: Claude Code and Codex, 18 runs in total.
4. Scripted student: the same replies every run: one right attempt, one wrong attempt, one "idk", then "end session".
5. Check each transcript against its level's row: the "does" line happened, no "must not" line was broken, and the answer appeared only on request.
6. Flow checks in the same runs:
   - No stall: when a question set runs out, the model says so and leads into the next set, or offers choices, in the same message (the Codex stall in `userfeedback.md`, 2026-11-04).
   - Clean end: the session closes only on "end session", and closes once.

Passes when every run meets its row and both flow checks pass on both models. A failure is first fixed by rewording that level's instruction or adding an example. A model that keeps failing is recorded as a known host gap, as in #23. The runs may be delegated to one Claude agent and one Codex agent that play the student and report pass or fail per row.

## Interview status

The interview frontier is empty: every open decision has been answered and recorded here. No implementation approval is implied by this draft.

## Parked idea

- Optional roleplay mode inspired by Mimir from God of War. Mentioned as a future idea; behavior, scope and implementation are not decided in this interview.
