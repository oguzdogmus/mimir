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
