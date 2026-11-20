# Acceptance runs: check ledger on Claude Code (#78)

2026-11-20. Live quiz runs with a scripted student on Claude Code 2.1.327, run lean (only Mimir) on Sonnet, as [`tests/acceptance/README.md`](../tests/acceptance/README.md) says: the quiz script of the speed round (3 questions; a right answer, a plausible wrong answer, a right answer, "end session", "thanks") on a fresh fixture folder. The student was played by the implementing agent. J to N are counted from the raw host events by `tests/acceptance/speed_checks.py`. Raw runs are kept outside the repo under `~/.cache/mimir-acceptance/results/claude-78-r1` and `r2`. These are fixture runs, not real student sessions.

## Round 2 (plugin `cd2c7f3`)

| Run | C | F | G | I | J | K (script) | L | M | N |
|---|---|---|---|---|---|---|---|---|---|
| quiz, 3 questions | P | F | P | P | P | F | P | P | P |

- **G passes.** One `Agent` call with `subagent_type` `mimir:verifier` and `run_in_background` false, whose whole prompt was "Check the evidence pack at `<pack>`." The checker made one tool call, a Read of the pack, and nothing else (#2). Its reply started with the pack token, then one `N | verdict | reason` line per question; the tutor pasted it into `verify.py settle` unchanged. All three keys were `correct`, stored in the ledger with `checker: independent`. The pack was deleted when the batch settled.
- **N passes**: the one `settle` followed its checker dispatch in the same turn. The counter's unit tests cover a settle with no dispatch (the #23 failure), which N fails.
- **`record` read the ledger**: three outcome lines under `## Results`, each with the label the ledger holds; no `gate` object, no `real_past_paper`.
- **K fails (script)** in turn 1, as in every #77 round: the declaration and Item 1 were written only after the checks. The #77 end-of-turn repeat put them on screen. Not changed by this slice.
- **F fails**: the close is right (one `ended:` line, `save.md` rewritten), but "thanks" got "Good luck with the midterm", as in #77's quiz run. Outside this slice.
- Answer turns 2 to 4 each wrote the next item a second time after `record` ("Item 2 is the one on screen"). That breaks the #77 rule "inside a set, nothing is written after `record`"; J (text before the first tool call) still passes. Outside this slice.

## Round 1 (plugin `ce99387`): the checker's working before the token

The checker wrote its working ("1: S → aaSc | b gives a^(2n) b c^n. Correct.") and then the token and the verdict lines. `settle` required the token on the first line, so it refused the reply; the tutor dispatched the checker again, got the same shape and stopped honestly, with batch 1 unsettled and nothing recorded. It did not edit the reply. Fix in `cd2c7f3`: the token must still stand on a line of its own, text before it is ignored and only the verdict lines after it count; the checker is told to reply with the token first and show no working. Round 2 got the token on the first line.

## Cost

About $1.60 for round 2 (6 turns) and about $0.24 for round 1 (1 turn), as the host reports it.
