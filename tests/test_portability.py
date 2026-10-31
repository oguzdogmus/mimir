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
