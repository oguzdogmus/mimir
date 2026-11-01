# Mimir: A head start, literally

**Version 0.3.4** · early release, features and file layout may still change ([what's planned](#planned-changes))

Mimir is an exam study plugin for AI coding agents: [Claude Code](https://claude.com/claude-code), [Codex](https://developers.openai.com/codex) and [Antigravity](https://antigravity.google) (Google's free agent that replaced Gemini CLI). It teaches you course material in your professor's style and remembers what you know across sessions.
## What it does

- **Starts from wherever you are.** Type "exam tomorrow, help" and attach a photo of a past paper. Mimir starts drilling right away, with no setup.
- **Sets the pace from the exam date.** Far from the exam, sessions are short teaching episodes (Standard). Close to it, Mimir drills the question types worth the most points per hour (Urgent). It picks the mode and tells you why.
- **Follows your professor.** Mimir reads the outline, slides and past papers, learns how the professor writes questions, and labels every question with where it came from. Answer keys are checked before you see them.
- **Remembers you.** It keeps dated evidence of what you solved alone and with help, and picks up where you left off.
- **Keeps your files local.** Everything lives in one folder (default `~/learning/`). Generated pages work offline. Mimir sends no telemetry; your agent still talks to its model as usual.

## Install

You need Python 3.11 or newer (available as `python3`) and one of the agents below. For Codex and Antigravity, also install `pdftotext` (part of poppler: preinstalled on most Linux, `brew install poppler` on macOS) for the best PDF text; without it Mimir falls back to a simpler built-in reader.

**Claude Code**

```
/plugin marketplace add oguzdogmus/mimir
/plugin install mimir@mimir
```

**Codex**

```sh
codex plugin marketplace add oguzdogmus/mimir
codex plugin add mimir@mimir
```

**Antigravity**

```sh
agy plugin install https://github.com/oguzdogmus/mimir
```

Create the learning folder before launch (`mkdir -p ~/learning`). Start with the real plugin directory added to its workspace:

```sh
mkdir -p ~/learning
cd ~/learning
agy --add-dir "$(realpath ~/.gemini/config/plugins/mimir)"
```

Grant any host permission requests for these directories. A skill symlink alone does not grant access to its target. If you use Antigravity through another app that doesn't load plugins, link the skills in as well:

```sh
ln -s ~/.gemini/config/plugins/mimir/skills/mimir-* ~/.gemini/config/skills/
```

**From a local clone** (any agent): `git clone https://github.com/oguzdogmus/mimir.git ~/mimir`, then use `~/mimir` in place of `oguzdogmus/mimir` or the GitHub URL above. To try it in Claude Code for one session without installing: `claude --plugin-dir ~/mimir`.

## Quick start

1. Run `mimir-setup` once to create your learning folder.
2. Drop course files (outline, slides, past papers) into `~/learning/_inbox/` and run `mimir-ingest`.
3. Run `mimir-study` and tell it when your exam is.

`mimir-setup` and `mimir-ingest` change your files, so they only run when you type the command yourself. Asking in plain words ("set me up") does not start them. Type exactly:

| Agent | Setup | Ingest |
|---|---|---|
| Claude Code | `/mimir:mimir-setup` | `/mimir:mimir-ingest` |
| Codex | `$mimir-setup` | `$mimir-ingest` |
| Antigravity | `/mimir-setup` | `/mimir-ingest` |

If you use Antigravity through another app that doesn't expand these commands, setup and ingest may not be reachable there; run those two steps in the Antigravity CLI.

Not sure which command fits? Run `mimir-help`, or ask "which Mimir command should I use?".

## Commands

Each command is a skill. How you call it depends on the agent: `/mimir:mimir-study` in Claude Code, `$mimir-study` in Codex, `/mimir-study` in Antigravity. For every command except `mimir-setup` and `mimir-ingest`, you can also just say what you want ("quiz me on automata") and the agent picks the skill.

| Skill | What it is for |
|---|---|
| `mimir-setup` | One-time setup: your learning folder, languages and any exam dates you know. |
| `mimir-ingest` | File everything in your `_inbox/` into course folders. |
| `mimir-study` | Study for an exam. Start here: "exam Friday, help" works, even with just a photo of a past paper. |
| `mimir-past-questions` | Drill a course's real past-paper questions, highest points per hour first. |
| `mimir-quiz` | Get quizzed at exam level in your professor's style, with checked answer keys. |
| `mimir-plan` | See how your plan grows with each day you wait to start. |
| `mimir-forecast` | A ranked guess at the topics of your next exam, with the evidence. |
| `mimir-progress` | What Mimir believes you know in a course, with dated evidence. |
| `mimir-debrief` | After an exam: what was on it, and what that changes. |
| `mimir-help` | Tells you which command fits your situation. |

## Works with

| Agent | Status |
|---|---|
| Claude Code | Tested |
| Codex | Tested |
| Antigravity | Tested |
| Cursor, Grok Build, Muse Code | Not tested yet. They read the same skill format, so they may work. |

So far Mimir has only been tested on **CachyOS (Arch Linux)**. It uses only the Python standard library and each system's default file opener, so it should work on other Linux distributions, macOS, Windows and WSL without problems. If something breaks on your system or agent, please open an issue. The manual cross-platform check is described in [`RELEASE.md`](RELEASE.md).

## Planned changes

These come from hands-on testing and are subject to change. Until 1.0, expect changes to how sessions run and to the folder layout.

- **Better-looking visuals.** The HTML pages and SVG diagrams Mimir builds work, but look plain. They need a stronger visual style.
- **Cleaner chat formatting.** Questions, options and answers can run together, especially in the Claude mobile and desktop apps. Planned: shared formatting rules (a heading per question, options one per line, language-tagged code blocks), and possibly a way to view generated pages on a phone.
- **Real textbook support.** Today ingest files a textbook but never reads it, so study sessions don't use it. Planned: a `textbook` folder, chapters linked to outline weeks and slide decks, indexing from the book's table of contents, a check that the edition matches the outline, and a book-only route for courses with no outline or slides.
- **Teaching before drilling.** Urgent sessions show a worked answer first, even on topics you have never seen. Planned: a short "why this exists" and the simplest rule before the first worked example, starting from the easiest form of a question, a short round of questions on the first session to find what you already know, and a clear rule for uncertain exam dates ("in 9 or 16 days").
- **Workspace migrations.** When the folder layout changes (for example the new `textbook` folder), existing workspaces need their files moved and references updated. Planned: a layout version in the workspace and a migration step with a dry run.

## License

Mimir is open source under the [Apache License 2.0](LICENSE). You can use, change and share it, including commercially, as long as you credit the original project: keep the [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) files, and say which files you changed.

## Credits

Math sheets use [KaTeX](https://katex.org/) (MIT license), vendored in `assets/vendor/katex/`. `mimir-help` is modelled on Matt Pocock's [`ask-matt`](https://github.com/mattpocock/skills) router skill.

These skills work well alongside Mimir:

- `watch`: turn lecture videos into notes
- `docx`, `pdf`: read and produce course documents
- `dataviz`: chart your own study data
- `skill-creator`: build your own skills
