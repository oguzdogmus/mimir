## Agent skills

### Issue tracker

Issues live in GitHub Issues on oguzdogmus/mimir, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Coding standards

Judgement rules for scripts and tests: `CODING_STANDARDS.md`. Every check (lint, tests, release build): `python3 tests/check.py`. The commit hook: README "Development".

### Running the plugin from a worktree

The installed plugin is a released snapshot; test a branch with `claude --plugin-dir <worktree>`. See `docs/agents/plugin-from-worktree.md`.
