# Acceptance runs: teaching levels on Claude Code and Codex (#44)

Live runs, not part of CI. A tester agent plays a scripted student against a real host and judges each transcript. Rules: `docs/teaching-preferences-design.md` ("Axis levels", "Level examples", "Acceptance test"), `skills/mimir-study/references/session.md` and `teaching.md`.

## Setup (once per plugin version)

Keep everything under `~/.cache/mimir-acceptance` (`$A`): `/tmp` is wiped on reboot.

```bash
A=~/.cache/mimir-acceptance
git worktree add --detach "$A/plugin" <commit>          # the frozen plugin under test
# Codex: a separate CODEX_HOME with Mimir installed from that plugin
mkdir -p "$A/codex-home" && cp ~/.codex/auth.json "$A/codex-home/"
printf '[marketplaces.mimir]\nsource_type = "local"\nsource = "%s"\n' "$A/plugin" > "$A/codex-home/config.toml"
CODEX_HOME="$A/codex-home" codex plugin add mimir@mimir
```

Never touch the real learning folder or `~/.config/mimir`: each run has its own HOME.

## One run

```bash
python3 tests/acceptance/make_fixture.py --out "$A/results/<host>-rN/<axis>-<level>" --axis <axis> --level "<level>"
python3 tests/acceptance/drive.py --run <that dir> --host claude --plugin "$A/plugin" "<student message>"
python3 tests/acceptance/drive.py --run <that dir> --host codex --plugin "$A/plugin" --codex-home "$A/codex-home" "<student message>"
```

Claude Code runs lean (only Mimir, no connectors, no user plugins, Sonnet by default; `--model opus` costs several times more). Each turn's token use is in `transcript.md`. Run at most 3 runs in parallel; keep a run's turns sequential.

Levels, one per run, the other two axes at their defaults: support example-first, method-first, try-first; frequency checks only, key decisions, every step; depth next step, why, what-if.

## Student script (same every run)

1. "Let's study CS301."
2. First question to solve (or first guiding question): a right answer.
3. Next: a plausible wrong answer.
4. Next: "idk".
5. Keep answering correctly and briefly; once, say "show me the answer" on a question not yet solved; go on until a set, drill or topic runs out and the hand-off is seen. Cap: 12 student turns.
6. "end session", then "thanks".

Answer like a student. Never say it is a test.

## Checks per run (PASS, FAIL or N/A, each with a short quote)

- **A** The level's "does" line happened.
- **B** No "must not" line of that level was broken.
- **C** Answers only on request: the answer of a question the student is working on never appeared before a right answer or "show me the answer"; on that request it came at once.
- **D** Retries: after a wrong answer, "not right yet" and guidance; after "idk", guidance. Never the key or the guiding question's answer (what-if included).
- **E** No stall: when a set, drill or topic ran out, the same message said it was done and led on. Every message that does not close ends with a question or a choice. N/A only when nothing ran out within the cap.
- **F** Clean end: closed only on "end session", exactly once (one `ended:` line in the new log, `save.md` rewritten), no unasked sign-off, "thanks" afterwards neither reopened nor closed again.
- **G** Independent answer check: Claude Code, an Agent call with `subagent_type` `mimir:verifier`; Codex, a `spawn_agent` call with `fork_turns` none (a child given the whole conversation, `fork_turns` all, is a FAIL). Verdicts with no subagent call are a FAIL (#23). Since 0.5.0 (#78): the dispatch is one line naming the evidence pack, the checker opens only the pack and files it names (no shell on Claude Code), and its reply, starting with the pack token, is pasted into `verify.py settle` unchanged.
- **H** No teaching-settings drift during the run.
- **I** The first thing the student read was the class line, "Standard delivery: exam in 21 days", with nothing before it.

Write `verdict.md` per run and `SUMMARY.md` per host round (rows: the nine runs; columns A to I and overall; then the failures with quotes and the likely skill line).

## Speed checks (#77, Claude Code)

Counted from each run's raw events by `python3 tests/acceptance/speed_checks.py <run dir>`, which prints one line per finding and a `J K L M N` summary (rules: `docs/trust-every-session-design.md` §9, `reference/verified-items.md`). Copy its summary into `verdict.md`.

- **J** No tool call before the feedback text in an answer turn (a turn that calls `session.py record`).
- **K** No `verify.py submit` call or checker dispatch before the text of a practice question that starts a set. The script fails a turn with no text before its first submit call or dispatch and quotes the last text before it; confirm by eye that this text is the set's first practice question (quiz, gauge, a recheck or try-first question), or the explanation (Standard), the recipe (Urgent) or the first real question after its submit (past questions).
- **L** One checker batch per question set, plus at most one recheck batch: at most 2 dispatches in a turn and at most 6 questions in a submit call. A turn that also replaces a withdrawn question may hold a third; name it in `verdict.md`.
- **M** No checker dispatch in the background (`run_in_background` true, or a task started in the background).
- **N** (#78) No batch settled without a checker call: every `verify.py settle` follows a checker dispatch made in the same turn after the previous settle. A FAIL here is the #23 failure: the tutor settled a batch it never sent to the checker.

The speed round adds a quiz run to one study run (support method-first). Quiz script, on a fresh fixture folder:

1. "Quiz me on CS301, 3 questions."
2. A right answer.
3. A plausible wrong answer.
4. A right answer, then "end session", then "thanks".

Checks C, F, G and I apply to the quiz run where they fit (I: the first line is the quiz declaration, since a quiz has no class line), plus J to N.

## Results

See `docs/acceptance-44.md` (teaching levels), `docs/acceptance-77.md` (speed checks) and `docs/acceptance-78.md` (check ledger).
