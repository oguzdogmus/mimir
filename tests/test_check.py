"""tests/check.py is the one check command, and it owns the pinned ruff version (run: python3 tests/check.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "tests" / "check.py"
NAMES_THE_COMMAND = ["README.md", "AGENTS.md", "ruff.toml", ".github/workflows/tests.yml"]


def test_an_unknown_step_exits_2_with_one_stderr_line():
    proc = subprocess.run([sys.executable, str(CHECK), "lint", "typo"], capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    assert proc.stderr.strip() == "unknown step 'typo': choose from lint, tests, release"
    assert proc.stdout == ""  # nothing ran


def test_check_owns_the_ruff_version_and_the_docs_and_ci_name_the_command():
    for name in NAMES_THE_COMMAND:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "ruff@" not in text, name
        assert "tests/check.py" in text, name
    assert "run: python3 tests/check.py lint" in (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
