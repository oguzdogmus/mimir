# Agent handoff

Copy this into a fresh conversation with an agent that can access the repository. Change the step number when ready.

```text
Implement step 1 of docs/audit-2026-10-31/PLAN.md.

First read docs/audit-2026-10-31/README.md, DECISIONS.md and STATUS.md.
Then read the selected PLAN step and its finding IDs in FINDINGS.md.
Use archive reports only if you need more evidence. Follow repository instructions.

Check the working tree and current code. Preserve unrelated changes.
Confirm prerequisites are complete. If this is a resumption, use STATUS's
branch/commit and remaining work; do not restart completed work.
Use one branch for this step from main with prerequisites merged.
Reproduce the relevant bugs, make the smallest fixes, and run the specified
targeted tests plus the full suite. The approved product decisions are in
DECISIONS.md; do not ask me to decide them again.

Keep scope to this step. Record unrelated discoveries for later.
Do not launch another audit or subagents unless I ask.
Update STATUS.md with the changes, actual commands/results, branch/commit,
remaining checks, blockers, and exact next action. Mark ready for review
only when required checks passed; never claim unrun checks passed.
Stop after this step and give me a concise review handoff.
Do not push, open a PR, or merge unless I request it.
```

For review, use:

```text
Review the current implementation of step N against
docs/audit-2026-10-31/PLAN.md and DECISIONS.md.
Read STATUS.md for the branch and validation evidence.
Inspect the diff and focus on correctness, regressions and missing acceptance
criteria. Report concrete findings with file locations, or say none found.
Do not implement changes during this review.
```

## Required agent completion / interruption note

Add to STATUS.md, then summarize for the user:

- Step and finding IDs addressed.
- Branch and commit, or explicitly “uncommitted”; PR link if one exists.
- Changes and why they satisfy the acceptance criteria.
- Exact test commands and observed results, including failures.
- Unrun manual checks and blockers.
- New discoveries (with IDs) and any implementation decision.
- Remaining work and exact next action.

A documentation update or passing unit tests alone does not mean a step is merged. Keep implementation, review and merge status distinct.
