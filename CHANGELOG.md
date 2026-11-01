# Changelog

## 0.3.4

This release delivers the nine audit-remediation slices tracked in [#5](https://github.com/oguzdogmus/mimir/issues/5).

### Major changes

- **Stronger mastery evidence.** A single recorder now owns mastery updates. Mastery requires two distinct unassisted solves, with evidence from a separate day or a real past-paper question. One wrong answer moves a mastered topic to shaky. Duplicate attempts and answers during a frustration override do not inflate progress. [#12](https://github.com/oguzdogmus/mimir/issues/12)
- **Usable study routes without an outline.** Courses built from slides or past papers use indexed topics in ingestion order. Empty routes get an actionable message; stale mastered topics receive a recheck. Standard past-paper practice includes mastered types for revision. [#7](https://github.com/oguzdogmus/mimir/issues/7)
- **Portable dates and session history.** Python helpers handle timestamps and supported exam-date phrases across platforms. Quiz and past-question sessions now update last-session state, count toward the cram bill, and enable post-exam debriefs while preserving first contact. [#8](https://github.com/oguzdogmus/mimir/issues/8), [#11](https://github.com/oguzdogmus/mimir/issues/11)
- **Better cross-agent verification and attachment handling.** Capability-based verifier dispatch supports independent agents where available, with a disclosed same-context fallback. The verifier can read PDF citations. Explicit outside-workspace attachments can be filed safely, retaining the copied file when deleting the original is denied. Antigravity installation and permission guidance is updated. [#13](https://github.com/oguzdogmus/mimir/issues/13)
- **Evidence-based planning and faster ingestion.** Planning uses matching fingerprint mark weights and logged topic timings, retaining explicitly rough estimates when evidence is insufficient. Ingest samples before confirmation, reads documents afterwards in batches, and records resumable coverage and observations. [#14](https://github.com/oguzdogmus/mimir/issues/14)

### Fixes and maintenance

- Quote claims and unknown page counts can no longer bypass answer-key verification. The built-in PDF reader enforces its size limit and handles malformed octal escapes safely. Retakes require a strictly earlier term; workspace root-pointer writes use unique atomic temporary files. [#6](https://github.com/oguzdogmus/mimir/issues/6)
- Frustration handling, startup reads, question budgets, skill triggers, and help invocation are aligned. Shared course resolution and host-specific command naming replace duplicated instructions. Manifests and shipped skill lists have consistency checks. [#9](https://github.com/oguzdogmus/mimir/issues/9), [#10](https://github.com/oguzdogmus/mimir/issues/10)
- Topic indexing parses the topic table once per update; early-return history lookups read logs lazily; PDF extraction caches shared font decoding within each call. Reproducible measurements are recorded in [the performance report](docs/measurements/issue-14.md).

### Validation and remaining limits

- The implementation passed **1,081 automated tests**. Release manifest consistency and artifact generation are checked again for this version.
- Live Codex and T3-managed Antigravity exercises are recorded in [host acceptance evidence](docs/issue-13-host-checks.md). These cover the documented scenarios, not every host or model run. [#23](https://github.com/oguzdogmus/mimir/issues/23) remains open for reported verification and packaging gaps; this release does not claim that issue is resolved.
- Native browser-opening checks for macOS, Windows, and WSL remain pending in [RELEASE.md](RELEASE.md).

### Updating

Update or reinstall Mimir through your agent's plugin manager to receive this version. Installed plugin snapshots do not automatically track edits to a development checkout.
