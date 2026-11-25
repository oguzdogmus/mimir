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


def test_a_merge_committed_with_the_leftover_conflicts_block_is_refused(conflicted):
    done = git(conflicted, "commit", "--no-edit", check=False)
    assert done.returncode != 0
    assert "# Conflicts:" in done.stderr
    assert git(conflicted, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0


def test_a_merge_with_a_clean_message_is_committed(conflicted):
    git(conflicted, "commit", "-q", "-m", "Merge side: keep both lines")
    assert git(conflicted, "log", "-1", "--format=%s").stdout.strip() == "Merge side: keep both lines"


def test_an_ordinary_message_that_mentions_the_block_is_committed(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    git(tmp_path, "add", "a.txt")
    git(tmp_path, "commit", "-q", "-m", "Refuse messages that keep the # Conflicts: block")
    assert git(tmp_path, "log", "-1", "--format=%s").stdout.strip().startswith("Refuse messages")
