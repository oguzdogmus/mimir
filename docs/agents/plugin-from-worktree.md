# Running the plugin from a worktree

An installed Mimir (`/plugin install mimir@mimir`, from GitHub or from a local clone) is a snapshot copied into Claude Code's plugin cache under `~/.claude/plugins/cache/mimir/`. It does not follow any branch: its skills, its helpers (`mimir:verifier`, `mimir:visual-builder`) and the scripts they run stay at the installed version until you update or reinstall.

To test a branch as it would ship, start Claude Code from the worktree with the worktree loaded as a session-only plugin:

```sh
claude --plugin-dir "$PWD"
```

`--plugin-dir` loads the folder for that session only and takes the place of the installed `mimir@mimir`, so the skills, the helper agents and `scripts/` all come from the worktree. Nothing is installed or changed. Only the session started this way sees it; every other session keeps the installed copy.

Check before a live test:

- `claude plugin validate .` checks the manifests in `.claude-plugin/` (two known warnings: the root `CLAUDE.md` is not shipped as context, and there is no icon).
- In the session, the `mimir:visual-builder` description in the agent list matches `helpers/visual-builder.md` of the worktree. Checked on 2026-11-25 with Claude Code 2.1.331 and Mimir 0.5.0 installed: `claude --plugin-dir <worktree> -p "..."` listed the worktree's description, not the installed one.

`scripts/release_check.py` imports `scripts/` straight from the clone, so it needs no plugin loading. Codex and Antigravity: install from the worktree path as README "From a local clone" says, and reinstall after every change (installed copies are snapshots there too).
