# Acceptance runs: teaching levels on Claude Code and Codex (#44)

2026-11-09 to 2026-11-10. Live runs with a scripted student, as the design's "Acceptance test" asks: each of the nine teaching levels (one per run, the other axes at their defaults) on Claude Code and on Codex. Protocol, harness and checks A to I: [`tests/acceptance/README.md`](../tests/acceptance/README.md). These are fixture runs, not real student sessions, and they show behavior on these models, not a guarantee for every run.

- Fixture: `tests/acceptance/make_fixture.py`, course CS301 Automata, the shared task "Describe in set notation the language of S → aSc | b" plus four more questions, a midterm 21 days ahead (Standard), all three settings saved as explicit so no probe trial moves a level mid-run.
- Hosts: Claude Code 2.1.316 on Sonnet 5.5, run lean (only Mimir loaded); Codex CLI 0.166.0 on gpt-6.1-sol. The student was played by a Codex agent (gpt-6.1-sol); Claude Code round 1 used a Claude Sonnet tester.
- Raw transcripts of rounds 1 and 2 were lost when `/tmp` was cleared on a reboot; their findings below come from the testers' reports. Rounds 3 and 4 are kept outside the repo under `~/.cache/mimir-acceptance/results/`.

## Final results (plugin `6d8e74a`)

Checks: A the level's "does" line; B no "must not" line broken; C answers only on request; D guidance after a wrong answer or "idk"; E no stall at the end of a set; F clean end on "end session"; G independent answer check; H no settings drift; I the class line first. P pass, F fail, – not reached within the 12-turn cap.

| Level | Claude Code | Codex |
|---|---|---|
| support example-first | PASS | A–H pass; I fail |
| support method-first | PASS | A–H pass; I fail |
| support try-first | PASS (round 3, `1392e76`) | A–H pass; I fail |
| frequency checks only | PASS | A–H pass; I fail |
| frequency key decisions | PASS | C fail; I fail |
| frequency every step | B fail (E –) | A–H pass (E –); I fail |
| depth next step | C, D fail | C fail (E –); I fail |
| depth why | PASS | A–H pass; I fail |
| depth what-if | PASS | A–H pass; I fail |

Both hosts, every run: the session closed only on "end session" and exactly once, "thanks" afterwards neither reopened nor closed it again, the teaching settings never drifted, and the answer check ran in a separate agent (Claude Code `mimir:verifier`; Codex `spawn_agent` with `fork_turns` none).

## Known host gaps

- **Codex announces the skill before the class line.** Every Codex run opened with "I'll use Mimir's study skill…" despite `session.md` saying nothing comes before the class line. The announcement comes from Codex's own skill handling; four rounds of rewording did not remove it. The class line is still the first line of Mimir's own output.
- **Answer given at the next-step level (both hosts).** After "idk" on a next-step guiding question, the tutor sometimes supplies the next form ("xxAyyyy") or the language instead of a smaller question. `teaching.md` §3 forbids it; it persisted on both models.
- **Claude Code on Sonnet, every step:** once stated a step's result ("zero or more times") before asking it.
- **Codex, key decisions:** once wrote the full language after the student asked for the answer to a narrower guiding question.
- **Answer check after showing (Claude Code, once).** In the every-step run the tutor showed a drill question before its independent check returned, and said so. The check itself was independent. Related to #23.

## How the rules changed

| Round | Commit | Finding | Change |
|---|---|---|---|
| 1 | `6b0bbd5` | Why-questions put the answer inside the question; a wrong what-if got its answer; sets ended without saying so; Codex announced the skill first | `b2d5402`: why only after the result is found; no guiding question carries its answer; the drill and each topic say when they are done; nothing before the class line |
| 1 (Claude Code) | `6b0bbd5` | Confirming the drill's shared structure gave a formula that answered both variants | `9438364`: the shared structure names what to look at, never a formula, exponents or a set |
| 2 | `b2d5402` | The language of the question being worked on stated unasked; messages ending without a question; Sonnet never said the class line | `1392e76`: that answer is never stated before a right answer or request; every message ends with a question or a choice; nothing is written before the class line; a wrong guiding answer is called not right yet |
| 3 | `1392e76` | The "I know this" check ran unasked; questions checked before the class line; frequency and depth followed loosely | `6d8e74a`: "I know this" only when the student says so; no question prepared or checked before the class line; frequency and depth spelled out while teaching |

The check D wording was also corrected after round 1: "not right yet" is said after a wrong answer, not after "idk", which gets guidance straight away (`session.md` Retries).

## Cost

The first Claude Code runs loaded the user's whole setup (connectors, plugins, hooks; about 133k tokens before the first message) on Opus, and the prompt cache was rebuilt whenever a connector reconnected; round 1 alone used most of a 5-hour usage window. `drive.py` now starts Claude Code with only Mimir (about 36k tokens) on Sonnet: round 4's eight Claude Code runs cost about $27 at API prices.
