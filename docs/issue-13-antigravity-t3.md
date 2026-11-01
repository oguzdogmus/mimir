# Issue 13 — Antigravity Live Verification Report (via T3 Code)

Date: `2026-11-01`
Repository: `/home/oguz/mimir`
Branch / HEAD: `issue-13-portable-verification` (`d68ed6d54c760003656092c212a14f6bdf546f59`)
Draft PR (background reference only): `https://github.com/oguzdogmus/mimir/pull/24`

---

## 1. Host, Model, Tooling, and Isolation Setup

### Host & Runtime Identity
- **Model**: `gemini-4-argon`
- **Orchestrator / Host**: T3 Code (`t3code-bin 0.1.5-1`) driving Antigravity ACP (`agy_acp_server.par` metadata version `1.4.1`, release `2e37012ceb2a5c7fc7309b6e6596234fb637ee3c62a5199f65d4cbe777871384`, harness `localharness_external`; direct CLI `agy --version` reports `1.4.12`).
- **Runtime tools**: Python `3.14.8`, Poppler `pdftotext` `26.08.0`.
- **Main conversation ID**: `3941963f-7403-41f2-8d6b-71e3c8ec8d59`
- **Available native agent tools**:
  - Subagent dispatch: `define_subagent`, `invoke_subagent` (built-in types `research`, `self`, plus custom defined `mimir-verifier`), `send_message`, `manage_subagents`, `run_workflow`.
  - File & command tools: `client_view_file`, `view_file`, `write_to_file`, `replace_file_content`, `run_command`.
- **Observed host permission model**:
  - Unlike prior direct headless `agy` CLI runs (which auto-denied `run_command`), T3-managed Antigravity permitted `run_command` and native subagent execution.
  - `run_command` executes inside an unprivileged Linux user namespace mapping container UID `0 -> 1000` (`/proc/self/uid_map`: `0 1000 1`) with namespace `CapEff: 000001ffffffffff` (including `CAP_DAC_OVERRIDE` over UID-1000-owned files).
  - Native file tools enforce strict workspace directory allowlists:
    - `client_view_file`: `/home/oguz/mimir` only.
    - `view_file` / `write_to_file` / `replace_file_content`: `['/home/oguz/mimir', '/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32', '/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/config/skills', '/home/oguz/mimir/.gemini/skills', '/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-cli/skills', '/home/oguz/mimir/.agents/skills']`.

### Disposable Workspace Isolation
- Base preserved evidence directory (inside Antigravity's allowed conversation `scratch/` tree so native file tools `view_file`, `write_to_file`, and `replace_file_content` operate on Mimir memory files without shell edits):
  `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live`
- Per-scenario isolated directories:
  - Scenario 1: `.../issue13-live/s1/{home,outside,wrappers}`
  - Scenario 2: `.../issue13-live/s2/{home,outside,wrappers}`
  - Scenario 4: `.../issue13-live/s4/{home_userns,home_dac,outside,ro_dir_userns,ro_dir_dac}`
- Subprocess-only isolation:
  - Parent CLI calls passed `HOME="$S*/home"` per subprocess (no global environment mutation).
  - Independent verifier subagent calls received per-scenario `wrappers/pdftext.py` setting `workspace.DEFAULT_ROOT = "<S*>/home/learning"` and `workspace.POINTER_PATH = "<S*>/home/.config/mimir/root"` before calling `pdftext.main()`.
  - Verified before and after all scenarios: `/home/oguz/learning` does not exist (`No such file or directory`), and `/home/oguz/.config/mimir/root` remained untouched (`mtime` `Eki 19 20:29`, 20 bytes, never read or written).
- Generated PDF fixtures (`make_fixtures.py`, valid PDF 1.7 with FlateDecode streams, 794 bytes):
  - `cs201-past-paper.pdf` (1 page, printed text: `CS201 Theory - Sample Past Paper` / `Q1 (10 marks): What is 2 plus 2?` / `Answer: 4`).
  - `cs201-unreadable-scan.pdf` (1 page, gray image XObject only, zero text layer).

---

## 2. Summary of Scenario Verdicts

| Scenario | Status | Summary |
|---|---|---|
| **1. Host capability, `pdftext.py`, and `helpers/verifier.md` independent dispatch** | **PASS** | `pdftext.py` enforced learning-root boundary and `attachment` exact-path scope; native subagent `mimir-verifier` (`define_subagent` + `invoke_subagent`) ran `pdftext.py pages` and returned `correct`, `wrong`, and `ambiguous` (for both scan-only empty text and missing PDF). |
| **2. Urgent first-contact workflow (`"exam tomorrow, help"` + outside-root PDF, missing workspace/course)** | **PASS** *(with host allowlist boundary noted)* | Executed full ordered `session.md` -> `urgent.md` §1–§3 flow on empty `HOME`: parsed date, emitted `Urgent delivery: exam in 10 hours` first, read outside-root PDF via `attachment` scope before classifying `CS201 Theory` / `2026-Fall` / `past-papers`, filed, indexed, fingerprinted, verified drill batch via independent subagent, and produced first verified `[real: ...]` drill item. |
| **3. Two-batch `checker: self` fallback & once-only fallback disclosure** | **UNEXERCISED (native independent agent available)** | Native independent subagents are available and succeeded in Antigravity/T3. Per test rules, fallback was not fabricated; Scenario 2 logged `checker: independent (...)` and emitted `0` fallback notices in both student output and `transcript.jsonl`. |
| **4. Permission boundaries: host denial vs. OS copy-with-denied-delete** | **PASS (OS VFS DAC + host file-tool denial); LIMITATION (default userns `CAP_DAC_OVERRIDE`)** | Native `view_file`/`client_view_file` genuinely denied `/tmp/...` outside workspace allowlist. Default ACP userns (`0 -> 1000`, `CAP_DAC_OVERRIDE`) bypassed `chmod 0555` `unlink()`; dropping `dac_override` via `setpriv --bounding-set=-dac_override` triggered real kernel `EACCES` on `unlink()`, returning `"action": "copied"`, retaining original, and indexing copied file cleanly. |

---

## 3. Scenario 1 Evidence — `pdftext.py` & Independent Verifier Dispatch

### 3.1 Direct `pdftext.py` Boundary & Extraction Checks
1. **Outside learning root without `attachment` (rejected, exit 2)**:
   ```text
   pdftext.py: /home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s2/outside/cs201-past-paper.pdf is not inside the learning root /home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s2/home/learning
   EXIT:2
   ```
2. **Outside learning root with exact `attachment` path (exit 0)**:
   ```json
   {"path": ".../s2/outside/cs201-past-paper.pdf", "pages": 1, "first": 1, "last": 1, "engine": "pdftotext", "text": [{"page": 1, "text": "CS201 Theory - Sample Past Paper\nQ1 (10 marks): What is 2 plus 2?\nAnswer: 4"}], "line": "Read page 1 of .../s2/outside/cs201-past-paper.pdf (pdftotext)."}
   ```
3. **Filed image-only scan PDF (`cs201-unreadable-scan.pdf`, exit 0, empty text)**:
   ```json
   {"path": ".../s1/home/learning/2026-Fall/CS201 Theory/past-papers/cs201-unreadable-scan.pdf", "pages": 1, "first": 1, "last": 1, "engine": "pdftotext", "text": [{"page": 1, "text": ""}], "line": "No text on page 1 of .../cs201-unreadable-scan.pdf (likely a scan): read the page as an image instead."}
   ```

### 3.2 Native Independent Verifier Subagent Dispatch
- Defined subagent `mimir-verifier` via `define_subagent` using the body of `/home/oguz/mimir/helpers/verifier.md` (`enable_write_tools: true`, required in Antigravity so the subagent receives `run_command` to invoke `pdftext.py`; `enable_mcp_tools: false`, `enable_subagent_tools: false`).
- Dispatched via `invoke_subagent` (`Model: "inherit"`, child conversation ID `708ccb513dd8721c254456a02a60d069`, transcript `.../brain/708ccb513dd8721c254456a02a60d069/.system_generated/logs/transcript.jsonl`).
- Verified child tool calls in child `transcript.jsonl`:
  - Step 1: 3 parallel `run_command` invocations calling `python3 ".../s1/wrappers/pdftext.py" pages` on `cs201-past-paper.pdf` p.1, `cs201-unreadable-scan.pdf` p.1, and `missing-paper.pdf` p.1.
  - Step 5: `send_message` returning verdicts to parent.
- **Actual verbatim reply from `708ccb513dd8721c254456a02a60d069`**:
  ```text
  1 | correct | no | matches cs201-past-paper.pdf p.1 Q1 and 2 + 2 = 4
  2 | wrong | no | answer key gives 2 + 2 = 5 instead of 4
  3 | ambiguous | no | could not read /home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s1/home/learning/2026-Fall/CS201 Theory/past-papers/cs201-unreadable-scan.pdf p.1
  4 | ambiguous | no | could not read /home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s1/home/learning/2026-Fall/CS201 Theory/past-papers/missing-paper.pdf p.1
  ```
- **Limitation noted**: Antigravity's `define_subagent` bundles `run_command` with file-write tools behind a single boolean `enable_write_tools: true`. Read-only behavior in `mimir-verifier` is therefore prompt-enforced rather than sandbox-enforced (verified via child transcript: zero write/edit tool calls occurred).

---

## 4. Scenario 2 Evidence — Live Urgent First-Contact Workflow

Simulated opening prompt on empty `HOME` (`.../s2/home`, no workspace, no course):
`"exam tomorrow, help"` with outside-root attachment `.../s2/outside/cs201-past-paper.pdf`.

### 4.1 Ordered Actual Calls and Results
1. **`session.py now` (`{}`)**:
   `{"now": "2026-11-01T13:36:06+02:00", "date": "2026-11-01", "log_name": "2026-11-01-1336", "last_session": "2026-11-01 13:36", "term": "2026-Fall", "line": "Now: 2026-11-01T13:36:06+02:00."}`
2. **`session.py start` (`{"now": "2026-11-01T13:36:06+02:00"}`)** -> exit `2`:
   `session.py: no workspace at .../s2/home/learning; run workspace.py init first`
   *(Routed per `mimir-core-rules` Study first-contact rule to `urgent.md` §1 Lazy setup; nothing emitted yet.)*
3. **`session.py parse-date` (`{"now": "2026-11-01T13:36:06+02:00", "phrase": "tomorrow"}`)**:
   `{"date": "2026-11-02", "line": "Exam date: 2026-11-02."}`
4. **`plan.py class` (`{"now": "2026-11-01T13:36:06+02:00", "exam": "2026-11-02", "topics": []}`)**:
   `{"class": "Urgent", "reason": "floor", "hours_to_exam": 10.4, "days_to_exam": 1, "route_minutes": {"low": 0, "point": 0, "high": 0}, "capacity_minutes": 21.66, "confidence": "rough: no topics timed yet, ±50%", "line": "Urgent delivery: exam in 10 hours"}`
   - **Initial student-facing class line (emitted before filing)**: `Urgent delivery: exam in 10 hours`
5. **`pdftext.py pages` with `attachment` scope (executed strictly at `13:36:06` BEFORE classification and `workspace.py file` at `13:36:23`)**:
   Extracted page 1 text: `CS201 Theory - Sample Past Paper\nQ1 (10 marks): What is 2 plus 2?\nAnswer: 4`
   - **Inferred classification**:
     - `course`: `CS201 Theory` (from printed header `CS201 Theory`)
     - `term`: `2026-Fall` (no outline/slides semester printed; fallback to `session.py now`'s `term`)
     - `role`: `past-papers` (printed past exam paper)
6. **`workspace.py file`**:
   `{"source": ".../s2/outside/cs201-past-paper.pdf", "dest": ".../s2/home/learning/2026-Fall/CS201 Theory/past-papers/cs201-past-paper.pdf", ..., "action": "moved", "line": "Moved cs201-past-paper.pdf to .../s2/home/learning/2026-Fall/CS201 Theory/past-papers/"}`
7. **`ingest.py index`**:
   Indexed `dest` with `[{"topic": "Basic arithmetic addition", "anchor": "page=1"}]` -> `Indexed 1 file ... (1 new, 1 topic added).`
8. **`fingerprint.py write`**:
   Wrote phrasing and `question_types` (`Basic arithmetic addition`, `marks: "10"`, `sources: ["past-papers/cs201-past-paper.pdf"]`) -> `18 of 60 lines, 2 entries, 0 tentative`.
9. **Native file edit (`replace_file_content`) on `<root>/.state/profile.md`**:
   Added `| CS201 | exam | 2026-11-02 |` under `## Exam dates`.
10. **Rerun `session.py start` (`{"now": "2026-11-01T13:36:06+02:00", "term": "2026-Fall", "course": "CS201 Theory"}`)**:
    Returned `inferred: false`, `exam: "2026-11-02"`, `first_contact: null`, `remaining: [{"name": "Basic arithmetic addition", "status": "unseen"}]`, `class.class: "Urgent"`, `line: "Urgent delivery: exam in 10 hours"`.
11. **Session log creation (`write_to_file`) & `save.md` read (`view_file`)**, followed by `urgent.md` §2 reads (`view_file` on `fingerprint.md`, `INDEX.md`, `mastery.md`).
12. **`session.py now` -> `session.py check` -> `plan.py triage`**:
    `{"drill": [{"name": "Basic arithmetic addition", "marks": 10, "frequency": 1, "weight": 3, "minutes": 75, "pph": 8}], "skip": [], "budget_minutes": 207.42, "basis": "papers", "line": "Drilling: Basic arithmetic addition."}`
13. **Initial `verify.py gate`**:
    `{"verify": [1, 2], "retry": [], "disagreements": [], "line": "Gate: 2 items, 2 to verify."}`
    - Item 1 label: `[real: past-papers/cs201-past-paper.pdf, p.1]`
    - Item 2 label: `[practice, not from a real paper]`
14. **Independent `mimir-verifier` subagent dispatch (`invoke_subagent`, conversation `69249fe05d7a686fcc6fd5870fe206bd`)**:
    Child ran `pdftext.py pages` on Scenario 2's filed `cs201-past-paper.pdf` p.1 and returned:
    ```text
    1 | correct | no | p.1 Q1 matches and 2 + 2 = 4 is right
    2 | correct | no | practice addition 3 + 5 = 8 is right
    ```
15. **Final `verify.py gate` with verdicts**:
    `{"results": [{"n": 1, ..., "label": "[real: past-papers/cs201-past-paper.pdf, p.1]", "decision": "show", "counts_for_mastery": true}, {"n": 2, ..., "label": "[practice, not from a real paper]", "decision": "show", "counts_for_mastery": true}], "verify": [], "retry": [], "disagreements": [], "line": "Gate: 2 items, 2 to show."}`

### 4.2 Destination `INDEX.md` Registry & Topics (`.../s2/home/learning/2026-Fall/CS201 Theory/INDEX.md`)
```markdown
## Registry
| path | term | role | pages | fidelity |
|---|---|---|---|---|
| past-papers/cs201-past-paper.pdf | 2026-Fall | past-papers | 1 | text |

## Topics
| topic | file#anchor |
|---|---|
| Basic arithmetic addition | past-papers/cs201-past-paper.pdf#page=1 |
```

### 4.3 Scenario 2 Session Log (`.../s2/home/learning/2026-Fall/CS201 Theory/.state/logs/2026-11-01-1336.md`)
```markdown
## Session
started: 2026-11-01T13:36:06+02:00
class: Urgent (floor)
first_contact: 2026-11-01T13:36:06+02:00
checker: independent (Antigravity define_subagent/invoke_subagent: mimir-verifier)
```

### 4.4 Produced Student-Facing Output (`.../s2/student_output_transcript.md`)
```text
Urgent delivery: exam in 10 hours
Moved cs201-past-paper.pdf to /home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s2/home/learning/2026-Fall/CS201 Theory/past-papers/
Drilling: Basic arithmetic addition.
Checking my answers before you study them, about 30 seconds.

[real: past-papers/cs201-past-paper.pdf, p.1]
Q1 (10 marks): What is 2 plus 2?

Worked answer:
Add the two integers: 2 + 2 = 4.
Final answer: 4.
Say "steps" to open this answer one step at a time.

[practice, not from a real paper]
Practice (10 marks): What is 3 plus 5?
```

### 4.5 Scenario 2 Limitations
- **Single-turn interactive boundary**: Per `urgent.md` §3.3.2, after showing the worked real item and posing the verified check question, Mimir must wait for the student's answer before showing the check key, calling `session.py record`, or running `urgent.md` §4 close. No student reply was fabricated.
- **Workspace allowlist requirement for native file tools**: Antigravity's `view_file` / `write_to_file` / `replace_file_content` only permit paths inside configured workspace directories (e.g., `--add-dir` or T3's provider/workspace directories). If a student's learning root (`~/learning`) or attachment directory is not included in Antigravity's workspace list at launch, native file-edit tools on `<root>/.state/*` will be denied even if `run_command` is allowed.

---

## 5. Scenario 3 Evidence — Provenance & Fallback Notice Count

- **Native independent subagent availability**: Available (`define_subagent` + `invoke_subagent`) and exercised live in both Scenario 1 (`708ccb513dd8721c254456a02a60d069`) and Scenario 2 (`69249fe05d7a686fcc6fd5870fe206bd`).
- **Fallback scenario status**: **Unexercised** (per instructions: *"If independent tool is available, do not pretend otherwise: mark fallback scenario unexercised and report independent provenance."*).
- **Session log provenance**: `checker: independent (Antigravity define_subagent/invoke_subagent: mimir-verifier)`.
- **Fallback notice count (`"Answer checks are running in this same context; an independent checker is unavailable."`)**:
  - Scenario 2 `student_output_transcript.md`: `0`
  - Main session `transcript.jsonl` visible `PLANNER_RESPONSE` `content`: `0`

---

## 6. Scenario 4 Evidence — Host Denial vs. OS Permission Copy/Delete vs. Mocks

### 6.1 Actual Host Tool Permission Denial (Observed Live)
Probed `/tmp/mimir-issue13-antigravity-t3/probe.txt` with Antigravity's file-reading tools:
- `client_view_file`:
  `Tool client_view_file failed with error message: Access to path '/tmp/mimir-issue13-antigravity-t3/probe.txt' is denied. It is outside the workspace '/home/oguz/mimir'.`
- `view_file`:
  `Tool view_file failed with error message: Access to path '/tmp/mimir-issue13-antigravity-t3/probe.txt' is denied. It is outside the allowed workspace directories: ['/home/oguz/mimir', '/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32', ...]`
- Consistent with `mimir-core-rules`, `/tmp/mimir-issue13-antigravity-t3/probe.txt` was **not** bypassed via shell/`pdftext.py`. Note that Antigravity's `run_command` tool itself does not enforce the `view_file` workspace path allowlist once command execution is authorized.

### 6.2 OS Filesystem Permission Test — Completed Copy with Denied Original Deletion (Zero Mocks)
1. **Default ACP userns (`s4/ro_dir_userns`, `chmod 0555` dir, `chmod 0444` file)**:
   Because `agy_acp_server` runs in a user namespace mapping `0 -> 1000` with `CAP_DAC_OVERRIDE` (`CapEff: 000001ffffffffff`), standard `chmod 0555` alone did **not** block `unlink()` for an unmodified subprocess (`workspace.py file` unlinked the source and reported `"action": "moved"`).
2. **Real Linux kernel VFS DAC enforcement (`s4/ro_dir_dac`, `chmod 0555` dir, `chmod 0444` file, `setpriv --bounding-set=-dac_override` before `python3 scripts/workspace.py file` — no Python mocks, unmodified `workspace.py` and `ingest.py`)**:
   - `workspace.py file` stdout (exit `0`):
     ```json
     {"source": ".../s4/ro_dir_dac/cs201-past-paper.pdf", "dest": ".../s4/home_dac/learning/2026-Fall/CS201 Theory/past-papers/cs201-past-paper.pdf", "course_dir": ".../s4/home_dac/learning/2026-Fall/CS201 Theory", "created": [...], "action": "copied", "line": "Copied cs201-past-paper.pdf to .../s4/home_dac/learning/2026-Fall/CS201 Theory/past-papers/ Original retained at .../s4/ro_dir_dac/cs201-past-paper.pdf."}
     ```
   - Verified filesystem state:
     - Original retained: `.../s4/ro_dir_dac/cs201-past-paper.pdf` (`-r--r--r--`, 794 bytes).
     - Copy created: `.../s4/home_dac/learning/2026-Fall/CS201 Theory/past-papers/cs201-past-paper.pdf` (`-rw-r--r--`, 794 bytes).
   - Subsequent `ingest.py index` on the copied destination (exit `0`):
     ```json
     {"index": ".../s4/home_dac/learning/2026-Fall/CS201 Theory/INDEX.md", ..., "files": [{"path": ".../past-papers/cs201-past-paper.pdf", "role": "past-papers", "pages": 1, "fidelity": "text", "new": true}], "topics_added": 1, "line": "Indexed 1 file in .../INDEX.md (1 new, 1 topic added)."}
     ```
3. **Distinction from Mocks**:
   - **Host denial**: Antigravity `view_file` / `client_view_file` allowlist rejection on `/tmp/...`.
   - **OS permission test**: Real Linux VFS `EACCES` on `unlink()` in `0555` directory (`s4/ro_dir_dac`) after dropping `CAP_DAC_OVERRIDE` from the userns root bounding set.
   - **Mocks**: None used here (unit-test monkeypatches in `tests/` are separate and not counted as live host evidence).

---

## 7. Preserved Artifacts for Parent Inspection

- Report: `/home/oguz/mimir/docs/issue-13-antigravity-t3.md`
- Scenario 1 fixtures & wrapper: `.../brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s1/`
- Scenario 1 independent verifier transcript: `.../brain/708ccb513dd8721c254456a02a60d069/.system_generated/logs/transcript.jsonl`
- Scenario 2 Urgent workspace, `INDEX.md`, `fingerprint.md`, `profile.md`, session log `2026-11-01-1336.md`, and `student_output_transcript.md`: `.../brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s2/`
- Scenario 2 independent verifier transcript: `.../brain/69249fe05d7a686fcc6fd5870fe206bd/.system_generated/logs/transcript.jsonl`
- Scenario 4 OS copy/delete trees (`ro_dir_dac`, `home_dac`): `.../brain/3941963f-7403-41f2-8d6b-71e3c8ec8d59/scratch/issue13-live/s4/`
