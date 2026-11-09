# Changelog

## 0.4.0

Study sessions are now led by the student: they run until the student says "end session", the student can choose how a session runs, and Mimir learns how each student likes to be taught. Tracked in [#30](https://github.com/oguzdogmus/mimir/issues/30); design in [the design doc](docs/teaching-preferences-design.md).

### Major changes

- **Sessions end only when the student says so.** No timer and no sign-off of Mimir's own: a finished set, topic or route leads straight into the next one or into choices, in the same message. "end session" closes once and records the session's length. [#32](https://github.com/oguzdogmus/mimir/issues/32)
- **Teaching settings.** Three saved settings shape Standard teaching in every course: support (example first, method first, try first), how often guiding questions come (checks only, key decisions, every step) and what they ask (next step, why, what-if). A lasting request ("always explain first") sets one; an optional sampler during setup picks starting levels; small probe trials move one step toward more independent teaching only after positive evidence on two different days, and pause near an exam. [#40](https://github.com/oguzdogmus/mimir/issues/40), [#41](https://github.com/oguzdogmus/mimir/issues/41), [#42](https://github.com/oguzdogmus/mimir/issues/42)
- **Choose how to study.** "Let's cram" or "study normally" picks Urgent or Standard for one session, or for every session until the coming exam. [#36](https://github.com/oguzdogmus/mimir/issues/36)
- **Real exam times.** The exam's date and time are saved and used (no more counting down to midnight); Urgent starts 48 hours before the actual time. [#34](https://github.com/oguzdogmus/mimir/issues/34)
- **Exam scope.** What an exam covers ("the midterm covers sessions 1–19") is confirmed once and saved with that exam; topics outside it are listed last and marked, never removed. [#45](https://github.com/oguzdogmus/mimir/issues/45)
- **Knowledge gauge.** A short check of what the student already knows runs once per course in Standard and is offered in Urgent. [#39](https://github.com/oguzdogmus/mimir/issues/39)
- **Unlimited retries.** A wrong answer or "idk" gets guidance, never the answer; the answer comes when the student asks for it. Question labels are lighter. [#37](https://github.com/oguzdogmus/mimir/issues/37)
- **Urgent drilling.** Triage is a ranked table with nothing cut; each question type starts with its short recipe, and three misses offer to continue or move on. [#35](https://github.com/oguzdogmus/mimir/issues/35), [#38](https://github.com/oguzdogmus/mimir/issues/38)

### Removed

- Learning-time forecasts and the rule that made a long route trigger Urgent. Only exam proximity, or the student's choice, decides the delivery class. [#33](https://github.com/oguzdogmus/mimir/issues/33)

### Fixes and maintenance

- Existing users see a one-time line about what changed. [#43](https://github.com/oguzdogmus/mimir/issues/43)
- Question-type triage moved from instructions into `session.py triage`, with the same ranking. [#62](https://github.com/oguzdogmus/mimir/pull/62)
- Review findings fixed across the branch: script refactors without behavior change, docstrings in sync, glossary on the shipped vocabulary. [#61](https://github.com/oguzdogmus/mimir/pull/61)

### Validation and remaining limits

- **1,356 automated tests** pass.
- Live acceptance runs of all nine teaching levels on Claude Code (Sonnet 5.5) and Codex (gpt-6.1-sol), with a scripted student: [results](docs/acceptance-44.md), [protocol](tests/acceptance/README.md). Claude Code passed 7 of 9 levels. On Codex every level met its teaching rules except two, but every run opened with Codex's own "I'll use Mimir's study skill" before the class line. On both hosts every run closed exactly once on "end session" and used an independent answer check. Remaining gaps are listed in the results. [#44](https://github.com/oguzdogmus/mimir/issues/44)
- [#23](https://github.com/oguzdogmus/mimir/issues/23) stays open; one Claude Code run showed a question before its independent check returned.
- Native browser-opening checks for macOS, Windows and WSL remain pending in [RELEASE.md](RELEASE.md).

### Updating

Update or reinstall Mimir through your agent's plugin manager. Saved progress carries over. An existing preference for fewer questions becomes the "checks only" setting; everything else starts at the defaults.

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
