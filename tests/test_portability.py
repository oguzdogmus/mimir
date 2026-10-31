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


def test_no_agents_folder_for_other_tools_to_misread():
    assert not (ROOT_DIR / "agents").exists()
