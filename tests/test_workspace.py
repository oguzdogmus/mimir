"""Boundary tests for scripts/workspace.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import ast
import errno
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
WS = ROOT_DIR / "scripts" / "workspace.py"
TEMPLATES = ROOT_DIR / "assets" / "templates"

_spec = importlib.util.spec_from_file_location("workspace", WS)
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)

PLACEHOLDER = re.compile(r"<[^<>]+>")
COURSE = {"term": "2026-Fall", "course": "CS201 Theory"}
COURSE_FILES = {"INDEX.md": "INDEX.md", ".state/mastery.md": "mastery.md",
                ".state/fingerprint.md": "fingerprint.md", ".state/save.md": "save.md",
                ".state/forecast.md": "forecast.md"}


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))  # for in-process calls
    return home


def run(home: Path, cmd: str, payload) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(WS), cmd], input=stdin, capture_output=True, env=env)


def ok(home: Path, cmd: str, payload) -> dict:
    proc = run(home, cmd, payload)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b""
    assert proc.stdout.count(b"\n") == 1  # one JSON object
    return json.loads(proc.stdout)


def fails(home: Path, cmd: str, payload, needle: str = "") -> str:
    proc = run(home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("workspace.py: ") and err.count("\n") == 1
    assert "Traceback" not in err
    assert needle in err
    return err


def pointer(home: Path) -> Path:
    return home / ".config" / "mimir" / "root"


def snapshot(path: Path) -> dict:
    """Relative path -> file bytes / 'dir' / 'link:<target>' for a whole tree."""
    out = {}
    for p in sorted(path.rglob("*")):
        rel = str(p.relative_to(path))
        if p.is_symlink():
            out[rel] = "link:" + os.readlink(p)
        elif p.is_dir():
            out[rel] = "dir"
        else:
            out[rel] = p.read_bytes()
    return out


def assert_absolute_paths(out: dict) -> None:
    for key, value in out.items():
        if key in {"root", "course_dir", "dest", "source", "from"}:
            assert Path(value).is_absolute(), (key, value)
        if key == "created":
            assert all(Path(v).is_absolute() for v in value)
    assert isinstance(out["line"], str) and out["line"]


# --- root ------------------------------------------------------------------------

def test_fresh_root(home):
    out = ok(home, "root", {})
    assert out == {"root": str(home / "learning"), "source": "default", "exists": False,
                   "setup_done": None, "line": f"Learning root: {home / 'learning'} (default, no workspace yet)."}
    assert not (home / "learning").exists()


def test_root_reports_setup_done(home):
    ok(home, "init", {})
    profile = home / "learning" / ".state" / "profile.md"
    profile.write_text(profile.read_text().replace("setup_done:", "setup_done: 2026-10-17"))
    out = ok(home, "root", {})
    assert out["exists"] is True
    assert out["setup_done"] == "2026-10-17"
    assert "setup done 2026-10-17" in out["line"]


def test_root_rejects_fields_and_bad_pointer(home):
    fails(home, "root", {"x": 1}, "unknown field")
    pointer(home).parent.mkdir(parents=True)
    pointer(home).write_text("relative/path\n")
    fails(home, "root", {}, "pointer file")


# --- init ----------------------------------------------------------------------

def test_init_creates_root_inbox_profile(home):
    out = ok(home, "init", {})
    root = home / "learning"
    assert out["root"] == str(root)
    assert set(out["created"]) == {str(root), str(root / "_inbox"), str(root / ".state"),
                                   str(root / ".state" / "profile.md")}
    assert (root / "_inbox").is_dir()
    assert str(root) in out["line"]
    assert_absolute_paths(out)
    assert not pointer(home).exists()


def test_init_rerun_keeps_edited_profile(home):
    ok(home, "init", {})
    profile = home / "learning" / ".state" / "profile.md"
    profile.write_text("level: 3rd year\n")
    out = ok(home, "init", {})
    assert out["created"] == []
    assert profile.read_text() == "level: 3rd year\n"
    assert "already set up" in out["line"]


def test_init_elsewhere_with_tracked_tree_refuses(home, tmp_path):
    ok(home, "init", {})
    other = tmp_path / "elsewhere"
    fails(home, "init", {"root": str(other)}, "use relocate")
    assert not other.exists()
    assert not pointer(home).exists()


def test_init_custom_root_sets_pointer_and_default_removes_it(home):
    out = ok(home, "init", {"root": "~/uni"})
    assert out["root"] == str(home / "uni")
    assert pointer(home).read_text() == f"{home / 'uni'}\n"
    assert ok(home, "root", {})["source"] == "pointer"
    # The tracked tree is now at ~/uni, so init at the default refuses ...
    fails(home, "init", {"root": "~/learning"}, "use relocate")
    # ... but an explicit init at the current root is fine and keeps the pointer.
    assert ok(home, "init", {"root": str(home / "uni")})["created"] == []
    assert pointer(home).exists()


def test_init_writing_default_removes_pointer(home):
    pointer(home).parent.mkdir(parents=True)
    pointer(home).write_text(f"{home / 'gone'}\n")  # stale pointer, no tree there
    ok(home, "init", {"root": "~/learning"})
    assert not pointer(home).exists()
    assert ok(home, "root", {})["source"] == "default"


@pytest.mark.parametrize("value", ["relative/dir", "", 5, None])
def test_init_bad_root(home, value):
    fails(home, "init", {"root": value})


# --- course ----------------------------------------------------------------------

def test_course_builds_full_tree(home):
    out = ok(home, "course", COURSE)
    root = home / "learning"
    course = root / "2026-Fall" / "CS201 Theory"
    assert out["course_dir"] == str(course)
    assert_absolute_paths(out)
    assert str(course) in out["line"]
    for d in ["_inbox", ".state"]:
        assert (root / d).is_dir()
    for d in ["outline", "slides", "past-papers", "notes", ".state/logs", ".state/out"]:
        assert (course / d).is_dir(), d
    assert not (course / "labs").exists()
    for rel, template in COURSE_FILES.items():
        assert (course / rel).read_text() == ws.instance_template((TEMPLATES / template).read_text())
    assert (root / ".state" / "profile.md").read_text() == \
        ws.instance_template((TEMPLATES / "profile.md").read_text())
    assert set(out["created"]) == {str(p) for p in [root, *root.rglob("*")]}


def test_course_rerun_is_idempotent(home):
    ok(home, "course", COURSE)
    course = home / "learning" / "2026-Fall" / "CS201 Theory"
    (course / "INDEX.md").write_text("edited\n")
    (course / ".state" / "save.md").unlink()
    out = ok(home, "course", COURSE)
    assert out["created"] == [str(course / ".state" / "save.md")]
    assert (course / "INDEX.md").read_text() == "edited\n"
    assert out["line"] == f"Course folder ready: {course}/"
    again = ok(home, "course", COURSE)
    assert again["created"] == []
    assert again["line"] == f"Course folder already set up: {course}/"


def test_built_workspace_has_no_placeholders_and_template_headers(home):
    ok(home, "course", COURSE)
    root = home / "learning"
    names = {"profile.md": "profile.md", **{Path(k).name: v for k, v in COURSE_FILES.items()}}
    files = list(root.rglob("*.md"))
    assert len(files) == 6
    for path in files:
        text = path.read_text()
        template = (TEMPLATES / names[path.name]).read_text()
        for line in text.splitlines():
            if not line.lstrip().startswith("<!--"):
                assert not PLACEHOLDER.search(line), (path.name, line)
        header_lines, dropped = [], False
        for l in template.splitlines():
            if l.startswith("#"):
                dropped = l.startswith("## ") and bool(PLACEHOLDER.search(l))  # a dropped ## block
            elif l.startswith("|") and not dropped and not PLACEHOLDER.search(l):
                header_lines.append(l)
        assert [l for l in text.splitlines() if l.startswith("|")] == header_lines, path.name
        assert text.splitlines()[0] == template.splitlines()[0]  # comment line kept as-is


def test_template_stripping_per_file():
    def inst(name):
        return ws.instance_template((TEMPLATES / name).read_text())
    profile = inst("profile.md")
    assert "<=~5" in profile.splitlines()[0]
    assert "setup_done:" in profile.splitlines()
    assert "forecast_record:" in profile.splitlines()
    assert [l for l in profile.splitlines() if l.startswith("## ")] == \
        ["## Exam dates", "## Active courses", "## Rung hints", "## Forecast record"]
    fingerprint = inst("fingerprint.md")
    assert "label:" in fingerprint.splitlines() and "professor:" in fingerprint.splitlines()
    assert not any(l.startswith("- ") for l in fingerprint.splitlines())
    forecast = inst("forecast.md")
    assert forecast.splitlines()[1:] == ["# Forecast"]  # the placeholder ## block is dropped whole
    save = inst("save.md")
    assert save.endswith("## Previously on\n")
    assert "pending_debrief:" in save.splitlines()
    mastery = inst("mastery.md")
    assert len([l for l in mastery.splitlines() if l.startswith("|")]) == 2
    index = inst("INDEX.md")
    assert [l for l in index.splitlines() if l.startswith("## ")] == ["## Registry", "## Topics"]


def test_template_rules_synthetic():
    text = ("<!-- keep <this> as-is -->\n# T\n\nkey: <value>\nplain: text\n\n## Keep\n- <drop me>\n"
            "- keep me\n| a | b |\n|---|---|\n| <x> | <y> |\n\n## <Drop> block\nanything\n- here\n\n## After\nok\n")
    assert ws.instance_template(text) == ("<!-- keep <this> as-is -->\n# T\n\nkey:\nplain: text\n\n## Keep\n"
                                          "- keep me\n| a | b |\n|---|---|\n\n## After\nok\n")


@pytest.mark.parametrize("payload", [
    {"term": "2026-Fall", "course": "../x"},
    {"term": "2026-Fall", "course": "a/b"},
    {"term": "2026-Fall", "course": "a\\b"},
    {"term": "2026-Fall", "course": ".hidden"},
    {"term": "2026-Fall", "course": "x..y"},
    {"term": "2026-Fall", "course": "CS201: Theory"},
    {"term": "2026-Fall", "course": "CS<201>"},
    {"term": "2026-Fall", "course": "a|b"},
    {"term": "2026-Fall", "course": "a?*"},
    {"term": "2026-Fall", "course": 'a"b'},
    {"term": "2026-Fall", "course": "bad\x01name"},
    {"term": "2026-Fall", "course": "bad\nname"},
    {"term": "2026-Fall", "course": " CS201"},
    {"term": "2026-Fall", "course": ""},
    {"term": "2026-Fall", "course": 7},
    {"term": "2026-Fall"},
    {"term": "Fall", "course": "CS201"},
    {"term": "26-Fall", "course": "CS201"},
    {"term": "2026-", "course": "CS201"},
    {"term": "2026-Fall/x", "course": "CS201"},
    {"term": "2026-Fall Extra", "course": "CS201"},
    {"course": "CS201"},
    {"term": "2026-Fall", "course": "CS201", "root": "/tmp"},
])
def test_course_unsafe_names(home, payload):
    fails(home, "course", payload)
    assert not (home / "learning").exists()


def test_course_accepts_free_text_terms(home):
    for term in ["2027-Q2", "2027-T1", "2026-Spring"]:
        assert Path(ok(home, "course", {"term": term, "course": "MA101 Calculus I"})["course_dir"]).is_dir()


# --- file ----------------------------------------------------------------------------

def test_file_moves_into_role(home):
    ok(home, "init", {})
    src = home / "learning" / "_inbox" / "2024-final.pdf"
    src.write_bytes(b"%PDF paper")
    out = ok(home, "file", {"source": str(src), **COURSE, "role": "past-papers"})
    dest_dir = home / "learning" / "2026-Fall" / "CS201 Theory" / "past-papers"
    assert out["dest"] == str(dest_dir / "2024-final.pdf")
    assert out["source"] == str(src)
    assert out["line"] == f"Saved 2024-final.pdf to {dest_dir}/"
    assert_absolute_paths(out)
    assert not src.exists()
    assert (dest_dir / "2024-final.pdf").read_bytes() == b"%PDF paper"
    assert (dest_dir.parent / "INDEX.md").is_file()  # course created on the fly


def test_file_creates_workspace_and_course_when_new(home, tmp_path):
    src = tmp_path / "Downloads" / "outline.pdf"
    src.parent.mkdir()
    src.write_text("x")
    out = ok(home, "file", {"source": str(src), "term": "2026-Fall", "course": "CS201", "role": "outline"})
    assert str(home / "learning" / ".state" / "profile.md") in out["created"]
    assert Path(out["dest"]).is_file()


def test_file_collision_leaves_source(home):
    ok(home, "course", COURSE)
    dest = home / "learning" / "2026-Fall" / "CS201 Theory" / "notes" / "a.md"
    dest.write_text("existing")
    src = home / "learning" / "_inbox" / "a.md"
    src.write_text("new")
    fails(home, "file", {"source": str(src), **COURSE, "role": "notes"}, "already exists")
    assert src.read_text() == "new" and dest.read_text() == "existing"
    assert not (dest.parent / "a (1).md").exists()


def test_bad_source(home, tmp_path):
    ok(home, "init", {})
    base = {**COURSE, "role": "slides"}
    fails(home, "file", {"source": str(tmp_path / "missing.pdf"), **base}, "regular file")
    folder = tmp_path / "folder"
    folder.mkdir()
    fails(home, "file", {"source": str(folder), **base}, "regular file")
    real = tmp_path / "real.pdf"
    real.write_text("x")
    link = tmp_path / "link.pdf"
    link.symlink_to(real)
    fails(home, "file", {"source": str(link), **base}, "regular file")
    fails(home, "file", {"source": "real.pdf", **base}, "absolute")
    assert folder.is_dir() and real.exists() and link.is_symlink()
    assert not (home / "learning" / "2026-Fall").exists()


@pytest.mark.parametrize("role", ["labs", "", None, "../notes", ["notes"]])
def test_file_bad_role(home, tmp_path, role):
    src = tmp_path / "a.pdf"
    src.write_text("x")
    fails(home, "file", {"source": str(src), **COURSE, "role": role}, "role")
    assert src.exists()


def test_file_unsafe_course_from_ingested_text(home, tmp_path):
    src = tmp_path / "a.pdf"
    src.write_text("x")
    fails(home, "file", {"source": str(src), "term": "2026-Fall", "course": "../../etc", "role": "notes"})
    assert src.exists()


# --- relocate --------------------------------------------------------------------

def _tree_with_link(home: Path) -> Path:
    ok(home, "course", COURSE)
    root = home / "learning"
    (root / "_inbox" / "paper.pdf").write_text("paper")
    (root / "2026-Fall" / "CS201 Theory" / "notes" / "old-state").symlink_to("../.state")
    return root


@pytest.mark.parametrize("make_target", [False, True])
def test_relocate_moves_tree_and_sets_pointer(home, tmp_path, make_target):
    root = _tree_with_link(home)
    before = snapshot(root)
    target = tmp_path / "uni" / "learning"
    if make_target:
        target.mkdir(parents=True)
    out = ok(home, "relocate", {"to": str(target)})
    assert out["from"] == str(root) and out["root"] == str(target)
    assert_absolute_paths(out)
    assert str(target) in out["line"]
    assert not root.exists()
    assert snapshot(target) == before
    assert (target / "2026-Fall" / "CS201 Theory" / "notes" / "old-state").is_symlink()
    assert pointer(home).read_text() == f"{target}\n"
    assert ok(home, "root", {})["root"] == str(target)


def test_relocate_across_filesystems_keeps_symlinks(home, tmp_path, monkeypatch):
    root = _tree_with_link(home)
    before = snapshot(root)
    target = tmp_path / "other-disk" / "learning"

    def cross_device(src, dst):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(ws.os, "rename", cross_device)
    out = ws.cmd_relocate({"to": str(target)})
    monkeypatch.undo()
    assert out["root"] == str(target)
    assert not root.exists()
    assert snapshot(target) == before
    assert os.readlink(target / "2026-Fall" / "CS201 Theory" / "notes" / "old-state") == "../.state"
    assert pointer(home).read_text() == f"{target}\n"


def test_relocate_failed_copy_keeps_source(home, tmp_path, monkeypatch):
    root = _tree_with_link(home)
    before = snapshot(root)
    monkeypatch.setattr(ws.os, "rename", lambda s, d: (_ for _ in ()).throw(OSError(errno.EXDEV, "x")))

    def broken_copy(*args, **kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(ws.shutil, "copytree", broken_copy)
    with pytest.raises(OSError):
        ws.cmd_relocate({"to": str(tmp_path / "full-disk")})
    monkeypatch.undo()
    assert snapshot(root) == before
    assert not pointer(home).exists()


def test_relocate_blocked(home, tmp_path):
    fails(home, "relocate", {"to": str(tmp_path / "b")}, "no workspace")
    root = _tree_with_link(home)
    before = snapshot(root)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "keep.txt").write_text("mine")
    fails(home, "relocate", {"to": str(busy)}, "not empty")
    assert (busy / "keep.txt").read_text() == "mine" and len(list(busy.iterdir())) == 1
    fails(home, "relocate", {"to": str(root / "2026-Fall" / "sub")}, "inside")
    fails(home, "relocate", {"to": str(root)}, "already")
    a_file = tmp_path / "file.txt"
    a_file.write_text("x")
    fails(home, "relocate", {"to": str(a_file)}, "not a directory")
    fails(home, "relocate", {"to": "rel/path"}, "absolute")
    fails(home, "relocate", {}, "to is required")
    assert snapshot(root) == before
    assert not pointer(home).exists()


def test_relocate_home_removes_pointer(home, tmp_path):
    ok(home, "init", {"root": str(tmp_path / "away")})
    (tmp_path / "away" / "_inbox" / "x.pdf").write_text("x")
    assert pointer(home).exists()
    out = ok(home, "relocate", {"to": "~/learning"})
    assert out["root"] == str(home / "learning")
    assert (home / "learning" / "_inbox" / "x.pdf").read_text() == "x"
    assert not (tmp_path / "away").exists()
    assert not pointer(home).exists()
    assert ok(home, "root", {})["source"] == "default"


# --- contract ----------------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["root", "init", "course", "file", "relocate"])
@pytest.mark.parametrize("raw", [b"", b"not json", b"[1]", b"\xff\xfe", b'"x"'])
def test_bad_json_exits_2(home, cmd, raw):
    fails(home, cmd, raw)


def test_unknown_fields_rejected(home):
    fails(home, "init", {"rooot": "/x"}, "unknown field")
    fails(home, "relocate", {"dest": "/x"}, "unknown field")


@pytest.mark.parametrize("argv", [["unzip"], [], ["root", "extra"]])
def test_usage_errors_are_one_line(home, argv):
    proc = subprocess.run([sys.executable, str(WS), *argv], input=b"{}", capture_output=True,
                          env={**os.environ, "HOME": str(home)})
    assert proc.returncode == 2 and proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("workspace.py: ") and err.count("\n") == 1, err


def test_help_still_works(home):
    proc = subprocess.run([sys.executable, str(WS), "-h"], capture_output=True)
    assert proc.returncode == 0 and b"relocate" in proc.stdout


def test_internal_error_exits_1(home, monkeypatch, capsys):
    def boom(data):
        raise KeyError("bug")

    monkeypatch.setitem(ws.COMMANDS, "root", (boom, "x"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    assert ws.main(["root"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "workspace.py: internal error (KeyError)\n"


def test_filesystem_error_exits_2(home, tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        if os.access(locked, os.W_OK):
            pytest.skip("running with privileges that ignore permissions")
        fails(home, "init", {"root": str(locked / "learning")}, "filesystem error")
    finally:
        locked.chmod(0o700)


def test_stdlib_only():
    tree = ast.parse(WS.read_text())
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0  # no relative imports
            tops.add(node.module.split(".")[0])
    assert tops and tops <= set(sys.stdlib_module_names) | {"__future__"}, tops


# --- review fixes ------------------------------------------------------------------

def test_root_right_after_init(home):
    ok(home, "init", {})
    root = home / "learning"
    assert ok(home, "root", {}) == {"root": str(root), "source": "default", "exists": True,
                                    "setup_done": None,
                                    "line": f"Learning root: {root} (default, setup not done yet)."}


@pytest.mark.parametrize("content", ["/a\n/b\n", "/a\x07b\n", "", "relative\n"])
def test_bad_pointer_exits_2_naming_it(home, content, tmp_path):
    pointer(home).parent.mkdir(parents=True)
    pointer(home).write_text(content)
    src = tmp_path / "a.pdf"
    src.write_text("x")
    for cmd, payload in [("root", {}), ("init", {}), ("course", COURSE), ("relocate", {"to": str(tmp_path / "b")}),
                         ("file", {"source": str(src), **COURSE, "role": "notes"})]:
        fails(home, cmd, payload, str(pointer(home)))
    assert src.exists()


def test_init_with_explicit_root_repairs_bad_pointer(home, tmp_path):
    pointer(home).parent.mkdir(parents=True)
    pointer(home).write_text("/a\n/b\n")
    out = ok(home, "init", {"root": str(tmp_path / "uni")})
    assert out["root"] == str(tmp_path / "uni")
    assert pointer(home).read_text() == f"{tmp_path / 'uni'}\n"
    pointer(home).write_text("garbage\n")
    ok(home, "init", {"root": "~/learning"})
    assert not pointer(home).exists()


@pytest.mark.parametrize("value", ["~", "/", "~/.config", "~/.config/mimir", "~/.config/mimir/root"])
def test_unsafe_roots_refused(home, value):
    fails(home, "init", {"root": value}, "not allowed")
    assert not pointer(home).exists()


def test_unsafe_root_alias_refused(home, tmp_path):
    alias = tmp_path / "home-alias"
    alias.symlink_to(home)
    fails(home, "init", {"root": str(alias)}, "not allowed")
    ok(home, "init", {})
    before = snapshot(home / "learning")
    for value in ["~", "/", "~/.config", str(alias)]:
        fails(home, "relocate", {"to": value}, "not allowed")
    assert snapshot(home / "learning") == before
    assert not pointer(home).exists()


def test_relocate_refuses_symlinked_current_root(home, tmp_path):
    ok(home, "init", {})
    real = home / "real-learning"
    (home / "learning").rename(real)
    (home / "learning").symlink_to(real)
    before = snapshot(real)
    fails(home, "relocate", {"to": str(tmp_path / "b")}, "symlink")
    assert snapshot(real) == before and (home / "learning").is_symlink()
    assert not (tmp_path / "b").exists()


def test_init_alias_of_current_root_is_same_root(home, tmp_path):
    ok(home, "init", {})
    alias = tmp_path / "alias"
    alias.symlink_to(home / "learning")
    out = ok(home, "init", {"root": str(alias)})
    assert out["created"] == []


@pytest.mark.parametrize("rel", [".state/profile.md", "2026-Fall/CS201 Theory/INDEX.md",
                                 "2026-Fall/CS201 Theory/.state/save.md",
                                 "2026-Fall/CS201 Theory/.state/logs/2026-10-17-0900.md"])
def test_file_refuses_memory_files(home, rel):
    ok(home, "course", COURSE)
    src = home / "learning" / rel
    src.write_text("memory")
    fails(home, "file", {"source": str(src), **COURSE, "role": "notes"}, "memory file")
    assert src.read_text() == "memory"
    assert list((home / "learning" / "2026-Fall" / "CS201 Theory" / "notes").iterdir()) == []


def test_file_partial_move_removes_dest(home, monkeypatch):
    ok(home, "course", COURSE)
    src = home / "learning" / "_inbox" / "big.pdf"
    src.write_bytes(b"full content")
    dest = home / "learning" / "2026-Fall" / "CS201 Theory" / "slides" / "big.pdf"

    def partial_move(source, destination):
        Path(destination).write_bytes(b"full")
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(ws.shutil, "move", partial_move)
    with pytest.raises(OSError):
        ws.cmd_file({"source": str(src), **COURSE, "role": "slides"})
    monkeypatch.undo()
    assert src.read_bytes() == b"full content"
    assert not dest.exists()


@pytest.mark.parametrize("payload", [
    ("course", {"term": "2026-Fall", "course": "\udc80"}),
    ("course", {"term": "2026-\udc80", "course": "CS201"}),
    ("init", {"root": "/tmp/x\udc80"}),
    ("relocate", {"to": "/tmp/x\udc80"}),
    ("file", {"source": "/tmp/\udc80.pdf", **COURSE, "role": "notes"}),
])
def test_lone_surrogates_rejected(home, payload):
    fails(home, *payload)


@pytest.mark.parametrize("value", ["soon", "2026-10-17 extra", "17.10.2026", "2026-1-7"])
def test_setup_done_must_be_a_date(home, value):
    ok(home, "init", {})
    profile = home / "learning" / ".state" / "profile.md"
    profile.write_text(profile.read_text().replace("setup_done:", f"setup_done: {value}"))
    out = ok(home, "root", {})
    assert out["setup_done"] is None and "setup not done yet" in out["line"]


def _fake_exdev(monkeypatch):
    def cross_device(src, dst):
        raise OSError(errno.EXDEV, "Invalid cross-device link")
    monkeypatch.setattr(ws.os, "rename", cross_device)


def _broken_pointer(monkeypatch):
    def broken(root):
        raise OSError(errno.EACCES, "Permission denied")
    monkeypatch.setattr(ws, "set_pointer", broken)


def test_cross_fs_pointer_failure_keeps_old_tree(home, tmp_path, monkeypatch):
    root = _tree_with_link(home)
    before = snapshot(root)
    target = tmp_path / "other-disk" / "learning"
    _fake_exdev(monkeypatch)
    _broken_pointer(monkeypatch)
    with pytest.raises(OSError):
        ws.cmd_relocate({"to": str(target)})
    monkeypatch.undo()
    assert snapshot(root) == before
    assert not target.exists()
    assert not pointer(home).exists()


@pytest.mark.parametrize("make_target", [False, True])
def test_same_fs_pointer_failure_rolls_back(home, tmp_path, monkeypatch, make_target):
    root = _tree_with_link(home)
    before = snapshot(root)
    target = tmp_path / "uni"
    if make_target:
        target.mkdir()
    _broken_pointer(monkeypatch)
    with pytest.raises(OSError):
        ws.cmd_relocate({"to": str(target)})
    monkeypatch.undo()
    assert snapshot(root) == before
    assert not pointer(home).exists()
    if make_target:
        assert target.is_dir() and list(target.iterdir()) == []
    else:
        assert not target.exists()


@pytest.mark.parametrize("make_target", [False, True])
def test_partial_copy_is_cleaned_up(home, tmp_path, monkeypatch, make_target):
    root = _tree_with_link(home)
    before = snapshot(root)
    target = tmp_path / "other-disk"
    if make_target:
        target.mkdir()
    _fake_exdev(monkeypatch)

    def partial_copy(src, dst, **kwargs):
        Path(dst).mkdir(exist_ok=True)
        (Path(dst) / "_inbox").mkdir()
        (Path(dst) / "_inbox" / "paper.pdf").write_text("pa")
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(ws.shutil, "copytree", partial_copy)
    with pytest.raises(OSError):
        ws.cmd_relocate({"to": str(target)})
    monkeypatch.undo()
    assert snapshot(root) == before
    assert not pointer(home).exists()
    if make_target:
        assert target.is_dir() and list(target.iterdir()) == []
    else:
        assert not target.exists()
    # A retry is not refused as "not empty".
    assert ok(home, "relocate", {"to": str(target)})["root"] == str(target)


def test_failed_old_tree_delete_is_a_warning(home, tmp_path, monkeypatch, capsys):
    root = _tree_with_link(home)
    target = tmp_path / "other-disk" / "learning"
    _fake_exdev(monkeypatch)
    real_rmtree = ws.shutil.rmtree

    def stuck_rmtree(path, *args, **kwargs):
        if Path(path) == root:
            raise OSError(errno.EBUSY, "Device or resource busy")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(ws.shutil, "rmtree", stuck_rmtree)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps({"to": str(target)}).encode())))
    assert ws.main(["relocate"]) == 0
    monkeypatch.undo()
    captured = capsys.readouterr()
    assert captured.err == ""
    out = json.loads(captured.out)
    assert out["root"] == str(target)
    assert str(root) in out["warning"]
    assert f"The old folder {root} was not fully removed" in out["line"]
    assert pointer(home).read_text() == f"{target}\n"
    assert (target / ".state" / "profile.md").is_file()
