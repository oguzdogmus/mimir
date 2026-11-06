#!/usr/bin/env python3
"""Mimir session runner: every date and clock decision a study session needs.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py``, ``ingest.py`` and ``plan.py`` (same folder). Run as::

    python3 session.py <now|parse-date|start|check|close|gauge|debrief|progress|record|prefs|pref-event|scope>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Only record (mastery.md), close and gauge (a session log), pref-event
(``.state/preferences.json``), scope (``scope.md``) and start with ``lasting``
(``save.md``) write, atomically; other commands are read-only. Only ``now``
reads the clock; every other subcommand takes "now" as an input (``now``, from
``session.py now``), so the same input and files always give the same output.

Datetimes are ISO 8601 with a time, as ``plan.py`` takes them
(e.g. "2026-10-17T09:00:00+03:00"). "Today" is ``now``'s own calendar date.

Files read (all inside the learning root, see ``workspace.py``)
---------------------------------------------------------------
* ``.state/profile.md``: ``## Exam dates`` rows ``| CODE | exam | date |``
  and ``## Active courses`` rows ``| CODE | YYYY-Term/CODE Name |``. The
  date cell is one of: ``unknown`` (date unknown); ``YYYY-MM-DD`` (time
  unknown); ``YYYY-MM-DD time unknown`` (time unknown, already asked for once
  more); a date with a time, ``YYYY-MM-DD HH:MM[:SS]`` or ``YYYY-MM-DDTHH:MM[:SS]``,
  optionally followed by ``Z`` or a ``+HH:MM``/``-HH:MM`` offset (no offset:
  ``now``'s offset). Case and extra spaces are ignored. Any other cell of the
  course is unreadable and reported in ``exam_problems``, never skipped silently.
* ``.state/preferences.json``: the global teaching settings, written only
  by ``pref-event``. Before it exists, ``dial_preference:`` in the profile
  (set unless empty, ``none`` or a ``<...>`` placeholder) is the legacy value.
* ``<course>/.state/save.md``: ``last_session:`` (``YYYY-MM-DD HH:MM`` or
  ``YYYY-MM-DD``), ``next_topic:``, ``pending_debrief:`` (``YYYY-MM-DD
  <exam name>``; ``no``, empty or anything else means none pending) and
  ``delivery_choice:`` (``Standard|Urgent YYYY-MM-DD <exam name>``, the
  lasting choice ``start`` saves; anything else means none).
* ``<course>/.state/mastery.md``: the table ``| topic | status | evidence |
  evidence_date | last_check | assisted | unassisted | frustration_override |``.
  Columns are found by header name (topic, status, evidence, evidence_date,
  last_check, assisted, unassisted, frustration_override); the first row of a
  topic wins. A status other than gap, shaky or mastered counts as unseen; a
  count that is not a whole number counts as 0; an ``evidence_date`` or
  ``last_check`` that is not a valid date is reported as null; ``evidence``
  and ``frustration_override`` are the cell text, trimmed.
* ``<course>/.state/scope.md``: exam scopes, written only by ``scope``. One
  section per exam, ``## YYYY-MM-DD <exam name>``, then ``words: <the
  student's words>`` and one ``- in: <name>``, ``- out: <name>`` or ``-
  unsure: <name>`` line per question type or topic. Other lines are ignored.
* ``.state/scope.md`` (in the learning root): exam scopes noted at setup,
  before the course had a folder, written only by ``scope`` with ``code``.
  Sections as in the course ``scope.md``, plus a ``code: <CODE>`` line;
  only ``words`` is kept (no lists).
* ``<course>/.state/fingerprint.md``: the ``## Question types`` names (the
  type cell before ``(source:``, ``(tentative)`` or ``(prior term)``), for
  ``start``'s ``scope.new``.
* ``<course>/INDEX.md``: the ``## Registry`` roles and ``## Topics`` names
  (``ingest.py`` rules; a non-UTF-8 one exits 2) for the route.
* ``<course>/.state/logs/*.md`` (name order): the first ``first_contact:``
  line whose value is a date or datetime (``plan.py`` rules); for ``debrief``
  and the first ``gauge_done:`` line whose value is a date or datetime (the
  gauge-done marker); for ``debrief``
  also ``started:``/``ended:`` datetimes, ``- `` lines under ``## Verifier
  disagreements``, and ``next_course_offer:`` lines in every course of the
  term. Symlinked, unreadable or non-UTF-8 logs are skipped.
* A ``save.md`` or ``mastery.md`` that is itself a symlink reads as empty.
  Unreadable or non-UTF-8 files of courses other than the chosen one, and
  unreadable logs, are skipped. A course whose term, course or ``.state``
  folder is a symlink is never picked (naming it exits 2).

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
now -- the local time, the one clock read of a session. Standard library only,
    so the same on Linux, macOS and Windows.
    in : {}
    out: {"now": "2026-10-17T09:05:07+03:00", "date": "2026-10-17",
          "log_name": "2026-10-17-0905", "last_session": "2026-10-17 09:05",
          "term": "2026-Fall", "line": "Now: 2026-10-17T09:05:07+03:00."}
    ``now`` is ISO 8601 to the second with the local UTC offset (the session
    timestamp); ``date`` the evidence date; ``log_name`` the log file name
    without ``.md``; ``last_session`` the ``save.md`` stamp; ``term`` the
    fallback term by month: Jan-May Spring, Jun-Aug Summer, Sep-Dec Fall.

parse-date -- the student's exam date-and-time phrase as an exam value, or a refusal.
    in : {"now": "2026-10-17T09:00:00+03:00", "phrase": "12:30 Friday"}
    out: {"date": "2026-10-23", "time": "12:30", "exam":
          "2026-10-23T12:30:00+03:00", "line": "Exam: 2026-10-23 at 12:30."}
    Without a time: {"date": "2026-10-23", "time": null, "exam":
    "2026-10-23", "line": "Exam date: 2026-10-23."}. ``exam`` is the value
    for the ``## Exam dates`` cell (a time is at ``now``'s offset).
    Only these date phrases, ignoring case and extra spaces: ``YYYY-MM-DD``;
    ``today``; ``tomorrow``; a full English weekday name (``friday``), the
    next such day counting today, so today's own weekday name means today;
    ``N days`` or ``in N days`` (N a whole number). Today is
    ``now``'s own calendar date. A time may come before the date phrase or
    after it (optionally after ``at``): ``H:MM`` or ``HH:MM`` (24-hour), or
    with ``am``/``pm`` (``2pm``, ``12:30 am``). This is not natural-language
    date parsing: anything else ("Nov 5", "5/11", "next friday", "fri",
    "noon", a time alone) exits 2 as unsupported. A date that does not exist,
    a time that does not exist, a date before today, a time not after ``now``,
    or a date more than plan.MAX_HORIZON_DAYS days after today also exits 2.

start -- pick the course, the exam and the class for a new session.
    in : {"now": "2026-10-17T09:00:00+03:00"}
         optional "course" (a course folder name, e.g. "CS201 Theory") and
         "term" (YYYY-Term). A term alone limits the pick to that term; a
         course name found in several terms needs its term. Optional
         "choice" ("Standard" or "Urgent"): the student's choice of class,
         for this session only; with "lasting": true, for every session
         until the picked exam passes.
    out: {"root": "/home/u/learning", "courses": [{"term": "2026-Fall",
          "course": "CS201 Theory", "course_dir": "..."}], "term":
          "2026-Fall", "course": "CS201 Theory", "course_dir": "...",
          "code": "CS201", "inferred": true, "exam": "2026-11-05",
          "exam_date": "2026-11-05", "exam_name": "final", "q0": false, "exam_problems": [],
          "ask_exam_time": false, "ask_exam_ahead": false, "ask_exam_scope": false,
          "remaining": [{"name": "Heaps", "status": "gap", "scope": null},
          {"name": "Graphs", "status": "unseen", "scope": null}],
          "class": {<plan.py class output>},
          "topic": {"name": "Graphs", "status": "unseen", "evidence_date":
          null, "stale": false, "attempt_first": false}, "route_line": null, "first_contact":
          "2026-10-10T20:00:00+03:00", "scope": null,
          "gauge": {"done": false, "topics": ["Graphs"]},
          "line": "Standard delivery: exam in 19 days"}
    (``class`` here includes "decided_by": "exam date".)
    Course: the given one (``inferred`` false); else the latest ``save.md``
    ``last_session:`` (ties: first by course name); else the first ``##
    Active courses`` row whose folder exists; else the last course in
    term/name order (year, then Spring < Summer < Fall < other words
    alphabetically, then course name). ``code`` is the first word of the
    course name. Exam: the earliest upcoming ``## Exam dates`` row for
    ``code``: a date-only row dated today or later (ordered as 00:00 that day),
    or a row with a time after ``now``. ``exam`` is ``YYYY-MM-DD`` for a
    date-only row, else the ISO datetime at ``now``'s offset (as ``plan.py``
    takes it); ``exam_date`` is its calendar day. With none, when a row for
    ``code`` says ``unknown``, exam null with ``q0`` false; else exam null with
    ``q0`` true (ask "When's the exam?"). Rows more than plan.MAX_HORIZON_DAYS days ahead are ignored like
    past ones. ``exam_problems``: the unreadable cells of ``code``, as
    [{"exam", "date"}] in file order. ``ask_exam_time``: the exam is date-only,
    not marked ``time unknown``, and at most TIME_ASK_DAYS days ahead (ask for
    its time once more). ``ask_exam_ahead``: the exam is date-only and today
    (ask whether it is still ahead). ``scope``: null when ``scope.md`` has no
    section for the picked exam or that section lists no name (scope
    unknown). A section is the exam's when it has the same ``exam_date`` and
    the same name (case and repeated spaces ignored); else, when the exam's
    date or time changed, the first section with the same name whose date no
    ``## Exam dates`` row of ``code`` has under that name any more (the scope
    follows its exam; a passed exam whose row stays keeps its own). Otherwise
    ``scope`` is {"words", "in", "out", "unsure", "new"}, ``new`` being the route
    topics and fingerprint question types in none of the three lists (found
    after the scope was confirmed), route first. Once the exam passes,
    ``start`` picks another exam and that exam's scope (or none) applies.
    ``scope_words``: when the course ``scope.md`` has no section for the
    picked exam, the ``words`` noted at setup for it (root ``scope.md``,
    a section of ``code`` found the same way), else null: the session
    resolves them through the confirm step instead of asking.
    ``ask_exam_scope``: the exam is at most TIME_ASK_DAYS days ahead, the
    course ``scope.md`` has no section for it at all (a saved "don't know"
    counts) and no scope was noted for it at setup.
    Route: ``mastery.md`` rows in order; when the
    ``INDEX.md`` registry has no ``outline`` row, each ``## Topics`` name not
    yet listed (ignoring case and repeated spaces) follows as an unseen row,
    in ``INDEX.md`` order. With a ``scope``, rows named in ``out`` move to the
    end (order kept, none removed). ``remaining`` = route rows not
    ``mastered``, each with ``scope``: "in", "out", "not checked" (in neither
    list) or null (no scope). ``remaining_line``: null when ``remaining`` is
    empty, else "Left on your route:" and one line per entry, in order,
    "- <name> (<status>)", adding ", not on your next exam" for ``out`` and
    ", not checked" for "not checked" (e.g. "- Sorting (gap, not on your
    next exam)"), joined by newlines. ``class``: ``plan.py class`` with ``now`` and the exam only (the
    route's size never decides) plus ``decided_by``, the rule that decided,
    first match wins:
      "session choice" -- ``choice`` without ``lasting``: that class, line
          "<choice> delivery: you asked; <plan.py line after 'delivery: '>",
          e.g. "Standard delivery: you asked; exam in 30 hours". Nothing is saved.
      "lasting choice" -- ``choice`` with ``lasting``, or a saved
          ``delivery_choice:`` whose date is ``exam_date`` and whose name is
          ``exam_name`` (case and repeated spaces ignored): that class, line
          "<class> delivery: you asked, until your <exam_name, else exam>;
          <plan.py tail>". With ``lasting``, ``save.md`` gets the line
          ``delivery_choice: <choice> <exam_date> <exam_name>``, replacing the
          first ``delivery_choice:`` line, else after the last ``key:`` line
          above the first ``##`` heading; an equal line is not rewritten.
          Once that exam passes, ``start`` picks another exam (or none), so the
          saved choice stops applying. ``lasting`` with exam null, or a
          symlinked ``save.md``, exits 2 and writes nothing.
      "exam date" -- otherwise: ``plan.py class`` unchanged.
    ``reason``, ``hours_to_exam`` and ``days_to_exam`` are always the exam
    date's. ``topic``:
    ``save.md`` ``next_topic`` when it is remaining and not ``out`` (unless
    every candidate is), else the first remaining topic; with none remaining, the same pick among the stale mastered topics
    (stale as in ``check``: the one-question recheck); else null. Its
    ``attempt_first`` is as in ``check``. ``route_line``: null when ``topic``
    is set; else "No topics on the route yet: drop the outline, slides or
    past papers into `_inbox/` and run mimir-ingest." for an empty route, or
    "Your route is complete: every topic is mastered in mastery.md. Want a
    `mimir-quiz` to keep it fresh?". ``gauge`` (the knowledge gauge): null when the
    route is empty (no gauge; never gauge from the course name); else ``done``
    (the course has a gauge-done marker, set by ``gauge``) and ``topics``, the
    route's ``unseen`` topic names in route order ([] when done).
    ``line`` is the class line. ``debrief``: null when ``pending_debrief:``
    holds no valid date P; else {"exam", "exam_name", "due", "deferred"}.
    P today or later: P with the pending name, due and deferred false (a
    date-only exam is past only from the next day, as in ``plan.py``). P
    before today: the target exam is the latest ``## Exam dates`` row of
    ``code`` dated after P and before today (a later passed exam supersedes;
    debriefs never stack), else P (named by the pending value, else by a row
    dated P); ``deferred`` = the class (as decided above) is Urgent, ``due`` = not deferred.
    ``preference_session``: true when the class is Standard and no upcoming
    ``## Exam dates`` row of any course is within NEAR_EXAM_HOURS hours of
    ``now``, so the session may give teaching-settings evidence and run a
    probe trial; false for Urgent and for Standard near any exam. A date-only
    exam counts as near when its day is at most NEAR_EXAM_HOURS // 24 days
    after today (some moment of that day is within 48 hours).
    A workspace with no course folder gives
    ``course`` null, every course field null, and the line "No course yet:
    run mimir-setup, then mimir-ingest."

check -- staleness and counts for named topics.
    in : {"now": "...", "term": "2026-Fall", "course": "CS201 Theory",
          "topics": ["Heaps"]}
    out: {"course_dir": "...", "topics": [{"name": "Heaps", "status": "gap",
          "evidence_date": "2026-10-01", "assisted": 1, "unassisted": 0,
          "stale": true, "attempt_first": false}],
          "line": "1 topic checked, 1 stale: Heaps."}
    Topic names match ``mastery.md`` ignoring case and repeated spaces; an
    absent topic is ``unseen``. ``stale`` = status not ``unseen`` and (no valid
    ``evidence_date``, an evidence date in the future, or evidence older than
    STALE_DAYS days). ``attempt_first`` = status not ``unseen``, ``assisted``
    at least ATTEMPT_FIRST_ASSISTED and ``unassisted`` 0 (false for an absent
    topic or one whose status reads as ``unseen``):
    the student tries a practice item before any hint or explanation.

close -- stamp a session's end in its log, once.
    in : {"now": "2026-10-17T10:47:30+03:00", "term": "2026-Fall", "course":
          "CS201 Theory", "log": "2026-10-17-0900", "started": "2026-10-17T09:00:00+03:00"}
    out: {"log": ".../.state/logs/2026-10-17-0900.md", "started": "...", "ended":
          "2026-10-17T10:47:30+03:00", "minutes": 107, "last_session":
          "2026-10-17 10:47", "already_closed": false,
          "line": "Session closed after 107 min."}
    ``log`` is ``session.py now``'s ``log_name``; ``started`` the session's
    ``started:`` value in that log, matched exactly. When that session's block
    (up to the next ``started:`` line) has no ``ended:`` line, appends ``ended:
    <now>`` to the log; when it has one, writes nothing and reports that stamp
    with ``already_closed`` true ("Session already closed after N min."), so a
    session gets one end stamp however often it is closed. ``minutes`` is whole
    minutes from started to ended, rounded down; ``last_session`` the end stamp
    as the ``save.md`` value. Exits 2 when the log is missing or a symlink,
    has no such ``started:`` line, a later session already started in it
    while this one is open, its ``ended:`` line is not a datetime, or ``now``
    is before ``started`` or mixes offset and no-offset with it.

gauge -- set the course's gauge-done marker, once.
    in : {"now": "2026-10-17T09:40:00+03:00", "term": "2026-Fall", "course":
          "CS201 Theory", "log": "2026-10-17-0900"}
    out: {"log": ".../.state/logs/2026-10-17-0900.md", "gauge_done":
          "2026-10-17T09:40:00+03:00", "already_done": false,
          "line": "Knowledge gauge done for CS201 Theory: it will not run again."}
    ``log`` is this session's log name (it must exist). When no log of the
    course has a gauge-done marker, appends ``gauge_done: <now>`` to the log;
    otherwise writes nothing and reports the existing marker with
    ``already_done`` true ("Knowledge gauge already done for <course>.").
    Exits 2 when the course has no topics yet (the route is empty: no gauge, so
    the marker stays unset), or on the ``close`` log errors.

debrief -- what the post-exam debrief needs. Read-only, like the rest.
    in : as ``start`` ({"now": ..., optional "term" and "course"}).
    out: {"term": "2026-Fall", "course": "CS201 Theory", "course_dir": "...",
          "code": "CS201", "inferred": false, "debrief": {"exam":
          "2026-11-05", "exam_name": "final", "due": true, "deferred": false},
          "cram": {<plan.py debrief output>}, "disagreements": ["- item 2:
          ..."], "offer_next_course": true, "line": "Cram bill: ..."}
    ``debrief`` is ``start``'s. Not due: ``cram``, ``disagreements`` and
    ``offer_next_course`` are null and ``line`` says why ("No debrief
    pending for <course>.", "Debrief opens after your <name, else exam> on
    <date>.", "Debrief waits until after your <next exam name, else exam>:
    today is for that.", or, with no next exam, "Debrief waits for a calmer
    session: today is for your exam."; no course: ``start``'s line). Due,
    with target T and previous exam B (the latest row of ``code`` dated
    before T, none when there is none):
    * ``cram``: ``plan.py debrief`` (actual hours studied only) with
      ``first_contact`` (as in ``start``), ``exam`` T and the sessions:
      each log's ``started:`` and the next ``ended:`` after it, kept when the start's own calendar date is after B and on or before T;
      a pair that ends before it starts, overlaps an earlier kept pair or
      mixes offset/no-offset with ``now`` is dropped. ``cram`` is null (line
      "Cram bill: no study sessions logged.") when ``first_contact`` is null,
      after T, or not comparable with ``now``. ``line`` is ``cram.line``.
    * ``disagreements``: distinct non-empty ``- `` lines under ``## Verifier
      disagreements`` (up to the next line starting with ``#``) in logs named
      ``YYYY-MM-DD-HHMM[-suffix].md`` whose date is after B and on or before
      T, in name order.
    * ``offer_next_course``: false when any log of any course in the same
      term has a ``next_course_offer:`` line, else true.

progress -- what Mimir believes the student knows. Read-only; never calls plan.py.
    in : as ``start`` ({"now": ..., optional "term" and "course"}).
    out: {"courses": [<as start>], "term": "2026-Fall", "course": "CS201 Theory",
          "course_dir": "...", "code": "CS201", "inferred": true, "topics": [{"name": "Heaps",
          "status": "mastered", "evidence": "solved heap sort alone",
          "evidence_date": "2026-10-01", "last_check": "2026-10-01",
          "assisted": 0, "unassisted": 1, "frustration_override": "",
          "stale": true}], "counts": {"unseen": 0, "gap": 0, "shaky": 0,
          "mastered": 1}, "table": "| Topic | Status | ...",
          "line": "CS201 Theory: 1 of 1 topics mastered, 0 shaky, 0 gap,
          0 unseen; 1 due a recheck."}
    Course pick, ``inferred`` and errors are ``start``'s. ``topics``: every
    route row (as in ``start``) in order; ``stale`` as in ``check``. ``table``:
    ``| Topic | Status | Evidence | Evidence date | Solved alone / with help |
    Recheck |``, one row per topic, ``-`` for empty evidence or a null date,
    Recheck ``due`` when stale, cells escaped as ``INDEX.md`` cells. ``line``
    ends "; none due a recheck." when no topic is stale. No rows: ``topics``
    [], ``table`` null, line ``start``'s empty-route ``route_line``. No course: ``start``'s line,
    ``courses`` as ``start``'s, every other field null.

record -- persist an eligible answer or a frustration override.
    Required: term, course, topic, item (stable identity), gate (the verifier
    result), outcome (unassisted|assisted|wrong), real_past_paper (boolean),
    session (unique identity), date (YYYY-MM-DD). Optional override and
    explanation_only booleans distinguish control events from item attempts.
    Per session, item and event, the first wrong answer records once (later
    misses return duplicate) and a right answer after it records as assisted.
    Alternatively {term, course, topic, initialize: true} adds an unseen topic.
    Returns status, recorded, duplicate and line. See the shared recording
    reference for examples and audit D2/D5 for exact transition semantics.
    Legacy Markdown is retained; recorder-owned JSON in a trailing comment
    supplies authoritative rows to check, start and progress.

prefs -- the global teaching settings. Read-only.
    in : {}
    out: {"axes": {"support": {"level": "method-first", "provenance":
          "default", "wording": null}, "frequency": {...}, "depth": {...}},
          "saved": false, "sampler": {"open": true, "started": false,
          "remaining": ["support", "frequency", "depth"]}, "trial": null,
          "trial_paused": false, "probe_axes": [], "whats_new": null, "line": "Teaching settings:
          support method-first (default), ..."}
    Axes and levels, more guided to more independent: support example-first,
    method-first, try-first; frequency checks only, key decisions, every
    step; depth next step, why, what-if. Provenance is default, sampler,
    learned, explicit or legacy; ``wording`` is the student's words for an
    explicit value, else null. ``saved`` = ``preferences.json`` exists. Before
    it does, every axis is at its middle level with provenance default, except
    that a set profile ``dial_preference:`` reads as frequency checks only with
    provenance legacy (``## Rung hints`` are ignored). A damaged or symlinked
    ``preferences.json`` exits 2.
    ``sampler`` is the setup sampler: ``remaining`` lists the axes still at
    default, in order, while setup is not done (no ``setup_done:`` date in the
    profile) and the sampler was not skipped, else []; ``open`` = remaining is
    non-empty; ``started`` = some axis has provenance sampler.
    ``trial`` is the one active probe trial across all courses, null when
    none: {"axis", "from" (the saved level), "to" (one level toward more
    independent), "evidence" (the sessions that gave positive evidence)}.
    ``trial_paused``: a trial is running but this output does not belong to
    this session's counted session, so the trial is not applied (teach at the
    saved level): always for ``prefs`` with a trial (the ``session`` event's
    output replaces it in a counted session), and for a ``pref-event`` event
    that names no session; false with no trial.
    ``probe_axes``: the axes a trial may start on now, in order, else [];
    see the session and trial-start events.
    ``whats_new``: the one-time line "New: sessions run until you say 'end
    session'. You can also ask to cram or to study normally." while the seen
    marker is unset and the student used Mimir before (setup is done, or a
    course has a readable ``.state/logs/*.md`` session log, e.g. from a lazy
    setup), else null. A new user has neither when setup or the first study
    session sets the marker, so they never get it.

pref-event -- apply one teaching-settings event and save the state.
    in : {"event": "explicit", "axis": "frequency", "level": "checks only",
          "wording": "ask fewer questions"}
         or {"event": "sampler", "axis": "support", "level": "example-first"}
         or {"event": "sampler-skip"} or {"event": "legacy-import"}
         or {"event": "session", "session": "<S>"}
         or {"event": "trial-start", "session": "<S>", "axis": "depth"}
         or {"event": "positive" | "neutral" | "pushback" | "frustration",
             "session": "<S>"} or {"event": "reopen", "axis": "frequency"}
         or {"event": "whats-new-seen"}
    out: as ``prefs`` plus "changed", with ``saved`` true; line e.g.
         "Saved for every course: guiding-question frequency is now checks only."
    ``explicit``: the student's lasting request sets that axis to that level
    (any distance), provenance explicit, wording kept with spaces collapsed;
    other axes are untouched. ``sampler``: one setup-sampler choice; it
    fills the axis only while that axis is at default (provenance sampler),
    never overwriting a sampler, learned, explicit or legacy value ("Kept:
    ..."), and after a skip changes nothing. The choice that leaves no axis
    remaining says the tentative summary of all three levels.
    ``sampler-skip``: ends the sampler for good; completed choices stay and
    unanswered axes keep their defaults. Both sampler events exit 2 once
    setup is done. ``legacy-import``: saves the state ``prefs``
    shows (the legacy value included) when nothing is saved yet; otherwise
    changes nothing. ``whats-new-seen``: sets the global seen marker, so
    ``whats_new`` is null from then on; allowed before and after setup.
    A state that would not change is not rewritten, so a
    rerun leaves the file byte-identical. An unknown event, axis, or a level
    from another axis exits 2 and writes nothing. An explicit request on the
    axis of the active trial ends that trial (no rejection counted).
    Probe trials. ``<S>`` is the session's ``started:`` datetime (``session.py
    now``'s ``now``, with its offset); a session is one ``started:`` record.
    ``session``: run once per session that ``start`` gives
    ``preference_session`` true; it counts one eligible Standard session
    (a rerun changes nothing; an earlier session than the last counted one
    exits 2). Continuing an active trial uses that session's one probe.
    Every other event naming a session exits 2 unless it is the counted
    session, so Urgent and near-exam sessions give no evidence, run no probe
    and do not advance cool-downs. ``trial-start``: starts one trial, one
    level toward more independent on ``axis``; exits 2 when the axis is not
    in ``probe_axes``: a trial is running, the session already had its probe,
    the axis is explicit (never probed) or already at its most independent
    level, or its transition is cooling down or stopped. ``positive``:
    positive evidence for the trial; a session counts once, and a session on
    the same calendar day as earlier evidence adds nothing. Evidence from
    ADOPT_SESSIONS sessions on different days adopts the trial: the axis
    moves to ``to`` with provenance learned ("Saved for every course: ...").
    ``neutral``: nothing counts or resets. ``pushback``: rejects the trial at
    once; the saved level never moved, so nothing reverts in the file, and
    its evidence is dropped. Rejections count per transition: after the
    first, the next eligible session is skipped; after the second, the next
    two; the third stops it. ``reopen``: the student's explicit request
    clears the rejections of the axis's next transition (exits 2 for an
    explicit axis or one at its most independent level). positive, neutral
    and pushback exit 2 with no trial running. ``frustration``: the
    frustration override gave the answer in this session; the second
    session with one (not counted near an exam) returns ``offer`` true and
    the line "Want fewer questions from now on?", once ever, unless frequency
    is already checks only; otherwise ``offer`` false. The saved state is
    closed: levels, provenance, wording of explicit values, the trial,
    rejection counts with the next eligible session index, the eligible
    session counter, the frustration count and the sampler-skipped and
    what's-new-seen markers; never free-text notes.

scope -- save the confirmed scope of one exam.
    in : {"now": "...", "term": "2026-Fall", "course": "CS201 Theory",
          "exam_name": "midterm", "exam_date": "2026-11-05", "words": "the
          midterm covers sessions 1-19", "in": ["DFA construction"], "out":
          ["PDA construction"], "unsure": []}
    out: {"course_dir": "...", "exam_name": "midterm", "exam_date":
          "2026-11-05", "scope": {"words": "...", "in": [...], "out": [...],
          "unsure": []}, "changed": true, "line": "Scope of your midterm on
          2026-11-05 saved: 1 in, 1 out."}
    At setup, before the course has a folder: {"now", "code" (the course
    code, one word, instead of ``term`` and ``course``), "exam_name",
    "exam_date", "words"} notes the student's words in the root
    ``.state/scope.md`` (``in``, ``out`` and ``unsure`` must be empty;
    ``course_dir`` null; line "Scope of your <name> on <date> noted: you
    confirm it at your first study session, once the course files are in.").
    ``start`` reports them as ``scope_words`` until the course has a section
    for that exam. Giving ``code`` with ``term`` or ``course`` exits 2.
    ``exam_name`` and ``exam_date`` are ``start``'s for that exam: the
    ``## Exam dates`` row of the course code with that name (case and repeated
    spaces ignored; null for an unnamed row) whose calendar day is
    ``exam_date``. ``words``: the student's words, one line, at most
    MAX_WORDING characters. ``in``, ``out`` and ``unsure`` (each optional,
    default []): one-line names of at most MAX_SCOPE_NAME characters, spaces
    collapsed, repeats dropped; a name in two lists exits 2. The section of
    that exam (found as in ``start``, so a section saved before the exam
    moved is moved to the new date) is replaced whole, else appended; other
    exams' sections are kept. All three lists empty saves "scope unknown" (``start`` then gives
    ``scope`` null and ``ask_exam_scope`` false; line "Scope of your <name> on
    <date>: unknown, saved so it is not asked again."). A save that would not
    change the file is not written (``changed`` false). No such exam row, a
    symlinked ``scope.md``, or an unknown course exits 2 and writes nothing.

Exit codes: invalid input (bad field, unknown course, no workspace) exits 2
with one line on stderr (``session.py: <message>``) naming the field, and
nothing on stdout. An unexpected internal error exits 1 with ``session.py:
internal error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import re
import json
import sys
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path

import ingest
import plan
import workspace
from workspace import InputError, _check_keys, _has_control, _short, parse_segment, parse_term

STALE_DAYS = 14
ATTEMPT_FIRST_ASSISTED = 3

NO_ROUTE_LINE = ("No topics on the route yet: drop the outline, slides or past papers into `_inbox/` "
                 "and run mimir-ingest.")
ROUTE_DONE_LINE = ("Your route is complete: every topic is mastered in mastery.md. "
                   "Want a `mimir-quiz` to keep it fresh?")

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")  # date.weekday() order
STATUSES = ("unseen", "gap", "shaky", "mastered")
_EXAM_TABLE = ("Exam dates", ("course", "exam", "date"))
_ACTIVE_TABLE = ("Active courses", ("course", "path"))
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_EXAM_AT = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[T ]([0-9]{2}:[0-9]{2}(?::[0-9]{2})?)(Z|[+-][0-9]{2}:[0-9]{2})?")
_LAST_SESSION = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?: ([0-9]{2}:[0-9]{2}))?")
_COUNT = re.compile(r"[0-9]+")
_RELATIVE = re.compile(r"(?:in )?([0-9]+) days?")
_MASTERY_COLUMNS = ("topic", "status", "evidence", "evidence_date", "last_check", "assisted", "unassisted",
                    "frustration_override")


# --- Inputs ------------------------------------------------------------------------

def _moment(data: dict, field: str) -> datetime:
    """A datetime with a time; plan.py's parser, its errors as workspace.InputError."""
    if data.get(field) is None:
        raise InputError(f"{field} is required (a datetime from `session.py now`)")
    try:
        return plan.parse_moment(data[field], field, need_time=True)
    except plan.InputError as exc:
        raise InputError(str(exc)) from None


def _plan(fn, payload: dict) -> dict:
    try:
        return fn(payload)
    except plan.InputError as exc:
        raise InputError(str(exc)) from None


def _valid_date(text: str) -> date | None:
    if not _DATE.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


# --- Memory file readers -------------------------------------------------------------

def _text(path: Path) -> str:
    return ingest.read_text(path) or ""


def _memory(course_dir: Path, name: str) -> str:
    """A course memory file's text; '' when it is missing or is itself a symlink."""
    path = course_dir / ".state" / name
    return "" if path.is_symlink() else _text(path)


def _key(text: str, key: str) -> str:
    """Value of the first ``key:`` line ('' when missing)."""
    for line in text.splitlines():
        m = re.fullmatch(rf"{key}:(.*)", line.strip())
        if m:
            return m.group(1).strip()
    return ""


def _section_rows(text: str, section) -> list[list[str]]:
    lines = text.splitlines()
    first, end = ingest._section_table(lines, section)  # repairs only this copy
    width = len(section[1])
    return [[ingest._unescape(c) for c in (ingest._split_row(l) + [""] * width)[:width]]
            for l in lines[first:end]]


def _norm(name: str) -> str:
    return " ".join(name.split()).casefold()


def mastery(course_dir: Path) -> list[dict]:
    """``mastery.md`` rows in route order, columns mapped by header name; the
    first row of a topic wins. The file is never changed."""
    lines = _memory(course_dir, "mastery.md").splitlines()
    rows: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if ingest._is_row(line) and not ingest._is_align(line):
            header = [c.strip().lower() for c in ingest._split_row(line)]
            if "topic" in header and "status" in header:
                cols = {name: header.index(name) for name in _MASTERY_COLUMNS if name in header}
                i += 1
                while i < len(lines) and ingest._is_row(lines[i]):
                    if not ingest._is_align(lines[i]):
                        rows.append(_mastery_row(ingest._split_row(lines[i]), cols))
                    i += 1
                break
        i += 1
    seen: set[str] = set()
    out = []
    for row in rows:
        if row["name"] and _norm(row["name"]) not in seen:
            seen.add(_norm(row["name"]))
            out.append(row)
    for key, entry in _record_state(_memory(course_dir, "mastery.md")).items():
        position = next((i for i, r in enumerate(out) if _norm(r["name"]) == key), len(out))
        if position == len(out):
            out.append(entry["row"])
        else:
            out[position] = entry["row"]
    return out


def route(course_dir: Path) -> list[dict]:
    """The route: ``mastery.md`` rows in order. When no ``outline`` file is in the
    ``INDEX.md`` registry, each ``## Topics`` name not yet listed follows as an unseen
    row, in ingestion order (decision D1). Nothing is written."""
    rows = mastery(course_dir)
    index = course_dir / "INDEX.md"
    if any(role == "outline" for role, _, _ in ingest.registry(index).values()):
        return rows
    seen = {_norm(r["name"]) for r in rows}
    for name in ingest.topics(index):
        if _norm(name) not in seen:
            seen.add(_norm(name))
            rows.append(_mastery_row([name], {"topic": 0}))  # an unseen row
    return rows


def _mastery_row(cells: list[str], cols: dict[str, int]) -> dict:
    cells = [ingest._unescape(c).strip() for c in cells]

    def cell(name: str) -> str:
        index = cols.get(name)
        return cells[index] if index is not None and index < len(cells) else ""

    def count(name: str) -> int:
        return int(cell(name)) if _COUNT.fullmatch(cell(name)) else 0

    def day(name: str) -> str | None:
        value = _valid_date(cell(name))
        return value.isoformat() if value else None

    status = cell("status").lower()
    return {"name": " ".join(cell("topic").split()),
            "status": status if status in STATUSES else "unseen",
            "evidence": cell("evidence"), "evidence_date": day("evidence_date"),
            "last_check": day("last_check"), "assisted": count("assisted"),
            "unassisted": count("unassisted"), "frustration_override": cell("frustration_override")}


def topic_state(row: dict | None, name: str, today: date) -> dict:
    if row is None:
        return {"name": name, "status": "unseen", "evidence_date": None,
                "assisted": 0, "unassisted": 0, "stale": False, "attempt_first": False}
    evidence = _valid_date(row["evidence_date"] or "")
    stale = row["status"] != "unseen" and (
        evidence is None or evidence > today or (today - evidence).days > STALE_DAYS)
    return {"name": row["name"], "status": row["status"], "evidence_date": row["evidence_date"],
            "assisted": row["assisted"], "unassisted": row["unassisted"], "stale": stale,
            "attempt_first": (row["status"] != "unseen" and row["assisted"] >= ATTEMPT_FIRST_ASSISTED
                              and row["unassisted"] == 0)}


def _last_session(course_dir: Path) -> str | None:
    try:
        value = _key(_memory(course_dir, "save.md"), "last_session")
    except (InputError, OSError):  # another course's unreadable save.md does not block the pick
        return None
    m = _LAST_SESSION.fullmatch(value)
    if not m or _valid_date(m.group(1)) is None:
        return None
    clock = m.group(2) or "00:00"
    hh, mm = int(clock[:2]), int(clock[3:])
    return f"{m.group(1)} {clock}" if hh < 24 and mm < 60 else None


def _logs(course_dir: Path):
    """(name, text) of each readable ``.state/logs/*.md`` in name order; symlinks,
    unreadable and non-UTF-8 logs are skipped."""
    logs = course_dir / ".state" / "logs"
    try:
        if logs.is_symlink() or not logs.is_dir():
            return
        names = sorted(p for p in logs.iterdir() if p.suffix == ".md")
    except OSError:
        return
    for log in names:
        try:
            if log.is_symlink() or not log.is_file():
                continue
            yield log.name, _text(log)
        except (InputError, OSError):
            continue


def _first_contact(course_dir: Path) -> str | None:
    for _, text in _logs(course_dir):
        for line in text.splitlines():
            m = re.fullmatch(r"first_contact:(.*)", line.strip())
            if m and _valid_moment(m.group(1).strip()):
                return m.group(1).strip()
    return None


def _gauge_done(course_dir: Path) -> str | None:
    """The course's gauge-done marker: the first ``gauge_done:`` log line holding a date or datetime."""
    for _, text in _logs(course_dir):
        for line in text.splitlines():
            m = re.fullmatch(r"gauge_done:(.*)", line.strip())
            if m and _valid_moment(m.group(1).strip()):
                return m.group(1).strip()
    return None


def _gauge(course_dir: Path, rows: list[dict], scope: dict | None) -> dict | None:
    """``start``'s gauge: null with no topics; else done, and while not done the unseen topics
    that are not out of the next exam's scope."""
    if not rows:
        return None
    done = _gauge_done(course_dir) is not None
    return {"done": done, "topics": [] if done else [r["name"] for r in rows if r["status"] == "unseen"
                                                     and scope_mark(scope, r["name"]) != "out"]}


def _valid_moment(text: str) -> bool:
    """True for a date or datetime under plan.py's parse rules."""
    if not text:
        return False
    try:
        plan.parse_moment(text, "first_contact")
    except plan.InputError:
        return False
    return True


# --- Course pick ----------------------------------------------------------------------

def _pick(courses: list[dict], profile: str) -> dict:
    stamped = [(c, s) for c in courses if (s := _last_session(Path(c["course_dir"])))]
    if stamped:
        latest = max(s for _, s in stamped)
        return min((c for c, s in stamped if s == latest), key=lambda c: c["course"])
    by_path = {f"{c['term']}/{c['course']}": c for c in courses}
    for _, path in _section_rows(profile, _ACTIVE_TABLE):
        hit = by_path.get(path.strip().strip("/"))
        if hit:
            return hit
    return max(courses, key=lambda c: (workspace.term_key(c["term"]), c["course"]))


def _usable(root: Path, course: dict) -> bool:
    try:
        workspace.course_folder(root, course["term"], course["course"])
    except InputError:
        return False
    return True


_TIME_ASKED = re.compile(r"(.*\S)\s+time\s+unknown", re.IGNORECASE)
TIME_ASK_DAYS = 2  # ask once more for a date-only exam's time within this many days


def exam_value(cell: str, tz: tzinfo | None) -> date | datetime | str | None:
    """An ``## Exam dates`` cell: "unknown", a date (time unknown; also
    ``YYYY-MM-DD time unknown``), a datetime (a time without a UTC offset is
    taken at ``tz``), or None when unreadable."""
    text = " ".join(cell.split())
    if text.casefold() == "unknown":
        return "unknown"
    asked = _TIME_ASKED.fullmatch(text)
    day = _valid_date(asked.group(1) if asked else text)
    if day is not None or asked:
        return day
    m = _EXAM_AT.fullmatch(text)
    if not m:
        return None
    try:
        moment = datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}{m.group(3) or ''}")
    except ValueError:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz) if tz is not None else moment.replace(tzinfo=None)


def _exam_day(value: date | datetime, tz: tzinfo | None) -> date:
    return value if plan.is_date_only(value) else value.astimezone(tz).date() if tz else value.date()


def _exam(profile: str, code: str, now: datetime) -> dict:
    """``start``'s exam fields for the course code: exam, exam_date, exam_name, q0,
    exam_problems, ask_exam_time, ask_exam_ahead."""
    best, unknown, today, problems = None, False, now.date(), []
    for course, exam, when in _section_rows(profile, _EXAM_TABLE):
        if course.strip().casefold() != code.casefold():
            continue
        value = exam_value(when, now.tzinfo)
        if value == "unknown":
            unknown = True
            continue
        if value is None:
            problems.append({"exam": " ".join(exam.split()), "date": " ".join(when.split())})
            continue
        if plan.is_date_only(value):
            at = datetime.combine(value, time(0), tzinfo=now.tzinfo)  # orders before a timed exam that day
            upcoming = 0 <= (value - today).days <= plan.MAX_HORIZON_DAYS
        else:
            at = value
            upcoming = timedelta(0) < value - now <= timedelta(days=plan.MAX_HORIZON_DAYS)
        if upcoming and (best is None or at < best[0]):
            best = (at, value, exam.strip(), bool(_TIME_ASKED.fullmatch(" ".join(when.split()))))
    out = {"exam": None, "exam_date": None, "exam_name": None, "q0": not unknown, "exam_problems": problems,
           "ask_exam_time": False, "ask_exam_ahead": False}
    if best:
        _, value, name, asked = best
        dated = plan.is_date_only(value)
        out.update(exam=value.isoformat(), exam_date=_exam_day(value, now.tzinfo).isoformat(),
                   exam_name=name or None, q0=False,
                   ask_exam_time=dated and not asked and (value - today).days <= TIME_ASK_DAYS,
                   ask_exam_ahead=dated and value == today)
    return out


# --- Exam scope ----------------------------------------------------------------------

SCOPE_FILE = "scope.md"
SCOPE_SIDES = ("in", "out", "unsure")
SCOPE_HEAD = ("<!-- Mimir exam scope. Changed only by session.py scope; one section per exam. -->\n"
              "# Exam scope\n")
NOTED_HEAD = ("<!-- Mimir exam scopes noted at setup, before the course had a folder. Changed only by "
              "session.py scope. -->\n# Noted exam scope\n")
_CODE = re.compile(r"[^\s|]{1,40}")
MAX_SCOPE_NAME = 120
_SCOPE_SECTION = re.compile(r"## ([0-9]{4}-[0-9]{2}-[0-9]{2})(?: (.*))?")
_SCOPE_ENTRY = re.compile(r"- (in|out|unsure): (.+)")


def scopes(course_dir: Path) -> list[dict]:
    """``scope.md`` sections in file order: {"exam_date", "exam_name", "words", "in", "out", "unsure"}."""
    out: list[dict] = []
    for line in _memory(course_dir, SCOPE_FILE).splitlines():
        line = line.strip()
        head = _SCOPE_SECTION.fullmatch(line)
        if head:
            out.append({"exam_date": head.group(1), "exam_name": " ".join((head.group(2) or "").split()),
                        "code": "", "words": "", "in": [], "out": [], "unsure": []})
            continue
        if not out:
            continue
        entry = _SCOPE_ENTRY.fullmatch(line)
        if entry:
            out[-1][entry.group(1)].append(" ".join(entry.group(2).split()))
        elif line.startswith("words:"):
            out[-1]["words"] = line[len("words:"):].strip()
        elif line.startswith("code:"):
            out[-1]["code"] = line[len("code:"):].strip()
    return out


def _scope_for(sections: list[dict], exam_date: str | None, exam_name: str | None,
               exams: list[tuple[date, str]]) -> dict | None:
    """The section saved for that exam: the first with the same date and name (case and spaces
    ignored); else, when the exam moved, the first with the same name whose date no row in
    ``exams`` (the course code's dated rows) has under that name any more."""
    if exam_date is None:
        return None
    name = _norm(exam_name or "")
    same = [s for s in sections if _norm(s["exam_name"]) == name]
    rows = {day.isoformat() for day, exam in exams if _norm(exam) == name}
    return (next((s for s in same if s["exam_date"] == exam_date), None)
            or next((s for s in same if s["exam_date"] not in rows), None))


def _scope_text(sections: list[dict], head: str = SCOPE_HEAD) -> str:
    parts = [head]
    for sec in sections:
        lines = [f"## {sec['exam_date']} {sec['exam_name']}".rstrip()]
        lines += [f"code: {sec['code']}"] if sec.get("code") else []
        lines += [f"words: {sec['words']}"]
        lines += [f"- {side}: {name}" for side in SCOPE_SIDES for name in sec[side]]
        parts.append("\n".join(lines) + "\n")
    return "\n".join(parts)


_FP_TYPES = ("Question types", ("type", "frequency", "marks"))
_FP_MARKERS = re.compile(r"\s*(?:\(source:.*|\(tentative\).*|\(prior term\).*)$")


def question_types(course_dir: Path) -> list[str]:
    """``fingerprint.md`` question type names, without their source and markers."""
    names = []
    for cells in _section_rows(_memory(course_dir, "fingerprint.md"), _FP_TYPES):
        name = " ".join(_FP_MARKERS.sub("", cells[0]).split())
        if name and not name.startswith("<"):
            names.append(name)
    return names


def _noted_scope(root: Path, code: str, exam: dict, exams: list[tuple[date, str]]) -> dict | None:
    """The scope noted at setup for the course code's exam, from ``<root>/.state/scope.md``."""
    sections = [s for s in scopes(root) if s["code"].casefold() == code.casefold()]
    return _scope_for(sections, exam["exam_date"], exam["exam_name"], exams)


def scope_view(root: Path, course_dir: Path, code: str, rows: list[dict], exam: dict,
               exams: list[tuple[date, str]], today: date) -> tuple[dict | None, bool, str | None]:
    """``start``'s ``scope``, ``ask_exam_scope`` and ``scope_words``. ``scope``: the saved lists of
    the picked exam plus ``new``, the route topics and question types in none of them; None when no
    list is saved for it (scope unknown). ``scope_words``: with nothing saved in the course, the
    words noted at setup for the exam, else None. ``ask_exam_scope``: nothing at all is saved or
    noted for the exam (not even "don't know") and it is at most TIME_ASK_DAYS days ahead."""
    saved = _scope_for(scopes(course_dir), exam["exam_date"], exam["exam_name"], exams)
    noted = _noted_scope(root, code, exam, exams) if saved is None else None
    words = noted["words"] if noted else None
    ask = (saved is None and noted is None and exam["exam_date"] is not None
           and (date.fromisoformat(exam["exam_date"]) - today).days <= TIME_ASK_DAYS)
    if saved is None or not any(saved[side] for side in SCOPE_SIDES):
        return None, ask, words
    known = {_norm(n) for side in SCOPE_SIDES for n in saved[side]}
    new: list[str] = []
    for name in [r["name"] for r in rows] + question_types(course_dir):
        if _norm(name) not in known:
            known.add(_norm(name))
            new.append(name)
    return {"words": saved["words"], **{side: saved[side] for side in SCOPE_SIDES}, "new": new}, False, None


def scope_mark(scope: dict | None, name: str) -> str | None:
    """A route topic's mark: "in", "out" or "not checked"; None without a scope."""
    if scope is None:
        return None
    for side in ("in", "out"):
        if _norm(name) in {_norm(n) for n in scope[side]}:
            return side
    return "not checked"


# --- Debrief ------------------------------------------------------------------------

_PENDING = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:T\S*)?(?:\s+(.*))?")  # a time is ignored
_CLOSE_LOG = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}(?:-[A-Za-z0-9-]+)?")
_LOG_NAME = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})-[0-9]{4}(?:-[^/]*)?\.md")
_NO_CRAM_LINE = "Cram bill: no study sessions logged."
NO_COURSE_LINE = "No course yet: run mimir-setup, then mimir-ingest."


def _code_exams(profile: str, code: str, tz: tzinfo | None) -> list[tuple[date, str]]:
    """Dated ``## Exam dates`` rows of a course code as (day in ``tz``, name), in file order."""
    out = []
    for course, exam, when in _section_rows(profile, _EXAM_TABLE):
        value = exam_value(when, tz)
        if course.strip().casefold() == code.casefold() and isinstance(value, date):
            out.append((_exam_day(value, tz), " ".join(exam.split())))
    return out


def _pending(save: str) -> tuple[date, str | None] | None:
    """``pending_debrief: YYYY-MM-DD <name>`` as (date, name); None when no, empty or malformed."""
    m = _PENDING.fullmatch(_key(save, "pending_debrief"))
    day = _valid_date(m.group(1)) if m else None
    if day is None:
        return None
    return day, " ".join((m.group(2) or "").split()) or None


def _debrief_target(profile: str, code: str, pending: date, pending_name: str | None,
                    now: datetime) -> tuple[date, str | None, date | None]:
    """(target exam date, its name, previous exam date or None).

    Target: the latest row of the code dated from the day after ``pending``
    to yesterday (a later passed exam supersedes; ties: the first such row),
    else ``pending`` itself, named by ``pending_name``, else by the first named
    row dated ``pending``. Previous: the latest row of the code dated before
    the target."""
    rows, today = _code_exams(profile, code, now.tzinfo), now.date()
    passed = [(day, exam) for day, exam in rows if pending < day < today]
    target, name = pending, pending_name
    if passed:
        target = max(day for day, _ in passed)
        name = next(exam for day, exam in passed if day == target) or None
    elif name is None:
        name = next((exam for day, exam in rows if day == pending and exam), None)
    before = [day for day, _ in rows if day < target]
    return target, name, max(before) if before else None


def debrief_state(profile: str, save: str, code: str, now: datetime,
                  klass: str | None) -> tuple[dict | None, tuple[date, date | None] | None]:
    """(``start``'s ``debrief``, the due window (target, previous exam) or None).
    The state is null with no valid pending value."""
    pending = _pending(save)
    if pending is None:
        return None, None
    day, name = pending
    if day >= now.date():  # a date-only exam is past only from the next day
        return {"exam": day.isoformat(), "exam_name": name, "due": False, "deferred": False}, None
    target, target_name, previous = _debrief_target(profile, code, day, name, now)
    deferred = klass == "Urgent"
    state = {"exam": target.isoformat(), "exam_name": target_name, "due": not deferred,
             "deferred": deferred}
    return state, None if deferred else (target, previous)


def _sessions(logs: list[tuple[str, str]], after: date | None, until: date,
              aware: bool) -> list[dict]:
    """Logged ``started:``/next ``ended:`` pairs that started in (after, until]."""
    kept: list[tuple[datetime, datetime]] = []
    for _, text in logs:
        start = None
        for line in text.splitlines():
            m = re.fullmatch(r"(started|ended):(.*)", line.strip())
            if not m:
                continue
            try:
                moment = plan.parse_moment(m.group(2).strip(), m.group(1), need_time=True)
            except plan.InputError:
                if m.group(1) == "started":
                    start = None
                continue
            if m.group(1) == "started":
                start = moment
                continue
            if start is None:
                continue
            begin, end, start = start, moment, None
            if (begin.tzinfo is not None) != aware or (end.tzinfo is not None) != aware:
                continue
            if end < begin or begin.date() > until or (after is not None and begin.date() <= after):
                continue
            if any(begin < k_end and k_begin < end for k_begin, k_end in kept):
                continue
            kept.append((begin, end))
    return [{"start": b.isoformat(), "end": e.isoformat()} for b, e in kept]


def _disagreements(logs: list[tuple[str, str]], after: date | None, until: date) -> list[str]:
    out: list[str] = []
    for name, text in logs:
        m = _LOG_NAME.fullmatch(name)
        day = _valid_date(m.group(1)) if m else None
        if day is None or day > until or (after is not None and day <= after):
            continue
        inside = False
        for line in text.splitlines():
            if line.startswith("#"):
                inside = line.rstrip() == "## Verifier disagreements"
            elif inside and line.startswith("- ") and line[2:].strip() and line.strip() not in out:
                out.append(line.strip())
    return out


def _offer_next_course(root: Path, term: str) -> bool:
    for course in ingest._courses(root):
        if course["term"] != term or not _usable(root, course):
            continue
        for _, text in _logs(Path(course["course_dir"])):
            if any(re.fullmatch(r"next_course_offer:.*", row.strip()) for row in text.splitlines()):
                return False
    return True


def _cram(course_dir: Path, logs, first_contact: str | None, target: date,
          previous: date | None, now: datetime) -> dict | None:
    if first_contact is None:
        return None
    contact = plan.parse_moment(first_contact, "first_contact")
    aware = now.tzinfo is not None
    if not plan.is_date_only(contact) and (contact.tzinfo is not None) != aware:
        return None  # cannot be compared with the logged sessions
    contact_day = contact if plan.is_date_only(contact) else contact.date()
    if contact_day > target:
        return None
    return _plan(plan.debrief, {"now": now.isoformat(), "exam": target.isoformat(),
                                "first_contact": first_contact,
                                "sessions": _sessions(logs, previous, target, aware)})


# --- Subcommands ----------------------------------------------------------------------

def cmd_start(data: dict) -> dict:
    choice, lasting = data.get("choice"), data.get("lasting", False)
    if choice is not None and choice not in plan.TRIAGE_CLASSES:
        raise InputError("choice must be Standard or Urgent")
    if not isinstance(lasting, bool) or (lasting and choice is None):
        raise InputError("lasting must be true or false, and true needs a choice")
    return _start({k: v for k, v in data.items() if k not in ("choice", "lasting")}, choice, lasting)[0]


def _course_pick(data: dict) -> tuple[datetime, Path, str, list[dict], dict | None, bool | None,
                                      Path | None]:
    """(now, root, profile text, courses, chosen course or None, inferred, its folder) for
    ``start``'s input; the course pick and its errors are ``start``'s."""
    _check_keys(data, {"now", "term", "course"})
    now = _moment(data, "now")
    term = parse_term(data) if data.get("term") is not None else None
    given = parse_segment(data, "course") if data.get("course") is not None else None
    root = ingest._workspace_root()
    profile = _text(root / ".state" / "profile.md")
    courses = ingest._courses(root)
    pool = [c for c in courses if term is None or c["term"] == term]
    if given is None:  # a refused (symlinked) candidate is skipped; a given one exits 2 below
        pool = [c for c in pool if _usable(root, c)]
    if given is not None:
        hits = [c for c in pool if c["course"] == given]
        if not hits:
            where = f" in term {term}" if term else ""
            raise InputError(f"course {_short(given)} has no course folder with an INDEX.md{where}")
        if len(hits) > 1:
            raise InputError(f"course {_short(given)} is in several terms; pass term")
        chosen, inferred = hits[0], False
    elif term is not None and not pool:
        raise InputError(f"term {_short(term)} has no course folder with an INDEX.md")
    elif not pool:
        return now, root, profile, courses, None, None, None
    else:
        chosen, inferred = _pick(pool, profile), True
    course_dir = workspace.course_folder(root, chosen["term"], chosen["course"])
    return now, root, profile, courses, chosen, inferred, course_dir


_CHOICE = re.compile(r"(Standard|Urgent)\s+([0-9]{4}-[0-9]{2}-[0-9]{2})(?:\s+(.*))?", re.IGNORECASE)


def _lasting_choice(save: str, exam: dict) -> str | None:
    """The saved ``delivery_choice:`` class when it names the exam ``start`` picked, else None:
    once that exam passes, ``start`` picks another exam (or none) and the choice stops applying."""
    m = _CHOICE.fullmatch(_key(save, "delivery_choice"))
    if not m or exam["exam_date"] is None or m.group(2) != exam["exam_date"]:
        return None
    if _norm(m.group(3) or "") != _norm(exam["exam_name"] or ""):
        return None
    return m.group(1).capitalize()


def _choice_line(choice: str, exam: dict) -> str:
    name = " ".join((exam["exam_name"] or "").split())
    return f"delivery_choice: {choice} {exam['exam_date']} {name}".rstrip()


def _save_choice(course_dir: Path, line: str) -> None:
    """Write the ``delivery_choice:`` line into ``save.md``: replace the first one, else add it
    after the last key line above the first ``##`` heading (else at the end)."""
    path = course_dir / ".state" / "save.md"
    if path.is_symlink():
        raise InputError("save.md must not be a symlink")
    lines = _text(path).splitlines()
    at = next((i for i, row in enumerate(lines) if re.fullmatch(r"delivery_choice:.*", row.strip())), None)
    if at is not None:
        if lines[at] == line:
            return
        lines[at] = line
    else:
        head = next((i for i, row in enumerate(lines) if row.startswith("## ")), len(lines))
        keys = [i for i in range(head) if re.fullmatch(r"[a-z_]+:.*", lines[i])]
        lines.insert(keys[-1] + 1 if keys else head, line)
    ingest._write_atomic(path, "\n".join(lines) + "\n")


def _class(now: str, exam: dict, choice: str | None, lasting: bool, save: str) -> dict:
    """``start``'s class: the student's choice for this session, else a saved lasting
    choice for this exam, else ``plan.py class`` for the exam."""
    klass = _plan(plan.delivery_class, {"now": now, "exam": exam["exam"]})
    tail = klass["line"].split(": ", 1)[1]  # "exam in 30 hours"
    if choice is not None and not lasting:
        return {**klass, "class": choice, "decided_by": "session choice",
                "line": f"{choice} delivery: you asked; {tail}"}
    saved = choice if lasting else _lasting_choice(save, exam)
    if saved is None:
        return {**klass, "decided_by": "exam date"}
    return {**klass, "class": saved, "decided_by": "lasting choice",
            "line": f"{saved} delivery: you asked, until your {exam['exam_name'] or 'exam'}; {tail}"}


NEAR_EXAM_HOURS = 48  # Standard sessions this close to any exam give no preference evidence and run no probe


def _near_exam(profile: str, now: datetime) -> bool:
    """True when any course's upcoming exam is within NEAR_EXAM_HOURS of ``now``. A date-only exam
    counts when its day is at most NEAR_EXAM_HOURS // 24 days after today: some moment of it is."""
    for _, _, when in _section_rows(profile, _EXAM_TABLE):
        value = exam_value(when, now.tzinfo)
        if not isinstance(value, date):  # unknown or unreadable
            continue
        if plan.is_date_only(value):
            if 0 <= (value - now.date()).days <= NEAR_EXAM_HOURS // 24:
                return True
        elif timedelta(0) < value - now <= timedelta(hours=NEAR_EXAM_HOURS):
            return True
    return False


_ROUTE_MARKS = {"out": "not on your next exam", "not checked": "not checked"}


def _remaining_line(remaining: list[dict]) -> str | None:
    """What is left on the route, one line per topic with its status and scope mark; None when empty."""
    if not remaining:
        return None
    rows = ["Left on your route:"]
    for r in remaining:
        mark = _ROUTE_MARKS.get(r["scope"])
        rows.append(f"- {r['name']} ({r['status']}{', ' + mark if mark else ''})")
    return "\n".join(rows)


def _preference_session(klass: dict, profile: str, now: datetime) -> bool:
    """Standard, and not within 48 hours of any exam in the profile."""
    return klass["class"] == "Standard" and not _near_exam(profile, now)


def _start(data: dict, choice: str | None = None,
           lasting: bool = False) -> tuple[dict, tuple[date, date | None] | None]:
    """``start``'s output and the due debrief window (see ``debrief_state``)."""
    now, root, profile, courses, chosen, inferred, course_dir = _course_pick(data)
    if chosen is None:
        return {"root": str(root), "courses": courses, "term": None, "course": None, "course_dir": None,
                "code": None, "inferred": None, "exam": None, "exam_date": None, "exam_name": None, "q0": None,
                "exam_problems": None, "ask_exam_time": None, "ask_exam_ahead": None, "ask_exam_scope": None,
                "scope_words": None,
                "remaining": [], "remaining_line": None, "class": None, "topic": None, "route_line": None,
                "first_contact": None, "scope": None, "gauge": None, "debrief": None, "preference_session": None,
                "line": NO_COURSE_LINE}, None
    code = chosen["course"].split()[0]
    today = now.date()
    exam = _exam(profile, code, now)
    rows = route(course_dir)
    scope, ask_scope, scope_words = scope_view(root, course_dir, code, rows, exam,
                                               _code_exams(profile, code, now.tzinfo), today)
    # The next exam's scope orders the route: topics not on it go last; none is removed.
    rows = sorted(rows, key=lambda r: scope_mark(scope, r["name"]) == "out")
    remaining = [r for r in rows if r["status"] != "mastered"]
    save = _memory(course_dir, "save.md")
    if lasting:
        if exam["exam"] is None:
            raise InputError("lasting needs an upcoming exam; without one a choice lasts this session only")
        _save_choice(course_dir, _choice_line(choice, exam))
    klass = _class(data["now"], exam, choice, lasting, save)
    next_topic = _norm(_key(save, "next_topic"))
    # Nothing unmastered left: a stale mastered topic gets the one-question recheck.
    candidates = remaining or [r for r in rows if topic_state(r, r["name"], today)["stale"]]
    first = candidates[0] if candidates else None
    pick = next((r for r in candidates if next_topic and _norm(r["name"]) == next_topic
                 and (scope_mark(scope, r["name"]) != "out" or scope_mark(scope, first["name"]) == "out")),
                first)
    debrief, window = debrief_state(profile, save, code, now, klass["class"])
    topic = None
    if pick is not None:
        state = topic_state(pick, pick["name"], today)
        topic = {k: state[k] for k in ("name", "status", "evidence_date", "stale", "attempt_first")}
    route_line = None if pick is not None else ROUTE_DONE_LINE if rows else NO_ROUTE_LINE
    left = [{"name": r["name"], "status": r["status"], "scope": scope_mark(scope, r["name"])} for r in remaining]
    return {"root": str(root), "courses": courses, "term": chosen["term"], "course": chosen["course"],
            "course_dir": str(course_dir), "code": code, "inferred": inferred, **exam,
            "ask_exam_scope": ask_scope, "scope_words": scope_words,
            "remaining": left, "remaining_line": _remaining_line(left),
            "class": klass, "topic": topic, "route_line": route_line,
            "first_contact": _first_contact(course_dir), "scope": scope,
            "gauge": _gauge(course_dir, rows, scope),
            "debrief": debrief, "preference_session": _preference_session(klass, profile, now), "line": klass["line"]}, window


def _scope_names(data: dict, side: str) -> list[str]:
    names = data.get(side, [])
    if not isinstance(names, list):
        raise InputError(f"{side} must be a list of names")
    out: list[str] = []
    for n, name in enumerate(names, 1):
        if not isinstance(name, str) or not name.strip() or _has_control(name) or len(name) > MAX_SCOPE_NAME:
            raise InputError(f"{side}[{n}] must be a one-line name of at most {MAX_SCOPE_NAME} characters")
        name = " ".join(name.split())
        if _norm(name) not in {_norm(o) for o in out}:
            out.append(name)
    return out


def cmd_scope(data: dict) -> dict:
    """Save the confirmed scope of one exam in the course's ``scope.md``, or, given a course
    ``code`` instead of ``term`` and ``course`` (setup, before the course has a folder), note the
    student's words in ``<root>/.state/scope.md`` for the first study session to confirm."""
    _check_keys(data, {"now", "term", "course", "code", "exam_name", "exam_date", "words", *SCOPE_SIDES})
    now = _moment(data, "now")
    noted = "code" in data
    if noted and ("term" in data or "course" in data):
        raise InputError("give code, or term and course, not both")
    if noted:
        code = data["code"]
        if not isinstance(code, str) or not _CODE.fullmatch(code):
            raise InputError("code must be a course code: one word of at most 40 characters")
    else:
        term, course = parse_term(data), parse_segment(data, "course")
    exam_date = data.get("exam_date")
    if not isinstance(exam_date, str) or _valid_date(exam_date) is None:
        raise InputError("exam_date must be a date YYYY-MM-DD (start's exam_date)")
    exam_name = data.get("exam_name")
    if exam_name is not None and (not isinstance(exam_name, str) or _has_control(exam_name)):
        raise InputError("exam_name must be a one-line exam name or null (start's exam_name)")
    exam_name = " ".join((exam_name or "").split())
    words = data.get("words")
    if not isinstance(words, str) or not words.strip() or _has_control(words) or len(words) > MAX_WORDING:
        raise InputError(f"words must be the student's words, one line of at most {MAX_WORDING} characters")
    lists = {side: _scope_names(data, side) for side in SCOPE_SIDES}
    for a, b in (("in", "out"), ("in", "unsure"), ("out", "unsure")):
        both = {_norm(n) for n in lists[a]} & {_norm(n) for n in lists[b]}
        if both:
            name = next(n for n in lists[a] if _norm(n) in both)
            raise InputError(f"{_short(name)} is in both {a} and {b}")
    if noted and any(lists.values()):
        raise InputError("a scope noted by code holds words only: its lists are confirmed once the course "
                         "has a folder")
    root = ingest._workspace_root()
    if noted:
        course_dir, folder = None, root
    else:
        course_dir = folder = workspace.course_folder(root, term, course)
        if not (course_dir / "INDEX.md").is_file():
            raise InputError(f"course {_short(course)} has no course folder with an INDEX.md in term {term}")
        code = course.split()[0]
    exams = _code_exams(_text(root / ".state" / "profile.md"), code, now.tzinfo)
    if not any(day.isoformat() == exam_date and _norm(name) == _norm(exam_name) for day, name in exams):
        raise InputError(f"no ## Exam dates row of {_short(code)} named {_short(exam_name or '(none)')} "
                         f"on {exam_date} in profile.md")
    path = folder / ".state" / SCOPE_FILE
    if path.is_symlink():
        raise InputError(f"{SCOPE_FILE} must not be a symlink")
    sections = scopes(folder)
    entry = {"exam_date": exam_date, "exam_name": exam_name, "code": code if noted else "",
             "words": " ".join(words.split()), **lists}
    mine = [s for s in sections if s["code"].casefold() == code.casefold()] if noted else sections
    old = _scope_for(mine, exam_date, exam_name, exams)
    if old is None:
        sections.append(entry)
    else:
        sections[sections.index(old)] = entry
    text = _scope_text(sections, NOTED_HEAD if noted else SCOPE_HEAD)
    changed = _text(path) != text
    if changed:
        ingest._write_atomic(path, text)
    label = f"your {exam_name or 'exam'} on {exam_date}"
    if noted:
        line = f"Scope of {label} noted: you confirm it at your first study session, once the course files are in."
    elif any(lists.values()):
        counts = f"{len(lists['in'])} in, {len(lists['out'])} out"
        counts += f", {len(lists['unsure'])} unsure" if lists["unsure"] else ""
        line = f"Scope of {label} saved: {counts}."
    else:
        line = f"Scope of {label}: unknown, saved so it is not asked again."
    return {"course_dir": str(course_dir) if course_dir else None, "exam_name": exam_name or None, "exam_date": exam_date,
            "scope": {"words": entry["words"], **lists}, "changed": changed, "line": line}


def cmd_debrief(data: dict) -> dict:
    st, window = _start(data)
    out = {"term": st["term"], "course": st["course"], "course_dir": st["course_dir"],
           "code": st["code"], "inferred": st["inferred"], "debrief": st["debrief"],
           "cram": None, "disagreements": None, "offer_next_course": None}
    state = st["debrief"]
    if st["course"] is None:
        return {**out, "line": st["line"]}
    if state is None:
        return {**out, "line": f"No debrief pending for {st['course']}."}
    if state["deferred"]:
        if st["exam"] is None:
            return {**out, "line": "Debrief waits for a calmer session: today is for your exam."}
        upcoming = st["exam_name"] or "exam"
        return {**out, "line": f"Debrief waits until after your {upcoming}: today is for that."}
    if window is None:
        return {**out, "line": f"Debrief opens after your {state['exam_name'] or 'exam'} on {state['exam']}."}
    now = _moment(data, "now")
    root = Path(st["root"])
    course_dir = Path(st["course_dir"])
    target, previous = window
    logs = list(_logs(course_dir))
    cram = _cram(course_dir, logs, st["first_contact"], target, previous, now)
    return {**out, "cram": cram, "disagreements": _disagreements(logs, previous, target),
            "offer_next_course": _offer_next_course(root, st["term"]),
            "line": cram["line"] if cram else _NO_CRAM_LINE}


_PROGRESS_HEAD = ("| Topic | Status | Evidence | Evidence date | Solved alone / with help | Recheck |\n"
                  "|---|---|---|---|---|---|")


def cmd_progress(data: dict) -> dict:
    now, _, _, courses, chosen, inferred, course_dir = _course_pick(data)
    if chosen is None:
        return {"courses": courses, "term": None, "course": None, "course_dir": None, "code": None,
                "inferred": None, "topics": None, "counts": None, "table": None, "line": NO_COURSE_LINE}
    today = now.date()
    topics = []
    for row in route(course_dir):
        state = topic_state(row, row["name"], today)
        topics.append({"name": row["name"], "status": row["status"], "evidence": row["evidence"],
                       "evidence_date": row["evidence_date"], "last_check": row["last_check"],
                       "assisted": row["assisted"], "unassisted": row["unassisted"],
                       "frustration_override": row["frustration_override"], "stale": state["stale"]})
    counts = {s: sum(1 for t in topics if t["status"] == s) for s in STATUSES}
    out = {"courses": courses, "term": chosen["term"], "course": chosen["course"],
           "course_dir": str(course_dir),
           "code": chosen["course"].split()[0], "inferred": inferred, "topics": topics, "counts": counts}
    if not topics:
        return {**out, "table": None, "line": NO_ROUTE_LINE}
    rows = [_PROGRESS_HEAD] + [
        "| " + " | ".join(ingest._cell(c) for c in (
            t["name"], t["status"], t["evidence"] or "-", t["evidence_date"] or "-",
            f"{t['unassisted']} / {t['assisted']}", "due" if t["stale"] else "")) + " |"
        for t in topics]
    due = sum(1 for t in topics if t["stale"])
    if counts["unseen"] == len(topics):
        line = (f"{chosen['course']}: nothing studied yet, so no topic has evidence "
                f"({len(topics)} unseen). Run mimir-study to start.")
    else:
        line = (f"{chosen['course']}: {counts['mastered']} of {len(topics)} topics mastered, "
                f"{counts['shaky']} shaky, {counts['gap']} gap, {counts['unseen']} unseen; "
                + (f"{due} due a recheck." if due else "none due a recheck."))
    return {**out, "table": "\n".join(rows), "line": line}


def cmd_check(data: dict) -> dict:
    _check_keys(data, {"now", "term", "course", "topics"})
    now = _moment(data, "now")
    term, course = parse_term(data), parse_segment(data, "course")
    names = data.get("topics")
    if not isinstance(names, list) or not names:
        raise InputError("topics is required (a non-empty list of topic names)")
    for n, name in enumerate(names, 1):
        if not isinstance(name, str) or not name.strip() or _has_control(name):
            raise InputError(f"topics[{n}] must be a one-line topic name")
    root = ingest._workspace_root()
    course_dir = workspace.course_folder(root, term, course)
    if not (course_dir / "INDEX.md").is_file():
        raise InputError(f"course {_short(course)} has no course folder with an INDEX.md in term {term}")
    rows = {_norm(r["name"]): r for r in mastery(course_dir)}
    today = now.date()
    out = [topic_state(rows.get(_norm(name)), " ".join(name.split()), today) for name in names]
    stale = [t["name"] for t in out if t["stale"]]
    noun = "topic" if len(out) == 1 else "topics"
    line = f"{len(out)} {noun} checked, {len(stale)} stale" + (f": {', '.join(stale)}." if stale else ".")
    return {"course_dir": str(course_dir), "topics": out, "line": line}


def _session_log(data: dict) -> tuple[Path, Path]:
    """(course folder, log path) for a ``term``, ``course`` and ``log`` name from ``session.py now``;
    exits 2 when the course or the log is missing, or the log is a symlink."""
    term, course = parse_term(data), parse_segment(data, "course")
    name = data.get("log")
    if not isinstance(name, str) or not _CLOSE_LOG.fullmatch(name):
        raise InputError("log must be a log name from `session.py now` (YYYY-MM-DD-HHMM)")
    course_dir = workspace.course_folder(ingest._workspace_root(), term, course)
    if not (course_dir / "INDEX.md").is_file():
        raise InputError(f"course {_short(course)} has no course folder with an INDEX.md in term {term}")
    path = course_dir / ".state" / "logs" / f"{name}.md"
    if path.is_symlink() or not path.is_file():
        raise InputError(f"log {name} not found in {_short(course)}")
    return course_dir, path


def _append(path: Path, text: str, line: str) -> None:
    ingest._write_atomic(path, text + ("" if text.endswith("\n") or not text else "\n") + line + "\n")


def cmd_close(data: dict) -> dict:
    """Stamp a session's end in its log once; a repeated close reuses the stamp and writes nothing."""
    _check_keys(data, {"now", "term", "course", "log", "started"})
    now, started = _moment(data, "now"), _moment(data, "started")
    _, path = _session_log(data)
    name = data["log"]
    text = _text(path)
    ended, found, inside = None, False, False
    for line in text.splitlines():
        m = re.fullmatch(r"(started|ended):(.*)", line.strip())
        if not m:
            continue
        value = m.group(2).strip()
        if m.group(1) == "started":
            if inside and ended is None:
                raise InputError(f"a later session started in log {name} before this one was closed")
            inside = value == data["started"]
            found = found or inside
        elif inside and ended is None:
            try:
                ended = plan.parse_moment(value, "ended", need_time=True)
            except plan.InputError:
                raise InputError(f"log {name} has an ended line that is not a datetime") from None
    if not found:
        raise InputError(f"log {name} has no started: {data['started']} line")
    already = ended is not None
    if not already:
        if (started.tzinfo is None) != (now.tzinfo is None):
            raise InputError("now and started mix values with and without a UTC offset")
        if now < started:
            raise InputError("now is before started")
        ended = now
        _append(path, text, f"ended: {data['now']}")
    minutes = max(0, int((ended - started).total_seconds() // 60))
    line = f"Session {'already closed' if already else 'closed'} after {minutes} min."
    return {"log": str(path), "started": data["started"], "ended": ended.isoformat(), "minutes": minutes,
            "last_session": ended.strftime("%Y-%m-%d %H:%M"), "already_closed": already, "line": line}


def cmd_gauge(data: dict) -> dict:
    """Set the course's gauge-done marker once: a ``gauge_done:`` line in this session's log."""
    _check_keys(data, {"now", "term", "course", "log"})
    _moment(data, "now")
    course_dir, path = _session_log(data)
    course = course_dir.name
    if not route(course_dir):
        raise InputError(f"course {_short(course)} has no topics yet: no gauge, and its marker stays unset")
    done = _gauge_done(course_dir)
    if done is None:
        _append(path, _text(path), f"gauge_done: {data['now']}")
    line = (f"Knowledge gauge already done for {course}." if done else
            f"Knowledge gauge done for {course}: it will not run again.")
    return {"log": str(path), "gauge_done": done or data["now"], "already_done": done is not None, "line": line}


def _clock() -> datetime:
    """The local wall clock with its UTC offset, to the second. Only ``now`` reads it."""
    return datetime.now().astimezone()


def _season(month: int) -> str:
    return "Spring" if month <= 5 else "Summer" if month <= 8 else "Fall"


def cmd_now(data: dict) -> dict:
    _check_keys(data, set())
    now = _clock().replace(microsecond=0)
    stamp = now.isoformat()
    return {"now": stamp, "date": now.date().isoformat(), "log_name": now.strftime("%Y-%m-%d-%H%M"),
            "last_session": now.strftime("%Y-%m-%d %H:%M"), "term": f"{now.year}-{_season(now.month)}",
            "line": f"Now: {stamp}."}


_CLOCK = r"[0-9]{1,2}(?::[0-9]{2} ?(?:am|pm)?| ?(?:am|pm))"
_TIME_FIRST = re.compile(rf"({_CLOCK}) (.+)")
_TIME_LAST = re.compile(rf"(.+?) (?:at )?({_CLOCK})")
_CLOCK_PARTS = re.compile(r"([0-9]{1,2})(?::([0-9]{2}))? ?(am|pm)?")


def _clock_time(text: str, phrase: str) -> time:
    hour, minute, half = _CLOCK_PARTS.fullmatch(text).groups()
    hour, minute = int(hour), int(minute or 0)
    if hour > (12 if half else 23) or minute > 59 or (half and hour == 0):
        raise InputError(f"phrase {_short(phrase)} is not a real time")
    if half:
        hour = hour % 12 + (12 if half == "pm" else 0)
    return time(hour, minute)


def _phrase_day(text: str, today: date, phrase: str) -> date:
    relative = _RELATIVE.fullmatch(text)
    if text == "today":
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    if relative:
        count = int(relative.group(1))
        return today + timedelta(days=min(count, plan.MAX_HORIZON_DAYS + 1))
    if text in WEEKDAYS:
        return today + timedelta(days=(WEEKDAYS.index(text) - today.weekday()) % 7)
    if _DATE.fullmatch(text):
        day = _valid_date(text)
        if day is None:
            raise InputError(f"phrase {_short(phrase)} is not a real date")
        return day
    raise InputError(f"phrase {_short(phrase)} is unsupported (use YYYY-MM-DD, today, tomorrow, "
                     "a weekday name or \"in N days\", optionally with a time such as 12:30 or 2pm)")


def cmd_parse_date(data: dict) -> dict:
    _check_keys(data, {"now", "phrase"})
    now = _moment(data, "now")
    today = now.date()
    phrase = data.get("phrase")
    if not isinstance(phrase, str):
        raise InputError("phrase is required (the student's exam-date phrase)")
    text = " ".join(phrase.split()).casefold()
    if not text:
        raise InputError("phrase is empty")
    clock = None
    if m := _TIME_FIRST.fullmatch(text):
        clock, text = m.group(1), m.group(2)
    elif m := _TIME_LAST.fullmatch(text):
        text, clock = m.group(1), m.group(2)
    day = _phrase_day(text, today, phrase)
    at = None if clock is None else _clock_time(clock, phrase)
    if day < today:
        raise InputError(f"phrase {_short(phrase)} is in the past ({day.isoformat()})")
    if day > today + timedelta(days=plan.MAX_HORIZON_DAYS):
        raise InputError(f"phrase {_short(phrase)} is more than {plan.MAX_HORIZON_DAYS} days ahead")
    if at is None:
        return {"date": day.isoformat(), "time": None, "exam": day.isoformat(),
                "line": f"Exam date: {day.isoformat()}."}
    moment = datetime.combine(day, at, tzinfo=now.tzinfo)
    if moment <= now:
        raise InputError(f"phrase {_short(phrase)} is in the past ({moment.isoformat()})")
    shown = at.strftime("%H:%M")
    return {"date": day.isoformat(), "time": shown, "exam": moment.isoformat(),
            "line": f"Exam: {day.isoformat()} at {shown}."}


def _record_state(text: str) -> dict:
    marker = "<!-- mimir-record-v1 "
    lines = [line for line in text.splitlines() if line.startswith(marker)]
    if not lines:
        return {}
    try:
        state = json.loads(lines[-1][len(marker):-4])
        if not isinstance(state, dict):
            raise ValueError()
        return state
    except (ValueError, TypeError):
        raise InputError("mastery record state is damaged; restore it before recording") from None


def _save_record(path: Path, text: str, state: dict) -> None:
    lines = [l for l in text.splitlines() if not l.startswith("<!-- mimir-record-v1 ")]
    encoded = json.dumps(state, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e")
    ingest._write_atomic(path, "\n".join(lines) + "\n<!-- mimir-record-v1 " + encoded + " -->\n")


def _initial_record(row: dict) -> dict:
    recent = ([{"date": row["evidence_date"], "evidence": row["evidence"]}]
              if row["evidence_date"] and row["evidence"] else [])
    return {"row": row, "attempts": [], "solves": [], "recent": recent,
            "blocked_session": "legacy" if row["frustration_override"] else None}


def cmd_record(data: dict) -> dict:
    """Record an idempotent attempt; retain legacy text and atomic authoritative state."""
    if data.get("initialize") is True:
        _check_keys(data, {"term", "course", "topic", "initialize"})
        term, course = parse_term(data), parse_segment(data, "course")
        topic = data.get("topic")
        if not isinstance(topic, str) or not topic.strip() or _has_control(topic):
            raise InputError("topic must be a nonempty one-line string")
        folder = workspace.course_folder(ingest._workspace_root(), term, course)
        if not (folder / "INDEX.md").is_file():
            raise InputError("course has no INDEX.md")
        path = folder / ".state" / "mastery.md"
        if path.is_symlink():
            raise InputError("mastery.md must not be a symlink")
        rows = mastery(folder)
        existing = next((r for r in rows if _norm(r["name"]) == _norm(topic)), None)
        if existing:
            return {"status": existing["status"], "recorded": False, "duplicate": True,
                    "line": "Topic already initialized."}
        text = _memory(folder, "mastery.md")
        state = _record_state(text)
        state[_norm(topic)] = _initial_record(_mastery_row([topic], {"topic": 0}))
        _save_record(path, text, state)
        return {"status": "unseen", "recorded": True, "duplicate": False,
                "line": "Topic initialized."}
    _check_keys(data, {"term", "course", "topic", "item", "gate", "outcome",
                       "real_past_paper", "session", "date", "override", "explanation_only"})
    term, course = parse_term(data), parse_segment(data, "course")
    for field in ("topic", "item", "session", "date"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or _has_control(value):
            raise InputError(f"{field} must be a nonempty one-line string")
    day = _valid_date(data["date"])
    if day is None:
        raise InputError("date must be YYYY-MM-DD")
    if data.get("outcome") not in ("unassisted", "assisted", "wrong"):
        raise InputError("outcome must be unassisted, assisted or wrong")
    for field in ("real_past_paper", "override", "explanation_only"):
        if type(data.get(field, False)) is not bool:
            raise InputError(f"{field} must be boolean")
    if "real_past_paper" not in data:
        raise InputError("real_past_paper is required")
    gate = data.get("gate")
    if not isinstance(gate, dict) or gate.get("decision") not in ("show", "flagged", "drop", "verify"):
        raise InputError("gate must contain a valid decision")
    if type(gate.get("counts_for_mastery")) is not bool:
        raise InputError("gate.counts_for_mastery must be boolean")
    folder = workspace.course_folder(ingest._workspace_root(), term, course)
    if not (folder / "INDEX.md").is_file():
        raise InputError("course has no INDEX.md")
    path = folder / ".state" / "mastery.md"
    if path.is_symlink():
        raise InputError("mastery.md must not be a symlink")
    text = _memory(folder, "mastery.md")
    state = _record_state(text)
    key = _norm(data["topic"])
    legacy = next((r for r in mastery(folder) if _norm(r["name"]) == key),
                  _mastery_row([data["topic"]], {"topic": 0}))
    entry = state.get(key, _initial_record(legacy))
    row = entry["row"]
    result = {"status": row["status"], "duplicate": False, "recorded": False}
    # One miss and one right answer per session, item and event: retries after a
    # miss record nothing more until the right answer, which counts as assisted.
    # Three-element identities predate this split and block both.
    base = [data["session"], data["item"], bool(data.get("override"))]
    outcome = data["outcome"]
    kind = "wrong" if outcome == "wrong" else "right"
    blocking = [base, base + ["right"]] + ([base + ["wrong"]] if kind == "wrong" else [])
    if any(identity in entry["attempts"] for identity in blocking):
        return {**result, "duplicate": True, "line": "Attempt already recorded."}
    if kind == "right" and base + ["wrong"] in entry["attempts"]:
        outcome = "assisted"
    identity = base + [kind]
    override = data.get("override", False)
    explanation = override and data.get("explanation_only", False) and gate["decision"] == "drop"
    if not explanation and (gate["decision"] != "show" or not gate["counts_for_mastery"]):
        return {**result, "line": "Attempt does not count: item is flagged or not shown."}
    if entry["blocked_session"] == data["session"] and not override:
        return {**result, "line": "After frustration override, not counted."}
    if entry.get("last_date") and data["date"] < entry["last_date"]:
        raise InputError("date precedes the latest recorded attempt")
    entry["attempts"].append(identity)
    entry["last_date"] = data["date"]
    if override:
        row["status"] = "shaky"
        row["frustration_override"] = data["date"]
        entry["blocked_session"] = data["session"]
        entry["solves"] = []
        evidence = "frustration override: answer given"
    else:
        evidence = f'{data["item"]} {gate.get("label", "")}: {outcome}'.strip()
        if outcome == "wrong":
            row["status"] = "shaky" if row["status"] == "mastered" else "gap"
            entry["solves"] = []
        elif outcome == "assisted":
            row["assisted"] += 1
            if not entry["blocked_session"] and row["status"] != "mastered":
                row["status"] = "shaky"
        else:
            row["unassisted"] += 1
            entry["blocked_session"] = None
            row["frustration_override"] = ""
            solve = {"item": data["item"], "date": data["date"], "real": data["real_past_paper"]}
            entry["solves"].append(solve)
            qualifies = any(a["item"] != b["item"] and
                            (a["date"] != b["date"] or a["real"] or b["real"])
                            for a in entry["solves"] for b in entry["solves"])
            row["status"] = "mastered" if qualifies or row["status"] == "mastered" else "shaky"
    entry["recent"] = (entry["recent"] + [{"date": data["date"], "evidence": evidence}])[-3:]
    row.update(evidence="; ".join(f'{e["date"]}: {e["evidence"]}' for e in entry["recent"]),
               evidence_date=data["date"], last_check=data["date"])
    state[key] = entry
    _save_record(path, text, state)
    return {"status": row["status"], "duplicate": False, "recorded": True,
            "line": f'{row["name"]}: {row["status"]}.'}


# Teaching settings: three global axes, each with three levels from more guided to more independent.
AXES = {"support": ("example-first", "method-first", "try-first"),
        "frequency": ("checks only", "key decisions", "every step"),
        "depth": ("next step", "why", "what-if")}
AXIS_NAMES = {"support": "support", "frequency": "guiding-question frequency", "depth": "guiding-question depth"}
PROVENANCES = ("default", "sampler", "learned", "explicit", "legacy")
PREFS_FILE = "preferences.json"
PREFS_VERSION = 1
MAX_WORDING = 200
# Probe trials (docs/teaching-preferences-design.md, Probes; the numbers are tunable heuristics).
ADOPT_SESSIONS = 2          # positive evidence in this many sessions, on different calendar days, adopts a trial
MAX_REJECTIONS = 3          # the third rejection of a transition stops it; before that, skip as many sessions
OFFER_SESSIONS = 2          # frustration overrides in this many sessions bring the one-time offer
FEWER_QUESTIONS_OFFER = "Want fewer questions from now on?"
# State keys beyond ``version`` and ``axes``; each is written only once it differs from its default.
OPTIONAL_STATE = {"sampler_skipped": False, "whats_new_seen": False, "trial": None,
                  "sessions": {"count": 0, "current": None, "probed": None},
                  "transitions": {}, "frustration": {"count": 0, "last": None, "offered": False}}
NO_SESSION = ("this session gives no preference evidence and runs no probe: run the session event first "
              "(only when start gives preference_session true)")
EVENT_FIELDS = {"legacy-import": set(), "sampler-skip": set(), "whats-new-seen": set(), "explicit": {"axis", "level", "wording"},
                "sampler": {"axis", "level"}, "session": {"session"}, "trial-start": {"session", "axis"},
                "positive": {"session"}, "neutral": {"session"}, "pushback": {"session"},
                "reopen": {"axis"}, "frustration": {"session"}}
WHATS_NEW = "New: sessions run until you say 'end session'. You can also ask to cram or to study normally."


def _default_axes() -> dict:
    return {axis: {"level": levels[1], "provenance": "default", "wording": None} for axis, levels in AXES.items()}


def _prefs_path(root: Path) -> Path:
    path = root / ".state" / PREFS_FILE
    if path.is_symlink():
        raise InputError(f"{PREFS_FILE} must not be a symlink")
    return path


def _next_level(axis: str, level: str) -> str | None:
    """The adjacent level one step toward more independent teaching, else None."""
    levels = AXES[axis]
    at = levels.index(level)
    return levels[at + 1] if at + 1 < len(levels) else None


def _transition(axis: str, level: str) -> str:
    """The name of the transition from ``level`` one step toward more independent teaching."""
    return f"{axis}: {level} > {_next_level(axis, level)}"


def _session_moment(value) -> datetime | None:
    """A session identity: its ``started:`` datetime with an offset, else None."""
    if not isinstance(value, str):
        return None
    try:
        moment = plan.parse_moment(value, "session", need_time=True)
    except plan.InputError:
        return None
    return moment if moment.tzinfo is not None else None


def _count(value, low: int, high: int | None = None) -> bool:
    return type(value) is int and value >= low and (high is None or value <= high)


def _valid_extras(state: dict) -> bool:
    """The optional state keys hold closed values only: no free text, every level and transition known."""
    trial, sessions, transitions, frustration = (state[k] for k in ("trial", "sessions", "transitions", "frustration"))
    if not (isinstance(sessions, dict) and set(sessions) == {"count", "current", "probed"}
            and _count(sessions["count"], 0) and all(sessions[k] is None or _session_moment(sessions[k])
                                                      for k in ("current", "probed"))):
        return False
    if trial is not None:
        if not (isinstance(trial, dict) and set(trial) == {"axis", "from", "to", "evidence"}
                and trial["axis"] in AXES and state["axes"][trial["axis"]]["provenance"] != "explicit"
                and trial["from"] == state["axes"][trial["axis"]]["level"]
                and trial["to"] is not None and trial["to"] == _next_level(trial["axis"], trial["from"])
                and isinstance(trial["evidence"], list) and len(trial["evidence"]) < ADOPT_SESSIONS
                and all(_session_moment(e) for e in trial["evidence"])):
            return False
    names = {_transition(a, level) for a, levels in AXES.items() for level in levels[:-1]}
    if not (isinstance(transitions, dict) and all(
            key in names and isinstance(rec, dict) and set(rec) == {"rejections", "next"}
            and _count(rec["rejections"], 1, MAX_REJECTIONS) and _count(rec["next"], 0)
            for key, rec in transitions.items())):
        return False
    return (isinstance(frustration, dict) and set(frustration) == {"count", "last", "offered"}
            and _count(frustration["count"], 0, OFFER_SESSIONS) and isinstance(frustration["offered"], bool)
            and (frustration["last"] is None or bool(_session_moment(frustration["last"]))))


def _prefs_state(root: Path) -> tuple[dict, bool]:
    """(state, saved): the saved preference state with every optional key filled in, else defaults
    with any legacy ``dial_preference`` already imported (what the legacy-import event would save)."""
    path = _prefs_path(root)
    if not path.exists():
        axes = _default_axes()
        if _set(_key(_text(root / ".state" / "profile.md"), "dial_preference")):
            axes["frequency"] = {"level": "checks only", "provenance": "legacy", "wording": None}
        return {"version": PREFS_VERSION, "axes": axes, **json.loads(json.dumps(OPTIONAL_STATE))}, False
    damaged = InputError(f"{PREFS_FILE} is damaged; restore it or delete it to use the defaults")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise damaged from None
    if not isinstance(state, dict) or state.get("version") != PREFS_VERSION or not isinstance(state.get("axes"), dict) \
            or set(state["axes"]) != set(AXES) or not set(state) <= {"version", "axes", *OPTIONAL_STATE}:
        raise damaged
    if state.get("sampler_skipped", True) is not True:  # optional; present only once the sampler was skipped
        raise damaged
    if state.get("whats_new_seen", True) is not True:  # optional; present only once the what's-new line was seen
        raise damaged
    for axis, entry in state["axes"].items():
        if not isinstance(entry, dict) or set(entry) != {"level", "provenance", "wording"} \
                or entry["level"] not in AXES[axis] or entry["provenance"] not in PROVENANCES \
                or (entry["wording"] is None) == (entry["provenance"] == "explicit") \
                or not (entry["wording"] is None or isinstance(entry["wording"], str)):
            raise damaged
    state = {**json.loads(json.dumps(OPTIONAL_STATE)), **state}
    if not _valid_extras(state):
        raise damaged
    return state, True


def _compact(state: dict) -> dict:
    """The state as saved: optional keys still at their default are left out."""
    return {k: v for k, v in state.items() if k not in OPTIONAL_STATE or v != OPTIONAL_STATE[k]}


def _set(value: str) -> bool:
    """A profile value counts as set unless empty, ``none`` or a ``<...>`` template placeholder."""
    return bool(value) and value.casefold() != "none" and not (value.startswith("<") and value.endswith(">"))


def _sampler(state: dict, root: Path) -> dict:
    """The setup sampler: open only before setup is done and until skipped; it fills default axes only."""
    axes = state["axes"]
    open_ = workspace.read_setup_done(root) is None and not state.get("sampler_skipped", False)
    remaining = [a for a in AXES if axes[a]["provenance"] == "default"] if open_ else []
    return {"open": bool(remaining), "started": any(axes[a]["provenance"] == "sampler" for a in AXES),
            "remaining": remaining}


def _probe_block(state: dict, axis: str) -> str | None:
    """Why no trial may start on ``axis`` in the counted session now, else None."""
    sessions, entry = state["sessions"], state["axes"][axis]
    if sessions["current"] is None:
        return NO_SESSION
    if state["trial"] is not None:
        return f"a trial of {AXIS_NAMES[state['trial']['axis']]} is already running; only one at a time"
    if sessions["probed"] == sessions["current"]:
        return "this session already had its probe"
    if entry["provenance"] == "explicit":
        return f"{AXIS_NAMES[axis]} is the student's standing instruction and is never probed"
    if _next_level(axis, entry["level"]) is None:
        return f"{AXIS_NAMES[axis]} is already at its most independent level"
    rec = state["transitions"].get(_transition(axis, entry["level"]))
    if rec and rec["rejections"] >= MAX_REJECTIONS:
        return f"{_transition(axis, entry['level'])} was rejected {MAX_REJECTIONS} times; only the student can reopen it"
    if rec and sessions["count"] < rec["next"]:
        return f"{_transition(axis, entry['level'])} was rejected recently; it waits until eligible session {rec['next']}"
    return None


def _used_before(root: Path) -> bool:
    """Evidence the student used Mimir before: setup is done, or some course has a session log."""
    if workspace.read_setup_done(root) is not None:
        return True
    return any(next(_logs(Path(c["course_dir"])), None) is not None
               for c in ingest._courses(root) if _usable(root, c))


def _whats_new(state: dict, root: Path) -> str | None:
    """The one-time line for existing users; the seen marker stops it. New users get the marker at
    setup or at their first session, before any evidence of use exists."""
    return WHATS_NEW if not state.get("whats_new_seen") and _used_before(root) else None


def _prefs_out(state: dict, saved: bool, root: Path, in_session: bool = False) -> dict:
    """The settings as ``prefs`` reports them. ``in_session``: the output belongs to this session's
    counted session (an event naming it), the only place a running trial applies."""
    axes = state["axes"]
    parts = ", ".join(f"{AXIS_NAMES[a]} {axes[a]['level']} ({axes[a]['provenance']})" for a in AXES)
    return {"axes": axes, "saved": saved, "sampler": _sampler(state, root), "trial": state["trial"],
            "trial_paused": state["trial"] is not None and not in_session,
            "probe_axes": [a for a in AXES if _probe_block(state, a) is None], "whats_new": _whats_new(state, root),
            "line": f"Teaching settings: {parts}."}


def cmd_prefs(data: dict) -> dict:
    """The global teaching settings, the active trial and the setup sampler's state; read-only."""
    _check_keys(data, set())
    root = ingest._workspace_root()
    return _prefs_out(*_prefs_state(root), root)


def _axis_level(data: dict, *, level: bool) -> tuple[str, str | None]:
    axis = data.get("axis")
    if axis not in AXES:
        raise InputError(f"axis must be one of {', '.join(AXES)}")
    if level and data.get("level") not in AXES[axis]:
        raise InputError(f"level for {axis} must be one of {', '.join(AXES[axis])}")
    return axis, data.get("level")


def _this_session(state: dict, data: dict) -> str:
    """The counted session the event belongs to; any other session gives no evidence."""
    moment, current = _session_moment(data.get("session")), state["sessions"]["current"]
    if moment is None:
        raise InputError("session must be this session's `session.py now` datetime (its started: line)")
    if current is None or moment != _session_moment(current):
        raise InputError(NO_SESSION)
    return current


def _active_trial(state: dict, data: dict) -> dict:
    _this_session(state, data)
    if state["trial"] is None:
        raise InputError("no trial is running")
    return state["trial"]


def _ev_session(state: dict, data: dict) -> str:
    moment, sessions = _session_moment(data.get("session")), state["sessions"]
    if moment is None:
        raise InputError("session must be this session's `session.py now` datetime (its started: line)")
    if sessions["current"] is not None:
        last = _session_moment(sessions["current"])
        if moment == last:
            return "This session is already counted."
        if moment < last:
            raise InputError("session is earlier than the last counted session")
    sessions["count"] += 1
    sessions["current"] = data["session"]
    if state["trial"] is not None:  # continuing the active trial is this session's probe
        sessions["probed"] = data["session"]
    return f"Standard session {sessions['count']} counted for teaching settings."


def _ev_trial_start(state: dict, data: dict) -> str:
    current = _this_session(state, data)
    axis, _ = _axis_level(data, level=False)
    block = _probe_block(state, axis)
    if block:
        raise InputError(block)
    frm = state["axes"][axis]["level"]
    state["trial"] = {"axis": axis, "from": frm, "to": _next_level(axis, frm), "evidence": []}
    state["sessions"]["probed"] = current
    return f"Trial started: {AXIS_NAMES[axis]} {state['trial']['to']} instead of {frm}."


def _ev_positive(state: dict, data: dict) -> str:
    trial = _active_trial(state, data)
    current = state["sessions"]["current"]
    if current in trial["evidence"]:
        return "Already noted for this session; the trial continues."
    if any(_session_moment(e).date() == _session_moment(current).date() for e in trial["evidence"]):
        return "Evidence from the same day counts once; the trial continues."
    trial["evidence"].append(current)
    if len(trial["evidence"]) < ADOPT_SESSIONS:
        return "Noted; the trial continues."
    axis = trial["axis"]
    state["axes"][axis] = {"level": trial["to"], "provenance": "learned", "wording": None}
    state["trial"] = None
    return f"Saved for every course: {AXIS_NAMES[axis]} is now {trial['to']}."


def _ev_neutral(state: dict, data: dict) -> str:
    _active_trial(state, data)
    return "Neutral: nothing counted; the trial continues."


def _ev_pushback(state: dict, data: dict) -> str:
    trial = _active_trial(state, data)
    key = _transition(trial["axis"], trial["from"])
    rec = state["transitions"].setdefault(key, {"rejections": 0, "next": 0})
    rec["rejections"] += 1
    rec["next"] = state["sessions"]["count"] + rec["rejections"] + 1  # skip one, then two, eligible sessions
    state["trial"] = None
    back = f"Trial rejected: {AXIS_NAMES[trial['axis']]} back to {trial['from']}."
    if rec["rejections"] >= MAX_REJECTIONS:
        return f"{back} This change is not tried again unless the student asks."
    return f"{back} It may be tried again from eligible session {rec['next']}."


def _ev_reopen(state: dict, data: dict) -> str:
    axis, _ = _axis_level(data, level=False)
    entry = state["axes"][axis]
    if entry["provenance"] == "explicit":
        raise InputError(f"{AXIS_NAMES[axis]} is the student's standing instruction; a new lasting request changes it")
    if _next_level(axis, entry["level"]) is None:
        raise InputError(f"{AXIS_NAMES[axis]} is already at its most independent level")
    if state["transitions"].pop(_transition(axis, entry["level"]), None) is None:
        return f"Nothing to reopen: {AXIS_NAMES[axis]} was never rejected at {entry['level']}."
    return f"Reopened: Mimir may try {AXIS_NAMES[axis]} {_next_level(axis, entry['level'])} again."


def _ev_frustration(state: dict, data: dict) -> str:
    current = _this_session(state, data)
    seen = state["frustration"]
    if seen["last"] == current:
        return "Already counted for this session."
    seen["count"], seen["last"] = min(seen["count"] + 1, OFFER_SESSIONS), current
    if seen["count"] >= OFFER_SESSIONS and not seen["offered"] and state["axes"]["frequency"]["level"] != "checks only":
        seen["offered"] = True
        return FEWER_QUESTIONS_OFFER
    return "Noted; no offer."


def _ev_whats_new_seen(state: dict, data: dict) -> str:
    line = "What's new already seen." if state["whats_new_seen"] else "What's new seen: it will not repeat."
    state["whats_new_seen"] = True
    return line


def _ev_sampler_skip(state: dict, data: dict) -> str:
    line = "Sampler already skipped." if state["sampler_skipped"] else \
        "Sampler skipped. Unanswered settings stay at the defaults and adapt as you study."
    state["sampler_skipped"] = True
    return line


def _ev_sampler(state: dict, data: dict, root: Path) -> str:
    axis, level = _axis_level(data, level=True)
    current = state["axes"][axis]
    if state["sampler_skipped"]:
        return "The sampler was skipped; settings unchanged."
    if current["provenance"] != "default":  # never overwrites a sampler, learned, explicit or legacy value
        return f"Kept: {AXIS_NAMES[axis]} stays {current['level']} ({current['provenance']})."
    state["axes"][axis] = {"level": level, "provenance": "sampler", "wording": None}
    if _sampler(state, root)["remaining"]:
        return f"Noted for now: {AXIS_NAMES[axis]} {level}."
    levels = ", ".join(f"{AXIS_NAMES[a]} {state['axes'][a]['level']}" for a in AXES)
    return f"Tentative starting settings: {levels}. They keep adapting as you study."


def _ev_explicit(state: dict, data: dict) -> str:
    axis, level = _axis_level(data, level=True)
    wording = data.get("wording")
    if not isinstance(wording, str) or not wording.strip() or _has_control(wording) or len(wording) > MAX_WORDING:
        raise InputError(f"wording must be the student's request, one line of at most {MAX_WORDING} characters")
    state["axes"][axis] = {"level": level, "provenance": "explicit", "wording": " ".join(wording.split())}
    if state["trial"] is not None and state["trial"]["axis"] == axis:  # never probe against a standing instruction
        state["trial"] = None
    return f"Saved for every course: {AXIS_NAMES[axis]} is now {level}."


def cmd_pref_event(data: dict) -> dict:
    """Apply one teaching-settings event and save the state atomically (unchanged state writes nothing)."""
    event = data.get("event")
    if event not in EVENT_FIELDS:
        raise InputError(f"event must be one of {', '.join(EVENT_FIELDS)}")
    _check_keys(data, {"event"} | EVENT_FIELDS[event])
    if event in ("explicit", "sampler"):
        _axis_level(data, level=True)
    root = ingest._workspace_root()
    if event.startswith("sampler") and workspace.read_setup_done(root) is not None:
        raise InputError("the sampler runs only during setup")
    state, saved = _prefs_state(root)
    before = json.dumps(state, sort_keys=True)
    handlers = {"whats-new-seen": _ev_whats_new_seen, "sampler-skip": _ev_sampler_skip, "explicit": _ev_explicit,
                "session": _ev_session, "trial-start": _ev_trial_start, "positive": _ev_positive, "neutral": _ev_neutral,
                "pushback": _ev_pushback, "reopen": _ev_reopen, "frustration": _ev_frustration}
    line = _ev_sampler(state, data, root) if event == "sampler" else \
        handlers[event](state, data) if event in handlers else None
    changed = not saved or json.dumps(state, sort_keys=True) != before
    if changed:
        ingest._write_atomic(_prefs_path(root), json.dumps(_compact(state), indent=2) + "\n")
    out = _prefs_out(state, True, root, in_session="session" in EVENT_FIELDS[event])
    if line is None:  # legacy-import: saved now only when nothing was saved before
        line = ("Teaching settings already saved." if not changed else
                "Your earlier \"fewer questions\" choice is now guiding-question frequency checks only."
                if state["axes"]["frequency"]["provenance"] == "legacy" else
                "Teaching settings saved with the defaults.")
    if event == "frustration":
        out["offer"] = line == FEWER_QUESTIONS_OFFER
    return {**out, "changed": changed, "line": line}


COMMANDS = {
    "prefs": (cmd_prefs, "the global teaching settings: level and provenance per axis"),
    "pref-event": (cmd_pref_event, "apply one teaching-settings event (explicit request, setup sampler, legacy import, "
                                   "probe trial, what's new seen)"),
    "record": (cmd_record, "record mastery evidence and frustration overrides"),
    "now": (cmd_now, "the local time: ISO timestamp, evidence date, log name, last_session stamp and term"),
    "parse-date": (cmd_parse_date, "the student's exam date-and-time phrase as an exam value, or a refusal"),
    "start": (cmd_start, "pick the course, exam, delivery class and first topic for a session"),
    "check": (cmd_check, "status, counts and staleness for named topics"),
    "close": (cmd_close, "stamp the end of a session in its log once and report its length"),
    "gauge": (cmd_gauge, "set the course's knowledge-gauge-done marker in the session log, once"),
    "debrief": (cmd_debrief, "post-exam debrief state, cram bill, verifier disagreements and next-course flag"),
    "progress": (cmd_progress, "every mastery row with its evidence, counts and staleness, as a table"),
    "scope": (cmd_scope, "save the confirmed scope of one exam: question types and topics in and out"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("session.py",
                             ("Mimir session runner. Subcommands: now, parse-date, start, check, close, gauge, debrief, "
                              "progress, record, prefs, pref-event, scope. Reads one JSON object on stdin and prints one "
                              "JSON object on stdout. Only record, close, gauge, pref-event, scope and start with lasting "
                              "write."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
