## Agent skills

### Issue tracker

Issues live in GitHub Issues on oguzdogmus/mimir, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Coding standards

Judgement rules for scripts and tests: `CODING_STANDARDS.md`. Lint (`uvx ruff@0.17.6 check`), tests and the commit hook: README "Development".

### Running the plugin from a worktree

The installed plugin is a released snapshot; test a branch with `claude --plugin-dir <worktree>`. See `docs/agents/plugin-from-worktree.md`.
