# Acceptance runs: speed slice on Claude Code (#77)

2026-11-20. Live runs with a scripted student on Claude Code 2.1.327, run lean (only Mimir) on Sonnet 5.5, as [`tests/acceptance/README.md`](../tests/acceptance/README.md) says: one study run (support method-first) and one quiz run of 3 questions per round. The student was played by the implementing agent. The speed rules J to M are counted from the raw host events by `tests/acceptance/speed_checks.py`; K is also checked by eye. Raw runs are kept outside the repo under `~/.cache/mimir-acceptance/results/claude-77-r1` to `r6`. These are fixture runs, not real student sessions.

## Final round (plugin `2788517`)

| Run | A | B | C | D | E | F | G | H | I | J | K (script / eye) | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| study, support method-first | P | P | P | P | P | P | P | P | P | P | P / F | P | P |
| quiz, 3 questions | – | – | P | – | – | F | P | – | F | P | P / F | P | P |

- **J (feedback first) holds.** Every answer turn of rounds 3 to 6, in both runs, wrote the feedback, the key and the next checked question before `session.py record`. The eight 0.4.0 runs of [#44](https://github.com/oguzdogmus/mimir/issues/44) each fail J.
- **L and M hold.** The checker was always `mimir:verifier` with `run_in_background` false, one batch per set.
- **`record` writes the log.** Every outcome line under `## Results` came from `record`, with no duplicates.
- **K fails by eye.** See below.
- Quiz F: the reply to "thanks" corrected the close line's topic status and added "Good luck". Quiz I: a progress note came before the declaration. Both are outside this slice's rules.

## Text before tool calls is lost on Claude Code

The design's at-once rule (a set's first practice question, the Standard explanation or the Urgent recipe written before the gate and the checker) did not work on this host in any round. On Sonnet in every round, and in one Opus turn, the tutor drafted that text in its thinking, called the gate and the checker, and then wrote "Item 1 is above" or "the question above stands" about a question the student never saw. Short verbatim lines, such as the class line, do appear before tool calls; generated questions and explanations did not. Five rewordings did not change this: visible reply text, no progress notes, thinking is never seen, compose the question straight into the reply.

Rounds 5 and 6 add the end-of-turn repeat (`verified-items.md`, Turn shape; `session.md`, Questions): the turn that starts a set ends, once its check settles, with the question, the quiz declaration or the explanation written again in full. The session is usable again, but on Claude Code the student still waits for the check at a set start. On a host where the early text shows, the student sees it twice. The maintainer has to decide whether that trade is right; design §8 already allows leaving a host out of the speed claim.

## How the rules changed

| Round | Commit | Finding | Change |
|---|---|---|---|
| 1 | `a1cce49` | Study: lesson and question only in thinking. Quiz: progress note first, Item 1 after the check, no declaration | `e8789d5`: the at-once text is visible reply text in full; nothing before the declaration; never report a check's result |
| 2 | `e8789d5` | Same, and the class line lost too | `9de2e98`: the student reads only reply text; never point at a question "above"; a late fallback |
| 3 | `9de2e98` | Answer turns: feedback first (J holds). Set start: still lost; status reports after `record` | `6a0cbdd`: nothing after `record`; compose the question straight into the reply |
| 4 | `6a0cbdd` | Unchanged on Sonnet; one Opus turn the same | `9b9386f`: the set's first question is always written again once its check settles |
| 5 | `9b9386f`, `3d05244`, `78ae278` | Question shown; declaration and explanation still lost | the repeat carries the quiz declaration and the explanation or recipe; the Standard explanation turn always ends with the explanation and its questions |
| 6 | `2788517` | Both runs usable; results above | none |

## Cost

About $5.10 for round 6 (study $3.52 over 9 turns, quiz $1.62 over 6 turns) and about $5.30 for rounds 1 to 5 and the Opus turn, at API prices.
