# Accepted decisions

Accepted by the user on 2026-10-31 after the eight-step proposal: “I agree to your reccomendations on the suggestions”.

| ID | Decision | Applies to |
|---|---|---|
| D1 | If no outline supplies a route, use topics in INDEX.md in ingestion order. Distinguish no topics from all topics mastered. Preserve an existing route. | Step 2; finding 2 |
| D2 | Mastered requires at least two unassisted solves on different items, with at least one on a separate day or on a real past-paper question. One wrong answer on a mastered topic produces shaky, not gap. | Step 6; finding 16 |
| D3 | Keep disable-model-invocation on setup and ingest. Remove it and model: haiku from read-only help; clarify invocation instructions in README. | Step 5; finding 13 |
| D4 | Follow the staged implementation approach, one reviewable branch/PR per step, starting from main after prerequisites merge. | All steps |
| D5 | Use the proposed frustration rule: solves during the override do not count for the rest of that session; an unassisted solve in a later session lifts the block. Lifting the block does not itself satisfy D2. | Steps 5–6; finding 7 |

D1–D3 were the three explicit questions in the prior proposal. D4–D5 capture the accepted overall recommendations. The current request is to save documents and make handoff easy; implementation has not begun.

## Implementation boundaries

- Favor small, evidence-backed changes. Do not rewrite the plugin.
- Preserve unrelated working-tree changes and existing user/course data.
- Reproduce relevant findings before fixing them. If current code already fixes a finding, document the evidence instead of duplicating the work.
- Do not ask again about D1–D3. Resolve routine implementation choices from the code and these decisions.
- D2 still needs explicit test cases for distinct items, dates, helped attempts, frustration overrides and repeated attempts. Choose a deterministic interpretation consistent with D2 and record it.
- Step 8 contains alternative technical approaches, not a mandate to implement all alternatives. Inspect host capabilities and filesystem behavior first; document the chosen approach and remaining limitations.
- Missing live host/OS access is a validation gap, not a passing result.
