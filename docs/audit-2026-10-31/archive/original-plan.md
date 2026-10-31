# Original implementation proposal

Historical proposal; the maintained version is [PLAN.md](../PLAN.md). Its open decision questions were subsequently accepted; see [DECISIONS.md](../DECISIONS.md). Its quick-win coverage and release-check guidance are corrected in the maintained plan.

I'd split it into 8 pull requests, done in order. Each one is small, keeps the tests passing and can be merged on its own. The order follows three rules:

1. **Script fixes with unit tests go first.** They are easy to prove and don't depend on anything else.
2. **Shared helpers come before the skill text that uses them.** That way the skill text is rewritten once, not twice.
3. **Changes that need a design decision or live testing in Codex/Antigravity go last.**

The numbers in brackets refer to rows in the findings table above.

| Step | Slice | Findings | Main files | Proof | Depends on |
|---|---|---|---|---|---|
| 1 | **Script safety fixes** | Quote items go to the verifier (#1), PDF reader octal crash and size check (#4), term order for retakes (#15), unique temp file for the root pointer (#25, that part only) | `verify.py`, `pdftext.py`, `fingerprint.py`, `workspace.py`, plus one line in `mimir-quiz` about `quote` | New unit tests for each fix; full test suite | none |
| 2 | **Route correctness** | Route when there is no outline (#2), stale mastered topics get rechecked (#10), past-questions includes mastered types in Standard mode (#11) | `session.py`, `plan.py`, `session.md:54`, `mimir-past-questions` | Tests on the output of `start` and the triage step | none |
| 3 | **Portable date helper** | Add a `session.py now` / `parse-date` subcommand and replace every `date` call in the skills (#3) | `session.py`, step 1 of all skills, `session.md`, `urgent.md` | Unit tests for date phrases (including "tomorrow", "Friday", "in 3 days", out-of-range dates); grep shows no `date -` left in `skills/` | none |
| 4 | **Closing sessions and quiz logging** | Quiz timestamps (#8), quiz and past-questions update `save.md` (#9), the duplicate gating in past-questions (#12) | `mimir-quiz`, `mimir-past-questions`, maybe a `session.py close` subcommand | The session parser accepts a quiz log; `debrief_state` finds the pending debrief | 3 |
| 5 | **Instruction cleanup** | One frustration rule (#7), session-start reads (#19), question budget (#20), remove the dead third question (#23), skill descriptions and the `mimir-help` flag (#13, #21), empty cases in forecast and progress (#26), manifest and portability test (#24) | `mimir-core-rules`, skill frontmatter, `README.md`, `marketplace.json`, `test_portability.py` | Portability test extended; `release_check.py` | 4 (same files) |
| 6 | **`session.py record` for mastery** | One place that owns the mastery status rules and the evidence history (#16); it also enforces #7 | `session.py`, `session.md`, `urgent.md`, `teaching.md`, `mimir-quiz` | Table of tests for every status change; grep shows no hand-written mastery rules left in skills | 5 |
| 7 | **Shared course-resolution text** | One "Resolve the course" block (#22); name steps instead of numbering them in cross-references | `mimir-core-rules`, step 2 of 5 skills | Grep for the old duplicated phrases; release check | 6 (same files) |
| 8 | **Cross-agent behaviour and planner** | Verifier in Codex/Antigravity plus PDF reading through `pdftext.py` (#5), attachments outside the learning folder (#6), Antigravity install (#14), planner weights and timings (#17), ingest batching (#18), remaining performance items (#25) | `verified-items.md`, `verifier.md`, `urgent.md`, `workspace.py`, `README.md`, `session.py`, `mimir-ingest` | Unit tests where possible; **needs a manual run in Codex and Antigravity** | 1–7 |

Step 8 is the loosest. It could be split into "cross-agent" (#5, #6, #14) and "planner and performance" (#17, #18, #25) once we get there.

Steps 1–3 cover all of the top 5 quick wins except the frustration rule, which lands in step 5. Steps 1 and 2 touch different files and could run in parallel. From step 3 on, each step edits the same skill files as the one before, so they go in sequence.

**Decisions I need from you before certain steps:**
- **Step 2:** where the route comes from when there is no outline. My suggestion: the topics in `INDEX.md`, listed in the order they were ingested.
- **Step 6:** the rule for `mastered`. My suggestion: at least 2 solves without help, on different items, with at least one on a separate day or on a real past-paper question. One wrong answer on a mastered topic then gives `shaky`, not `gap`.
- **Step 5:** keeping `disable-model-invocation` on setup and ingest, and only rewording the README. My suggestion: yes.

**Workflow:** one branch per step, created from `main`, with each step's tests passing before the merge. I'll run the tests with `uvx pytest` because pytest isn't installed for the system Python.

Should I start with step 1?
