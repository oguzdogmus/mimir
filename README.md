# Mimir: Wisdom from the well, brought to your terminal

A head start, literally.

In Norse myth, Mimir is the severed head Odin consults for wisdom. This Mimir is a Claude Code plugin that teaches you and learns about you across sessions.

## What Mimir does

Mimir aims for **understanding that survives the professor's disguises, on a route that starts early.**

- **The front door is urgent.** Most students first show up the night before an exam. Type "exam tomorrow, help" and attach a past paper. Mimir starts drilling right away, with no setup interview.
- **The destination is Standard.** Short episodes start early. Each one opens with a "previously on" recap and ends on a question for next time. Mimir keeps dated evidence of what you can solve without help.
- **The exam date sets the pace.** You never pick a mode. Mimir works out Standard or Urgent from the exam date and tells you which one it chose, and why.
- **The professor's material comes first.** Mimir learns how your professor writes and disguises questions. It drills you on variants in that style and labels every question with where it came from.
- **Your files stay local.** Everything lives in one folder (default `~/learning/`). Generated pages work offline, and Mimir sends no telemetry and uses no cloud storage. Claude Code itself still talks to the model as usual.

## Install (local development)

```sh
git clone https://github.com/oguzdogmus/mimir.git ~/mimir
claude --plugin-dir ~/mimir
```

Once built, skills are invoked as `/mimir:<name>`.

## Status

Under construction. The plugin skeleton, the shared `core-rules` skill and the memory templates exist. `scripts/plan.py` is built: a deterministic planning engine (Python 3.11+, standard library only) with four subcommands, `class` (Standard or Urgent delivery with its reason), `delay` (cost of delay for each start day), `debrief` (cram bill against the counterfactual) and `summary` (one shareable first-contact line). `scripts/workspace.py` builds the learning folder (standard library only) with five subcommands, `root` (where the learning folder is and whether setup finished), `init` (root, `_inbox/` and profile), `course` (one course tree from the templates), `file` (move one file into a course role folder) and `relocate` (move the whole tree). `/mimir:setup` runs the one-time full setup through it. `scripts/ingest.py` (standard library only) has two subcommands, `scan` (safely unpack archives in `_inbox/` and list each item with its kind, fidelity and page count) and `index` (add a course's files and topics to its `INDEX.md`). `scripts/fingerprint.py` (standard library only) has two subcommands, `write` (render a course's professor fingerprint, computing the tentative and prior-term labels, question-type frequencies and the 60-line cap) and `retake` (link a retaken course read-only to its prior term and decide whether it is the same professor). `/mimir:ingest` reads the inbox, asks one confirmation table, then files and indexes everything, links retaken courses to their prior term and updates each course's fingerprint. `scripts/verify.py` (standard library only) has one subcommand, `gate`, which labels each quiz or drill item with its provenance from the course registry and decides whether it is shown, sent to the checker, retried, flagged with a comparison source or dropped. `/mimir:quiz` writes an exam-level quiz in the professor's style, has the `verifier` agent (Sonnet, read-only) check every answer key in one batch before you see it, and records your results in the mastery map and the session log. `scripts/visual.py` (standard library only) has three subcommands, `sheet` (an offline HTML math sheet with vendored KaTeX 0.19.0, escaped content and a hash-pinned Content-Security-Policy, with photo or scan originals beside their transcription), `svg` (check an SVG diagram against a safe element list and write it unchanged) and `open` (open a built file in your browser, or print its path). The model-only `notation` skill picks terminal Unicode, a math sheet or an SVG, and the `visual-builder` agent (Sonnet) builds the file into the course's `.state/out/` and opens it. The default learning folder is `~/learning/`; if you move it, Mimir remembers the new location in `~/.config/mimir/root`. `scripts/session.py` (standard library only, read-only) owns every date and clock decision of a study session, with three subcommands, `start` (pick the course, the next exam, the delivery class from `plan.py`, the cost-of-delay line and the next route topic, and say whether the exam date is still unknown), `check` (status, counts and staleness of named topics, stale after 14 days, and whether a topic needs an attempt before any hint: 3 or more solves with help and none without) and `clock` (episode minutes and phase: teach under 20, wrap up to 25, then over). `/mimir:study` is the front door: type "exam Friday, help" and it reads the date from your message (or asks "When's the exam?" once), announces the delivery class, recaps "previously on", resolves last time's cliffhanger, rechecks stale topics with one question, tests "I know this" with two quick questions, teaches the next topic, and ends on a cliffhanger for next time. Teaching starts in the professor's notation and steps down one rung at a time when it doesn't land (analogy, worked example, visual, your own language when it differs from the course's), then climbs back to the professor's notation and remembers which rung worked. By default each step opens with one guiding question; if you get frustrated ("just tell me"), you get one smaller step, then the answer, the topic stays shaky until you solve one on your own, and later sessions ask fewer questions. After 3 solves with help and none alone, you try the problem before any hint. Each topic ends with a disguise drill: one verified problem in two surface forms, where you name the shared structure, then solve both. Urgent drilling is not built yet, so an Urgent session offers `/mimir:quiz` instead. Quiz and study share one answer-key check flow. Other skills are not built yet; see the roadmap below.

## Roadmap

The plugin is built in 15 stories. Stories 1 to 9 are done. The token estimates for the remaining stories cover one full build run, with all subagents and headless test runs combined. They are scaled from what stories 1 to 7 used (12M to 39M each, median about 20M). Most of each total is cache reads.

| # | Story | Status | Estimated tokens |
|---|---|---|---|
| 1 | Plugin skeleton, core rules and memory templates | Done | |
| 2 | `plan.py` delivery class and cost-of-delay engine | Done | |
| 3 | Setup skill and shared workspace builder | Done | |
| 4 | Ingest core with confirmation table, INDEX and fidelity | Done | |
| 5 | Professor fingerprint extraction and retake linking | Done | |
| 6 | Verifier agent and quiz skill | Done | |
| 7 | Notation skill, visual builder, math sheet and SVG | Done | |
| 8 | Study core session runner | Done | |
| 9 | Teaching engine | Done | |
| 10 | Urgent cargo and past-questions skill | Next | ~35M (30M to 45M) |
| 11 | Interactive pages and plan skill | Planned | ~20M (18M to 25M) |
| 12 | Forecast skill and hit-rate record | Planned | ~16M (13M to 20M) |
| 13 | Debrief skill | Planned | ~15M (13M to 20M) |
| 14 | Progress skill | Planned | ~12M (10M to 14M) |
| 15 | Help skill, README credits and cross-OS release test | Planned | ~14M (12M to 18M) |

Remaining total: about 112M tokens (96M to 142M), of which about 6M is uncached input and output.

## Credits and companions

Mimir is built for [Claude Code](https://claude.com/claude-code). Math sheets use [KaTeX](https://katex.org/) (MIT license), vendored in `assets/vendor/katex/`. These skills work well alongside it:

- `watch`: turn lecture videos into notes
- `docx`, `pdf`: read and produce course documents
- `dataviz`: chart your own study data
- `skill-creator`: build your own skills
