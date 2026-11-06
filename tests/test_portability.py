"""Mimir must load in every agent that reads Agent Skills, not only Claude Code."""
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SKILLS = sorted(d for d in (ROOT_DIR / "skills").iterdir() if (d / "SKILL.md").is_file())
MARKDOWN = sorted((ROOT_DIR / "skills").rglob("*.md")) + sorted((ROOT_DIR / "helpers").glob("*.md"))
NAME = re.compile(r"^(?!.*--)[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def frontmatter(path):
    head = path.read_text(encoding="utf-8").split("---")[1]
    return dict(line.split(": ", 1) for line in head.strip().splitlines() if ": " in line)


def test_every_skill_has_a_spec_name_matching_its_folder():
    for skill in SKILLS:
        front = frontmatter(skill / "SKILL.md")
        assert front.get("name") == skill.name, skill.name
        assert NAME.match(skill.name) and skill.name.startswith("mimir-"), skill.name
        assert 0 < len(front["description"]) <= 1024, skill.name


def test_no_claude_only_paths_or_command_names():
    for path in MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert "CLAUDE_PLUGIN_ROOT" not in text, path
        assert not re.search(r"/mimir:(?!mimir-)", text), path
        assert not re.search(r"`mimir:(?!verifier`|visual-builder`)", text), path


def test_every_mimir_path_exists():
    for path in MARKDOWN:
        for ref in re.findall(r"<mimir>/([A-Za-z0-9_./-]+)", path.read_text(encoding="utf-8")):
            if "<" in ref or ref.endswith("/"):
                continue
            assert (ROOT_DIR / ref).exists(), (path, ref)


def test_manifests_agree():
    claude = json.loads((ROOT_DIR / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    portable = json.loads((ROOT_DIR / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT_DIR / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    for key in ("name", "version", "description", "license", "repository", "author"):
        assert claude[key] == portable[key], key
    assert market["plugins"][0]["description"] == claude["description"]
    assert portable["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
               "keywords", "extensions"}
    assert set(portable) <= allowed
    for agent in claude["agents"]:
        assert (ROOT_DIR / agent).is_file(), agent


def test_manifests_match_shipped_plugin():
    claude = json.loads((ROOT_DIR / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT_DIR / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    listed = sorted(Path(s).name for s in claude["skills"])
    assert listed == [s.name for s in SKILLS]  # every shipped skill listed once, nothing extra
    for skill in claude["skills"]:
        assert (ROOT_DIR / skill / "SKILL.md").is_file(), skill
    assert market["plugins"][0]["version"] == claude["version"]
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    assert re.search(r"\*\*Version (\S+)\*\*", readme).group(1) == claude["version"]
    for text in (market["description"], market["plugins"][0]["description"], claude["description"]):
        assert not re.search(r"(plugin )?for Claude Code\b", text), text  # agent-neutral


# Agent Skills spec keys, plus Claude Code hints other agents ignore. D3 keeps
# disable-model-invocation on setup and ingest only: Antigravity hides those skills.
PORTABLE_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools", "user-invocable"}
MANUAL_ONLY = {"mimir-setup", "mimir-ingest"}


def test_frontmatter_keys_are_portable():
    for skill in SKILLS:
        front = frontmatter(skill / "SKILL.md")
        extra = set(front) - PORTABLE_KEYS
        if skill.name in MANUAL_ONLY:
            assert front.get("disable-model-invocation") == "true", skill.name
            extra -= {"disable-model-invocation"}
        assert not extra, (skill.name, extra)
        if "user-invocable" in front:
            assert front["user-invocable"] == "false", skill.name


def test_no_agents_folder_for_other_tools_to_misread():
    assert not (ROOT_DIR / "agents").exists()


SHELL_DATE = re.compile(r"`date( [-+'\"][^`]*)?` (call|command)|\(`date`\)|`date [-+'\"]|\$\(date\b|\bdate -[A-Za-z]|\bdate \+%")


def test_no_shell_date_commands():
    """GNU `date -d` and friends differ on macOS and are missing on Windows: the
    clock and date phrases go through `session.py now` and `parse-date`."""
    for path in MARKDOWN:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not SHELL_DATE.search(line), f"{path}:{n}: {line.strip()[:80]}"


def test_verification_dispatch_and_provenance_contract():
    core = (ROOT_DIR / "skills/mimir-core-rules/SKILL.md").read_text()
    helper = (ROOT_DIR / "helpers/verifier.md").read_text()
    assert "native independent subagent" in core
    assert "checker: self" in core and "checker: independent" in core
    assert "once per session" in core
    assert "pdftext.py" in helper and "ambiguous" in helper
    assert "Bash" in frontmatter(ROOT_DIR / "helpers/verifier.md")["tools"]


FORECAST = re.compile(r"delay_line|cost.of.delay|counterfactual|route_minutes|capacity_minutes|visual\.py delay"
                      r"|\bmin(utes)? a day\b|\d+\s*days?\s*×", re.IGNORECASE)


def test_no_learning_time_forecasts():
    """Mimir never promises how fast a student learns: no cost of delay, no
    "N days × M min" lines, no counterfactual cram estimate."""
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not FORECAST.search(line), f"{path}:{n}: {line.strip()[:80]}"


# Sessions end only when the student says "end session": no episode timer and
# no close the agent triggers itself (a finished set, route or drill list).
AUTO_CLOSE = re.compile(r"session\.py clock|`clock`|episode timer|20 to 25 min|Good luck|"
                        r"\bthen close\b|Then close|None left: close|: close\.|and close \(|close now", re.I)
SESSION_FLOWS = ["skills/mimir-study/references/session.md", "skills/mimir-study/references/urgent.md",
                 "skills/mimir-quiz/SKILL.md", "skills/mimir-past-questions/SKILL.md"]


def test_no_episode_clock_or_automatic_close():
    for path in MARKDOWN:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not AUTO_CLOSE.search(line), f"{path}:{n}: {line.strip()[:100]}"


def test_sessions_close_only_on_end_session_with_a_set_hand_off():
    core = (ROOT_DIR / "skills/mimir-core-rules/SKILL.md").read_text(encoding="utf-8")
    assert "## Ending a session" in core and "**End-of-set hand-off**" in core
    assert '"end session"' in core
    close = (ROOT_DIR / "skills/mimir-core-rules/references/session-close.md").read_text(encoding="utf-8")
    assert "session.py close" in close  # the script writes the one end stamp
    for flow in SESSION_FLOWS:
        text = (ROOT_DIR / flow).read_text(encoding="utf-8")
        assert "End-of-set hand-off" in text and '"end session"' in text, flow


# Teaching settings: three global axes with named levels, read once per Standard
# session through session.py; the frustration override saves no preference.
LEVELS = ["example-first", "method-first", "try-first", "checks only", "key decisions", "every step",
          "next step", "why", "what-if"]
TEACHING = ROOT_DIR / "skills/mimir-study/references/teaching.md"
STUDY_SESSION = ROOT_DIR / "skills/mimir-study/references/session.md"


def test_every_teaching_level_has_a_does_and_a_must_not_row():
    text = TEACHING.read_text(encoding="utf-8")
    assert text.count("| Level | Does | Must not |") == 3
    for level in LEVELS:
        rows = [l for l in text.splitlines() if l.startswith(f"| {level} | ")]
        assert len(rows) == 1 and rows[0].count(" | ") == 2, level


def test_teaching_settings_are_read_once_and_changed_only_through_the_script():
    session = STUDY_SESSION.read_text(encoding="utf-8")
    teaching = TEACHING.read_text(encoding="utf-8")
    assert session.count("session.py prefs") == 1
    assert "session.py pref-event" in teaching and '"event": "explicit"' in teaching
    assert "legacy-import" not in teaching + session  # prefs already shows the legacy value
    for path in MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert "preferences.json" not in text, path  # the script owns the file


def test_frustration_override_saves_no_preference():
    for path in MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert "Fewer questions from now on" not in text, path
        assert "dial_preference" not in text, path
        assert "Rung hints" not in text, path


def test_urgent_quiz_and_past_questions_ignore_teaching_settings():
    for flow in ["skills/mimir-study/references/urgent.md", "skills/mimir-quiz/SKILL.md",
                 "skills/mimir-past-questions/SKILL.md"]:
        text = (ROOT_DIR / flow).read_text(encoding="utf-8")
        assert "session.py pref" not in text, flow


def test_triage_is_rendered_as_a_ranked_table_not_a_paragraph():
    """Urgent study and past-question practice show `plan.py triage` rows as a
    table; nothing ranks by points per hour or says a drill/skip paragraph."""
    urgent = (ROOT_DIR / "skills/mimir-study/references/urgent.md").read_text(encoding="utf-8")
    past = (ROOT_DIR / "skills/mimir-past-questions/SKILL.md").read_text(encoding="utf-8")
    assert "`rows`" in urgent and "| Question type | Marks | Seen in papers | Reason |" in urgent
    assert "urgent.md" in past and "table" in past
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"points.per.hour|lower yield|`line` said verbatim", line, re.I), \
                f"{path}:{n}: {line.strip()[:100]}"


# Standard retries: unlimited guided attempts, the answer only on request, the
# first miss recorded once and a later right answer recorded as assisted.
def test_standard_study_has_unlimited_retries_and_the_recording_rule():
    session = (ROOT_DIR / "skills/mimir-study/references/session.md").read_text(encoding="utf-8")
    assert "**Retries**" in session and "unlimited" in session
    assert "only when the student asks" in session
    assert "`duplicate`" in session  # repeated misses add no log line either
    assert not re.search(r'"idk": show the key', session)  # "idk" gets guidance, not the key
    recording = (ROOT_DIR / "skills/mimir-core-rules/references/recording.md").read_text(encoding="utf-8")
    assert "first wrong answer" in recording and "records as assisted" in recording


# Per-item labels only for real, flagged, OCR and tentative items; plain
# practice is declared once per session.
LABEL_FLOWS = ["skills/mimir-study/references/session.md", "skills/mimir-study/references/teaching.md",
               "skills/mimir-study/references/urgent.md", "skills/mimir-quiz/SKILL.md"]


def test_plain_practice_is_declared_once_and_other_items_keep_their_label():
    core = (ROOT_DIR / "skills/mimir-core-rules/SKILL.md").read_text(encoding="utf-8")
    labels = core.split("## Provenance labels", 1)[1].split("\n## ", 1)[0]
    assert "Every question shown carries exactly one label" not in labels
    assert "**Plain practice item**" in labels and "once per session" in labels
    for kind in ("real", "`ocr`", "flagged", "`(tentative)`"):
        assert kind in labels, kind
    for flow in LABEL_FLOWS:
        text = (ROOT_DIR / flow).read_text(encoding="utf-8")
        assert "Provenance labels" in text, flow
        assert not re.search(r"each opening with the gate's `label`|each with its label", text), flow


URGENT = ROOT_DIR / "skills/mimir-study/references/urgent.md"


def urgent_section(heading):
    return URGENT.read_text(encoding="utf-8").split(heading, 1)[1].split("\n## ", 1)[0]


# Urgent teaches before it tests: recipe, then a fresh similar question; after
# a miss, a correction and a fresh question, never the same one again.
def test_urgent_teaches_a_recipe_then_a_fresh_question():
    drill = urgent_section("## 3. ")
    assert "**Recipe**" in drill
    assert drill.index("**Recipe**") < drill.index("Check item")
    assert "correction" in drill and "fresh similar question" in drill
    assert "never the same question again" in drill
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"answer-first|lesson before the first worked example", line, re.I), \
                f"{path}:{n}: {line.strip()[:100]}"


# Misses are counted per type across the whole session; at three, Mimir cites
# real frequency when known and asks whether to continue or move on.
def test_urgent_asks_to_continue_or_move_on_after_three_misses():
    rule = urgent_section("## 3. ").split("**Continue-or-move-on check**", 1)[1].split("\n\n", 1)[0]
    assert "per type" in rule and "across the session" in rule and "not only in a row" in rule
    for miss in ('wrong answer', '"idk"', '"skip"', '"just tell me"'):
        assert miss in rule, miss
    assert "right answer after a hint" in rule and "does not reset" in rule
    assert "dropped" in rule and "not an attempt" in rule
    assert "three" in rule and "`frequency`" in rule and "never invent" in rule
    assert '"continue"' in rule and "resets the count to zero" in rule and '"move on"' in rule


# Urgent opens with the class line, then the gauge slot, then the triage table,
# then the drill; a lazy setup still says the class line first.
def test_urgent_opening_order_and_every_right_answer_is_assisted():
    cargo = urgent_section("## 2. Urgent cargo")
    order = cargo.split("**Opening order**", 1)[1].split("\n", 1)[0]
    steps = ["class line", "gauge", "triage table", "drill"]
    assert [order.index(s) for s in steps] == sorted(order.index(s) for s in steps), order
    assert cargo.index("Gauge slot") < cargo.index("`plan.py triage`") < cargo.index("Drill: §3")
    lazy = urgent_section("## 1. Lazy setup")
    assert "the student's first line from Mimir is that class line" in lazy
    assert "right answers always use `assisted`" in urgent_section("## 3. ")
    assert "No Urgent answer ever sets `mastered`" in URGENT.read_text(encoding="utf-8")


# Exams carry a time when known (issue #34): intake asks for the date and time
# together, a date-only exam is asked about once more within two days, and a
# date-only exam today is checked before drilling.
def _read(rel):
    return (ROOT_DIR / rel).read_text(encoding="utf-8")


def test_exam_intake_asks_date_and_time_together():
    for rel in ("skills/mimir-setup/SKILL.md", "skills/mimir-study/references/session.md"):
        text = _read(rel)
        assert "date and time" in text and "Don't know" in text, rel
        assert "parse-date" in text and "its `exam`" in text, rel  # the row value keeps the time
    ingest = _read("skills/mimir-ingest/SKILL.md")
    assert "| YYYY-MM-DD HH:MM |" in ingest  # an outline's printed time is recorded with the date


def test_study_asks_exam_time_within_two_days_and_whether_today_is_still_ahead():
    session = _read("skills/mimir-study/references/session.md")
    for field in ("`ask_exam_time`", "`ask_exam_ahead`", "`exam_problems`"):
        assert field in session, field
    assert "time unknown" in session  # the marker that stops a second re-ask
    assert "still ahead" in session
    core = _read("skills/mimir-core-rules/SKILL.md")
    assert "within two days" in core and "still ahead" in core  # allowed admin questions


BARE_DATE = re.compile(r"`date` of [^.]*parse-date|its `date` is usable")


def test_no_skill_writes_a_bare_date_from_parse_date():
    for path in MARKDOWN:
        assert not BARE_DATE.search(path.read_text(encoding="utf-8")), path


# The student may choose the delivery class: for this session, or lastingly for
# one exam (issue #36). The old "the student never picks a mode" rule is gone.
def test_student_chooses_standard_or_urgent_through_session_start():
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        text = path.read_text(encoding="utf-8")
        assert "never picks a mode" not in text and "only mode input" not in text, path
    core = _read("skills/mimir-core-rules/SKILL.md")
    assert '"choice"' in core and '"lasting": true' in core
    assert "study normally" in core and "cram" in core and "until that exam passes" in core
    session = _read("skills/mimir-study/references/session.md")
    assert '"choice"' in session and '"lasting": true' in session
    assert "<class.decided_by>" in session  # the log records which rule decided
    assert "choose" in _read("skills/mimir-study/SKILL.md")
    assert "delivery_choice:" in _read("assets/templates/save.md")
    for rel in ("skills/mimir-study/references/session.md", "skills/mimir-study/references/urgent.md"):
        assert "pending_debrief and the `delivery_choice:` line" in _read(rel), rel  # the close keeps it


# The setup sampler: offered once during setup with a skip, run before setup is
# marked done, one everyday demonstration per axis, saved only through session.py.
SETUP = "skills/mimir-setup/SKILL.md"
SAMPLER = "skills/mimir-setup/references/sampler.md"


def test_setup_offers_the_sampler_once_with_a_skip_before_setup_is_done():
    text = _read(SETUP)
    assert "references/sampler.md" in text and 'session.py" prefs' in text
    assert '"event": "sampler-skip"' in text and "skip" in text and "default" in text
    assert text.index("references/sampler.md") < text.index("`setup_done:` set to")  # events refused after it
    assert "`started`" in text and "`remaining`" in text  # an interrupted setup resumes, not re-offers


def test_only_setup_runs_sampler_events():
    for path in MARKDOWN:
        rel = str(path.relative_to(ROOT_DIR))
        text = path.read_text(encoding="utf-8")
        if rel not in (SETUP, SAMPLER):
            assert '"event": "sampler' not in text, rel


def test_each_sampler_demonstration_isolates_one_axis():
    text = _read(SAMPLER)
    assert '"event": "sampler"' in text and "knowledge gauge" in text
    assert '"Which suits you: A, B or C?" and wait' in text  # one active question per demonstration
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    assert [s.splitlines()[0] for s in sections] == ["support", "frequency", "depth"]
    for section, levels in zip(sections, (LEVELS[0:3], LEVELS[3:6], LEVELS[6:9])):
        options = re.findall(r"^\*\*([ABC])\*\* \(`([^`]+)`\)", section, flags=re.M)
        assert options == list(zip("ABC", levels)), section.splitlines()[0]
    # frequency differs only in when questions come: every option discloses the same and ends on one fresh check
    frequency = sections[1]
    endings = re.findall(r"Your turn: [^\n]*", frequency)
    assert len(endings) == 3 and len(set(endings)) == 1
