# Acceptance runs: host parity on Claude Code, Codex and Antigravity (#79)

2026-11-20. Live runs with a scripted student on all three hosts, on Linux (CachyOS), as [`tests/acceptance/README.md`](../tests/acceptance/README.md) says: one study run (support method-first, shortened to reach an independent check and a clean close) and one quiz run of 3 questions per host, each on a fresh fixture folder. The student was played by the implementing agent. J to N are counted from the raw host events by `tests/acceptance/speed_checks.py` on Claude Code and Antigravity; on Codex, whose `--json` stream lacks the subagent calls, G and the settle order were read from the session rollout. Raw runs are kept outside the repo under `~/.cache/mimir-acceptance/results/{claude,codex,agy}-79-r1/{study,quiz}`. These are fixture runs, not real student sessions.

- Plugin: `2d94b42` (this branch, before the merge of #3), frozen as a worktree. **Not from the GitHub install**: the code is not on `main` yet. Codex used a clean `CODEX_HOME` with the login copied and Mimir added from a local marketplace (`codex plugin add mimir@mimir`, 12 skills); Antigravity used a clean HOME with `agy plugin install <local plugin>` (12 skills). See "To repeat after merge".
- Hosts: Claude Code 2.1.327 run lean on Sonnet 5.5; Codex CLI 0.166.0 on gpt-6.2-sol; Antigravity CLI `agy` 1.4.12 on its default model (gemini-4-neon-high), in print mode with `--dangerously-skip-permissions` and the installed plugin folder added with `--add-dir`.

## Results

P pass, F fail, – not applicable. G is the independent check; J to N as in the README.

| Host | Run | C | F | G | I | J | K (script / eye) | L | M | N |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Code | study | P | F | P | P | P | P / F | P | P | P |
| Claude Code | quiz | P | F | P | F | P | F / F | P | P | P |
| Codex | study | P | P | P | F | – | – / P | P | – | P (rollout) |
| Codex | quiz | P | P | P | F | – | – / P | P | – | P (rollout) |
| Antigravity | study | P | P | P | P | P | P / P | P | P | P |
| Antigravity | quiz | P | P | P | P | P | P / P | P | P | P |

**G passes on all six runs.**

- **Claude Code**: `Agent` with `subagent_type` `mimir:verifier` and `run_in_background` false, prompt one line naming the pack (quiz: 1 batch; study: 2 batches). The checker made one tool call per batch, a Read of the pack.
- **Codex**: `spawn_agent` with `fork_turns` none, then `wait_agent`, then `verify.py settle`, in that order in the parent rollout (quiz: task `verifier`; study: task `checker`). The child read the pack and the notes file the pack names, and first also read `skills/mimir-core-rules/SKILL.md` from the installed plugin (finding 2).
- **Antigravity**: `define_subagent` with the whole body of `helpers/verifier.md` as its system prompt and write, MCP and subagent tools off, then `invoke_subagent` with the one pack line, then `verify.py settle` after the reply arrived. The child made one `read_file` of the pack and sent its reply (token line, then one verdict line per question). The quiz used the name `verifier`, the study `mimir-verifier`.

Other checks:

- **Turn shape on Antigravity and Codex** (design §2, §8). Both hosts emit the at-once text before the tool calls that follow it. On Antigravity the quiz's declaration and Item 1 finished as a reply step before `verify.py submit`; in the study the feedback came before the submit of the practice set. On Codex the `agent_message` with the declaration and Item 1 came before the submit command, and every answer turn's feedback came before `session.py record`. That is the event order in the JSON streams; whether each host's window shows it before the turn ends is the by-eye look the maintainer still has to do (`docs/issue-13-host-checks.md`). On Claude Code K failed again by eye in both runs and by script in the quiz: the class line or the feedback came before the checks, the explanation or the set's first question only after them (known since #77; not re-litigated).
- **Claude Code F and I**: both runs answered "thanks" with a "Good luck" sign-off, and the quiz put a progress note before the declaration, all known from `docs/acceptance-77.md` and `docs/acceptance-78.md`. Each close itself was right on every host: one `ended:` line in the new log.
- **Codex I**: the skill announcement comes before the class line or declaration, as in #44.
- Every host repeated the first question at the end of a set-start turn, as the #77 end-of-turn repeat asks; on Antigravity and Codex, where the early text does show in the stream, the student sees it twice.

## Findings

1. **Antigravity's stream leaves out the checker definition.** agy 1.4.12 streams a `define_subagent` call with only its name and description; the system prompt and tool switches are only in the conversation's `brain/<id>/.system_generated/logs/transcript_full.jsonl`. `drive.py` now copies that file next to the run's events, and check G reads it. Two argument shapes exist (one JSON `definition`, or separate `Name`, `SystemPrompt` and `Enable*Tools` fields); both are read.
2. **The Codex checker child loads the core rules.** In both Codex runs and in every Codex benchmark pack, the child's first command printed `skills/mimir-core-rules/SKILL.md`: the skill's description asks to be loaded before reading any Mimir `.state/` file, and the pack lives in `.state/checks/`. It read no course file the pack did not name. On Codex the checker's read-only rule is a prompt rule anyway (README); after #3 the core rules are no longer a skill, so this trigger should disappear. Not changed here.
3. **Antigravity is slow at a set start.** The quiz's first turn took about 185 s to the first question; the tutor also set a `schedule` timer of 120 s while it waited for the checker. Answer turns took 20 to 40 s in step time. agy's usage and seconds in the result event are totals for the conversation, so `transcript.md` shows running totals on Antigravity.
4. **agy print mode needs the prompt last.** `agy -p` takes the next word as its prompt; with flags after it, agy refuses. Fixed in the driver and the benchmark.
5. **No rule or README change was needed** from these runs: every host found its dispatch recipe in the core rules and used it.

## To repeat after merge (from the GitHub install)

The ticket asks for the Codex and Antigravity runs to start from the GitHub install, which closes #4. That can only happen once this branch is on `main`. After the merge, repeat on a clean home, with the README's commands:

```sh
A=~/.cache/mimir-acceptance
mkdir -p "$A/codex-home-gh" && cp ~/.codex/auth.json "$A/codex-home-gh/"
CODEX_HOME="$A/codex-home-gh" codex plugin marketplace add oguzdogmus/mimir
CODEX_HOME="$A/codex-home-gh" codex plugin add mimir@mimir
mkdir -p "$A/agy-home-gh" && HOME="$A/agy-home-gh" agy plugin install https://github.com/oguzdogmus/mimir
```

Then the Codex study and quiz runs and the Antigravity study and quiz runs above (four runs), and confirm the skill count (10 once #3 is merged). The Claude Code runs need no repeat for #4; repeating them from `/plugin install` is optional.

## Cost

- Claude Code: quiz $0.32 (6 turns), study $0.48 (7 turns), as the host reports it.
- Codex (subscription): quiz about 814k input tokens (755k cached) and 4.1k output over 6 turns; study about 903k input (803k cached) and 3.4k output over 7 turns.
- Antigravity (subscription): quiz about 394k input, 3.4M cache read, 104k output (76k thinking) over 6 turns; study about 602k input, 4.5M cache read, 145k output (115k thinking) over 9 turns.
- The checker benchmark is in [`docs/measurements/checker-benchmark.md`](measurements/checker-benchmark.md).
