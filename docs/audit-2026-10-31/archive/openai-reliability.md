# Original report: openai-reliability

Source: <t3-thread://v2/4c5bcb11-81b0-41c1-95df-d92fe94a74a7/thread:delegated-task:command%3Amcp%3A135b902e-d7b3-42f5-997f-5cb0739fa9c2%3Adelegate-task%3A2223592b-339e-4b1d-a693-c83885677e39>

Historical agent report, not a new verification. Findings may overlap or disagree; use the consolidated findings and accepted decisions for implementation.

I’ll audit the scripts and skill invocations, run the tests, and reproduce potential failures in temporary directories. I’ll leave the repo unchanged.

---

I found two reliability issues worth checking closely: the skills use GNU-only date commands, and session startup reads the full log history to recover first contact. The test run couldn’t start because `pytest` isn’t installed; I’ll try an isolated runner and continue with targeted checks.

---

Targeted checks confirmed that retake linking accepts a later term in the same year, and the built-in PDF reader crashes on a malformed string escape. I’m also measuring the indexing loop and log reads to assess their impact on larger workspaces.

---

The indexing benchmark shows quadratic growth: 500, 1,000, and 2,000 topics took about 0.36, 1.46, and 5.57 seconds. First-contact lookup read all 100 logs even though the answer was in the first one. I also reproduced a race between pointer updates caused by their shared temporary filename. The isolated test suite is still running.

---

Read-only audit complete. **970 tests passed** in 87 seconds using isolated pytest dependencies; repo status remains clean. Ranked findings:

1. **GNU-only date commands break macOS study flows.**  
   **Location:** [session.md:9](/home/oguz/mimir/skills/mimir-study/references/session.md:9), [session.md:16](/home/oguz/mimir/skills/mimir-study/references/session.md:16)  
   **Impact:** High · **Effort:** Small  
   **Evidence:** Skills require `date -Iseconds` and `date -d '<phrase>'`; stock macOS BSD `date` does not support these invocations. Failed parsing can turn a supplied exam date into `unknown`.  
   **Proposed fix:** Provide a Python clock/date helper with defined relative-date formats; use it consistently across skills. Return session timestamp, evidence date, and log name together.

2. **PDF fallback bypasses the file-size guard.**  
   **Location:** [pdftext.py:389](/home/oguz/mimir/scripts/pdftext.py:389), [ingest.py:240](/home/oguz/mimir/scripts/ingest.py:240)  
   **Impact:** High · **Effort:** Small  
   **Evidence:** `pdf_info()` avoids reading PDFs above 128 MiB, returning `"ocr", None`; when Poppler is missing or fails, `builtin_text()` immediately executes `path.read_bytes()` without that guard. Requesting one page can load an arbitrarily large PDF plus copied object streams.  
   **Proposed fix:** Check size before builtin extraction and return an actionable refusal for oversized files. Bound accumulated page output during extraction, rather than only truncating after joining it.

3. **Ingest requires reading every slide deck fully before filing confirmation.**  
   **Location:** [mimir-ingest/SKILL.md:15](/home/oguz/mimir/skills/mimir-ingest/SKILL.md:15)  
   **Impact:** Medium · **Effort:** Small  
   **Evidence:** “Read every item … Read past papers and slides fully.” With the 20-page PDF-call limit, a 500-page deck requires at least 25 extraction calls before the confirmation table; unchanged inbox items repeat this work on subsequent runs.  
   **Proposed fix:** Classify from filenames and bounded representative pages before confirmation. After confirmation, process fingerprint material in bounded batches, retaining page coverage so interrupted ingest can resume.

4. **Topic indexing is quadratic.**  
   **Location:** [ingest.py:709](/home/oguz/mimir/scripts/ingest.py:709), [ingest.py:717](/home/oguz/mimir/scripts/ingest.py:717)  
   **Impact:** Medium · **Effort:** Small  
   **Evidence:** Each topic rescans the section and reparses existing rows; `_split_row(cell)` also repeats inside the comparison generator. Fresh temporary-course benchmarks: 500 topics **0.358s**, 1,000 **1.462s**, 2,000 **5.574s**.  
   **Proposed fix:** Parse both tables once into ordered rows, a registry-position map, and a topic-pair set. Apply updates, then render each section once.

5. **Every session startup eagerly reads the entire log history.**  
   **Location:** [session.py:332](/home/oguz/mimir/scripts/session.py:332), [session.py:353](/home/oguz/mimir/scripts/session.py:353), [session.py:635](/home/oguz/mimir/scripts/session.py:635)  
   **Impact:** Medium · **Effort:** Small  
   **Evidence:** `_first_contact()` calls `_logs()`, which builds a list containing every log’s complete text before searching. Instrumented reproduction read **all 100 logs**, although `first_contact:` appeared in the first file. Debrief subsequently reads the logs again.  
   **Proposed fix:** Make log iteration lazy so first-contact lookup stops immediately. Reuse loaded logs within debrief; consider storing first contact in bounded course state.

6. **Shared PDF fonts are repeatedly decoded, consuming the budget and corrupting later text.**  
   **Location:** [pdftext.py:205](/home/oguz/mimir/scripts/pdftext.py:205), [pdftext.py:400](/home/oguz/mimir/scripts/pdftext.py:400)  
   **Impact:** Medium · **Effort:** Small  
   **Evidence:** Every requested page calls `_fonts()`, reinflating shared ToUnicode streams against one cumulative budget. A reduced-budget reproduction decoded the same font twice: first `"Ω"`, then `"A"` after exhaustion triggered the Latin-1 fallback.  
   **Proposed fix:** Cache decoded streams and parsed fonts by object number for the extraction call. Report budget exhaustion explicitly instead of silently substituting a different encoding.

7. **Malformed PDF escapes crash the builtin reader.**  
   **Location:** [pdftext.py:253](/home/oguz/mimir/scripts/pdftext.py:253)  
   **Impact:** Medium · **Effort:** Trivial  
   **Evidence:** `_page_text(b'BT (bad\\8) Tj ET', {})` raises `AttributeError`: `isdigit()` accepts `8`, but `[0-7]{1,3}` returns `None`, followed by `octal.group(0)`. CLI callers receive an opaque internal error.  
   **Proposed fix:** Enter the octal branch only for `0`–`7`; handle other escaped characters through the existing literal fallback.

8. **Root-pointer updates share one temporary filename.**  
   **Location:** [workspace.py:252](/home/oguz/mimir/scripts/workspace.py:252)  
   **Impact:** Medium · **Effort:** Small  
   **Evidence:** Both writers use `root.tmp`. An interleaved reproduction made writer B replace the shared file, then writer A raised `FileNotFoundError`. Relocation treats pointer-write failure as grounds to roll back the move.  
   **Proposed fix:** Use a unique same-directory `mkstemp` with cleanup. Serialize relocation and pointer updates with a workspace-operation lock.

9. **Retake validation accepts a future semester in the same year.**  
   **Location:** [fingerprint.py:413](/home/oguz/mimir/scripts/fingerprint.py:413)  
   **Impact:** Low · **Effort:** Small  
   **Evidence:** A temporary-workspace call with current `2026-Spring` and prior `2026-Fall` succeeded: “Linked 2026-Spring/CS201 Theory read-only to 2026-Fall/CS201 Theory.” Validation compares only years after excluding identical terms.  
   **Proposed fix:** Share the existing semester-order logic from `session._term_key()` and require the prior term to sort strictly before the current term.
