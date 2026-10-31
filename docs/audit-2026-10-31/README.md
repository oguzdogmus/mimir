# Mimir audit: start here

This folder carries the 2026-10-31 audit into implementation without requiring the chat history. All 26 findings and all five original agent reports are saved. No fixes have been implemented by this documentation task.

## The simple workflow

1. Save this folder in Git along with the project. A commit is a recoverable snapshot; a branch keeps one change separate; a pull request (PR) is the reviewable change before it joins `main`.
2. Start a fresh agent conversation in this repository. Paste the prompt in [HANDOFF.md](HANDOFF.md), choosing one step.
3. The agent reads this page, [DECISIONS.md](DECISIONS.md), [STATUS.md](STATUS.md), the selected step in [PLAN.md](PLAN.md), and only its relevant rows in [FINDINGS.md](FINDINGS.md).
4. Let the agent implement and test that step. Review the diff and its test evidence. Merge the completed step before starting the next branch from updated `main`.
5. Have the agent update STATUS with changes, commands/results, remaining work and the exact next step before ending—even if interrupted. A new agent can resume from those files.

Run one implementation step at a time initially. The historical parallel audit is complete; it is not a request to launch five agents for every implementation task. A fresh conversation per step reduces irrelevant context. Send file paths and a precise step number; there is no need to paste every report.

## Where each kind of information lives

| File | Purpose | Read when |
|---|---|---|
| [STATUS.md](STATUS.md) | Current step, owner, validation, next action | Every handoff |
| [DECISIONS.md](DECISIONS.md) | Accepted behavior and constraints | Every implementation |
| [PLAN.md](PLAN.md) | Scope and acceptance checklist per step | Selected step |
| [FINDINGS.md](FINDINGS.md) | All 26 original consolidated findings and top 5 quick wins | Relevant finding IDs |
| [HANDOFF.md](HANDOFF.md) | Copyable agent prompt and completion format | Starting/resuming work |
| [archive/provenance.md](archive/provenance.md) | Source links, roster, acceptance and archive coverage | Resolving evidence questions |
| `archive/*` | Original reports and proposal | Only if evidence is unclear |

## Capture new discoveries without losing scope

Append a short entry to STATUS's new-findings section: stable ID (`N01`, etc.), symptom, file/function, reproduction or evidence, impact, suggested fix and destination step. Keep the original 1–26 IDs unchanged. Do not silently expand the active step. If a discovery blocks it, record why and fix the necessary dependency; otherwise queue it.

Change accepted decisions only when the user changes them or code evidence reveals a conflict requiring a decision. Record the date and reason. Keep historical reports unchanged.

The historical audit reported 970 passing tests through `uvx pytest`. That is a past result, not current validation. Line numbers in the report are navigation hints; functions and current behavior are authoritative.
