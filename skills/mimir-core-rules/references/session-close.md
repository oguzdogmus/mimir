# Shared session close

Used by study, quiz and past-question sessions, only when the student asks to end the session (Ending a session in core rules), including after zero items. Use file read/write/edit tools for memory changes.

1. Run `session.py now` with `{}`, then `session.py close` with `{"now": "<its now>", "term": "<term>", "course": "<course>", "log": "<log name>", "started": "<S>"}`. It appends `ended: <now>` to this session's `started: <S>` block once and reports the session length (`minutes`); when the block already has its `ended:` stamp it writes nothing and returns that stamp (`already_closed` true). Never write an `ended:` line yourself. Use its `last_session` for save.md.
2. Read save.md. Edit only last_session and pending_debrief, preserving its other fields and template. Set pending_debrief to <start.exam_date> <start.exam_name, else exam> only when it is empty or no and start.exam is set; preserve an existing pending exam. A repeated close after both writes is a no-op.
3. Read the current log. Preserve every existing first_contact line. If start.first_contact was null and this session log has none, add first_contact: <S> once. Append any gate disagreements not already logged under ## Verifier disagreements, verbatim.

If interrupted between the log and save edits, run this close again: `session.py close` returns the stored stamp and its `last_session`, so the missing save edit uses the existing end time, never a new one. Completion means one ended stamp for this start, the matching last_session, and a preserved or newly set pending_debrief.
