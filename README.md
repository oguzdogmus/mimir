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

Under construction. The plugin skeleton, the shared `core-rules` skill and the memory templates exist. `scripts/plan.py` is built: a deterministic planning engine (Python 3.11+, standard library only) with four subcommands, `class` (Standard or Urgent delivery with its reason), `delay` (cost of delay for each start day), `debrief` (cram bill against the counterfactual) and `summary` (one shareable first-contact line). `scripts/workspace.py` builds the learning folder (standard library only) with five subcommands, `root` (where the learning folder is and whether setup finished), `init` (root, `_inbox/` and profile), `course` (one course tree from the templates), `file` (move one file into a course role folder) and `relocate` (move the whole tree). `/mimir:setup` runs the one-time full setup through it. The default learning folder is `~/learning/`; if you move it, Mimir remembers the new location in `~/.config/mimir/root`. Other skills are not built yet.

## Credits and companions

Mimir is built for [Claude Code](https://claude.com/claude-code). These skills work well alongside it:

- `watch`: turn lecture videos into notes
- `docx`, `pdf`: read and produce course documents
- `dataviz`: chart your own study data
- `skill-creator`: build your own skills
