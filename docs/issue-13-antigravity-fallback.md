# Issue 13 — Antigravity Live Fallback Acceptance Report (via T3 Code)

Date: `2026-11-01`
Repository: `/home/oguz/mimir`
Branch / HEAD: `issue-13-portable-verification` (`c70f2c2a4727a60a6b4157557e2bc8416048142a`)
Companion report (version metadata, independent verification, quick start, permission boundaries): `/home/oguz/mimir/docs/issue-13-antigravity-t3.md`
Parent conversation ID: `995c4a3e-3289-42a8-a27b-ba5b69fae2c2`
Child session subagent ID: `cbfd4ab9a48e9af2c731556a61f013ad` (`mimir-fallback-session`)

---

## 1. Capability Restriction & Actual Child Tool Inventory

### Subagent Definition
Defined and invoked exactly one native test session subagent via `define_subagent` + `invoke_subagent` (`Model: "inherit"`, `Workspace: "inherit"`):
- `name`: `mimir-fallback-session`
- `enable_subagent_tools`: `false`
- `enable_mcp_tools`: `false`
- `enable_write_tools`: `true` (required in Antigravity so the session agent has `write_to_file` / `replace_file_content` for session logs and `run_command` for `session.py`, `plan.py`, `verify.py`, and `pdftext.py`)

### Observed Capability Enforcement vs. Disabled Flags
Child inspected its actual live tool declarations and recorded them in `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad/scratch/observed_tools.json`:

| Capability Flag | Expected Effect | Observed Effect in Antigravity ACP | Check Result |
|---|---|---|---|
| `enable_subagent_tools: false` | Remove native subagent/workflow tools | **Enforced.** `define_subagent`, `invoke_subagent`, `manage_subagents`, and `run_workflow` (plus `ask_question` and `client_view_file`) were genuinely absent from the child's tool schema. | **PASS** |
| `enable_mcp_tools: false` | Remove MCP tool access | **Partial / Failed check on `call_mcp_tool`.** `list_resources` and `read_resource` were removed, **but `call_mcp_tool` remained declared and callable** against `<mcp_servers>` (`t3-code`). Child step 14–15 verified `call_mcp_tool(ServerName="t3-code", ToolName="orchestrator_capabilities")` succeeded (`canRunChildTask: true` for lazy tool `delegate_task`). | **LIMITATION (`call_mcp_tool` retained)** |

- **Exact 13 native tools declared in child**: `call_mcp_tool`, `generate_image`, `manage_task`, `multi_replace_file_content`, `notebook_edit`, `read_url_content`, `replace_file_content`, `run_command`, `schedule`, `search_web`, `send_message`, `view_file`, `write_to_file`.
- **Why `mimir-core-rules` fallback applied without pretending tools were absent**:
  - `skills/mimir-core-rules/SKILL.md` specifies: *"Use the named Claude helper when available; otherwise use a **native independent subagent** (for example Codex spawn_agent) ... Only when no independent agent is available, perform a fresh separate pass following the helper body."*
  - Zero native subagent tools existed in the child (`define_subagent`, `invoke_subagent`, `manage_subagents`, `run_workflow` all absent), and `send_message` only messages an existing conversation ID and cannot spawn a checker.
  - External MCP `t3-code:delegate_task` is T3 Code's host-level thread orchestrator rather than a native subagent tool, and T3's orchestration instructions forbid child subagents from spawning further subagents unless instructed (*"If you are a subagent or child, do the work yourself. Start no subagents unless your task says to"*). Zero `delegate_task` or subagent calls were made.

---

## 2. Isolation & Artifact-Directory Boundary

- User's real learning root (`/home/oguz/learning`) and pointer (`/home/oguz/.config/mimir/root`) were never read, written, or queried; every `scripts/*.py` command ran with subprocess-scoped `HOME`.
- **Per-conversation `brain/<id>` write boundary discovered live**:
  - Initially, isolated `HOME` was staged under the parent's scratch directory (`.../brain/995c4a3e-3289-42a8-a27b-ba5b69fae2c2/scratch/issue13-fallback/home`).
  - Child native `write_to_file` calls at steps 26 and 39 were rejected by Antigravity ACP with:
    `error executing cascade step: CORTEX_STEP_TYPE_CODE_ACTION: files must be written to the correct artifact directory: /home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad`
  - Consistent with `mimir-core-rules` (*"Never use shell access to bypass a denial"*, native file tools only for memory/logs), the child paused without using shell writes.
  - Relocating the disposable `CS201 Theory` workspace (with copied synthetic `cs201-past-paper.pdf`) into the child's own scratch tree `.../brain/cbfd4ab9a48e9af2c731556a61f013ad/scratch/issue13-fallback/home` resolved the boundary; native `write_to_file` (with `ArtifactMetadata.UserFacing: false`, step 58) and `replace_file_content` (steps 72, 79) succeeded cleanly.

---

## 3. Two-Batch Single-Session Execution & Gate / PDF Evidence

All steps below ran in **one Mimir session** (`2026-11-01-1820`, `started: 2026-11-01T18:20:10+02:00`) inside child `cbfd4ab9a48e9af2c731556a61f013ad` (`transcript_full.jsonl` = 89 rows, 31 `PLANNER_RESPONSE` steps). Neither parent prompt contained the literal fallback notice or `checker: self`.

### Batch 1 — Turn 1 (`Basic arithmetic addition`)
1. **Session & triage (steps 46–67)**: `session.py now` -> `2026-11-01T18:20:10+02:00` (`log_name: "2026-11-01-1820"`); `session.py start` -> `CS201 Theory`, `Urgent` (`exam: "2026-11-02"`, `line: "Urgent delivery: exam in 6 hours"`); created `.state/logs/2026-11-01-1820.md` via `write_to_file` (step 58); read `.state/{save,fingerprint,mastery}.md` and `INDEX.md` via `view_file`; `plan.py triage` -> `Drilling: Basic arithmetic addition. Skipping: Integer sum properties (lower yield).`; read `cs201-past-paper.pdf` p.1 via `pdftext.py pages` (step 67) to draft items.
2. **Initial gate (step 68–69)**: `verify.py gate` on Item 1 (`origin: "real"`, `source: "past-papers/cs201-past-paper.pdf"`, `page: 1`, `question: "Q1"`) and Item 2 (`origin: "practice"`, `compare: p.1 Q1`):
   `{"verify": [1, 2], "retry": [], "disagreements": [], "line": "Gate: 2 items, 2 to verify."}`
3. **Fallback verifier pass & provenance write (steps 70–72)**:
   - Fresh separate pass following `helpers/verifier.md` executed `pdftext.py pages` on `.../past-papers/cs201-past-paper.pdf` p.1 (step 71, exit `0`, extracted `"CS201 Theory - Sample Past Paper\nQ1 (10 marks): What is 2 plus 2?\nAnswer: 4"`).
   - Native `replace_file_content` (step 72) recorded `checker: self` in `.state/logs/2026-11-01-1820.md`.
4. **Final gate (step 73–74)**: `verify.py gate` with `verdicts: ["correct"]` on both items:
   `{"results": [{"n": 1, ..., "label": "[real: past-papers/cs201-past-paper.pdf, p.1]", "decision": "show", "counts_for_mastery": true}, {"n": 2, ..., "label": "[practice, not from a real paper]", "decision": "show", "counts_for_mastery": true}], "verify": [], "retry": [], "disagreements": [], "line": "Gate: 2 items, 2 to show."}`
5. **Student-facing assistant message (step 75)**: Emitted class line, triage line, wait line once, fallback disclosure once, worked real Q1 (`2 plus 2 = 4`), and practice check (`What is 3 plus 5?`).

### Batch 2 — Turn 2 in Same Session (`Integer sum properties`)
1. **Batch 1 check grading & recording (steps 77–79)**: Recorded student answer `"8"` via `session.py record` (`outcome: "assisted"`, `"Basic arithmetic addition: shaky."`, step 78) and appended result to `.state/logs/2026-11-01-1820.md` via `replace_file_content` (step 79).
2. **Initial gate (step 77 & 80)**: `verify.py gate` on two new `Integer sum properties` items (Item 1 `origin: "practice"` with `quote: {"path": "past-papers/cs201-past-paper.pdf", "page": 1}` and `compare: p.1 Q1`; Item 2 `origin: "practice"` with `compare: p.1 Q1`):
   `{"verify": [1, 2], "retry": [], "disagreements": [], "line": "Gate: 2 items, 2 to verify."}`
3. **Second fallback verifier pass (step 81–82)**: Executed `pdftext.py pages` on `.../past-papers/cs201-past-paper.pdf` p.1 (exit `0`) to confirm the quoted PDF text and check both commutativity keys.
4. **Final gate (step 83–84)**: `verify.py gate` with `verdicts: ["correct"]` on both items:
   `{"results": [{"n": 1, "topic": "Integer sum properties", ..., "decision": "show", "counts_for_mastery": true}, {"n": 2, "topic": "Integer sum properties", ..., "decision": "show", "counts_for_mastery": true}], "verify": [], "retry": [], "disagreements": [], "line": "Gate: 2 items, 2 to show."}`
5. **Student-facing assistant message (step 88)**: Emitted feedback/key for `"8"`, worked Item 1 (`4 plus 6 = 6 plus 4 = 10`), and check Item 2 (`5 plus 7?`), with **zero** repeated wait lines and **zero** repeated fallback notices.

---

## 4. Transcript Content Counts & Session Log Excerpt

### Child Transcript Assistant Message Counts (`PLANNER_RESPONSE.content`)
Inspected directly in `cbfd4ab9a48e9af2c731556a61f013ad/.system_generated/logs/transcript.jsonl` and `transcript_full.jsonl` (excluding prompts, `thinking`, and tool payloads):

| Step Index | Turn / Role | Content Length | Count of `"Answer checks are running in this same context; an independent checker is unavailable."` | Count of `"Checking my answers before you study them, about 30 seconds."` |
|---|---|---|---|---|
| `44` | Pre-relocation idle pause (`"…"`) | 1 char | `0` | `0` |
| `75` | Turn 1 — Batch 1 student-facing output | 587 chars | **`1`** | **`1`** |
| `88` | Turn 2 — Batch 2 student-facing output | 785 chars | **`0`** | **`0`** |
| **Total** | **3 visible assistant messages across 31 `PLANNER_RESPONSE` steps** | **1,373 chars** | **`1` (exact)** | **`1` (exact)** |

### Absence of Independent-Agent Calls (All 54 Tool Calls in Child Transcript)
- `view_file`: `30`
- `run_command`: `16` (`session.py`, `plan.py`, `verify.py`, `pdftext.py` only)
- `write_to_file`: `4` (2 blocked on parent `brain/` path, 1 `observed_tools.json`, 1 session log creation)
- `replace_file_content`: `2` (step 72 `checker: self`, step 79 `## Results` entry)
- `call_mcp_tool`: `1` (step 14 `t3-code:orchestrator_capabilities` read-only capability check; `0` `delegate_task` calls)
- `send_message`: `1` (step 40 artifact-directory blocker report to parent)
- `define_subagent` / `invoke_subagent` / `run_workflow` / `delegate_task`: **`0`**

### Actual Session Log (`.../2026-Fall/CS201 Theory/.state/logs/2026-11-01-1820.md`)
```markdown
## Session
started: 2026-11-01T18:20:10+02:00
class: Urgent (floor)
first_contact: 2026-11-01T18:20:10+02:00
checker: self

## Results
- Basic arithmetic addition urgent check [practice, not from a real paper]: assisted solve
```

---

## 5. Limitations

1. **`enable_mcp_tools: false` does not remove `call_mcp_tool` in Antigravity ACP (`1.4.1`)**: While `enable_subagent_tools: false` cleanly strips all native subagent/workflow tools (`define_subagent`, `invoke_subagent`, `manage_subagents`, `run_workflow`), `enable_mcp_tools: false` only strips `list_resources`/`read_resource` and leaves `call_mcp_tool` active. Under T3 Code, `t3-code:delegate_task` therefore remains reachable at the protocol layer unless excluded by `mimir-core-rules`'s *"native independent subagent"* rule and T3's child-subagent policy.
2. **Per-conversation `brain/<conversation-id>` ownership on `write_to_file`**: Antigravity's `write_to_file` rejects writes into another conversation's `brain/<id>/scratch/` directory and requires `ArtifactMetadata` when creating files under the calling agent's own `brain/<id>/scratch/` tree. (Normal user workspaces added via `--add-dir` outside `brain/` do not require `ArtifactMetadata`.)

---

## 6. Preserved Paths

- Evidence report: `/home/oguz/mimir/docs/issue-13-antigravity-fallback.md`
- Child transcript (compact): `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad/.system_generated/logs/transcript.jsonl`
- Child transcript (full): `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad/.system_generated/logs/transcript_full.jsonl`
- Observed child tool inventory: `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad/scratch/observed_tools.json`
- Isolated course workspace: `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad/scratch/issue13-fallback/home/learning/2026-Fall/CS201 Theory`
- Session log with `checker: self`: `/home/oguz/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/cbfd4ab9a48e9af2c731556a61f013ad/scratch/issue13-fallback/home/learning/2026-Fall/CS201 Theory/.state/logs/2026-11-01-1820.md`
