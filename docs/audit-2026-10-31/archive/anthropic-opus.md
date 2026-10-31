# Original report: anthropic-opus

Source: <t3-thread://v2/4c5bcb11-81b0-41c1-95df-d92fe94a74a7/thread:delegated-task:command%3Amcp%3A135b902e-d7b3-42f5-997f-5cb0739fa9c2%3Adelegate-task%3A16bf01c9-a224-4c50-81e7-7f71b8904592>

Historical agent report, not a new verification. Findings may overlap or disagree; use the consolidated findings and accepted decisions for implementation.

Five design findings, highest impact first. I read the files only; nothing was changed or committed.

**1. A "quote" claim lets an answer key skip the checker**
- Location: `scripts/verify.py:240-244` (and `:263`); used by `skills/mimir-quiz/SKILL.md:21`
- Impact: High · Effort: Small
- Finding: If an item says its key is a direct quote from professor material, the gate sets `needs=False` and the item goes straight to `show` with `counts_for_mastery` true. The gate only checks that the cited file is a text-readable professor file covering that page. It never checks that the key matches what that page says. The generating model makes the claim and nobody verifies it, which breaks the README promise that answer keys are checked before you see them.
- Evidence: `needs = not (row is not None and row[2] == "text" and row[0] in _QUOTE_ROLES)` … `decision = "verify" if needs else "show"`
- Proposed fix: Make the gate pull the quoted page through `pdftext.py` and check that the key text appears on it after normalising whitespace. If that's too much, still send quote items to the verifier, with a cheaper "confirm the quote" instruction. Never let an item reach `show` with an empty verdict list.

**2. Mastery is edited by hand from five copies of the rules; it should go through one script**
- Location: `skills/mimir-quiz/SKILL.md:38`, `skills/mimir-study/references/session.md:60-64`, `session.md:68`, `skills/mimir-study/references/urgent.md:56`, `skills/mimir-study/references/teaching.md:53`, plus `skills/mimir-past-questions/SKILL.md:20`, which points to session.md
- Impact: High · Effort: Moderate
- Finding: `fingerprint.md` and `forecast.md` can only change through scripts (`skills/mimir-core-rules/SKILL.md:68-69`). `mastery.md` is the data behind "remembers you", yet each skill edits it by hand from its own copy of the rules. The column order, the `|` escaping, the "+1" counts and the "mastered stays mastered" exception are all re-implemented in prose each time. The copies already disagree on the frustration rule (item 4).
- Evidence: `Edit the topic's mastery.md line (add it if missing; keep the column order; escape |)`. This text appears in session.md, urgent.md and teaching.md, and quiz has its own version.
- Proposed fix: Add `session.py record` taking `{term, course, topic, gate_result, outcome: unassisted|assisted|wrong|override, evidence, date}`. It should apply the status change, refuse when `counts_for_mastery` is false, and write the row. Each skill replaces its prose rules with one call to it. Add tests for the status changes.

**3. Status reflects only the latest answer, so it is weak evidence of mastery**
- Location: `skills/mimir-study/references/session.md:61-63`, `skills/mimir-quiz/SKILL.md:38`, `assets/templates/mastery.md`
- Impact: High · Effort: Small, once item 2 exists
- Finding: One correct unassisted answer to a single generated practice question sets `mastered`. The study route then skips that topic (`session.md:70`). One wrong answer drops a `mastered` topic to `gap`. The `assisted` and `unassisted` counts are kept but nothing uses them. The `evidence` cell holds only the most recent event, so `mimir-progress` cannot show the history the README promises ("dated evidence of what you solved alone and with help").
- Evidence: `right without a hint: unassisted +1, status mastered` … `wrong: status gap.`
- Proposed fix: Compute status inside `record`. For example, `mastered` needs at least 2 unassisted solves on different items, at least one on a separate day or one on a real past-paper question. One wrong answer on a mastered topic gives `shaky`, not `gap`. Keep the 2-3 most recent evidence entries, each dated.

**4. The frustration-override rule contradicts itself**
- Location: `skills/mimir-core-rules/SKILL.md:51` vs `skills/mimir-study/references/session.md:64` and `skills/mimir-study/references/teaching.md:52`; `mimir-quiz` ignores it
- Impact: Medium · Effort: Trivial
- Finding: Core rules say solves after an override never count. session.md limits this to the rest of the session. The student is told "stays marked shaky until you solve one on your own". Quiz never reads the `frustration_override` column, so the next quiz can set `mastered` straight away.
- Evidence: core: `solves after a frustration_override never count toward mastery` / session.md: `no answer on it changes mastery.md for the rest of the session`
- Proposed fix: Pick one rule. Likely: the override blocks counting for the rest of that session, and the next unassisted solve in any later session lifts it. Write it once in core rules and enforce it in `record` using the stored override date.

**5. Without a verifier agent, the model checks its own answer keys**
- Location: `skills/mimir-core-rules/SKILL.md:16`; `skills/mimir-core-rules/references/verified-items.md:8`
- Impact: Medium · Effort: Small
- Finding: In Codex and Antigravity, the same model, in the same context, re-checks keys it just wrote. The only safeguard is "as if you had not written the key". The gate counts those verdicts the same as independent ones, and nothing in the log shows which kind of check ran. Yet the README lists both agents as "Tested" and promises checked keys.
- Evidence: `As the checker, solve each item fresh from the sources, as if you had not written the key.`
- Proposed fix: Use the agent's own subagent feature where it has one (Codex has native agent spawning). Otherwise, add a `checker: self` line to the session log and say once that this check is less independent. Optionally, have the gate accept `checker: "self"` and record it in `disagreements` and in the mastery evidence.
