# Trust every session measurements

The baseline numbers in `docs/trust-every-session-design.md` come from the scripts in `docs/measurements/trust-every-session/`. They are dev-only (standard library, Python 3.11+); no skill uses them. They read Claude Code session transcripts and print numbers, never transcript text, with one exception: `checker_reads.py --detail` prints the reply of each checker run that disagreed, which shows course content.

The baseline was measured on 2026-11-12 from the maintainer's study transcripts of 30 Oct to 10 Nov 2026 (Opus tutor, Sonnet checker). The transcripts are private and are not in the repository.

## Run them

Claude Code keeps one folder of transcripts per working directory under `~/.claude/projects/`. Pass the folders of the learning folder. Run from the repository root:

```sh
P="$HOME/.claude/projects/-home-me-Learning"
python3 docs/measurements/trust-every-session/session_latency.py "$P" --since 2026-11-01 --until 2026-11-12
python3 docs/measurements/trust-every-session/answer_time.py "$P" --since 2026-11-01 --until 2026-11-12
python3 docs/measurements/trust-every-session/checker_reads.py "$P" --until 2026-11-12
python3 docs/measurements/trust-every-session/label_anchor_probe.py "$P" --until 2026-11-12 --learning-root ~/Learning
```

`--since` is the first day counted for latency and `--until` the first day not counted, both in UTC. Leave `--until` out to measure everything up to now. The baseline used two project folders, because the learning folder had been moved once.

| Script | What it prints |
|---|---|
| `session_latency.py` | Model step before a tool call; wall time of a plain dialogue turn, of an answer turn that only records, and of a turn with a checker dispatch, each with its time to first text; the gate, checker, gate cycle and the checker's share of it; how many dispatches ran in the background; verdict words over all sessions |
| `answer_time.py` | How long the student takes to answer, overall and for the first question after a check |
| `checker_reads.py` | Per checker run: calls that opened a source named in the dispatch prompt against other calls; batch sizes; labels in the prompts; verdict words; fake-real cells |
| `label_anchor_probe.py` | For each real question sent to the checker: the longest run of words its wording shares with the text of the cited page |
| `aggregate.py`, `timeline.py` | The same latency measures for single session files passed as arguments, such as acceptance runs: `aggregate.py SESSION.jsonl ...` for totals, `timeline.py SESSION.jsonl --detail` for one line per turn |

## How the numbers are taken

- Each transcript row has a timestamp that marks when its block was complete. Time to the first token cannot be measured; "time to first text" is the time until the first text block was complete.
- A forked session copies the turns of its parent. Student turns are counted once, by message id. Checker runs are counted once, by dispatch prompt.
- A turn longer than 900 s is left out of the latency numbers as an outlier.
- A turn ends at its last assistant row or tool-result row. Hook and system rows are stamped when the next student message arrives, so they do not end a turn.
- `checker_reads.py` uses a heuristic: a call opens a named source when the name of the file it targets appears in the dispatch prompt. A shell loop that builds file names from variables counts as "other".

## Numbers without a script

Two baseline numbers were one-off counts and have no script here: the share of tutor usage spent on check steps (11.7% of API messages, 12.4% of cache-read tokens since 2026-11-01), and the 14 of 16 background dispatches of the lean acceptance host, which `aggregate.py` prints for the acceptance run's session files.

## After a change

Section 9 of the design sets the targets. Rerun `session_latency.py` and `answer_time.py` with `--since` set to the day the change shipped and compare:

| Measure | Baseline | Target |
|---|---|---|
| Answer turn that only records: time to first text | 16.8 s median | at most 15 s |
| Turn with a checker dispatch: time to first text | 51.7 s median | at most 15 s |
| Answer to next question | 16.8 s to 86.8 s median | at most 25 s |
