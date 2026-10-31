# Original report: openai-architecture

Source: <t3-thread://v2/4c5bcb11-81b0-41c1-95df-d92fe94a74a7/thread:delegated-task:command%3Amcp%3A135b902e-d7b3-42f5-997f-5cb0739fa9c2%3Adelegate-task%3A140440e2-0599-4b9a-9f54-b8a9e6f18891>

Historical agent report, not a new verification. Findings may overlap or disagree; use the consolidated findings and accepted decisions for implementation.

I’ll check the skills against the scripts they call and trace the main study workflows, focusing on concrete architecture and logic issues. I’ll keep the audit read-only.

---

I found potential mismatches in past-paper practice and retake handling. I’ll check the surrounding logic to confirm their impact before reporting them.

---

The main issues are workflow gaps: study can report an empty route as complete, standalone practice doesn’t consistently update session state, and past-paper triage skips mastered topics even when the student asks to practise them. I couldn’t run the test suite because this environment has no `pytest` module.

---

Read-only audit complete; no files changed. Test suite unavailable: `python3 -m pytest` reports `No module named pytest`. Pure-function checks confirmed findings 3 and 4.

1. **Finding:** Standard study treats an empty route as completed mastery.
   - **Location:** `scripts/session.py:616`; `skills/mimir-study/references/session.md:54`; `skills/mimir-ingest/SKILL.md:33`
   - **Impact:** High · **Effort:** Small
   - **Proposed fix:** Distinguish “no route” from “all topics mastered”; initialize a fallback route from indexed topics when no outline exists.
   - **Evidence:** Only outlines populate mastery. An empty mastery table produces `topic: null`, which triggers “Your route is complete: every topic is mastered.” Slides-only and papers-only courses therefore cannot start Standard teaching.

2. **Finding:** Mastered topics bypass stale rechecks indefinitely.
   - **Location:** `scripts/session.py:617`; `skills/mimir-study/references/session.md:54`
   - **Impact:** Medium · **Effort:** Small
   - **Proposed fix:** When no unfinished topics remain, select a stale mastered topic for the existing single-question recheck.
   - **Evidence:** `remaining = [r for r in rows if r["status"] != "mastered"]` excludes mastered topics before checking staleness. An entirely mastered route closes immediately, even when every evidence date is stale.

3. **Finding:** Explicit past-paper practice silently excludes mastered topics.
   - **Location:** `skills/mimir-past-questions/SKILL.md:16`; `scripts/plan.py:699`
   - **Impact:** Medium · **Effort:** Small
   - **Proposed fix:** Let Standard past-question practice rank mastered topics too; retain mastery-based exclusion for Urgent triage.
   - **Evidence:** Past questions always uses Urgent triage. A direct check with one mastered type returned `drill: []` and “Nothing to drill: every question type is mastered,” preventing requested revision.

4. **Finding:** Quiz logs cannot contribute to the cram bill.
   - **Location:** `skills/mimir-quiz/SKILL.md:25`; `skills/mimir-quiz/SKILL.md:40`; `scripts/session.py:497`
   - **Impact:** Medium · **Effort:** Small
   - **Proposed fix:** Use `date -Iseconds` for quiz start/end timestamps, append `ended:`, and record first contact when absent.
   - **Evidence:** Quiz specifies `started: <YYYY-MM-DD HH:MM>` and never writes `ended:` or `first_contact:`. The session parser rejects that timestamp: `started must be YYYY-MM-DD or an ISO datetime`.

5. **Finding:** Standalone practice does not maintain the state required for course continuation and debrief.
   - **Location:** `skills/mimir-past-questions/SKILL.md:21`; `skills/mimir-quiz/SKILL.md:40`; `scripts/session.py:472`
   - **Impact:** Medium · **Effort:** Small
   - **Proposed fix:** Share a minimal close routine that updates `last_session` and initializes `pending_debrief` for quiz and Standard past-question sessions.
   - **Evidence:** Both flows finish without those save updates. `debrief_state()` immediately returns `(None, None)` without a pending value, so a student using only these commands cannot run the advertised post-exam debrief; automatic course selection also ignores their recent practice.

6. **Finding:** Urgent past-question verification has conflicting batch ownership.
   - **Location:** `skills/mimir-past-questions/SKILL.md:17`; `skills/mimir-past-questions/SKILL.md:19`; `skills/mimir-study/references/urgent.md:39`
   - **Impact:** Medium · **Effort:** Trivial
   - **Proposed fix:** Branch before gating: Standard gates real items; Urgent prepares worked/check pairs and gates them once through the shared drill.
   - **Evidence:** Step 6 already gates all real items. Step 7 then requires practice checks “gated in the same batch” and invokes urgent §3, which prepares and gates the whole set again. The prescribed sequence cannot satisfy both instructions as written.

7. **Finding:** Retake validation allows links to later terms within the same year.
   - **Location:** `scripts/fingerprint.py:413`
   - **Impact:** Low · **Effort:** Small
   - **Proposed fix:** Compare full term ordering using the existing Spring/Summer/Fall ordering, preferably through one shared helper.
   - **Evidence:** Validation rejects equal terms and later **years** only: `int(prior_term[:4]) > int(term[:4])`. Thus `2026-Spring` can link to `2026-Fall`, contradicting the “earlier term” invariant and permitting chronological cycles.

8. **Finding:** The third “I know this” question cannot affect the outcome.
   - **Location:** `skills/mimir-study/references/session.md:68`
   - **Impact:** Low · **Effort:** Trivial
   - **Proposed fix:** Remove the third-question branch under the current all-correct pass rule.
   - **Evidence:** One right and one wrong triggers a third question, but passing requires “every one was right without a hint.” Once a wrong answer exists, the third question cannot produce a pass.
