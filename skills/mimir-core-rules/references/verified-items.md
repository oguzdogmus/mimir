# Verified items: question sets, the check and failed checks

Shared by every Mimir skill that shows questions with answer keys (`quiz`, `study` with its knowledge gauge and Urgent drill, `past-questions`). The calling skill knows the course `term`, `course` and `course_dir`, and says what its student reads at once while a set's check runs. Gate calls: `python3 "<mimir>/scripts/verify.py" gate` with JSON on stdin in a quoted heredoc (`<<'EOF'`).

## Check policy

1. A practice question may be shown before its check has finished, provided the check runs in the same turn.
2. An answer key, a worked answer or a hint is never shown before its question has a `correct` verdict (gate decision `show`).
3. A real question waits for its check: it is shown, with its label, only after the final gate decides `show`.

## Question sets

A question set is the group of questions prepared and checked together as one checker batch.

- A set holds at most 6 questions. A longer quiz runs as several sets. An Urgent set of up to 3 question types, with a worked item and a check item each, fits the cap.
- Per question keep: `topic`, `origin` (`practice`, or `real` with `source`, `page` and `question`), optional `quote` `{path, page}`, the question with its marks, a complete worked answer key and one hint.
- When the set's first question is a practice question, write it to the student at once, before any gate call or checker dispatch. "Write" means visible reply text the student reads (a chat message), never your own reasoning or a note that you are preparing or checking questions: the question itself, in full, in the reply, then the tool calls. Prepare the other questions after that text, in the same turn; the whole set goes to the checker as one batch.
- A fresh question after a miss, and a replacement for a withdrawn question, are sets of one.
- The turn that starts a set ends when its check has settled. Nothing else from the set is shown before that.

## Turn shape

Feedback on an answer and the next question share one turn, in this order:

1. Text that needs no tool call: feedback on the answer, the key, and the next question when it is already checked or is a practice question that starts a new set.
2. Tool calls: `session.py record` for the answer and, when a new set starts, the calls that prepare and check it. Calls that do not depend on each other go in one step.
3. Text after the tool calls only for what depended on them: a question that had to wait for its check, the dropped line or a withdrawal line. Inside a set, nothing is written after `record`. Never report a check's result ("all keys passed", "the check came back clean") or repeat a question already written. If the set's first question is not in your reply text yet (only in your thinking), write it now, in full: late is better than unseen.

## The check

1. Gate: `verify.py gate` with `{"term": "...", "course": "...", "items": [{"topic": "...", "origin": "...", ...}]}`, without verdicts. Items carry only `topic`, `origin`, `source`, `page`, `question`, `quote`, `verdicts` and `dispute`; question text, answer keys and hints stay with you. Every gate call of the set (here and in steps 3–5) sends the full item list in the same order, so each item keeps its number `N`.
   - Exit 2 naming `items[N].<field>`: a real item's `source`, `page` or `question` gets the correct citation from `INDEX.md` or the item becomes `practice`; any other field is fixed; rerun. In this step only, if the same field is named twice, remove that item (a question already on screen is withdrawn, see Failed checks) and rerun. After step 2 no item is ever removed: if a fix fails twice, make that item `practice` (no `source`, `page`, `question` or `quote`), keep its `verdicts`, and rerun.
   - Any other exit 2 (not naming `items[N].<field>`): print its stderr line and stop.
2. If `verify` is empty, that gate is the final one: go to step 5. Otherwise dispatch ONE checker batch with all `verify` items, by the core rules' Checker dispatch, in the foreground. The wait line is core rules' (say it at most once per session, and only when the student has nothing new to read this turn). Pass the resolved `<mimir>/scripts/pdftext.py` path and, per item, its number `N`, the gate's `label`, the question, the answer key, and its sources as absolute paths (`course_dir` + registry path) with pages, or short excerpts. A real item always gets its `source` as an absolute path with its `page` and `question`; an `ocr` one also gets the gate's `original`. An item with a `quote` also gets the quote's absolute path and page with one line: "The key claims to quote this page: confirm it does." Leave the reply format and the verdicts to the checker's own definition; do not restate or narrow them.
3. Read the reply. Split each line on its first three `|` into `N`, verdict, fake-real and reason; strip and lowercase the verdict and fake-real cells. Use only the first line for each `N` that was in the batch you sent. Append each verdict to item N's `verdicts`. `fake-real yes` with `correct` is recorded as `source-conflict`. An item with no usable line or an unknown verdict word gets `ambiguous`; if the dispatch fails or errors, every item in that batch gets `ambiguous`. Remember each item's latest fake-real answer. Rerun the gate with the verdicts.
4. If `retry` is empty, go to step 5. Otherwise fix each `retry` item as Failed checks says, checking the source yourself (a question on screen whose question is flawed is withdrawn there, not rechecked), and set its `dispute` to a few of your own words naming the disputed point (e.g. `step 3`). Keep its `verdicts`. Rerun the gate for the fixed labels, then make one recheck batch with all `retry` items, the same way as step 2. Read the reply as in step 3.
5. Final gate. First, every item whose latest checker line said `fake-real yes` becomes `practice` (drop `source`, `page` and `question`, keep `verdicts`): a shown item never keeps a real label the checker disputed. Then run the gate with all verdicts. Only `show` items reach the student. Append the gate's `disagreements` lines verbatim under `## Verifier disagreements` in the session log.

## Failed checks

Each question gets at most one recheck (step 4).

- **A question the student has not seen yet:** fix the key or the question; it is rechecked once. If the final gate drops it, it is not shown. Say once per set, when K > 0: "Dropped K question(s) my checker could not confirm."
- **A question on screen, key wrong** (`wrong`, or `source-conflict` on the key): fix the key; it is rechecked once. The student never sees the wrong key, and nothing is said in the moment. The gate's `fixed` line logs the disagreement.
- **A question on screen, question flawed** (`ambiguous`, or a reason that faults the question rather than the key), **or its recheck also fails:** say one line, "Withdrawn: my checker could not confirm this question." It is not counted in the dropped line, and nothing is recorded for it. A replacement of the same question type follows as a set of one, prepared and checked in the same turn and shown only once its check settles; when it is dropped too, say the dropped line and go on.
