"""The versioned git hooks in .githooks/, driven through real git commits."""

import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / ".githooks"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    config = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false",
              "-c", f"core.hooksPath={HOOKS.as_posix()}", "-c", "init.defaultBranch=main"]
    return subprocess.run(["git", *config, *args], cwd=repo, capture_output=True, text=True,
                          encoding="utf-8", check=check)


@pytest.fixture
def conflicted(tmp_path):
    """A repo mid-merge: both branches changed one line, the conflict resolved and staged."""
    git(tmp_path, "init", "-q")
    note = tmp_path / "note.txt"
    note.write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "note.txt")
    git(tmp_path, "commit", "-q", "-m", "Base")
    git(tmp_path, "switch", "-q", "-c", "side")
    note.write_text("side\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "Side")
    git(tmp_path, "switch", "-q", "main")
    note.write_text("main\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "Main")
    assert git(tmp_path, "merge", "side", check=False).returncode != 0
    note.write_text("both\n", encoding="utf-8")
    git(tmp_path, "add", "note.txt")
    return tmp_path


def message(repo: Path) -> str:
    return git(repo, "log", "-1", "--format=%B").stdout


def test_a_merge_committed_without_the_editor_loses_the_conflicts_block(conflicted):
    git(conflicted, "commit", "-q", "--no-edit")
    body = message(conflicted)
    assert body.startswith("Merge branch 'side'")
    assert "# Conflicts:" not in body
    assert "#\tnote.txt" not in body


def test_a_merge_committed_through_the_editor_is_not_refused(conflicted):
    git(conflicted, "-c", "core.editor=true", "commit", "-q")
    body = message(conflicted)
    assert body.startswith("Merge branch 'side'")
    assert "Conflicts" not in body


def test_only_the_conflicts_block_is_deleted_from_a_message_file(conflicted, tmp_path_factory):
    msg = tmp_path_factory.mktemp("msg") / "message.txt"
    msg.write_text("Merge side: keep both lines\n\n# Conflicts:\n#\tnote.txt\n#\tother.txt\n"
                   "\nCo-Authored-By: Test <test@example.com>\n", encoding="utf-8")
    git(conflicted, "commit", "-q", "--cleanup=verbatim", "-F", str(msg))
    body = message(conflicted)
    assert "Conflicts" not in body
    assert "#\t" not in body
    assert body.startswith("Merge side: keep both lines\n")
    assert "Co-Authored-By: Test <test@example.com>" in body


def test_a_merge_with_a_clean_message_is_committed(conflicted):
    git(conflicted, "commit", "-q", "-m", "Merge side: keep both lines")
    assert git(conflicted, "log", "-1", "--format=%s").stdout.strip() == "Merge side: keep both lines"


def test_an_ordinary_message_that_mentions_the_block_is_committed(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    git(tmp_path, "add", "a.txt")
    git(tmp_path, "commit", "-q", "-m", "Strip the # Conflicts: block from merge messages")
    assert git(tmp_path, "log", "-1", "--format=%s").stdout.strip() == "Strip the # Conflicts: block from merge messages"
