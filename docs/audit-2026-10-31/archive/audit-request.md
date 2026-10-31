# Original audit request

Launch **5 subagents in parallel** to audit the current skill for quick wins, bugs, inefficiencies, and practical improvements.

### Agent allocation

1. **OpenAI Agent 1 — Architecture & Logic**
   - Inspect the skill's structure, logic, and overall implementation.
   - Identify bugs, unnecessary complexity, and architectural weaknesses.
   - Suggest simple, high-impact fixes.

2. **OpenAI Agent 2 — Performance & Reliability**
   - Look for performance bottlenecks, redundant operations, edge cases, and error-handling gaps.
   - Identify opportunities to improve reliability and efficiency.
   - Prioritize low-risk, high-value changes.

3. **Anthropic Agent 1 — Opus 5.5 (Medium Effort)**
   - Perform a targeted review of the skill's design and implementation.
   - Focus on the 3–5 highest-impact improvements.
   - Avoid exhaustive exploration to conserve tokens.

4. **Anthropic Agent 2 — Sonnet 5.5 (Medium Effort)**
   - Review clarity, maintainability, instructions, and potential mistakes.
   - Look for easy fixes and overlooked edge cases.
   - Keep the investigation and final report concise to minimize usage.

5. **Google Agent 1 — Independent Audit**
   - Independently examine the skill for overlooked issues, inconsistencies, and improvement opportunities.
   - Challenge assumptions made by the implementation.
   - Identify additional quick wins.

### Execution rules

- Run all five agents concurrently using T3 Code's subagent capabilities.
- Give every agent access to the relevant skill files and necessary project context.
- Keep each agent within its assigned scope to reduce redundant work.
- **Analysis only:** Do not modify any files during this audit.
- Prioritize concrete, actionable findings over speculative refactors.
- Do not recommend unnecessary rewrites or changes that add complexity without clear benefit.
- Anthropic agents should use tightly scoped investigations and concise responses to conserve usage.

### Reporting protocol

Every subagent must report its findings **back to the original/orchestrating agent**, not directly to the user.

Each report must include:

- **Finding:** What is wrong or could be improved.
- **Location:** Relevant file and line number, where applicable.
- **Impact:** High / Medium / Low.
- **Effort:** Trivial / Small / Moderate.
- **Proposed fix:** Specific implementation recommendation.
- **Evidence:** Why the finding matters.

### Orchestrator responsibilities

After all five subagents return:

1. Collect and review every report.
2. Deduplicate overlapping findings.
3. Resolve conflicting recommendations using code evidence.
4. Rank improvements by **impact, implementation effort, risk, and confidence**.
5. Separate quick wins from larger architectural changes.
6. Produce one consolidated, prioritized action plan.

Present the final findings in a table:

| Priority | Finding | File / Location | Impact | Effort | Recommended Fix |
|---|---|---|---|---|---|

Conclude with the **top 5 quick wins** that provide the greatest benefit for the least implementation effort.

**Do not implement fixes until the orchestrating agent has completed the review and presented the consolidated recommendations.**
