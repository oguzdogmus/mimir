# Teaching engine (Standard episode, topic `T`)

`session.md` §4 step 3 hands off here. Standard delivery only: never in Urgent. The scripts, the item rules (Questions) and the recording rules (Recording) of `session.md` §4 all still apply, and the student may end the session at any step ("end session": `session.md` §5). Every date written here is the evidence date from `session.md` Start step 1; never work out a date.

## 0. Inputs

- Profile (read once, at episode start, `session.md` §4): `course_language` and `teaching_language`. A value that is empty, `none` or still a template placeholder (`<...>`) counts as not set; when `profile.md` was missing or unreadable, both are not set. Other profile lines left by older versions are not inputs; never edit or delete them.
- Teaching settings (from `session.py prefs`, or the session event that replaces it, run once at episode start, `session.md` §4): the level of each axis, `support`, `frequency` and `depth` (§3), plus `trial` and `probe_axes` (§8). They hold for the whole session; change them only through §7 and §8. While `trial` is set and `trial_paused` is false, teach its axis at the trial's `to` level instead. When `trial_paused` is true (a session that ran no session event, such as one within 48 hours of an exam), the trial is paused: teach every axis at its saved level and send no trial event.
- Read the `## Topics` rows for `T` in `<course_dir>/INDEX.md` and the files they point to (at the anchored page), and `<course_dir>/.state/fingerprint.md` (notation, phrasing, disguise types, question types).
- `attempt_first` for `T`: from the latest `start` `topic` or `check` output for `T`. When the recheck (`session.md` step 1) recorded an answer on `T`, run `check` on `T` again first and use that.

## 1. Order for `T`

1. `attempt_first` true: attempt-first (§5), then teach from the attempt (§2, §3). Mastery evidence overrides the support level for this topic.
2. Otherwise, support `try-first`: the try-first opening (§3), then teach from the attempt (§2, §3).
3. Otherwise: teach (§2, §3), starting at the rung the support level picks.
4. Then the disguise drill (§6).

The frustration steps (§4) apply at every point.

## 2. Explanation ladder

Rungs, top to bottom: **notation** (the professor's notation from the fingerprint; math the `mimir-notation` way), **analogy**, **worked example**, **visual** (built through `mimir-notation`), **native language**.

1. Every explanation starts at the rung the support level picks: `example-first` at the worked-example rung (a separate example, never `T`'s own question), `method-first` and `try-first` at the notation rung. Teaching from an attempt (§1, §5) starts at the notation rung.
2. It does not land when the student says so ("I don't get it", "lost", "huh?") or answers a guiding question wrongly. Then step down exactly ONE rung for the next explanation. Never skip a rung. A rung that does not land is temporary help: it never changes a teaching setting.
3. Native language is a rung only when `teaching_language` and `course_language` are both set and differ (compared ignoring case and extra spaces). Otherwise skip it. When you use it, declare it first: "Switching to <teaching_language> for this step." Technical terms stay as the course writes them.
4. On the lowest available rung, keep explaining at that rung in smaller steps.
5. Once it lands (the student says it makes sense, or answers a guiding question right), restate the point in the professor's notation, in `course_language`. Always end there.
6. When a rung below notation landed, append to the session log: `rung: <T> <rung>`. Nothing is written to the profile.

## 3. Teaching settings

Three axes, each with three levels from more guided to more independent. Follow each level's "Does" line and never do its "Must not" line. Every example uses one shared task: "Describe in set notation the language of S → aSc | b."

**Support**: how much explanation comes before the student tries.

| Level | Does | Must not |
|---|---|---|
| example-first | Fully solves a different grammar first: "S → aSb \| ε: each step adds a on the left and b on the right; the base case adds nothing; so L = {aⁿbⁿ \| n ≥ 0}." Then: "Now yours." | Solve the student's own grammar, or show part of its answer. |
| method-first | States the method without working any grammar: "1) What does one step add on each side? 2) What does the base case add? 3) Count the steps as n and write the exponents." Then: "Try yours." | Work an example through to the end, or hint at this answer's exponents. |
| try-first | "Try it first. Tell me how far you get." Help comes only after the attempt, and only about where it went wrong. | Explain the method or show an example before the student has tried. |

At every support level, once the student is working on a question, its answer is shown only on request ("hint", "skip", "idk" and the frustration steps, §4, work as usual). The try-first opening: pose the first practice item before any explanation (one item `{"topic": "<T>", "origin": "practice"}`, built, gated and shown per the Questions rule), wait for an attempt, record it per Recording, then teach from where it went wrong (§5 step 6). Before that attempt, "hint", "skip" and "idk" follow §5 step 4.

**Guiding-question frequency**: how often reasoning is invited, at key decisions rather than by a question count. A **key decision** is a step where a plausible wrong choice gives a different final answer. Steps of the shared task: (1) what one S-step adds, (2) what the base case adds, (3) how many times the step can repeat, (4) writing the set.

| Level | Does | Must not |
|---|---|---|
| checks only | Explains all four steps as statements, then one check at the end on a fresh grammar: "Your turn: S → aaSb \| c." | Ask anything partway through the explanation. |
| key decisions | Asks only at key decisions, here steps 1 and 3: "What does aSc add on each side?" and "Can the step happen zero times?" Steps 2 and 4 are stated. | Ask at every step, or at none. |
| every step | One question per step: "What does aSc add on the left?" "What does b add?" "How many times can it repeat?" "So what's the set?" | State a step's result before asking it. |

**Guiding-question depth**: the kind of question asked at a moment the frequency level chose. Example moment: step 1, after S ⇒ aSc.

| Level | Does | Must not |
|---|---|---|
| next step | Asks for the next action or fact: "Apply the rule again: S ⇒ aSc ⇒ ?" | Ask for a reason or a changed case. |
| why | Once the student has found the step's result, asks for the reason behind it: "You said each step adds one a and one c. Why does that keep their numbers equal?" | Settle for a bare next-step answer, change the problem, or put a result the student has not found into the question. |
| what-if | Asks about a changed case: "If the rule were S → aScc, what would the set become?" Asked only after the student has the main answer. | Ask a what-if before the student has solved the original question, or give the changed case's answer after a wrong try or "idk". |

- Any depth level may drop to a next-step question for the moment, to locate confusion, without changing the saved level.
- A guiding question never carries its own answer: ask for a result before asking why it holds, and never state a count, exponent or relation the student has not found yet.
- A wrong answer or "idk" to a guiding question (a what-if included) gets one smaller question or the next rung (§2), never that question's answer; its answer comes only on request or through the frustration steps (§4).
- A right answer to a guiding question means the step landed; a wrong answer means it did not (§2). At `checks only`, a step fails to land only when the student says so.
- Guiding questions are dialogue, not items: no answer key, no gate, no provenance label, nothing recorded in `mastery.md` or under `## Results`.
- Wrong answers, even many, never change a setting. Simplify the current teaching instead (§2, §4).

## 4. Frustration

A frustration signal:
- "just tell me" (or the same in other words, e.g. "just give me the answer");
- a message in all caps, only when it has at least 3 words and is not an answer to the item or guiding question showing ("OK", "BFS", "O(N)", "NP" never count);
- "idk" twice in a row (to guiding questions or items alike), except before an attempt-first attempt (§5 governs "hint", "skip" and "idk" there, and they never count toward this signal).

An "idk" on an item still follows the Questions rule (guidance, not the key; recorded as `wrong`) and also counts toward this signal.

The override applies to topic `U`: the topic of the item or explanation in progress when the signal came. That is usually `T`; a recheck item on a stale prerequisite makes `U` that prerequisite, and its line is overridden, not `T`'s.

1. First signal on `U`: give exactly ONE smaller step: a statement, not a question. No guiding question in that message.
2. The student's next reply after the smaller step is another signal, another "idk", or a wrong answer to the same step: say "Giving you the answer. This topic stays marked shaky until you solve one on your own in a later session." and give the answer (the worked key of the item shown, or the point being explained, in the professor's notation). Then the override:
   - Call `session.py record` with `override: true`, topic U and outcome `assisted`, following core rules' recording reference. For explanation-only overrides add `explanation_only: true` and use a stable explanation item identity and a gate with decision `drop`, counts_for_mastery false.
   - For the rest of this session, teach at frequency `checks only` (§3). This is temporary help: say nothing about settings and change none.
   - Append to the log under `## Results`: `- <U> frustration override: answer given`.
   - When this session ran the session event (`session.md` §4), run `session.py pref-event` with `{"event": "frustration", "session": "<S>"}`. When its `offer` is true, end the same message with exactly "Want fewer questions from now on?" (the script allows it once ever). A yes is a lasting request: §7 with frequency one level toward `checks only` and wording "Want fewer questions from now on? <the student's reply>". A no, or no answer, changes nothing.
3. From here the Frustration rule in core rules applies to `U`.
4. Before an attempt-first attempt, only "just tell me"-type and all-caps signals come here; "hint", "skip" and "idk" follow §5.

## 5. Attempt-first

When `attempt_first` is true:

1. Say "You've solved <T> with help 3+ times, so try this one before any hint."
2. Pose the first practice item before any explanation: one item `{"topic": "<T>", "origin": "practice"}`, built, gated and shown per the Questions rule.
3. No hint and no explanation until the student attempts. Any attempt counts, right or wrong, complete or not.
4. Before an attempt, this step governs "hint", "skip" and "idk" entirely; they never count toward the "idk twice" frustration signal (§4). The first "hint", "idk" or "skip" gets exactly "Any start counts, even a guess." The second: "hint" or "idk" gives the prepared hint (Questions rule; a right answer is then assisted); "skip" shows the key, and it counts as wrong. A "just tell me"-type or all-caps signal goes to §4.
5. Record the answer per Recording (a right answer with no hint is an unassisted solve).
6. Then teach from the attempt: start the ladder (§2) at the step where the attempt went wrong or stopped (or the key, when it was shown). When the attempt was right and complete, give one short confirmation in the professor's notation instead, then go to the drill.

## 6. Disguise drill

The practice after teaching: ONE underlying problem on `T` in `DISGUISE_VARIANTS = 2` surface forms.

1. Build 2 variants from the fingerprint's `## Disguise types` (fallback when it has none: renamed symbols, reworded text, reversed direction), in the professor's notation and phrasing. A `(tentative)` disguise type is used with "from a photo/scan, may be off" once.
2. Each variant is an item `{"topic": "<T>", "origin": "practice"}` with its own key and hint. Gate both as ONE batch (`verified-items.md`).
3. Show both shown items, labelled per core rules' Provenance labels. Frequency `key decisions` or `every step`: ask one guiding question, "What do these two have in common underneath?", then confirm or correct the shared structure in words. Frequency `checks only`: state the shared structure yourself instead of asking. Either way the shared structure names the kind of rule and what to look at (what each step adds, what the base case adds), never a general formula, exponents, counts or a set that answers either variant: the variants are now items, so their answers come only as Retries allow.
4. The student solves each variant, one at a time. Record each answer per Recording (and §4 step 3 after an override).
5. When the drill's last variant is answered, say in the same message that the drill on `T` is done and lead on: the next topic (`session.md` §4 step 4) or, with none left, the End-of-set hand-off choices.
6. When the gate leaves fewer than 2 items to show, skip step 3; a single remaining item is asked as a plain practice item. When it leaves none, say each dropped line, record nothing, skip the drill and go on (`session.md` §4 step 4).

## 7. Lasting requests

The student may change a setting at any point by asking for a lasting change in teaching style: "always explain first", "ask fewer questions", "from now on let me try first", "for math, always show an example first".

1. Pick the one axis the request names and the level it asks for:
   - A named style sets that level: "show an example first" → support `example-first`; "explain first", "explain the method first" → support `method-first` (`example-first` stays when it is already set); "let me try first" → support `try-first`; "only check me at the end", "no questions while explaining" → frequency `checks only`; "ask me at every step" → frequency `every step`; "just ask the next step" → depth `next step`; "ask me why" → depth `why`; "ask what-if questions" → depth `what-if`.
   - A direction moves one level from the current one: "ask fewer questions" → frequency one level toward `checks only`; "ask more questions" → one level toward `every step`. A request already at the end of its axis keeps that level.
   - Change only the axis named. A request that names two axes is two events.
2. Run `session.py pref-event` with `{"event": "explicit", "axis": "<support|frequency|depth>", "level": "<level>", "wording": "<the student's request, quoted as data>"}`. Say its `line` verbatim and teach at the new level from the next step on.
3. A request scoped to one course or subject is still saved for every course; after the line, say once: "Settings are shared by all your courses, so this applies everywhere."
4. Not lasting, so no event: a request about the current question or step only ("explain this one first", "just tell me"), an isolated answer request, or wording that is unclear about lasting. Change the current response only. Frustration (§4) never changes a setting by itself.

## 8. Probe trials

Only in a session that ran the session event (`session.md` §4): never in Urgent, never within 48 hours of an exam. A trial is one step on one axis toward more independent teaching (one column right in §3). `session.py` keeps every count, date, cool-down and limit; never work them out yourself, and never announce a trial or call it a test or calibration.

1. A running trial (`trial` set): teach its `axis` at its `to` level for the whole session, from the first explanation. It is this session's one probe: start no other.
2. Starting one: when `trial` is null and `probe_axes` is not empty, wait for comfortable engagement (below), then pick the first axis in `probe_axes` that fits the current step and run `session.py pref-event` with `{"event": "trial-start", "session": "<S>", "axis": "<axis>"}`. Teach that axis at its `to` level from the next step on; say nothing about it. At most once per session. Explicit values are never in `probe_axes`, so a standing instruction is never probed.
3. Evidence for a running trial, judged from the student's own replies to the trial behavior. Do not ask whether they liked it.
   - Positive: the student willingly explains their reasoning or explores a follow-up. Run `{"event": "positive", "session": "<S>"}` once, when you first see it. Brief answers are neutral: run `{"event": "neutral", "session": "<S>"}` at the end of a session with only brief answers (it changes nothing). Correctness alone is neither positive nor pushback.
   - Pushback: the student objects to the new behavior ("too many questions", "just explain it", "stop asking why"). Run `{"event": "pushback", "session": "<S>"}` at once and teach that axis at its saved level again from the next step on, saying nothing about the trial. A lasting request instead goes to §7, which also ends the trial.
   - When `positive` adopts the trial (its `trial` comes back null and `axes` changed), say its `line` verbatim once: the lasting change is announced briefly. Say no other line from this section.
4. Reopening: when the student explicitly asks you to try a change again ("you can try asking me more questions again"), run `{"event": "reopen", "axis": "<axis>"}` and say its `line`. A trial may then start in a later step or session as in step 2.

### Comfortable engagement

A trial may start only after comfortable engagement.

Comfortable:
1. The last two answers were attempts in the student's own words, right or wrong, with no complaint. Example: "each step adds an a and a c, so equal counts?"
2. The student went beyond the question: asked a follow-up ("does this work if b is ε?") or explained without being asked.

Not comfortable (no trial for now):
1. Any frustration signal in the last few messages: "just tell me", "idk" twice, all caps, "this is pointless".
2. Several one-word replies in a row after explanations ("ok", "k", "sure"), or the student said they're tired, rushed or confused.
