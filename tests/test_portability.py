"""Mimir must load in every agent that reads Agent Skills, not only Claude Code."""
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SKILLS = sorted(d for d in (ROOT_DIR / "skills").iterdir() if (d / "SKILL.md").is_file())
MARKDOWN = (sorted((ROOT_DIR / "skills").rglob("*.md")) + sorted((ROOT_DIR / "reference").glob("*.md"))
            + sorted((ROOT_DIR / "helpers").glob("*.md")))
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
        assert not re.search(r"`mimir:(?!verifier`|visual-builder`|figure-checker`|field-researcher`|base-figure-builder`)", text), path


INTERNAL = {"mimir-core-rules", "mimir-notation"}
CORE_RULES_LINE = re.compile(r"^First read `([^`]+)`")


def test_internal_rules_live_in_reference_not_skills():
    """#3: Antigravity ignores `user-invocable: false`, so every folder under skills/
    is a user command. Core rules and notation are plain files under reference/."""
    assert not INTERNAL & {s.name for s in SKILLS}
    assert len(SKILLS) == 10, [s.name for s in SKILLS]
    for skill in SKILLS:
        assert "user-invocable" not in frontmatter(skill / "SKILL.md"), skill.name
    for name in ("core-rules.md", "notation.md", "recording.md", "session-close.md", "verified-items.md"):
        text = (ROOT_DIR / "reference" / name).read_text(encoding="utf-8")
        assert not text.startswith("---"), name  # plain file, no skill frontmatter


def test_every_skill_first_loads_the_core_rules_by_a_path_that_resolves():
    for skill in SKILLS:
        body = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[2]
        first = next(line for line in body.splitlines() if line.strip() and not line.startswith("#"))
        match = CORE_RULES_LINE.match(first)
        assert match, (skill.name, first[:80])
        target = match.group(1)
        assert (skill / target).resolve() == ROOT_DIR / "reference" / "core-rules.md", skill.name


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


def test_python_command_fallback_for_windows():
    """A standard Windows Python install ships `python` and `py`, not `python3`."""
    core = (ROOT_DIR / "reference/core-rules.md").read_text(encoding="utf-8")
    paths = core.split("## Paths, commands and helpers", 1)[1].split("\n## ", 1)[0]
    assert "`python3` is missing" in paths and "`python`" in paths and "`py -3`" in paths


def test_verification_dispatch_and_provenance_contract():
    core = (ROOT_DIR / "reference/core-rules.md").read_text()
    helper = (ROOT_DIR / "helpers/verifier.md").read_text()
    assert "checker: self" in core and "checker: independent" in core
    assert "once per session" in core
    assert "ambiguous" in helper and "evidence pack" in helper and "Pack token" in helper
    assert "Read the pack and the files it names, nothing else." in helper
    # The pack carries the page text, so the checker needs no shell on Claude Code (#78).
    assert frontmatter(ROOT_DIR / "helpers/verifier.md")["tools"] == "Read, Grep, Glob"
    assert "<pack token>\nN | verdict | reason" in helper


def test_nothing_refers_to_the_gate_a_typed_gate_object_or_the_fake_real_cell():
    """#78: the check ledger replaced `verify.py gate`; labels are checked by script, so the
    checker's fake-real cell is gone, and record reads the ledger instead of a typed gate."""
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"verify\.py\W+gate|\bgate\b|\bgated\b|fake.real|real_past_paper|"
                                 r"counts_for_mastery", line, re.I), f"{path}:{n}: {line.strip()[:100]}"
    flow = _read(VERIFIED)
    for step in ("verify.py submit", "verify.py settle", "verify.py read", "verify.py concede"):
        assert f"`{step}`" in flow or step.split()[1] in flow, step
    assert "pasted unchanged" in flow and "Check the evidence pack at `<pack>`." in flow
    assert "verify.py summary" in _read("reference/session-close.md")
    recording = _read(RECORDING)
    assert '"gate"' not in recording and "settled `correct` check" in recording


FORECAST = re.compile(r"delay_line|cost.of.delay|counterfactual|route_minutes|capacity_minutes|visual\.py delay"
                      r"|\bmin(utes)? a day\b|\d+\s*days?\s*×", re.IGNORECASE)


def test_no_learning_time_forecasts():
    """Mimir never promises how fast a student learns: no cost of delay, no
    "N days × M min" lines, no counterfactual cram estimate."""
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not FORECAST.search(line), f"{path}:{n}: {line.strip()[:80]}"


# #94: the fixed `sheet`, `steps` and `trace` templates are gone; pages are written in the house style
# through `page` (and `svg`). Living docs must not describe the old kinds or their template files.
# Historical records (CHANGELOG.md, the rest of docs/, the user feedback) keep their wording.
REMOVED_VISUALS = re.compile(
    r"\bmath[- ]sheets?\b|math-sheet\.html|step-reveal|step-through|assets/interactive|"
    r"`{1,2}(?:sheet|steps|trace)`{1,2}|visual\.py\W+(?:sheet|steps|trace)\b|cmd_(?:sheet|steps|trace)\b|"
    r"\"(?:sheet|steps|trace)\": \(", re.I)
LIVING_DOCS = (MARKDOWN + sorted((ROOT_DIR / "scripts").glob("*.py"))
               + sorted((ROOT_DIR / "docs" / "agents").glob("*.md"))
               + [ROOT_DIR / name for name in ("README.md", "RELEASE.md", "AGENTS.md", "GLOSSARY.md", "plugin.json",
                                               ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json")])


def test_no_living_doc_names_the_removed_visual_kinds():
    for path in LIVING_DOCS:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not REMOVED_VISUALS.search(line), f"{path}:{n}: {line.strip()[:100]}"
    assert not (ROOT_DIR / "assets" / "math-sheet.html").exists()
    assert not (ROOT_DIR / "assets" / "interactive").exists()


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
    core = (ROOT_DIR / "reference/core-rules.md").read_text(encoding="utf-8")
    assert "## Ending a session" in core and "**End-of-set hand-off**" in core
    assert '"end session"' in core
    close = (ROOT_DIR / "reference/session-close.md").read_text(encoding="utf-8")
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
    """Urgent study and past-question practice show `session.py triage` rows as a
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
    recording = (ROOT_DIR / "reference/recording.md").read_text(encoding="utf-8")
    assert "first wrong answer" in recording and "records as assisted" in recording


# Per-item labels only for real, OCR and tentative items; plain
# practice is declared once per session.
LABEL_FLOWS = ["skills/mimir-study/references/session.md", "skills/mimir-study/references/teaching.md",
               "skills/mimir-study/references/urgent.md", "skills/mimir-quiz/SKILL.md"]


def test_plain_practice_is_declared_once_and_other_items_keep_their_label():
    core = (ROOT_DIR / "reference/core-rules.md").read_text(encoding="utf-8")
    labels = core.split("## Provenance labels", 1)[1].split("\n## ", 1)[0]
    assert "Every question shown carries exactly one label" not in labels
    assert "**Plain practice item**" in labels and "once per session" in labels
    for kind in ("real", "`ocr`", "`(tentative)`"):
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
    assert cargo.index("Gauge offer") < cargo.index("`session.py triage`") < cargo.index("Drill: §3")
    lazy = urgent_section("## 1. Lazy setup")
    assert "the student's first line from Mimir is that class line" in lazy
    assert "right answers always use `assisted`" in urgent_section("## 3. ")
    assert "No Urgent drill answer ever sets `mastered`" in URGENT.read_text(encoding="utf-8")


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
    core = _read("reference/core-rules.md")
    assert "within two days" in core and "still ahead" in core  # allowed admin questions


def test_past_questions_checks_an_exam_today_and_passes_the_class_choice():
    exam_today = "Is your <name> today still ahead?"
    holders = [p.relative_to(ROOT_DIR).as_posix() for p in MARKDOWN if exam_today in p.read_text(encoding="utf-8")]
    assert holders == ["reference/core-rules.md"], holders  # defined once, reused
    past = _read("skills/mimir-past-questions/SKILL.md")
    assert "`ask_exam_ahead`" in past and "Exam today" in past and "Mode and dates" in past
    assert past.index("Exam today") < past.index("5. Triage")  # before any drilling
    assert "<class.decided_by>, <class.reason>" in past  # the same class line as study logs


def test_urgent_past_questions_closes_once():
    past = _read("skills/mimir-past-questions/SKILL.md")
    assert "§4 then step 8" not in past
    assert "step 8 does not run" in past
    assert past.split("\n8. ", 1)[1].startswith("Standard only")


BARE_DATE = re.compile(r"`date` of [^.]*parse-date|its `date` is usable")


def test_no_skill_writes_a_bare_date_from_parse_date():
    for path in MARKDOWN:
        assert not BARE_DATE.search(path.read_text(encoding="utf-8")), path


# The knowledge gauge (issue #39): rules and the Urgent offer live once in core
# rules; study (Standard and Urgent) and past-question practice use them.
CORE = "reference/core-rules.md"
GAUGE_OFFER = "Quick gauge first? A few fresh questions, before any recipe, to see what you can already solve. Yes or no?"


def core_section(heading):
    return _read(CORE).split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_gauge_rules_live_in_core_rules():
    gauge = core_section("Knowledge gauge")
    assert "`start`'s `gauge`" in gauge and "`done` false" in gauge and "`session.py gauge`" in gauge
    assert "`topics`" in gauge  # only unseen topics; any topic with evidence is skipped
    assert "never from the course name" in gauge and "checkable against the course files" in gauge
    assert "before any recipe or worked answer" in gauge
    assert "`unassisted`" in gauge and "`wrong`" in gauge and "`session.py record`" in gauge
    assert "one right answer never marks a topic mastered" in gauge
    assert "no teaching-preference evidence" in gauge
    assert "skips its recipe" in gauge
    assert "highest-priority" in gauge
    assert "Urgent gauge offer" in gauge and "every Urgent session" in gauge


def test_urgent_gauge_offer_is_defined_once_and_used_by_study_and_past_questions():
    holders = [path for path in MARKDOWN if GAUGE_OFFER in path.read_text(encoding="utf-8")]
    assert holders == [ROOT_DIR / CORE], holders
    cargo = urgent_section("## 2. Urgent cargo")
    assert "not built yet" not in cargo
    assert "Urgent gauge offer" in cargo and "Knowledge gauge" in cargo and "core rules" in cargo
    past = _read("skills/mimir-past-questions/SKILL.md")
    assert "Urgent gauge offer" in past and "Knowledge gauge" in past
    assert past.index("Urgent gauge offer") < past.index("§2 steps 1–3")  # the offer before the table
    assert "the Urgent gauge offer" in core_section("Question budget")


def test_standard_session_runs_the_gauge_once_before_any_topic():
    episode = _read("skills/mimir-study/references/session.md").split("## 4. Episode", 1)[1]
    gauge = episode.split("**Knowledge gauge**", 1)[1].split("\n\n", 1)[0]
    assert "`gauge`" in gauge and "`done` false" in gauge and "`session.py gauge`" in gauge
    assert "core rules" in gauge
    assert episode.index("**Knowledge gauge**") < episode.index("Topic `T` is")
    recording = _read("reference/recording.md")
    assert "gauge" in recording and "unassisted" in recording


# The student may choose the delivery class: for this session, or lastingly for
# one exam (issue #36). The old "the student never picks a mode" rule is gone.
def test_student_chooses_standard_or_urgent_through_session_start():
    for path in MARKDOWN + [ROOT_DIR / "README.md"]:
        text = path.read_text(encoding="utf-8")
        assert "never picks a mode" not in text and "only mode input" not in text, path
    core = _read("reference/core-rules.md")
    assert '"choice"' in core and '"lasting": true' in core
    assert "study normally" in core and "cram" in core and "until that exam passes" in core
    session = _read("skills/mimir-study/references/session.md")
    assert '"choice"' in session and '"lasting": true' in session
    assert "<class.decided_by>" in session  # the log records which rule decided
    assert "choose" in _read("skills/mimir-study/SKILL.md")
    assert "delivery_choice:" in _read("assets/templates/save.md")
    for rel in ("skills/mimir-study/references/session.md", "skills/mimir-study/references/urgent.md"):
        assert "pending_debrief and the `delivery_choice:` line" in _read(rel), rel  # the close keeps it


# What an exam covers (issue #45): resolved once into in/out lists, confirmed by the
# student, saved with the exam through session.py scope, then used unchanged.
def test_exam_scope_is_confirmed_before_it_is_saved_through_session_scope():
    core = _read("reference/core-rules.md")
    assert "## Exam scope" in core
    assert "In scope:" in core and "Out:" in core and "confirm" in core
    assert "`session.py scope`" in core and "never a file edit" in core
    assert "never reinterpret" in core  # the saved list is used unchanged
    assert "not on this exam" in core and "never drilled, gauged or used for a recipe" in core
    assert "no marks" in core and "paper names" in core  # unknown scope: no guessing
    assert "New question type '<name>' was found. Is it on your <exam>?" in core
    assert "`scope.new`" in core and '"unsure"' in core
    assert "scope" in core.split("## Question budget")[1].split("##")[0]  # an allowed admin question


def test_exam_intake_and_the_two_day_check_ask_for_the_scope_with_the_time():
    session = _read("skills/mimir-study/references/session.md")
    assert "What does it cover?" in session  # asked with the date and time when the exam is added
    assert "`ask_exam_scope`" in session
    assert "and what does it cover?" in session  # the same question as a missing time
    ingest = _read("skills/mimir-ingest/SKILL.md")
    assert "covers" in ingest and "Exam scope" in ingest  # an outline's stated coverage is proposed


def test_setup_asks_the_scope_with_each_exam_and_the_first_session_confirms_it():
    setup = _read(SETUP)
    intake = setup.split("3. Ask everything", 1)[1].split("\n4. ", 1)[0]
    assert "date and time and what it covers" in intake  # asked together when the exam is added
    assert '"code"' in setup and "session.py\" scope" in setup  # noted by course code, no folder yet
    session = _read("skills/mimir-study/references/session.md")
    checks = session.split("Exam checks", 1)[1].split("\n5. ", 1)[0]
    assert "`scope_words`" in checks and "confirm step" in checks
    lazy = urgent_section("## 1. Lazy setup")
    assert "no scope question in a lazy setup" in lazy  # lazy setup still leaves it out on purpose


def test_plan_says_the_scripts_remaining_line_verbatim():
    plan = _read("skills/mimir-plan/SKILL.md")
    assert "`remaining_line`" in plan and "verbatim" in plan.split("`remaining_line`", 1)[1].split("\n", 1)[0]
    assert "(<status>)" not in plan  # the list with its scope marks comes from session.py, not composed here


def test_triage_and_the_standard_route_use_the_saved_scope():
    urgent = _read("skills/mimir-study/references/urgent.md")
    assert "`session.py triage`" in urgent and "exam scope from the workspace" in urgent
    assert "not on this exam" in urgent and "not checked" in urgent
    session = _read("skills/mimir-study/references/session.md")
    assert "not on your next exam" in session and "not checked" in session
    assert "never removed" in session or "none is removed" in session


def test_shared_triage_leaves_only_semantic_associations_to_the_agent():
    cargo = urgent_section("## 2. Urgent cargo")
    for field in ('"now"', '"term"', '"course"', '"class"'):
        assert field in cargo, field
    assert '"class": "<start.class.class>"' in cargo
    assert "`needs-associations`" in cargo and "`mastery_topics`" in cargo
    assert "every exact type name" in cargo and "including exact-name matches" in cargo
    assert "JSON `null` when none fits" in cargo and "several types may share a topic" in cargo
    assert "without echoing the returned draft" in cargo
    assert "no fingerprint types is already `ready`" in cargo
    assert "`needs-associations`, print nothing" in cargo  # The draft's line stays internal.
    for old_step in ("`plan.py triage`", "`session.py check`", "first number in the marks cell"):
        assert old_step not in cargo, old_step
    past = _read("skills/mimir-past-questions/SKILL.md")
    assert "shared §2 steps 1–3" in past and "`session.py triage`" in past
    assert "`plan.py triage`" not in past


def test_triage_rows_carry_recording_topics_and_provenance_into_both_flows():
    urgent = _read("skills/mimir-study/references/urgent.md")
    cargo = urgent_section("## 2. Urgent cargo")
    assert "`drill` contains type-name strings" in cargo
    assert "matching row's `topic`" in cargo and "every gauge, item, verification and mastery record" in cargo
    for field in ("`source_note`", "`tentative`", "`prior_term`"):
        assert field in cargo, field
    assert "filenames can contain semicolons" in cargo
    assert "from a photo/scan, may be off" in cargo and '"prior term"' in cargo
    assert "both items with `topic` = the matching triage row's `topic`" in urgent
    past = _read("skills/mimir-past-questions/SKILL.md")
    assert "Match drill names to its returned rows for topic and provenance in both classes" in past
    assert "record against the matching triage row's `topic`" in past


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
        rel = path.relative_to(ROOT_DIR).as_posix()
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


# Probe trials (issue #41): the teaching engine tries one step toward more independent teaching,
# only after comfortable engagement, and the script owns every count and cool-down.
PROBE_EVENTS = ["trial-start", "positive", "neutral", "pushback", "reopen", "frustration"]


def test_teaching_holds_the_comfortable_engagement_examples():
    text = TEACHING.read_text(encoding="utf-8")
    section = text[text.index("Comfortable engagement"):]
    for example in ['"each step adds an a and a c, so equal counts?"', '"does this work if b is ε?"',
                    '"just tell me"', '"idk" twice', "all caps", '"this is pointless"', '"ok", "k", "sure"',
                    "tired, rushed or confused"]:
        assert example in section, example
    assert section.index("Comfortable:") < section.index("Not comfortable")


def test_probes_run_through_the_script_and_are_never_announced():
    text = TEACHING.read_text(encoding="utf-8")
    for event in PROBE_EVENTS:
        assert f'"event": "{event}"' in text, event
    assert "`probe_axes`" in text and "`trial`" in text
    assert "never announce" in text.casefold()
    assert "Correctness alone" in text and "Brief answers are neutral" in text
    for path in MARKDOWN:  # Urgent, quiz, past questions and setup never run probe events
        if path != TEACHING:
            for event in PROBE_EVENTS:
                assert f'"event": "{event}"' not in path.read_text(encoding="utf-8"), (path, event)


def test_only_eligible_standard_sessions_are_counted_for_probes():
    session = STUDY_SESSION.read_text(encoding="utf-8")
    assert session.count('"event": "session"') == 1 and "`preference_session`" in session
    assert session.index("`preference_session`") < session.index('"event": "session"')
    assert session.count("session.py prefs") == 1
    for path in MARKDOWN:
        if path != STUDY_SESSION:
            assert '"event": "session"' not in path.read_text(encoding="utf-8"), path


def test_a_paused_trial_is_not_applied_outside_a_counted_session():
    text = TEACHING.read_text(encoding="utf-8")
    inputs = text.split("## 0. Inputs", 1)[1].split("\n## ", 1)[0]
    assert "`trial_paused`" in inputs and "saved level" in inputs
    session = STUDY_SESSION.read_text(encoding="utf-8")
    episode = session.split("## 4. Episode", 1)[1].split("### Questions", 1)[0]
    assert "`trial_paused`" in episode and "saved level" in episode


def test_the_fewer_questions_offer_is_asked_once_by_the_script():
    text = TEACHING.read_text(encoding="utf-8")
    assert text.count('"Want fewer questions from now on?"') == 1
    assert '"event": "frustration"' in text and "`offer`" in text
    for path in MARKDOWN:
        if path != TEACHING:
            assert "Want fewer questions" not in path.read_text(encoding="utf-8"), path


# The one-time what's-new line (issue #43): existing users hear it at their first
# study session, Standard or Urgent; new users' setup marks it seen before setup is done.
def test_whats_new_line_is_said_once_at_session_start_and_setup_marks_it_seen():
    session = _read("skills/mimir-study/references/session.md")
    start = session[session.index("## Start"):session.index("## 2. Urgent")]  # before either class branches
    assert "`whats_new`" in start and 'session.py prefs' in start
    assert start.index("`whats_new`") < start.index('{"event": "whats-new-seen"}')  # said, then marked seen
    setup = _read(SETUP)
    assert setup.index('{"event": "whats-new-seen"}') < setup.index("`setup_done:` set to")
    # Only a new user is marked seen at setup; a user with earlier sessions still hears the line.
    assert "`whats_new` null" in setup
    # Every first session marks it seen, said or not, so a new lazy-setup user never hears it later.
    assert "either way" in start[start.index("`whats_new`"):start.index('{"event": "whats-new-seen"}')]
    for path in MARKDOWN:
        rel = path.relative_to(ROOT_DIR).as_posix()
        text = path.read_text(encoding="utf-8")
        assert "sessions run until you say" not in text, rel  # the line comes from session.py, verbatim
        if rel not in (SETUP, "skills/mimir-study/references/session.md"):
            assert "whats-new-seen" not in text, rel


# The motion level (issue #91): setup asks it in its numbered message; a student without one is
# asked once at the start of the next study session, and the answer is always saved.
MOTION_QUESTION = ("How much animation do you want in the visuals I build: none, gentle or full? "
                   "You can change it any time.")


def test_setup_asks_the_motion_level_in_its_numbered_message_and_saves_it():
    setup = _read(SETUP)
    message = setup[setup.index("3. Ask everything in one numbered message"):setup.index("4. Apply the folder choice")]
    assert f"   4. {MOTION_QUESTION}" in message
    assert "motion none" in message[message.index("For anything left unanswered"):]  # the declared default
    profile_edit = setup[setup.index("5. Edit `.state/profile.md`"):setup.index("6. Teaching-style sampler")]
    assert "`motion:`" in profile_edit and "none" in profile_edit


def test_a_student_without_a_motion_level_is_asked_once_beside_the_whats_new_line():
    session = _read("skills/mimir-study/references/session.md")
    start = session[session.index("## Start"):session.index("## 2. Urgent")]  # both classes
    announce = start[start.index("6. Announce."):start.index("7. Log:")]
    assert MOTION_QUESTION in announce and "`motion` null" in announce
    assert announce.index("`whats_new`") < announce.index(MOTION_QUESTION)
    after = announce[announce.index(MOTION_QUESTION):]
    assert "`motion:`" in after and "no clear choice" in after and "saves none" in after
    admin = session[:session.index("## Start")]
    assert "the motion question of Start step 6" in admin  # the only admin questions in this flow
    for path in MARKDOWN:
        rel = path.relative_to(ROOT_DIR).as_posix()
        if rel not in (SETUP, "skills/mimir-study/references/session.md"):
            assert MOTION_QUESTION not in path.read_text(encoding="utf-8"), rel


def test_core_rules_keep_the_motion_level_out_of_the_teaching_settings():
    core = _read("reference/core-rules.md")
    rules = core[core.index("## Motion level"):]
    rules = rules[:rules.index("\n## ", 1)]
    assert "`motion:`" in rules and "none, gentle or full" in rules
    assert "not a teaching setting" in rules and "only when the student asks" in rules
    assert "built from now on" in rules  # visuals already built keep their motion

# --- speed slice (#77): show what is ready first, check behind the first question ----

VERIFIED = "reference/verified-items.md"
RECORDING = "reference/recording.md"
QUESTION_FLOWS = ["skills/mimir-study/references/session.md", "skills/mimir-study/references/teaching.md",
                  "skills/mimir-study/references/urgent.md", "skills/mimir-quiz/SKILL.md",
                  "skills/mimir-past-questions/SKILL.md"]
WAIT_LINE = "Checking my answers before you study them."


def test_no_flagged_state_compare_reference_or_wait_estimate_is_left():
    for path in MARKDOWN:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"flagged|`flag`|flag line|\bcompare|⚠|about 30 seconds", line, re.I), \
                f"{path}:{n}: {line.strip()[:100]}"


def test_checker_dispatch_names_one_foreground_recipe_per_host_before_the_fallback():
    dispatch = core_section("Checker dispatch")
    claude = dispatch.index("`run_in_background: false`")
    codex = dispatch.index("`spawn_agent`")
    antigravity = dispatch.index("`define_subagent`")
    fallback = dispatch.index("checker: self")
    assert claude < codex < antigravity < fallback
    assert "`mimir:verifier`" in dispatch and "`fork_turns` none" in dispatch and "`wait_agent`" in dispatch
    assert "`invoke_subagent`" in dispatch and "helpers/verifier.md" in dispatch
    assert "foreground" in dispatch and "never in the background" in dispatch


def test_wait_line_has_no_estimate_and_is_said_once_when_nothing_new_is_readable():
    holders = [p for p in MARKDOWN if WAIT_LINE in p.read_text(encoding="utf-8")]
    assert holders == [ROOT_DIR / CORE], holders
    rule = next(line for line in _read(CORE).splitlines() if WAIT_LINE in line)
    assert "once per session" in rule and "nothing new to read" in rule


def test_feedback_and_the_next_question_share_one_turn_with_text_before_tools():
    core = _read(CORE)
    assert "share one turn" in core and "share one message" not in core
    turn = _read(VERIFIED).split("## Turn shape", 1)[1].split("\n## ", 1)[0]
    steps = [turn.index(f"\n{k}. ") for k in (1, 2, 3)]
    assert steps == sorted(steps)
    assert "needs no tool call" in turn and "`session.py record`" in turn
    # Hosts end a turn with a message after its last tool call: leaving nothing new to say made
    # the tutor write its feedback twice, so the next question is what follows `record`.
    assert "before any file read, checker definition or script call" in turn
    assert "the next already checked question or the End-of-set hand-off" in turn
    assert "The feedback and the key are never written again" in turn
    for path in (VERIFIED, "skills/mimir-quiz/SKILL.md", "skills/mimir-past-questions/SKILL.md"):
        assert "written after `record`" not in _read(path), path
    # Live runs (Claude Code, Sonnet and Opus) lost text written before tool calls: the set's
    # first question is written again once its check settles, so it is never lost.
    assert "written again in full: the set's first question" in turn and "explanation or recipe" in turn and 'never point to a question "above"' in turn


def test_question_sets_cap_and_failed_check_lines():
    text = _read(VERIFIED)
    sets = text.split("## Question sets", 1)[1].split("\n## ", 1)[0]
    assert "at most 6 questions" in sets and "sets of one" in sets
    assert "before any submit call or checker dispatch" in sets
    assert "at least 8 words in a row" in sets
    assert "ends when its check has settled" in sets
    policy = text.split("## Check policy", 1)[1].split("\n## ", 1)[0]
    assert "before its check has finished" in policy and "never shown before" in policy
    failed = text.split("## Failed checks", 1)[1]
    assert "at most one recheck" in failed
    assert '"Dropped K question(s) my checker could not confirm."' in failed
    assert '"Withdrawn: my checker could not confirm this question."' in failed
    assert "never sees the wrong key" in failed and "nothing is recorded" in failed.lower()


def test_every_question_flow_follows_the_set_rules_and_names_what_is_shown_at_once():
    for flow in QUESTION_FLOWS:
        assert "verified-items.md" in _read(flow), flow
    shown = {"skills/mimir-quiz/SKILL.md": "first question of the set",
             "skills/mimir-study/references/teaching.md": "explanation",
             "skills/mimir-study/references/urgent.md": "recipe of the first question type",
             "skills/mimir-past-questions/SKILL.md": "first real question"}
    for flow, needle in shown.items():
        assert "at once" in _read(flow) and needle in _read(flow), flow
    assert "first question of the set" in core_section("Knowledge gauge")


def test_record_writes_the_results_line_and_skills_no_longer_append_it():
    recording = _read(RECORDING)
    assert '"log":' in recording and "## Results" in recording and "duplicate" in recording
    for path in MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert "## Quiz results" not in text, path
        assert not re.search(r"[Aa]ppend (the outcome|to the log)|logging under `## Results`|"
                             r"Log each under `## Results`", text), path


# Field research (#98): ingest dispatches the field researcher in the background
# with only the field name and public topic names, never course text or paths.
RESEARCHER = "helpers/field-researcher.md"
INGEST = "skills/mimir-ingest/SKILL.md"


def _ingest_step(number):
    text = _read(INGEST)
    return text.split(f"\n{number}. ", 1)[1].split(f"\n{number + 1}. ", 1)[0]


def test_field_researcher_is_a_registered_helper_with_web_tools_and_no_file_readers():
    front = frontmatter(ROOT_DIR / RESEARCHER)
    assert front["name"] == "field-researcher"
    assert front["description"].endswith("Dispatched by Mimir skills; not for direct use.")
    assert front["tools"] == "WebSearch, WebFetch, Bash"  # no Read, Grep or Glob over the workspace
    agents = json.loads(_read(".claude-plugin/plugin.json"))["agents"]
    assert f"./{RESEARCHER}" in agents
    assert "mimir:field-researcher" in _read("docs/agents/plugin-from-worktree.md")


def test_field_researcher_input_is_only_the_field_name_and_public_topic_names():
    helper = _read(RESEARCHER)
    contract = "only the field name and public topic names"
    given = helper.split("\n## Input\n", 1)[1].split("\n## ", 1)[0]
    assert contract in given
    assert "`script`" in given and "`field`" in given and "`topics`" in given
    assert "never receive" in given and "course files" in given and "paths" in given
    queries = helper.split("\n## Queries\n", 1)[1].split("\n## ", 1)[0]
    assert "only the field name and topic names" in queries
    research = _ingest_step(10)
    assert contract in research and "`fieldpack.py match`" in research and "`brief`" in research
    assert "nothing else" in research
    assert "`mimir:field-researcher`" in research or "Background dispatch" in research
    core = core_section("Background dispatch")
    assert contract in core and "field-researcher.md" in core


def test_ingest_asks_nothing_about_the_field_and_never_waits_for_research():
    research = _ingest_step(10)
    assert "?" not in research and "ask nothing" in research.lower()
    assert "background" in research and "never waits" in research
    assert "`fieldpack.py report`" in research and "`fieldpack.py list`" in research
    assert "one researcher per field" in research
    assert "one line" in research  # the result, when the research finishes
    final = _read(INGEST).split("\n11. ", 1)[1]
    assert final.startswith("Finish with one line")


def test_background_dispatch_names_one_recipe_per_host_and_leaves_the_checker_in_the_foreground():
    dispatch = core_section("Background dispatch")
    claude = dispatch.index("`run_in_background: true`")
    codex = dispatch.index("`spawn_agent`")
    antigravity = dispatch.index("`define_subagent`")
    fallback = dispatch.index("no independent agent")
    assert claude < codex < antigravity < fallback
    assert "`mimir:field-researcher`" in dispatch and "`fork_turns` none" in dispatch
    assert "never the checker" in dispatch
    helpers = core_section("Paths, commands and helpers")
    assert "field research" in helpers and "<mimir>/helpers/field-researcher.md" in helpers


# No builder without its field pack (#100): the builder dispatch makes sure the course has a
# pack first, running field research (#98's Background dispatch) and only then the builder.
def _building_a_file():
    return _read("reference/notation.md").split("\n## Building a file\n", 1)[1].split("\n## ", 1)[0]


def test_builder_dispatch_runs_field_research_and_then_the_builder_when_a_pack_is_missing():
    text = _building_a_file()
    report, match = text.index("`fieldpack.py report`"), text.index("`fieldpack.py match`")
    research, builder = text.index("Background dispatch"), text.index("`mimir:visual-builder`")
    assert report < match < research < builder
    assert "`mimir-ingest` step 10" in text  # the field is named as ingest names it
    assert "`visual.py: field pack missing" in text and "dispatch the builder again" in text
    assert "then dispatch the builder" in text
    background = core_section("Background dispatch")
    assert "Building a file" in background and "notation.md" in background
