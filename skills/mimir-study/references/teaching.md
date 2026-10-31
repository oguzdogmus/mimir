# Teaching engine (Standard episode, topic `T`)

`session.md` §4 step 3 hands off here. Standard delivery only: never in Urgent. The scripts, the item rules (Questions), the recording rules (Recording) and the `clock` rule of `session.md` §4 all still apply: after each step below (each explanation step, each guiding answer, each item answer), run `session.py now` and `session.py clock`, and obey `wrap` and `over`. Every date written here is the evidence date from `session.md` §1 step 1; never work out a date.

## 0. Inputs

- Profile (read once, at episode start, `session.md` §4): `course_language`, `teaching_language`, `dial_preference`, `## Rung hints`. A value that is empty, `none` or still a template placeholder (`<...>`) counts as not set. When `profile.md` was missing or unreadable, all four are not set and every profile Edit below is skipped, silently.
- Read the `## Topics` rows for `T` in `<course_dir>/INDEX.md` and the files they point to (at the anchored page), and `<course_dir>/.state/fingerprint.md` (notation, phrasing, disguise types, question types).
- `attempt_first` for `T`: from the latest `start` `topic` or `check` output for `T`. When the recheck (`session.md` step 1) recorded an answer on `T`, run `check` on `T` again first and use that.
- Profile edits go through your file-editing tool, keep the template's shape and stay within the 50-line cap.

## 1. Order for `T`

1. `attempt_first` true: attempt-first (§5), then teach from the attempt (§2, §3).
2. Otherwise: teach (§2, §3).
3. Then the disguise drill (§6).

The frustration rule (§4) applies at every point.

## 2. Explanation ladder

Rungs, top to bottom: **notation** (the professor's notation from the fingerprint; math the `mimir-notation` way), **analogy**, **worked example**, **visual** (built through `mimir-notation`), **native language**.

1. Every explanation starts at the notation rung.
2. It does not land when the student says so ("I don't get it", "lost", "huh?") or answers a guiding question wrongly. Then step down exactly ONE rung for the next explanation. Never skip a rung, and never start lower because of `## Rung hints` (the hint is only recorded).
3. Native language is a rung only when `teaching_language` and `course_language` are both set and differ (compared ignoring case and extra spaces). Otherwise skip it. When you use it, declare it first: "Switching to <teaching_language> for this step." Technical terms stay as the course writes them.
4. On the lowest available rung, keep explaining at that rung in smaller steps.
5. Once it lands (the student says it makes sense, or answers a guiding question right), restate the point in the professor's notation, in `course_language`. Always end there.
6. When a rung below notation landed, record it:
   - Topic type: the `## Question types` type in `fingerprint.md` that covers `T`; when none does, `T` itself.
   - Edit `## Rung hints` in the profile, row `| <topic type> | <rung> |` (`analogy`, `worked example`, `visual` or `native language`). Replace that type's row if there is one; else replace a template placeholder row; else, with 5 or more rows already, replace the last row; else add the row. Escape `|`.
   - Append to the session log: `rung: <T> <rung>`.

## 3. Socratic dial

- **Default (Socratic):** each explanation step opens with ONE guiding question about the step, then the explanation builds on the answer. A right answer means the step landed; a wrong answer means it did not (§2).
- **Fewer questions** (`dial_preference` set): declared once at episode start (`session.md` §4). Explain each step directly, with no guiding questions; the only check is the practice item (the drill, §6). A step still fails to land when the student says so (§2).
- Guiding questions are dialogue, not items: no answer key, no gate, no provenance label, nothing recorded in `mastery.md` or under `## Results`.

## 4. Frustration

A frustration signal:
- "just tell me" (or the same in other words, e.g. "just give me the answer");
- a message in all caps, only when it has at least 3 words and is not an answer to the item or guiding question showing ("OK", "BFS", "O(N)", "NP" never count);
- "idk" twice in a row (to guiding questions or items alike), except before an attempt-first attempt (§5 governs "hint", "skip" and "idk" there, and they never count toward this signal).

An "idk" on an item still follows the Questions rule (key shown, counts as wrong) and also counts toward this signal.

The override applies to topic `U`: the topic of the item or explanation in progress when the signal came. That is usually `T`; a recheck item on a stale prerequisite makes `U` that prerequisite, and its line is overridden, not `T`'s.

1. First signal on `U`: give exactly ONE smaller step: a statement, not a question. No guiding question in that message.
2. The student's next reply after the smaller step is another signal, another "idk", or a wrong answer to the same step: say "Giving you the answer. This topic stays marked shaky until you solve one on your own." and give the answer (the worked key of the item shown, or the point being explained, in the professor's notation). Then the override:
   - Edit `U`'s `mastery.md` line (add it if missing; keep column order): status `shaky`; append the date to `frustration_override` (comma-separated after any earlier dates); `assisted` and `unassisted` unchanged; evidence `frustration override: answer given`; `evidence_date` and `last_check` the date. Nothing else is recorded for the item that was showing.
   - Edit the profile: `dial_preference: fewer questions (<date>)`. Say "Fewer questions from now on." The rest of this session teaches in the fewer-questions way (§3).
   - Append to the log under `## Results`: `- <U> frustration override: answer given`.
3. For the rest of the session, no answer on `U` changes `mastery.md`: say right or wrong and show the key as usual, and log `- <U> <kind> <label>: after frustration override, not counted`.
4. Before an attempt-first attempt, only "just tell me"-type and all-caps signals come here; "hint", "skip" and "idk" follow §5.

## 5. Attempt-first

When `attempt_first` is true:

1. Say "You've solved <T> with help 3+ times, so try this one before any hint."
2. Pose the first practice item before any explanation: one item `{"topic": "<T>", "origin": "practice"}`, built, gated and shown per the Questions rule.
3. No hint and no explanation until the student attempts. Any attempt counts, right or wrong, complete or not.
4. Before an attempt, this step governs "hint", "skip" and "idk" entirely; they never count toward the "idk twice" frustration signal (§4). The first "hint", "idk" or "skip" gets exactly "Any start counts, even a guess." The second: "hint" gives the prepared hint (Questions rule; a right answer is then assisted); "idk" or "skip" shows the key, and it counts as wrong. A "just tell me"-type or all-caps signal goes to §4.
5. Record the answer per Recording (a right answer with no hint is an unassisted solve).
6. Then teach from the attempt: start the ladder (§2) at the step where the attempt went wrong or stopped (or the key, when it was shown). When the attempt was right and complete, give one short confirmation in the professor's notation instead, then go to the drill.

## 6. Disguise drill

The practice after teaching: ONE underlying problem on `T` in `DISGUISE_VARIANTS = 2` surface forms.

1. Build 2 variants from the fingerprint's `## Disguise types` (fallback when it has none: renamed symbols, reworded text, reversed direction), in the professor's notation and phrasing. A `(tentative)` disguise type is used with "from a photo/scan, may be off" once.
2. Each variant is an item `{"topic": "<T>", "origin": "practice"}` with its own key and hint. Gate both as ONE batch (`verified-items.md`).
3. Show both shown items, each with its label. Socratic dial: ask one guiding question, "What do these two have in common underneath?" Then confirm or correct the shared structure in the professor's notation. Fewer questions: state the shared structure yourself instead of asking.
4. The student solves each variant, one at a time. Record each answer per Recording (and §4 step 3 after an override).
5. When the gate leaves fewer than 2 items to show, skip step 3; a single remaining item is asked as a plain practice item. When it leaves none, say each dropped line, record nothing, skip the drill and go on (`session.md` §4 step 4).
