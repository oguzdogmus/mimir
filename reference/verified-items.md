# Verified items: question sets, the check and failed checks

Shared by every Mimir skill that shows questions with answer keys (`quiz`, `study` with its knowledge gauge and Urgent drill, `past-questions`). The calling skill knows the course `term`, `course` and `course_dir`, and says what its student reads at once while a set's check runs. Check calls: `python3 "<mimir>/scripts/verify.py" <submit|settle|read|concede|summary>` with JSON on stdin in a quoted heredoc (`<<'EOF'`). The scripts own the check state in the session's check ledger; never read or edit the ledger or a pack yourself (the checker reads the pack).

## Check policy

1. A practice question may be shown before its check has finished, provided the check runs in the same turn.
2. An answer key, a worked answer or a hint is never shown before its question has a `correct` verdict (`settle` decision `show`).
3. A real question is shown with its label only after `submit` issued that label. It may then be shown at once, before the checker runs, like a practice question.

## Question sets

A question set is the group of questions prepared and checked together as one batch.

- A set holds at most 6 questions. A longer quiz runs as several sets. An Urgent set of up to 3 question types, with a worked item and a check item each, fits the cap.
- Per question keep: `item` (its stable item identity, the one `session.py record` gets), `topic`, `origin` (`practice`, or `real` with `source` and `page`), `question` (with its marks), `key` (a complete worked answer key), `hint` (one hint), `sources` (the course files the key rests on, `{path, page}`; a PDF needs its page), and `quote` `{path, page}` only when the key quotes professor material.
- A real question copies the paper's wording: at least 8 words in a row from the cited page (or the page after it, when it crosses the page break). `submit` refuses a real question whose words it cannot find there; then correct the citation, or make it practice.
- When the set's first question is a practice question, write it to the student at once, before any submit call or checker dispatch. "Write" means visible reply text the student reads (a chat message), never your own reasoning or a note that you are preparing or checking questions: the question itself, in full, in the reply, then the tool calls. Do not draft that question in your thinking first; compose it straight into the reply. Prepare the other questions after that text, in the same turn; the whole set goes to the checker as one batch. A real first question is written right after the `submit` call, with its label, before the checker runs.
- A fresh question after a miss, and a replacement for a withdrawn question, are sets of one.
- The turn that starts a set ends when its check has settled. Nothing else from the set is shown before that.

## Turn shape

Feedback on an answer and the next question share one turn, in this order:

1. Text that needs no tool call comes first, before any file read, checker definition or script call of the turn: feedback on the answer and the key, plus the first question of a new set when it is a practice question.
2. Tool calls: `session.py record` for the answer, any reference file the turn still needs and, when a new set starts, the calls that prepare and check it. Calls that do not depend on each other go in one step.
3. Text after the tool calls, each thing once: the next already checked question or the End-of-set hand-off, a question that had to wait for its check, the dropped line or a withdrawal line. The feedback and the key are never written again. Never report a check's or `record`'s result ("all keys passed", "recorded as a solo solve", "the topic is now shaky") and never point to a question "above". The one repeat: a turn that started a set ends, once its check settles, with what the student was to read at once written again in full: the set's first question (when it was not withdrawn or dropped), or the explanation or recipe the calling skill shows at once. On some hosts text written before tool calls is lost, so this keeps it on screen; say nothing about the repeat.

## The check

1. Submit: `verify.py submit` with `{"term": "...", "course": "...", "session": "<this session's identity, the one record gets>", "questions": [{"item": "...", "topic": "...", "origin": "...", "question": "...", "key": "...", "hint": "...", "sources": [...]}]}`. It issues each question's `label` (and `original` for a photo or scan), writes the set to the ledger and returns `batch` and `pack`, the path of the evidence pack.
   - Exit 2 naming `questions[N].<field>`: fix that field (a real question's `source` or `page` from `INDEX.md`, or its wording copied from the paper, or the question becomes `practice`) and run `submit` again with the whole set. If the same question is refused twice, leave it out (a question already on screen is withdrawn, see Failed checks).
   - Any other exit 2: print its stderr line and stop.
2. Dispatch ONE checker batch for the set, by the core rules' Checker dispatch, in the foreground. Its whole input is one line naming the pack: "Check the evidence pack at `<pack>`." Add nothing else: the pack holds the questions, keys, sources and notation, and the checker's own definition holds the reply format. The wait line is core rules' (say it at most once per session, and only when the student has nothing new to read this turn).
3. Settle: `verify.py settle` with `{"term", "course", "session", "batch": <batch>, "checker": "independent", "reply": "<the checker's reply, pasted unchanged>"}`; `"checker": "self"` for a same-context check. If the dispatch failed or errored, send `"dispatch_failed": true` instead of `reply`. Never type, repair or reorder the reply: `settle` reads it, refuses one without its pack token line (the batch stays unsettled: dispatch again and settle with the new reply), and returns `show`, `retry` and `dropped` lists of items.
4. If `retry` is empty, the check is done. Otherwise fix each `retry` question as Failed checks says, checking the source yourself (a question on screen whose question is flawed is withdrawn there, not rechecked), and `submit` the fixed questions again under the same `item`s as one recheck set; `submit` allows this once per question. Dispatch and settle that batch as in steps 2 and 3. A question that is not `correct` on its recheck is `dropped`.
5. Only `show` questions reach the student. Their keys, worked answers and hints are yours to show once the student has answered (or asked).

Lost a prepared question (for example after context compaction)? `verify.py read` with `{"term", "course", "session", "item"}` returns its question, key, hint, label and decision.

## Failed checks

Each question gets at most one recheck (step 4).

- **A question the student has not seen yet:** fix the key or the question; it is rechecked once. If it is dropped, it is not shown. Say once per set, when K > 0: "Dropped K question(s) my checker could not confirm."
- **A question on screen, key wrong** (`wrong`, or `source-conflict` on the key): fix the key; it is rechecked once. The student never sees the wrong key, and nothing is said in the moment. The ledger keeps the disagreement.
- **A question on screen, question flawed** (`ambiguous`, or a reason that faults the question rather than the key), **or its recheck also fails:** say one line, "Withdrawn: my checker could not confirm this question." It is not counted in the dropped line, and nothing is recorded for it. A replacement of the same question type follows as a set of one under a new `item`, prepared and checked in the same turn and shown only once its check settles; when it is dropped too, say the dropped line and go on.
- **A key the student challenges after seeing it:** check it against the sources. When you concede it was wrong, run `verify.py concede` with `{"term", "course", "session", "item", "reason": "<a few words>"}` (an escape), correct the key for the student, and go on.
