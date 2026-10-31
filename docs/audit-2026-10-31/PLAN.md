# Implementation plan

Use [DECISIONS.md](DECISIONS.md) for approved behavior and [STATUS.md](STATUS.md) for execution state. Numbers below refer to the unchanged IDs in [FINDINGS.md](FINDINGS.md).

Each step is a GitHub sub-issue of the spec [#5](https://github.com/oguzdogmus/mimir/issues/5). The Prerequisite column lists only real logic dependencies, mirrored as native GitHub blocking links; a step whose blockers are merged can start. Steps 5, 6 and 7 edit the same skill files, and steps 1 and 2 share test surface: merge such branches one at a time and rebase the next on updated main.

## Overview

| Step | Issue | Scope | Findings | Prerequisite | Risk / confidence |
|---|---|---|---|---|---|
| 1 | [#6](https://github.com/oguzdogmus/mimir/issues/6) | Script safety | 1, 4, 15, 25 (temp file only) | None | Low–medium / high from audit code checks |
| 2 | [#7](https://github.com/oguzdogmus/mimir/issues/7) | Route correctness | 2, 10, 11 | None | Medium / high from audit |
| 3 | [#8](https://github.com/oguzdogmus/mimir/issues/8) | Portable dates | 3 | None | Medium / high defect confidence; parser contract needs care |
| 4 | [#11](https://github.com/oguzdogmus/mimir/issues/11) | Session closing and quiz logs | 8, 9, 12 | 3 (#8) | Low–medium / high from audit |
| 5 | [#9](https://github.com/oguzdogmus/mimir/issues/9) | Instruction cleanup | 7, 13, 19, 20, 21, 23, 24, 26 | None | Low–medium / host claims need live validation |
| 6 | [#12](https://github.com/oguzdogmus/mimir/issues/12) | Central mastery recording | 16; enforcement of 7 | 5 (#9) | Medium / behavior change requires transition tests |
| 7 | [#10](https://github.com/oguzdogmus/mimir/issues/10) | Shared course resolution | 22 | None | Low–medium / high duplication confidence |
| 8A | [#13](https://github.com/oguzdogmus/mimir/issues/13) | Cross-agent behavior | 5, 6, 14 | 1 (#6), 3 (#8) | Medium / host-dependent; requires live evidence |
| 8B | [#14](https://github.com/oguzdogmus/mimir/issues/14) | Planner and performance | 17, 18, 25 (remaining parts) | 4 (#11) | Medium / benchmark and integration evidence needed |

Risk/confidence above are planning judgments, not fresh audit results. Step 8 is split into two reviewable parts while preserving the original eight-step roadmap. Finding 25 is complete only after both step 1 and 8B.

## Common completion criteria

- Reproduce the relevant behavior and inspect current code; historical line numbers may have shifted.
- Add meaningful regression tests for behavioral fixes. Do not add tests that merely echo edited prose.
- Run relevant test files, then `uvx pytest` for implementation changes. Record exact commands/results; use an already-installed pytest runner if appropriate.
- Inspect the diff for scope and unintended data/schema changes.
- Update STATUS, including any manual validation that remains.
- PR/review readiness is separate from merge completion.

`scripts/release_check.py` checks native browser opening of generated HTML/SVG, as explained in [RELEASE.md](../../RELEASE.md). It is not an instruction validator. Use `tests/test_portability.py` for manifest/frontmatter consistency. Run the live release check when opener behavior or release readiness warrants it; `--no-open` verifies generation only and does not establish live OS support.

## Step 1 — Script safety fixes

Findings: **1, 4, 15, 25 (root pointer)**.
Files: `scripts/verify.py`, `scripts/pdftext.py`, `scripts/fingerprint.py`, `scripts/workspace.py`, quote instructions in `skills/mimir-quiz/SKILL.md`.

- [ ] Quote keys enter the verifier path; source metadata alone never marks them checked. Unknown office-document page counts cannot justify a bypass.
- [ ] Built-in PDF reading checks the existing 128 MiB limit before allocating the file contents. Invalid octal escapes such as backslash-8 do not crash.
- [ ] Retakes require a strictly earlier year/term, including ordering within the same year. Reuse term-order logic without introducing an import cycle.
- [ ] Root pointer writes use unique temporary files, atomic replacement, and cleanup on failure.
- [ ] Tests cover verified/rejected quote keys, unknown page counts, oversized PDFs, malformed escapes, same-year/reversed/equal terms and independent temporary paths/failure cleanup.

Targeted: `uvx pytest tests/test_verify.py tests/test_pdftext.py tests/test_fingerprint.py tests/test_workspace.py`.
Keep broader PDF caching and ingestion optimizations for 8B.

## Step 2 — Route correctness

Findings: **2, 10, 11**. Decision: **D1**.
Files: `scripts/session.py`, `scripts/plan.py`, `skills/mimir-study/references/session.md`, `skills/mimir-past-questions/SKILL.md`.

- [ ] Slides-only and past-paper-only courses get a route from INDEX topics in ingestion order when no outline route exists.
- [ ] An empty INDEX/route is reported as missing route evidence, never “every topic is mastered”.
- [ ] Existing outline/mastery state is preserved; repeated starts do not duplicate topics.
- [ ] When no unmastered topics remain, stale mastered topics receive the existing recheck; fresh mastered topics do not.
- [ ] Standard past-question practice includes mastered types; Urgent keeps its current prioritization/exclusion.
- [ ] Tests exercise start output and triage across empty, partial, all-mastered and stale cases.

Targeted: `uvx pytest tests/test_session.py tests/test_plan.py tests/test_ingest.py`.

## Step 3 — Portable date helper

Finding: **3**.
Files: `scripts/session.py`, skill/references currently invoking shell date.

- [ ] Add portable `now` / `parse-date` functionality using Python standard library date handling.
- [ ] Define output fields for ISO timestamp, evidence date, log name and parsed exam date; use timezone-aware local dates consistently.
- [ ] Specify and test supported inputs: ISO date, tomorrow, weekday names and “in N days”; reject impossible dates and unsupported/ambiguous phrases clearly. Document the same-day weekday convention.
- [ ] Replace shell date use across skills, including urgent term inference.
- [ ] Test month/year boundaries, timezone offsets and malformed inputs with a fixed clock.
- [ ] Search skills for remaining `date` commands and inspect each hit; no GNU-dependent date parsing remains.

Targeted: `uvx pytest tests/test_session.py tests/test_portability.py`.
Do not claim unrestricted natural-language date parsing from a small standard-library helper.

## Step 4 — Session closing and quiz logging

Findings: **8, 9, 12**. Depends on **3**.
Files: quiz and past-questions skills; shared session reference/helper as needed.

- [ ] Quiz logs parser-compatible ISO started/ended timestamps and initializes first_contact when absent.
- [ ] Quiz and past-question sessions update last_session and pending_debrief through one shared close step (a CLI helper only if justified).
- [ ] Repeated closing does not corrupt logs or overwrite an earlier first contact.
- [ ] Standard and Urgent branch before gating; each displayed item gets the intended single verification path.
- [ ] A quiz/practice-only course contributes elapsed time to session accounting and is discoverable for debrief.

Targeted: `uvx pytest tests/test_session.py tests/test_verify.py`; inspect both skill flows.

## Step 5 — Instruction cleanup

Findings: **7, 13, 19, 20, 21, 23, 24, 26**. Decisions: **D3, D5**.
Files: core rules, study references, relevant skill frontmatter, README, `.claude-plugin/marketplace.json`, `tests/test_portability.py`.

- [ ] Write the frustration rule once and reference it from study/quiz; reserve enforcement helper work for step 6.
- [ ] Each skill specifies its own startup reads.
- [ ] Clarify that teaching/drill/quiz content and the cliffhanger do not consume the clarification-question budget.
- [ ] Remove the dead third-question branch in “I know this”.
- [ ] Apply D3 and document accurate invocation forms; shorten study description and separate quiz vs real past-paper practice triggers.
- [ ] Give forecast and progress explicit evidence-empty/unseen responses.
- [ ] Align manifest description/version and extend meaningful consistency checks without banning intentionally retained setup/ingest flags.

Targeted: `uvx pytest tests/test_portability.py`; inspect affected flows and run full suite. Host invocation claims still need step 8A live checks.

## Step 6 — Central mastery recording

Finding: **16**, with enforcement of **7**. Decisions: **D2, D5**.
Files: `scripts/session.py`, study session/urgent/teaching references, quiz skill and any other mastery writers found by search.

- [ ] Add `session.py record` as the owner of mastery transitions and dated evidence.
- [ ] Require two eligible unassisted solves on distinct items plus the date/real-paper condition in D2.
- [ ] Repeated records of the same attempt cannot manufacture additional evidence.
- [ ] One incorrect answer on mastered gives shaky; helped, invalid and override-session attempts do not falsely promote.
- [ ] A later unassisted solve lifts the override while preserving the ordinary mastery requirements.
- [ ] Keep 2–3 dated evidence entries without losing facts needed to evaluate mastery. Preserve/read existing state safely.
- [ ] All callers use the helper; remove duplicated transition logic.
- [ ] Table-driven tests cover transitions, distinctness, dates, real-paper evidence, overrides, invalid input and legacy state.

Targeted: `uvx pytest tests/test_session.py`; search all mastery-writing instructions and inspect each remaining match.

## Step 7 — Shared course resolution

Finding: **22**.
Files: core rules, plan/forecast/progress/debrief/past-questions as applicable, study session references.

- [ ] One named “Resolve the course” block defines behavior; all callers refer to it.
- [ ] Missing, explicit and automatic course selection retain intended behavior.
- [ ] Host command naming applies to every student-facing message, including fixed fallback text.
- [ ] Replace fragile numbered references affected by this change with named sections and verify all callers.

Targeted: `uvx pytest tests/test_session.py tests/test_portability.py`; search old duplicated phrases and inspect references.

## Step 8A — Cross-agent verification, attachments and installation

Findings: **5, 6, 14**.
Files: core rules, verified-items reference, `helpers/verifier.md`, urgent reference, `scripts/workspace.py`, PDF path handling if needed, README.

- [ ] Use available native independent verifier capabilities; disclose/log `checker: self` for same-context fallback.
- [ ] Verifiers read PDF evidence through `pdftext.py pages`; unsupported or unreadable evidence stays ambiguous.
- [ ] Make explicit outside-root attachments usable without bypassing host permissions. Resolve the current read-before-file dependency and course classification requirements.
- [ ] If a permitted copy succeeds but deleting the original is unavailable, keep the valid destination, report that it was copied, and do not lose or falsely claim to move the source.
- [ ] Document an Antigravity installation that can access the actual plugin path; create learning directory before launching.
- [ ] Unit-test path/copy failure behavior and provenance. Manually exercise PDF verification and quick-start attachments in Codex and Antigravity.
- [ ] Record host/version, scenario, observed result and remaining access limitations. No “passed” from mocks alone.

Targeted: `uvx pytest tests/test_workspace.py tests/test_pdftext.py tests/test_verify.py tests/test_portability.py`.
Choose the smallest working approach after inspecting current host tools; the audit's alternatives are not all simultaneous requirements.

## Step 8B — Planner wiring and measured efficiency

Findings: **17, 18, 25 (topic indexing, log reads, fonts)**.
Files: `scripts/session.py`, `scripts/plan.py`, `scripts/ingest.py`, `scripts/pdftext.py`, ingest skill.

- [ ] Supply real logged timings and fingerprint topic weights to the planner; preserve an explicit rough fallback when evidence is absent.
- [ ] Add session-to-planner integration coverage showing that weights and timing evidence change the appropriate output.
- [ ] Classify ingest candidates from filenames/sample pages before confirmation; perform full evidence extraction afterwards in batches.
- [ ] Parse topic tables once, read logs lazily where semantics allow, and cache shared font decoding per PDF call.
- [ ] Preserve first_contact semantics and extraction/index results; avoid global caches with stale-data risks.
- [ ] Record before/after representative measurements; pursue only optimizations with evidence of benefit.

Targeted: `uvx pytest tests/test_session.py tests/test_plan.py tests/test_ingest.py tests/test_pdftext.py tests/test_fingerprint.py`.

## Quick-win placement

The original top five are: quote verification (step 1), fallback route (2), PDF guards (1), quiz timestamps (4), frustration rule (5, enforced in 6). This corrects the original proposal's statement that steps 1–3 cover all but frustration.
