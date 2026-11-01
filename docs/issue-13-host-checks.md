# Issue 13 host acceptance — 2026-11-01

## Capability decision

Use the existing PDF reader, exact-path attachment scope, separate copy/delete
stages, and capability-based native helper dispatch. No additional agent
framework is needed.

Codex CLI 0.166.0 through T3 offers native independent agents.
T3-managed Antigravity ACP 1.4.1 offers define_subagent/invoke_subagent.
Direct agy CLI 1.4.12 headless attempts denied commands; the T3-managed run
successfully exercised the actual workflow. These are different host setups,
not contradictory results.

## Verified evidence

- [Codex Urgent baseline](issue-13-codex-urgent.md): actual date/class routing,
  outside-root read before classification/filing, registry and fingerprint,
  triage and independent PDF verification. Both items reached show.
- [Antigravity live acceptance](issue-13-antigravity-t3.md): native independent
  verifier returned correct/wrong and ambiguous for unreadable evidence;
  Urgent attachment workflow reached the first verified drill; real host
  file-tool denial remained denied; real OS deletion denial retained the
  completed copy, reported copied, and allowed indexing.
- [Antigravity fallback acceptance](issue-13-antigravity-fallback.md): a child
  with native subagent tools disabled completed two batches in one session.
  Parent audit of actual PLANNER_RESPONSE.content confirmed exactly one
  fallback disclosure and one wait notice. The actual session log contains
  checker: self; no independent-agent dispatch was recorded.

Parent inspection also confirmed the independent child transcripts, registry,
session log and output artifact, and identical retained original/copy bytes:
794 bytes, SHA-256
26a008970c350193d1d9e86a1009273e75f0c66682cc4e43c266eae580882bd2.

## Validation and review

- Targeted workspace/PDF/verify/portability suites: 263 passed.
- Full suite: 1080 passed in 89.61 seconds.
- Python compileall and git diff --check passed.
- GPT-6.1 Terra Standards review: no violations or actionable smells.
- GPT-6.1 Terra Spec review identified missing live checks, runtime provenance
  evidence, and full-suite documentation. The reports and audited transcript
  evidence above resolve those gaps. No scope creep was reported.

Only evidence documents changed after the passing full suite.

## Practical limits

These are synthetic-fixture live agent exercises, not tests with student data.
They prove the recorded workflows, not universal reliability of future model
behavior. No student reply was fabricated in the first-contact scenario.

Antigravity file tools require workspace access to the learning root, real
plugin directory, and any outside attachment directory. Its native verifier
requires command access, bundled with file-write tools; read-only behavior is
prompt-enforced and the observed verifier made no write calls.

Disabling native subagent tools genuinely removed them in the fallback test.
Disabling MCP tools did not fully remove call_mcp_tool. External T3 delegation
remained exposed but was prohibited by the child's orchestration policy; the
fallback test establishes behavior without an authorized native checker,
not complete protocol-level isolation from every possible delegation tool.

The copy-denial test used real kernel permissions after dropping
CAP_DAC_OVERRIDE in Antigravity's user namespace. It is distinct from host
tool permission enforcement and from the unit tests' injected failures.
