# Shared session close

Used by study, quiz and past-question sessions, including zero items and early stop. Use file read/write/edit tools for memory changes.

1. Read the current log and save.md. For this session's started: <S> block, reuse its ended: stamp if present; otherwise run session.py now with {} and append ended: <its now> once. Keep the ISO timestamp exactly as returned. Use that same closing result's last_session for save.md; on a repeated close preserve the already saved last_session.
2. Edit only last_session and pending_debrief in save.md, preserving its other fields and template. Set pending_debrief to <start.exam> <start.exam_name, else exam> only when it is empty or no and start.exam is set; preserve an existing pending exam. A repeated close after both writes is a no-op.
3. Preserve every existing first_contact line. If start.first_contact was null and this session log has none, add first_contact: <S> once. Append any gate disagreements not already logged under ## Verifier disagreements, verbatim.

If interrupted between the log and save edits, finish the missing save edit using the existing ended timestamp formatted as YYYY-MM-DD HH:MM (its own local date/time), without obtaining a new end time. Completion means one ended stamp for this start, the matching last_session, and a preserved or newly set pending_debrief.
