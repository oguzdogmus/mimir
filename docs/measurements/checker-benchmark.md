# Checker benchmark (#79)

How well each host's answer-key checker catches wrong keys. Measured on 2026-11-20 with plugin `2d94b42` (the checker prompt of #78: `helpers/verifier.md` reading one evidence pack). Background: in real use the checker returned 427 `correct` verdicts and 1 `wrong` (`docs/trust-every-session-design.md`), which says nothing about the wrong keys it let through. The keep-or-drop review after 2027-01-04 (design §10) uses these numbers with the season counts from the ledger.

## The set

`tests/acceptance/checker_benchmark.json`: 60 questions on the CS301 Automata fixture course of `tests/acceptance/make_fixture.py`, all practice questions.

- 20 clean questions with right keys.
- 28 with one general error: a wrong exponent or range, a swapped relation, a grammar that generates too much, a wrong count, a DFA or NFA with a wrong transition, a wrong closure argument, a wrong pumping-lemma condition, an ambiguity claim, a wrong derivation step.
- 12 with one course-convention error: a key that is right in general and wrong by the course's conventions sheet (`notes/conventions.md`, added to the fixture and cited by every question) and the fingerprint's Notation, which the evidence pack carries: λ for the empty string, a set without its exponent ranges, `|`, `r⁺` or `∩` in a regular expression, a DFA with missing transitions, an NFA with ε-transitions, a PDA that accepts by empty stack.

The runner submits the questions through `verify.py submit` as 10 question sets of 6 in a fixed shuffled order, so each evidence pack mixes clean and planted questions. Each host's checker runs once per pack, as the core rules dispatch it, and each reply is settled through `verify.py settle`. A planted error counts as caught for any verdict other than `correct`; a clean question counts as wrongly rejected the same way; a reply without the pack token would leave its batch unsettled and catch nothing (none did).

- **Claude Code**: the plugin's `mimir:verifier` agent (`claude -p --agent mimir:verifier`, lean, tools Read, Grep and Glob), prompt "Check the evidence pack at <pack>." Its own setting is Sonnet at medium effort.
- **Codex**: `codex exec` read-only (CLI 0.166.0, gpt-6.2-sol), given the body of `helpers/verifier.md` and the pack line: the message a `spawn_agent` child starts from.
- **Antigravity**: `agy -p` (1.4.12, gemini-4-neon-high), given the same message.

## Results

| Run | Planted caught | General | Convention | Clean rejected | Unsettled | Time per question | Tokens per question | Cost per question |
|---|---|---|---|---|---|---|---|---|
| Claude Code, Sonnet, medium (shipped) | 39/40 (97.5%) | 27/28 | 12/12 | 0/20 | 0 | 1.42 s | 2,026 in / 118 out | $0.0039 |
| Claude Code, Sonnet, medium (rerun) | 39/40 (97.5%) | 27/28 | 12/12 | 0/20 | 0 | 1.85 s | 2,030 in / 123 out | $0.0040 |
| Claude Code, Sonnet, low | 40/40 (100.0%) | 28/28 | 12/12 | 0/20 | 0 | 1.79 s | 2,024 in / 116 out | $0.0039 |
| Claude Code, Haiku, medium | 39/40 (97.5%) | 27/28 | 12/12 | 0/20 | 0 | 1.57 s | 2,041 in / 275 out | $0.0003 |
| Claude Code, Haiku, low | 38/40 (95.0%) | 26/28 | 12/12 | 0/20 | 0 | 1.35 s | 2,035 in / 225 out | $0.0003 |
| Codex | 40/40 (100.0%) | 28/28 | 12/12 | 0/20 | 0 | 5.49 s | 15,426 in / 64 out | subscription |
| Antigravity | 40/40 (100.0%) | 28/28 | 12/12 | 0/20 | 0 | 11.44 s | 3,700 in / 1,094 out | subscription |

Time per question is the checker's run time for its pack divided by the pack's 6 questions: about 9 s per pack on Claude Code, 33 s on Codex and 69 s on Antigravity. Tokens are per question; input counts cached reads (most of Codex's input is cached: it loads the installed skills). Claude Code's cost is as the host reports it.

Misses: `g14` (an NFA for "ends in b" whose `δ(q0, b)` drops `q0`, so `bb` is rejected) passed as `correct` in both Sonnet medium runs and on Haiku low; `g20` (a PDA that accepts before its stack is back to the bottom marker, so `aab` is accepted) passed on both Haiku runs. No clean key was rejected anywhere, and every course-convention error was caught on every host and setting.

## Reading the numbers

- **Floor.** Every host's checker catches far more than 50% of the planted errors, so the checker was not strengthened and not rerun for the floor.
- **Cheaper checker on Claude Code.** Today's catch rate is 97.5% (Sonnet, medium, twice). The cheapest setting within 5 points of it is **Haiku at low effort: 95.0%, at about one thirteenth of the cost** ($0.017 for the 60 questions against $0.23). Haiku at medium effort matched Sonnet's 97.5% at the same low cost. Sonnet at low effort cost the same as at medium. Changing the shipped setting is the maintainer's decision.
- **The set is easy.** Three settings and two hosts scored 100%, and one question is worth 2.5 points, so these runs cannot tell 95% from 100% apart with confidence; the 5-point margin is two questions. Every error is a single planted fault in a short key, five of the general errors contradict the answer list in the fixture's notes file, and the convention errors break rules the pack spells out. Real wrong keys are rarer and subtler. A harder set (longer keys, errors in a middle step, real-paper questions with a page to compare) would separate the settings better.

## Rerun

From a clone, with a frozen plugin and homes as in [`tests/acceptance/README.md`](../../tests/acceptance/README.md) (`$A` is `~/.cache/mimir-acceptance`):

```bash
python3 tests/acceptance/checker_benchmark.py run --host claude --plugin "$A/plugin" --out "$A/bench/claude-sonnet-medium"
python3 tests/acceptance/checker_benchmark.py run --host claude --plugin "$A/plugin" --effort low --out "$A/bench/claude-sonnet-low"
python3 tests/acceptance/checker_benchmark.py run --host claude --plugin "$A/plugin" --model haiku --out "$A/bench/claude-haiku-medium"
python3 tests/acceptance/checker_benchmark.py run --host claude --plugin "$A/plugin" --model haiku --effort low --out "$A/bench/claude-haiku-low"
python3 tests/acceptance/checker_benchmark.py run --host codex --codex-home "$A/codex-home" --out "$A/bench/codex"
python3 tests/acceptance/checker_benchmark.py run --host antigravity --out "$A/bench/antigravity"
python3 tests/acceptance/checker_benchmark.py report "$A"/bench/*
```

Each run writes `results.json` (the summary, every question's verdict and reason, every pack's reply, time and usage) into its folder. The raw results of this measurement are kept outside the repo under `~/.cache/mimir-acceptance/bench-79/`.

## Cost

About $0.80 on Claude Code for the five Claude runs (one first attempt crashed on a home-setup race, fixed before these runs). Codex used about 0.93M input tokens (0.74M cached) and 4k output for its 10 packs; Antigravity about 0.12M input, 0.1M cache read and 66k output (63k of it thinking).
