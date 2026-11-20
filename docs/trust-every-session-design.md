# Trust every session — design

Status: design agreed in conversation on 2026-11-12 and 2026-11-19 (27 questions over three rounds) and approved by the maintainer on 2026-11-19. Implemented on the `trust-every-session` branch (issues #77 to #80 and #3, see Slices). Command and field names below are working names; the issue for each slice and the script docstrings settle the exact contract.

## Goal

The README roadmap names the next milestone "trust every session": answer keys checked on every agent (#23, #2), smoother installs (#3, #4), and live checks on macOS, Windows and WSL (`RELEASE.md`). Two goals were added on 2026-11-12: cut the wait between questions, and make the answer checks fast.

Speed and trust have the same cause. The answer-key check is a chain of steps that the tutor follows from prose: gate, wait line, checker, gate, show. Every tool call costs one tutor model step, so the chain is slow. And because only prose holds the chain together, a host can skip the checker and no script notices (#23).

## Measured baseline

Measured from the maintainer's Claude Code study transcripts of 30 Oct to 10 Nov 2026 (Opus tutor, Sonnet checker), using the timestamp of each transcript row. The transcripts are private. The scripts and how to run them are in `docs/measurements/trust-every-session.md`.

| What | Value |
|---|---|
| One tutor model step before a tool call | 8.1 s median. The tool itself runs in under 1 s. |
| Plain dialogue turn | 12.7 s |
| Answer turn with only `session.py record` | 16.8 s |
| Turn that needs a newly checked question | 86.8 s, with its first text at 51.7 s |
| One gate, checker, gate cycle | 47 s mean: 35 s in the tutor's own steps, 12 s in the checker |
| Session start to first question | about 130 s over 11 to 14 tool calls |
| Checker verdicts | 427 `correct`, 1 `wrong`. The gate never returned `flagged` or `dropped`. |
| Fake-real cell of the checker reply | Never `yes`: 0 of 364 reply lines in the 73 checker runs whose transcripts exist |
| Checker runs that opened no source (#2) | 24 of 73 |
| What the other 49 runs did | 36 read only sources the tutor had named. 13 also made other calls, 15 in all: 9 ran `pdftext.py --help`, 3 searched the disk for `pdftext.py`, 3 were shell loops over named files. No run opened a course file the tutor had not named. |
| The one `wrong` verdict | Found with a search in a notes file the tutor had named |
| Questions per check batch | median 3, mean 5.0, maximum 27. Five batches held 20 or more. |
| Checked questions by kind | 67% practice, 29% real with a text label, 4% real from a scan |
| Time the student takes to answer | 61 s median, a quarter of answers within 18 s (74 answers) |
| Share of tutor usage spent on check steps since 2026-11-01 | 11.7% of API messages, 12.4% of cache-read tokens |
| Lean acceptance host (Claude Code) | 14 of 16 checker dispatches ran in the background, because no rule says foreground |

The checker is not the bottleneck. The number of tutor steps around it is.

## Agreed direction

- Scope: the trust items (#23, #2, #3, #4, `RELEASE.md`) plus speed between questions. Faster session start and close are a later milestone. The one exception is that `session.py record` writes its own log line.
- A practice question may appear while its answer key is being checked. Answer keys, worked answers and real-paper labels stay strict.
- The tutor says what is ready first and calls tools after it.
- Questions are prepared and checked in question sets of at most 6. The first question of a set is shown at once.
- Scripts own the check state in a check ledger. A question without a settled check earns no mastery credit.
- The checker reads one closed evidence pack per batch. A script, not the checker, confirms real-paper labels.
- The independent check stays for now. Keeping or dropping it is reviewed after the finals with benchmark numbers and season counts.
- Done means proven: live runs on Claude Code, Codex and Antigravity on Linux, and a test matrix on Linux, macOS and Windows.
- The work ships in slices. The speed slice comes first as 0.4.1, before the ledger exists.

## 1. Check policy

1. A practice question may be shown before its check has finished, provided the check runs in the same turn.
2. An answer key, a worked answer or a hint is never shown before the question has a `correct` verdict.
3. A real-paper label is never shown before it is confirmed: by the checker until the ledger slice, by a script after it (section 6).
4. The independent check stays for now, as one batch per question set (section 10 reviews this).
5. On a host with no subagent the tutor rechecks its own keys in the same context. Those answers still count toward mastery. The student is told once per session, as today, and `checker: self` is stored for each question.

What the student can read while a set's check runs:

| Session | Shown at once | Shown after the check |
|---|---|---|
| Quiz, knowledge gauge | The first question of the set, when it is a practice question | Its key after the student answers; the other questions |
| Standard study | The explanation of the topic | The topic's application questions |
| Urgent | The recipe of the first question type | The worked item, then the check item |
| Past questions | Until the ledger slice: nothing new, so the wait line is said. After it: the first real question, once the script has confirmed its label. | Keys; the other questions |

## 2. Turn shape

The core rule "Feedback on an answer and the next question share one message" becomes "share one turn". The order inside an answer turn:

1. Text that needs no tool call: feedback on the answer, the key, and the next question when it is already checked or is a practice question that starts a new set.
2. Tool calls: `session.py record` for the answer and, when a new set starts, the calls that prepare and check it. Calls that do not depend on each other go in one step.
3. Text after the tool calls only for what depended on them: a question that had to wait for its check, or a withdrawal line. Inside a set, nothing is written after `record`.

Further rules:

- `record` appends the outcome line to the session log itself. The tutor makes no separate log edit per answer.
- The checker always runs in the foreground. On Claude Code the rule names `run_in_background: false`.
- The wait line loses its estimate (#23 finding 5): "Checking my answers before you study them." It is said once per session, the first time a check runs while the student has nothing new to read.

## 3. Question sets

A question set is the group of questions prepared and checked together as one batch.

- A set holds at most 6 questions. A longer quiz runs as several sets. An Urgent set of up to 3 question types, with a worked item and a check item each, fits the cap.
- The first question is shown at once. The other questions are written after that text in the same turn, and the whole set goes to the checker as one batch.
- A fresh question after a miss, and a replacement for a withdrawn question, are sets of one.
- The catch: the turn ends when the check settles, so an answer typed before that waits. Preparing and checking a set takes about 75 s (estimate) and the student answers in 61 s median. At roughly half of set starts the answer waits for the remainder, 15 to 55 s. Today every set start waits 87 s with nothing to read.
- Rejected: checking each question on its own as the student goes. It costs about three times the check steps and does not shorten the waits.

## 4. Failed checks

Each question gets at most one recheck. A checker dispatch that fails checked nothing: it does not use up the recheck, and the question stays unshown until a checker settles it.

A question the student has not seen yet: the tutor fixes the key or the question and it is rechecked once. If the verdict is still not `correct`, the question is dropped and the existing line is said once: "Dropped K question(s) my checker could not confirm."

A question already on screen:

- **Key wrong.** The tutor fixes the key and it is rechecked once. The student never sees the wrong key. Nothing is said in the moment. The disagreement is logged.
- **Question flawed, or the recheck also fails.** One line: "Withdrawn: my checker could not confirm this question." A replacement of the same question type follows as a set of one. Nothing is recorded for the withdrawn question.

The `flagged` state goes away, and with it the ⚠ question shown beside a compare reference, the `compare` field and the rule that solves on flagged questions never count. In 428 real verdicts the state was never reached.

## 5. Check ledger

Today `verify.py gate` is stateless and `session.py record` trusts a `gate` object that the tutor types. No script can tell that a check was skipped. The check ledger replaces both.

- **`verify.py submit`** takes a question set as full text: question, key, hint, sources and, for a real question, its citation. It checks citations against the registry, issues the labels (section 6), writes the questions to the ledger, writes the evidence pack (section 7) and returns an id and a label for each question plus the pack's path.
- **Dispatch** is one line that names the pack. It is the same on every host.
- **`verify.py settle`** takes the checker's reply, pasted unchanged by the tutor, and the checker kind (`independent` or `self`). The script parses the reply. It returns `show`, `retry` or `dropped` for each question. A `retry` question is submitted again under the same id, and the script allows that once.
- **`session.py record`** takes the question's ledger id in place of the typed `gate` object. A question without a settled `correct` check earns no mastery credit. `record` reads the real-paper flag from the ledger, not from the tutor.

The ledger is one script-owned file per session in `<course>/.state/checks/`. It holds the full text of every prepared question with its key, hint, sources, label, verdicts with reasons and checker kind. It is kept after the session. The tutor never reads the file. One read command returns a single prepared question when the tutor no longer has it, for example after context compaction. The cost is about 1 to 2 KB per question (estimate).

Full text, not hashes, for four reasons:

- The checker reads the batch from a file, so the dispatch is one line on every host.
- A verdict is tied to the exact text that was checked.
- Prepared questions survive context compaction.
- Disagreements keep their evidence for the benchmark.

**Trust boundary.** The ledger stops forgetting, not lying. Tutor and checker share one shell, so no script can tell who calls it. A tutor that invents a checker reply stays invisible to the scripts. Only the acceptance transcripts prove that a real checker ran on a host.

**Pack token.** In #23 both hosts ran the gate, skipped the checker and typed `correct` verdicts. `settle` alone would accept that. So `submit` writes a short random token into the pack, the checker's reply must hold a line with just the token, and `settle` refuses a reply without one. Text before that line (the checker's working) is ignored; only the verdict lines after it count. A tutor that skips the checker cannot settle the batch unless it opens the pack to copy the token. That turns an omission into a deliberate act. It does not stop a lie.

## 6. Real-paper labels

The label check moves from the checker to `verify.py submit`.

- A real question carries an anchor: at least 8 words in a row copied from the paper.
- `submit` must find the anchor on the cited page before it issues `[real: <file>, p.<N>]`. A question that crosses a page break may match on the page after it. Without a match the question is not shown as real: the tutor corrects the citation or makes it a practice question.
- A cited page with no text layer gets today's cautious label, `[real, from photo/scan, wording may be off]`, with the original beside it. There is no label check for scans.
- The checker reply loses the fake-real cell, so #23 finding 3 disappears. The checker still sees the page text and reports a question that differs from the paper as `source-conflict`.
- A real question can then be first on screen, after one script call.

A probe on the maintainer's 62 real questions supports the rule: 48 cited pages had a text layer, and 41 of those already shared 8 or more words in a row with the tutor's wording, although the tutor paraphrases today. 13 cited pages had no text layer and 1 was unreadable.

Until the ledger slice ships, a real question waits for its check as today.

## 7. The checker

**Model and effort** stay as they are (Sonnet, medium effort) until the benchmark exists.

**Evidence pack.** One file per batch in `<course>/.state/checks/`, deleted when the batch is settled. It holds:

- each question with its number, label and key;
- the text of every cited PDF page;
- every cited text or Markdown source, whole when small (the 32 such sources in the maintainer's folder have a median of 4.8 KB, and 3 exceed 20 KB), else its path for the checker to search;
- the Notation section of the course fingerprint, so course conventions are in front of the checker;
- the paths of cited scans;
- the pack token.

The checker reads the pack and the files named in it, nothing else. This closes #2: the source text is in front of the checker every time. It loses nothing seen so far, because the one real catch came from a file the tutor had named.

**Reply.** One line per question, `N | verdict | reason`, after the token line. The verdict words stay: `correct`, `wrong`, `ambiguous`, `source-conflict`.

**Rights.**

| Host | Read-only checker |
|---|---|
| Claude Code | Enforced by the host. The helper's tools become Read, Grep and Glob; it loses shell access once the pack carries the page text. |
| Codex | A prompt rule. Codex cannot limit a child's tools. |
| Antigravity | A prompt rule. Antigravity ties reading files outside its workspace to command access. |

The README states this per host.

**Dispatch.** The rules name one explicit recipe per host, and the generic fallback only after them:

- Claude Code: `Agent` with `mimir:verifier`, in the foreground.
- Codex: `spawn_agent` with `fork_turns` none, then `wait_agent`.
- Antigravity: `define_subagent` from `helpers/verifier.md`, then `invoke_subagent`.

## 8. Hosts and platforms

- **Host bar.** The milestone is done only when live acceptance runs show an independent check in a study session and in a quiz on Claude Code, Codex and Antigravity on Linux. This needs an Antigravity acceptance driver; `tests/acceptance/drive.py` drives only Claude Code and Codex today.
- **One flow for all hosts.** Saying feedback first only helps where the host shows text before the following tool calls finish. Claude Code does. The host checks gain one look by eye per host: does the text appear before the turn ends, and can the student type meanwhile. If a host holds text back, the flow stays and the README speed claim leaves that host out.
- **#3.** `mimir-core-rules` and `mimir-notation` move out of `skills/` into plain files under `<mimir>/reference/`. The 12 shipped skills become 10. The folder is not named `rules/`, which Antigravity may load as always-on rules.
- **#4** closes when the live acceptance runs on Codex and Antigravity start from the GitHub install.
- **#23 finding 4.** Two Antigravity packaging leftovers are won't-fix and are written into the issue as such: the strict-mode warning on the root `AGENTS.md`, and the whole repository being copied on install. `RELEASE.md` gains the line that an Antigravity install is a snapshot and needs a reinstall after every change.
- **Test matrix.** GitHub Actions runs the script tests on Linux, macOS and Windows. The repository has no CI today.
- **Windows.** The script tests must pass on Windows; what fails gets fixed. Known gaps: `os.symlink` for the prior-term link, the `python3` command name, and the POSIX heredoc that every skill uses to pass JSON, which PowerShell does not run. Unknown until the first run: how many tests assume POSIX paths. The rules gain one sentence: use `python` or `py -3` when `python3` is missing. The README claims exactly this: Claude Code on Windows with Git Bash is tested in CI and not checked by hand; Codex and Antigravity on Windows are supported through WSL only.
- **By-eye release checks.** The macOS row of `RELEASE.md` is filled later on a borrowed Mac. The Windows and WSL rows are marked as not checked by hand.

## 9. Proof of speed

Rules that can be counted in any transcript:

- No tool call before the feedback text.
- No check call before the text of a practice question.
- One check batch per question set, plus one recheck batch for the questions whose verdict was not `correct`.

Medians on the maintainer's real sessions, measured the same way as the baseline:

| Measure | Target | Baseline |
|---|---|---|
| Answer to feedback text | at most 15 s | 16.8 s when the turn only records; 51.7 s when a new question must be checked |
| Answer to next question | at most 25 s | 16.8 s to 86.8 s |

## 10. Keep-or-drop review

The maintainer asked whether the check is needed at all, given 427 `correct` verdicts to 1 `wrong`. The check stays until there are numbers to decide with.

- **When:** the week after the finals of 2027-01-04.
- **Benchmark:** 60 questions on the fixture course, 20 clean and 40 with one planted error each, course-convention errors included. It runs on each host's checker.
- **Season counts from the ledger:** questions checked, catches and escapes. A catch is a verdict other than `correct` that led to a fixed key or a dropped question. An escape is a key the student challenged after seeing it and the tutor conceded; conceding becomes a recorded event. If the ledger ships after the December study weeks, the counts for the earlier weeks come from the transcripts.
- **Floor:** if the checker catches under 50% of the planted errors, the check does not stay as it is. It is strengthened once and the benchmark is rerun. If it still fails, the check is dropped and the README is reworded.
- **Cheaper checker:** once the benchmark exists, lower effort and a smaller model are tried. The cheapest setting within 5 points of today's catch rate wins.
- Above the floor the maintainer decides with real numbers: catches and escapes per 1,000 questions against usage.

## Slices

| Slice | Version | Contains | Closes |
|---|---|---|---|
| 1. Speed (#77) | 0.4.1 | Check policy, turn shape, question sets, failed-check rules with `flagged` and `compare` removed, foreground dispatch with the per-host recipes, wait line, `record` writing its log line | The two speed goals; #23 finding 5 |
| 2. Check ledger (#78) | 0.5.0 | `submit`, `settle`, the ledger file, evidence pack, pack token, script-side real-paper labels, `record` reading the ledger, checker without shell on Claude Code, the conceded-key event | #2; #23 finding 3 |
| 3. Host parity (#79) | with or after 0.5.0 | Antigravity acceptance driver, live runs from the GitHub install, the by-eye look per host, the benchmark, README host statements | #23, #4 |
| 4. Test matrix (#80) | any time | GitHub Actions on three systems, Windows fixes, the `python` rule, README and `RELEASE.md` wording | The `RELEASE.md` part of the milestone, except the macOS row |
| #3 | any time | The move to `<mimir>/reference/` as a move-only change, kept out of the slice 1 change so both stay reviewable | #3 |

Slices 1 to 3 run in that order. Slice 4 and #3 depend on nothing.

Slice 1 works on today's stateless `verify.py gate`. It writes the dispatch recipes for all three hosts; slice 3 proves them live. Versions: 0.4.1 changes how sessions run; 0.5.0 changes script contracts.

No skill or script changes before the maintainer says go on slice 1.

## Not in this milestone

- Faster session start (about 130 s to the first question) and faster session close.
- A different checker model or effort before the benchmark exists.
- A separate flow per host.
- Checks by hand on Windows and WSL.

## New terms

Added to `GLOSSARY.md` on approval:

**Check ledger**: the script-owned record of every prepared question and its check, one file per session.

**Evidence pack**: the one file a checker reads for a batch: the questions, their keys and the text of every cited source.

**Question set**: the questions prepared and checked together as one batch, at most 6.

**Checker**: the independent helper that checks answer keys (`mimir:verifier` on Claude Code). A same-context check is the fallback when a host has no subagent.

**Catch**: a check verdict other than `correct` that led to a fixed key or a dropped question.

**Escape**: a wrong key that reached the student, counted when the student challenges it and the tutor concedes.
