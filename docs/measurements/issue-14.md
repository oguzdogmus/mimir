# Issue 14 measurements

2026-11-01, Python 3.11, local Linux workspace. Median of five in-process runs, milliseconds. Reproduce from repository root with `uv run --with pytest python docs/measurements/issue-14-{before,after}.py`; run the before script against commit 36639c5 for the original readers. Temporary fixtures are deleted automatically. Index timings isolate the topic-update loop (identical existing rows and additions); they exclude PDF detection and disk writing.

| Input | Before | After |
|---|---:|---:|
| First-contact lookup, 1,000 logs of 10 KB each, valid first log | 41.987 | 4.158 |
| Built-in PDF reader, 200 pages sharing one Unicode font | 14.278 | 10.088 |
| Index topic loop, 2,000 existing rows plus 200 additions | 1883.827 | 4.634 |

Retained lazy log iteration (early-return first-contact and next-course-offer consumers), call-local font caching, and one topic-table parse per index update. Full-history consumers still read all required logs; debrief materializes its iterable because sessions and disagreements both consume it. Session planning now necessarily reads topic timing evidence; no constant-time session-start claim is made. Ingest confirmation reads at most three PDF pages per candidate instead of full decks, then extracts in bounded batches after confirmation; coverage and accumulated observations are checkpointed by the skill so interrupted reads resume.
