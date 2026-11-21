# Changelog

## 0.5.0

Scripts now own the answer-key check. Before, `verify.py gate` was stateless and `session.py record` trusted a `gate` object the tutor typed, so no script noticed a skipped checker ([#23](https://github.com/oguzdogmus/mimir/issues/23)). Tracked in [#78](https://github.com/oguzdogmus/mimir/issues/78); design in [the design doc](docs/trust-every-session-design.md), sections 5 to 7.

### Major changes

- **Check ledger.** Every prepared question goes into one script-owned file per session in `<course>/.state/checks/`, with its full text, key, hint, sources, label, verdicts with reasons and checker kind. It is kept after the session. A question earns mastery credit only with a settled `correct` check there.
- **Evidence pack.** The checker reads one pack per question set: the questions and keys, the text of every cited PDF page, small text and Markdown sources whole (longer ones by path), the paths of scans and the Notation section of the course fingerprint. This closes [#2](https://github.com/oguzdogmus/mimir/issues/2): in 24 of 73 real runs the checker had opened no source. On Claude Code the checker loses shell access and keeps Read, Grep and Glob.
- **Pack token.** A checker reply must carry the pack's token on a line of its own, and only the verdict lines after it count; without it the batch stays unsettled. A tutor that skips the checker can no longer settle a batch by accident. The ledger stops forgetting, not lying: the README states this trust boundary.
- **Real-paper labels by script.** A real question must carry at least 8 words in a row from the cited page (or the page after it); only then does it get `[real: <file>, p.<N>]`. A page with no text layer keeps the cautious scan label. A real question can now be shown at once, like a practice question, before its check finishes. The checker's fake-real cell is gone ([#23](https://github.com/oguzdogmus/mimir/issues/23) finding 3).
- **Escapes and catches.** A key the student challenged and the tutor conceded is recorded as an escape, and `verify.py summary` counts questions checked, catches and escapes for the keep-or-drop review of the check after the exam season.

### Script changes

- `verify.py gate` is removed. New: `verify.py submit` (a question set as full text: labels, ledger, evidence pack), `settle` (the checker's reply, pasted unchanged, with `checker` `independent` or `self`, or `dispatch_failed`), `read` (one prepared question), `concede` (an escape) and `summary` (counts and disagreement lines).
- `session.py record` no longer accepts `gate` or `real_past_paper`. It looks the question up in the session's ledger by `item`; the label and the real-paper flag come from there. Frustration overrides need no ledger entry.
- The checker (`helpers/verifier.md`) takes the path of a pack and replies with the token line, then `N | verdict | reason` per question.

### Layout

- The core rules and the notation rules are no longer skills: they moved from `skills/` to plain files in `reference/` (`core-rules.md`, `notation.md`, and the shared `recording.md`, `session-close.md` and `verified-items.md`). Antigravity ignores `user-invocable: false` and listed them as `/mimir-core-rules` and `/mimir-notation` commands ([#3](https://github.com/oguzdogmus/mimir/issues/3)). Mimir now ships 10 skills, one per command, and each still reads the core rules first.

### Validation

- The full test suite passes.
- A live quiz run on Claude Code with a scripted student: the checker read only the evidence pack, its reply carried the pack token, `settle` and `record` worked from the ledger, and the new acceptance check N (no batch settled without a checker call) passed: [results](docs/acceptance-78.md). The first run found that the checker wrote its working before the token line; `settle` now ignores text before it.
- Live study and quiz runs on Claude Code, Codex and Antigravity: the answer check ran as an independent helper on all three hosts, each with its own dispatch recipe, and the README now says per host how the checker is kept read-only: [results](docs/acceptance-79.md) ([#79](https://github.com/oguzdogmus/mimir/issues/79)). A checker benchmark of 60 questions with 40 planted errors found 95% to 100% of them on every host and setting tried, with no right key rejected: [numbers](docs/measurements/checker-benchmark.md).

### Updating

Update or reinstall Mimir through your agent's plugin manager. Saved progress carries over. Session logs of earlier versions keep their disagreement lines; the ledger starts with the first session on 0.5.0.

## 0.4.1

Less waiting between questions. Measured on real study sessions, the checker was never the slow part: the tutor's own steps before the student had anything to read were. This release changes how sessions run, not the script contracts, except where listed. Tracked in [#77](https://github.com/oguzdogmus/mimir/issues/77); design in [the design doc](docs/trust-every-session-design.md), sections 1 to 4 and 9.

### Major changes

- **What is ready comes first.** Feedback on an answer and its key are written before any tool call; `session.py record` and the checks run after them, and the next checked question follows once, in the same turn.
- **Question sets.** Questions are prepared and checked in sets of at most 6, one checker batch per set. The first question of a set is shown at once when it is a practice question, and the set is checked behind it. Answer keys, worked answers and hints still wait for a `correct` verdict, and a real past-paper question still waits for its check. Standard study shows the explanation first, Urgent the first recipe.
- **Failed checks.** Each question gets at most one recheck. A question not yet seen is fixed or dropped. A wrong key on a question already on screen is fixed quietly; a flawed question on screen is withdrawn in one line and replaced. The "flagged" state, its ⚠ line and the `compare` field are gone: in 428 real verdicts it was never reached.
- **The checker runs in the foreground,** with one named recipe per host (Claude Code, Codex, Antigravity) before the same-context fallback.
- **Shorter wait line:** "Checking my answers before you study them.", once per session, only when there is nothing new to read ([#23](https://github.com/oguzdogmus/mimir/issues/23) finding 5).

### Script changes

- `verify.py gate` no longer returns `flagged` and no longer accepts `compare`; a question whose recheck fails is `dropped`. A key the checker caught and the tutor fixed adds a `fixed` disagreement line.
- `session.py record` takes the session's `log` name and writes the outcome line under `## Results` itself, once: a retried call or a `duplicate` writes no second line. It no longer accepts `flagged` as a gate decision.

### Validation

- **1,407 automated tests** pass.
- Live acceptance on Claude Code (Sonnet 5.5), a study run and a quiz run: [results](docs/acceptance-77.md). Feedback now comes before every tool call in answer turns, the checker always runs in the foreground with one batch per set, and `record` writes every log line. On Claude Code the first question of a set (and a Standard explanation) is not shown before its check: the tutor drafts it in its thinking and the text is lost, so the turn ends by writing it again once the check settles. At a set start the student still waits for the check on this host.
- The speed targets (answer to feedback at most 15 s, answer to next question at most 25 s, as medians) are measured on real sessions after release; see [the measurements](docs/measurements/trust-every-session.md).

### Updating

Update or reinstall Mimir through your agent's plugin manager. Saved progress carries over.

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
