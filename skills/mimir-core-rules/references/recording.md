# Recording mastery

Call `python3 <mimir>/scripts/session.py record` with one JSON object on stdin:
`{"term":"2026-Fall","course":"CS201 Theory","topic":"Heaps","item":"paper.pdf:p3:q2","gate":{"decision":"show","counts_for_mastery":true,"label":"[real: past-papers/paper.pdf, p.3]"},"outcome":"unassisted","real_past_paper":true,"session":"unique-session-id","date":"2026-10-31","log":"2026-10-31-0900"}`.

Use the actual final gate result, stable item identity (same question keeps the same identity), and one unique session identity reused throughout this session. Use the date from `session.py now` and this session's log name (its `log_name`, the log the session created at its start). Outcomes are `unassisted | assisted | wrong`; Urgent drill correct answers are always assisted. Knowledge-gauge answers (core rules' Knowledge gauge) are the exception in both classes: right is always unassisted, wrong is wrong. Set real_past_paper only for an actual past-paper question, not generated practice or a worked example.

The item identity is shown in the log, so let it name the kind of question: `gauge:<topic>:N`, `quiz:N`, `urgent:<type>:N`, `practice:<topic>:N`, or `<paper>:p<page>:<question>` for a real question.

For a frustration override add `override: true` and use outcome assisted; this is a control event, not a counted solve. For an explanation without a gated item add `explanation_only: true` and pass decision drop and counts_for_mastery false. Retrying the same session/item/event is idempotent. Standard retries: record every try on an item. Within one session the first wrong answer on an item is recorded once (later misses return `duplicate`), and a right answer after it records as assisted, even when sent as unassisted.

`record` writes the outcome line under `## Results` in the session log itself; make no log edit for an answer. Its lines: `- <item> <label> (<topic>): <unassisted solve|assisted solve|wrong>`, `- <topic> frustration override: answer given`, and `- <item> <label> (<topic>): after frustration override, not counted`. A `duplicate` result, a retried call and an item without a correct check write no line. Only lines with no `record` call (`not reached` for a shown question the student never answered) are written by the skill, under `## Results`.

Print or use the returned status; never invent evidence. Subsequent answers in the override session do not count. A later unassisted answer lifts the block but still needs D2 evidence to promote.

Use `session.py check` or `progress` for current status and evidence. The Markdown file preserves legacy rows and notes; the recorder-owned state supersedes those rows. Only record changes mastery; initialization may create an empty table.
