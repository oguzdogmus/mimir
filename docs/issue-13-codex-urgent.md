# Codex Urgent attachment baseline — 2026-11-01

Host: Codex CLI 0.166.0 through T3; parent GPT-6 Astra, independent native
verifier GPT-6.1 Terra. This is an agent-led acceptance exercise through the
real command handlers, with a synthetic paper, not a real student's session.

Isolation: workspace.DEFAULT_ROOT and POINTER_PATH set in each Python
process to /tmp/mimir-13-codex-urgent-zz0ue_4v/learning and its sibling pointer.
No global HOME change. Actual JSON outputs remain in that directory's
evidence.json; the filed PDF and session log remain available for inspection.

Observed sequence:
1. session now: 2026-11-01T13:32:24+02:00. Initial start reported no workspace.
2. parse-date "tomorrow": 2026-11-02. Class: Urgent, floor, output
   "Urgent delivery: exam in 10 hours".
3. Before filing, pdftext read the explicitly scoped outside-root CS201.pdf:
   "CS201 Theory - Q1: What is 2 plus 2? [4 marks]".
4. Classified from that output as CS201 Theory, past-papers; used current
   term 2026-Fall. Filed successfully (action moved), indexed one text PDF
   and Addition at page=1, wrote fingerprint from its printed 4 marks.
5. Edited exam row; restarted session: Urgent. Triage: "Drilling: Addition."
6. Gate returned verify for real Q1 and one generated addition check.
7. Native independent verifier actually read the filed PDF via pdftext:
   - 1 | correct | fake-real no | Q1 appears on p.1 and 2 plus 2 is 4
   - 2 | correct | fake-real no | 2 plus 3 is 5
8. Final gate returned show for both, preserving real/practice labels.
   The actual session log records checker: independent and the native tool.

First drill content authorized by final gate:
[real: past-papers/CS201.pdf, p.1]
Q1: What is 2 plus 2? [4 marks]
Worked answer: 4.
[practice, not from a real paper]
What is 2 plus 3?

Limits: the date/class/read/file/index/fingerprint/triage/gate and independent
check sequence ran live. This fixture exercise does not establish that an
unprompted conversational skill invocation will always emit the class line
first; the content above is recorded test output, not a student transcript.
No student answer or session-close behavior was tested. Same-context fallback
was not used because native independence was available.
