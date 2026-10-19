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

Skills are invoked as `/mimir:<name>`. Not sure which one? Run `/mimir:help`.

## Commands

| Command | What it is for |
|---|---|
| `/mimir:setup` | One-time setup: your learning folder, languages and any exam dates you know. |
| `/mimir:ingest` | File everything in your `_inbox/` into course folders. |
| `/mimir:study` | Study for an exam. The front door: "exam Friday, help" works, even with just a photo of a past paper. |
| `/mimir:past-questions` | Drill a course's real past-paper questions, highest points per hour first. |
| `/mimir:quiz` | Get quizzed at exam level in your professor's style, with checked answer keys. |
| `/mimir:plan` | See how your plan grows with each day you wait to start. |
| `/mimir:forecast` | A ranked guess at the topics of your next exam, with the evidence. |
| `/mimir:progress` | What Mimir believes you know in a course, with dated evidence. |
| `/mimir:debrief` | After an exam: what was on it, and what that changes. |
| `/mimir:help` | Tells you which command fits your situation, then stops. |

## Status

All 15 stories are built. The release waits on the live browser-open check in [`RELEASE.md`](RELEASE.md), run by hand on Linux, macOS, Windows and WSL; see its results table for which have passed.

The plugin has its skeleton, the shared `core-rules` skill and the memory templates. `scripts/plan.py` is built: a deterministic planning engine (Python 3.11+, standard library only) with five subcommands, `class` (Standard or Urgent delivery with its reason), `delay` (cost of delay for each start day), `debrief` (cram bill against the counterfactual), `summary` (one shareable first-contact line) and `triage` (rank an exam's question types by points per hour and split them into drilled and consciously skipped within a third of the hours left). `scripts/workspace.py` builds the learning folder (standard library only) with five subcommands, `root` (where the learning folder is and whether setup finished), `init` (root, `_inbox/` and profile), `course` (one course tree from the templates), `file` (move one file into a course role folder) and `relocate` (move the whole tree). `/mimir:setup` runs the one-time full setup through it. `scripts/ingest.py` (standard library only) has two subcommands, `scan` (safely unpack archives in `_inbox/` and list each item with its kind, fidelity and page count) and `index` (add a course's files and topics to its `INDEX.md`). `scripts/fingerprint.py` (standard library only) has two subcommands, `write` (render a course's professor fingerprint, computing the tentative and prior-term labels, question-type frequencies and the 60-line cap) and `retake` (link a retaken course read-only to its prior term and decide whether it is the same professor). `/mimir:ingest` reads the inbox, asks one confirmation table, then files and indexes everything, links retaken courses to their prior term and updates each course's fingerprint. `scripts/verify.py` (standard library only) has one subcommand, `gate`, which labels each quiz or drill item with its provenance from the course registry and decides whether it is shown, sent to the checker, retried, flagged with a comparison source or dropped. `/mimir:quiz` writes an exam-level quiz in the professor's style, has the `verifier` agent (Sonnet, read-only) check every answer key in one batch before you see it, and records your results in the mastery map and the session log. `scripts/visual.py` (standard library only) has six subcommands, `sheet` (an offline HTML math sheet with vendored KaTeX 0.19.0, escaped content and a hash-pinned Content-Security-Policy, with photo or scan originals beside their transcription), `svg` (check an SVG diagram against a safe element list and write it unchanged), `steps` (a worked answer revealed one step per click), `trace` (feed an input into a DFA, NFA, PDA or labelled tree and watch it move state by state, with the current states outlined and every step said in words), `delay` (the cost-of-delay start-day slider page and a bar chart, from the same numbers as the session's cost-of-delay line) and `open` (open a built file in your browser, or print its path). Every page works offline in plain JavaScript and from the keyboard. The model-only `notation` skill picks terminal Unicode, a math sheet or an SVG, and the `visual-builder` agent (Sonnet) builds the file into the course's `.state/out/` and opens it. The default learning folder is `~/learning/`; if you move it, Mimir remembers the new location in `~/.config/mimir/root`. `scripts/session.py` (standard library only, read-only) owns every date and clock decision of a study session, with five subcommands, `start` (pick the course, the next exam, the delivery class from `plan.py`, the cost-of-delay line and the next route topic, say whether the exam date is still unknown, and whether a post-exam debrief is due, still waiting for the exam day to pass, or deferred because the next exam is close), `check` (status, counts and staleness of named topics, stale after 14 days, and whether a topic needs an attempt before any hint: 3 or more solves with help and none without), `clock` (episode minutes and phase: teach under 20, wrap up to 25, then over), `debrief` (what a due debrief needs: the cram bill, the logged answer-checker disagreements and whether to offer the next course) and `progress` (every mastery row with its dated evidence, solves alone and with help, and staleness, as a table and a one-line summary). `/mimir:study` is the front door: type "exam Friday, help" and it reads the date from your message (or asks "When's the exam?" once), announces the delivery class, recaps "previously on", resolves last time's cliffhanger, rechecks stale topics with one question, tests "I know this" with two quick questions, teaches the next topic, and ends on a cliffhanger for next time. Teaching starts in the professor's notation and steps down one rung at a time when it doesn't land (analogy, worked example, visual, your own language when it differs from the course's), then climbs back to the professor's notation and remembers which rung worked. By default each step opens with one guiding question; if you get frustrated ("just tell me"), you get one smaller step, then the answer, the topic stays shaky until you solve one on your own, and later sessions ask fewer questions. After 3 solves with help and none alone, you try the problem before any hint. Each topic ends with a disguise drill: one verified problem in two surface forms, where you name the shared structure, then solve both. Close to the exam, an Urgent session triages the question types by points per hour, says which it drills and which it skips, and drills answer-first: a worked answer to a real past-paper question of each type (quoted with its file and page, or beside the original photo), then one check question. Urgent checks can raise a topic to shaky, never to mastered. The night before, with no workspace at all, "exam tomorrow, help" plus one phone photo of a past paper is enough: Mimir files the photo under `~/learning/` without asking, starts drilling, and reminds you of `/mimir:setup` in a later calm session. `/mimir:past-questions` drills one real past-paper question per high-yield question type, answer-first when Urgent, attempt-first otherwise. In an Urgent drill, say "steps" after a worked answer to open it one step at a time in your browser. `/mimir:plan` shows how the remaining plan grows with each day you wait: the cost-of-delay line, a start-day slider and a chart, with ranges and how confident they are. `scripts/forecast.py` (standard library only) has two subcommands, `write` (store one forecast for an exam, checking every topic's sources against the course registry and computing the confidence line from how many past papers and debriefs back it) and `score` (store how many of the top 5 forecast topics appeared, out of the topic count when the forecast has fewer than 5, and recompute your forecast record across all courses in the profile). `/mimir:forecast` reads the outline, past papers and debrief notes and gives a ranked list of likely topics for the next exam, one evidence line each, labelled `[forecast, not a guarantee]`, with the confidence line and how past forecasts did. `/mimir:debrief` (also run at the start of a calm `/mimir:study` session once the exam has passed) asks at most 3 questions, and one word like "skip" ends it: what was on the exam (recorded in the professor fingerprint, and the forecast for it scored), which version was right where the answer checker disagreed, and, once a term, whether to set up the next course. It also gives the forecast for the next exam and the cram bill: hours studied against the counterfactual, with the days before the exam at first contact as a plain number. A later exam that has also passed replaces an older pending one, so debriefs never stack. `/mimir:progress` shows what Mimir believes you know in a course: each topic's status, its dated evidence, how many problems you solved alone and with help, and which topics are due a recheck (each gets one recheck question the next time it comes up in `/mimir:study`). It asks nothing and changes nothing. Quiz, study and past questions share one answer-key check flow.

## Roadmap

The plugin was built in 15 stories, all done.

| # | Story | Status |
|---|---|---|
| 1 | Plugin skeleton, core rules and memory templates | Done |
| 2 | `plan.py` delivery class and cost-of-delay engine | Done |
| 3 | Setup skill and shared workspace builder | Done |
| 4 | Ingest core with confirmation table, INDEX and fidelity | Done |
| 5 | Professor fingerprint extraction and retake linking | Done |
| 6 | Verifier agent and quiz skill | Done |
| 7 | Notation skill, visual builder, math sheet and SVG | Done |
| 8 | Study core session runner | Done |
| 9 | Teaching engine | Done |
| 10 | Urgent cargo and past-questions skill | Done |
| 11 | Interactive pages and plan skill | Done |
| 12 | Forecast skill and hit-rate record | Done |
| 13 | Debrief skill | Done |
| 14 | Progress skill | Done |
| 15 | Help skill, README credits and cross-OS release test | Done (release check: see `RELEASE.md`) |

## Credits and companions

Mimir is built for [Claude Code](https://claude.com/claude-code). Math sheets use [KaTeX](https://katex.org/) (MIT license), vendored in `assets/vendor/katex/`. `/mimir:help` is modelled on Matt Pocock's [`ask-matt`](https://github.com/mattpocock/skills) router skill. These skills work well alongside it:

- `watch`: turn lecture videos into notes
- `docx`, `pdf`: read and produce course documents
- `dataviz`: chart your own study data
- `skill-creator`: build your own skills
