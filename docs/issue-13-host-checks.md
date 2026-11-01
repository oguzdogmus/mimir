# Issue 13 host checks

## Capability inspection — 2026-11-01

Codex CLI 0.166.0, running through T3 Code: native independent agent tools are
available. T3 also advertises GPT-6.1 Terra for the requested review agents.
Antigravity CLI 1.4.12 is installed; its actual help output advertises
`--add-dir` (repeatable). The install instructions use this to expose the
resolved plugin directory alongside the learning folder.

Chosen approach: capability-based helper dispatch in the shared core rules,
the existing PDF page reader with exact-path attachment scope, and separate
copy/delete stages in workspace filing. No new agent framework is needed.

## Live scenarios still required

These are pending, not passes. Unit tests do not substitute for these checks.

- Codex: independent verifier reads an actual cited PDF and returns its verdict;
  record tool used, evidence path/page and observed result.
- Codex: Urgent first contact reads an explicitly supplied outside-root PDF
  before course classification, files it and indexes the returned destination.
- Antigravity: repeat both scenarios with the plugin directory added to the
  workspace; record actual agent availability and fallback provenance.
- Permission boundary: a denied attachment read remains denied; a completed
  copy survives denied deletion and is reported as copied.

The current process has unrestricted filesystem access. It cannot establish
host-denial behavior merely by reading an outside-root path successfully.

## Observed results

- Codex 0.166.0 / T3, native independent GPT-6.1 Terra agent:
  read /tmp/mimir-issue13-live/attachment.pdf page 1 using pdftext.py
  with explicit attachment scope. Actual pdftotext output: "Pumping lemma".
  Given a deliberately incorrect "hello" key, returned
  "1 | wrong | fake-real no | page 1 says Pumping lemma, not hello".
  This is a live independent PDF verification pass.
- Antigravity 1.4.12, launched with --add-dir for the repository and fixture
  directory: the headless run reported that command permission was auto-denied
  because it cannot prompt. No evidence was read; this scenario is blocked,
  not passed. Permissions were not bypassed. An interactive permission grant
  is needed to finish its PDF and attachment quick-start checks.
- Targeted boundary suite: 263 tests passed. Copy-deletion denial is injected
  at the filesystem boundary; this is unit coverage, not a live host pass.
- Codex host, live script workflow in isolated temporary HOME:
  read outside-root PDF first ("Pumping lemma"), applied the missing-course
  fallback "Exam 2026-11-02", filed as past-papers, and indexed the returned
  destination with page=1. Observed: action moved; Indexed 1 file (1 new,
  1 topic added). Workspace: /tmp/mimir-13-codex-1r_e9r59.
  This checks real read/file/index integration, not a full conversational
  Urgent session or its date/class routing.

## Final automated validation and review

- Targeted suites: 263 passed.
- Full suite: 1080 passed in 89.61 seconds.
- Python compileall and git diff --check passed.
- GPT-6.1 Terra Standards review: no documented violations or actionable smells.
- GPT-6.1 Terra Spec review: live acceptance incomplete; instruction-string
  provenance assertions do not establish runtime log/once-only behavior.
  Full-suite evidence missing from the original reviewed commit is recorded
  above. No scope creep found.
- Retrying Antigravity with a session-only command(python3) allow rule still
  returned the same headless command-permission denial. No successful
  Antigravity verification or quick-start run is claimed.

## Remaining acceptance work

Run the complete conversational Urgent attachment flow on both hosts, and
exercise the same-context fallback through two verification batches in one
session: inspect the actual session log for checker: self and the transcript
for exactly one disclosure. Existing portability assertions are contract
checks only. Antigravity requires an interactive permission grant or a
working narrowly scoped permission configuration before these can run.

## T3 Antigravity evidence audit criteria

The T3-managed live run must be evaluated separately from the failed direct
CLI attempts. Before marking its scenarios passed, inspect:

- The actual tool inventory and any independent verifier dispatch/result,
  distinguishing T3 orchestration tools from native Antigravity agent tools.
- PDF page-reader output for the cited page and correct/wrong key verdicts.
  Unreadable evidence must produce ambiguity rather than guessed correctness.
- Ordered date parsing, Urgent class output, outside-root attachment read,
  course classification, filing destination, registry entry, fingerprint,
  session restart, and gated first drill item. A successful file/index script
  alone does not prove the conversational quick start.
- An actual session log and transcript for two fallback batches, if native
  independence is unavailable: checker: self in the log and exactly one
  student-facing disclosure. Count transcript messages, not quoted text in
  test code or report prose.
- For deletion-denied filing, inspect both source and destination bytes,
  the returned action and printed line, and the permission setup. Label
  operating-system permission tests separately from host permission tests.

The delegated run writes docs/issue-13-antigravity-t3.md. Its report is evidence
to audit, not an automatic acceptance decision.
