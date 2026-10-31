# Recording mastery

Call `python3 <mimir>/scripts/session.py record` with one JSON object on stdin:
`{"term":"2026-Fall","course":"CS201 Theory","topic":"Heaps","item":"paper.pdf:p3:q2","gate":{"decision":"show","counts_for_mastery":true,"label":"[past paper]"},"outcome":"unassisted","real_past_paper":true,"session":"unique-session-id","date":"2026-10-31"}`.

Use the actual gate result, stable item identity (same question keeps the same identity), and one unique session identity reused throughout this session. Use the date from `session.py now`. Outcomes are `unassisted | assisted | wrong`; Urgent correct answers are always assisted. Set real_past_paper only for an actual past-paper question, not generated practice or a worked example.

For a frustration override add `override: true` and use outcome assisted; this is a control event, not a counted solve. For an explanation without a gated item pass decision drop and counts_for_mastery false. Retrying the same session/item/event is idempotent.

Print or use the returned status; log refusals without inventing evidence. Subsequent answers in the override session do not count. A later unassisted answer lifts the block but still needs D2 evidence to promote.

Use `session.py check` or `progress` for current status and evidence. The Markdown file preserves legacy rows and notes; the recorder-owned state supersedes those rows. Only record changes mastery; initialization may create an empty table.
