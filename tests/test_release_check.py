"""Tests for scripts/release_check.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
RC = SCRIPTS / "release_check.py"

sys.path.insert(0, str(SCRIPTS))
import release_check  # noqa: E402
import visual  # noqa: E402

KEYS = ["platform", "html", "svg", "opened_html", "opened_svg", "line"]
SVG_NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(release_check.tempfile, "tempdir", str(tmp_path))


def _run(args, tmp_path):
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path), "HOME": str(tmp_path)}
    return subprocess.run([sys.executable, str(RC), *args], capture_output=True, text=True, env=env, timeout=30)


def test_build_only(tmp_path):
    proc = _run(["--no-open"], tmp_path)
    assert proc.returncode == 0 and proc.stderr == ""
    out = json.loads(proc.stdout)
    assert list(out) == KEYS
    assert out["opened_html"] is False and out["opened_svg"] is False
    page, image = Path(out["html"]), Path(out["svg"])
    assert page.is_file() and image.is_file() and page.parent == image.parent
    assert page.name == "mimir-release-check.html" and image.name == "mimir-release-check.svg"
    assert " " in page.parent.name and page.parent.parent == tmp_path
    assert page.is_absolute()
    root = ET.parse(image).getroot()
    assert root.tag == f"{SVG_NS}svg"
    assert root.find(f"{SVG_NS}title").text == "Mimir release check"
    assert out["platform"] in root.find(f"{SVG_NS}desc").text
    text = page.read_text(encoding="utf-8")
    assert "Mimir release check" in text and "<script" not in text
    assert "http://" not in text and "https://" not in text  # self-contained
    assert out["line"] == f"Built `{page}` and `{image}` (not opened)."


def test_opened(monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(visual, "open_in_browser", lambda path: seen.append(path) or True)
    assert release_check.main([]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["opened_html"] is True and out["opened_svg"] is True
    assert seen == [Path(out["html"]), Path(out["svg"])]
    assert out["platform"] in out["line"] and out["html"] in out["line"]


@pytest.mark.parametrize("results", [(False, False), (True, False), (False, True)])
def test_not_opened(monkeypatch, capsys, results):
    answers = iter(results)
    monkeypatch.setattr(visual, "open_in_browser", lambda path: next(answers))
    assert release_check.main([]) == 1
    out = json.loads(capsys.readouterr().out)
    assert (out["opened_html"], out["opened_svg"]) == results
    assert out["html"] in out["line"] and out["svg"] in out["line"]


def test_headless_linux_uses_the_shipped_opener(monkeypatch, capsys):
    monkeypatch.setattr(visual, "_platform", lambda: "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert release_check.main([]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == "linux" and out["opened_html"] is False and out["opened_svg"] is False


@pytest.mark.parametrize("platform", ["linux", "macos", "windows", "wsl", "other"])
def test_platform_is_echoed(monkeypatch, capsys, platform):
    monkeypatch.setattr(visual, "_platform", lambda: platform)
    assert release_check.main(["--no-open"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == platform
    assert f"Platform: <code id=\"platform\">{platform}</code>" in Path(out["html"]).read_text(encoding="utf-8")
    assert f"Platform: {platform}" in Path(out["svg"]).read_text(encoding="utf-8")


@pytest.mark.parametrize("args", [["--bogus"], ["extra"]])
def test_bad_args(tmp_path, args):
    proc = _run(args, tmp_path)
    assert proc.returncode == 2 and proc.stdout == ""
    lines = proc.stderr.splitlines()
    assert len(lines) == 1 and lines[0].startswith("release_check.py: ")


def test_no_copy_of_the_opener():
    tree = ast.parse(RC.read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    imports = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert "subprocess" not in imports | names and "startfile" not in attrs
    assert "open_in_browser" in attrs and "_platform" in attrs
    for word in ("xdg-open", "wslview", "explorer.exe"):
        assert word not in RC.read_text(encoding="utf-8")


def test_no_skill_uses_it():
    for path in (ROOT_DIR / "skills").rglob("*.md"):
        assert "release_check" not in path.read_text(encoding="utf-8"), path


def test_unwritable_temp_folder_exits_2_with_one_line(monkeypatch, capsys):
    def boom(*_args, **_kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(release_check.tempfile, "mkdtemp", boom)
    assert release_check.main(["--no-open"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("release_check.py: ") and captured.err.count("\n") == 1
    assert "disk full" in captured.err


def test_help_lists_every_user_command():
    plugin = json.loads((ROOT_DIR / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    help_text = (ROOT_DIR / "skills" / "help" / "SKILL.md").read_text(encoding="utf-8")
    for entry in plugin["skills"]:
        name = entry.rstrip("/").rsplit("/", 1)[-1]
        front = (ROOT_DIR / "skills" / name / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        if "user-invocable: false" in front:
            assert f"/mimir:{name}`" not in help_text, name
        else:
            assert f"| `/mimir:{name}` |" in help_text, name
