#!/usr/bin/env python3
"""The repo's one check command: lint, the tests and the release build. Run from a clone::

    python3 tests/check.py [lint] [tests] [release]

Dev only, standard library only, Python 3.11+. With no argument it runs all three in that order and stops at
the first failure, with that step's exit code. An unknown step exits 2 with one stderr line. CI's lint job runs
``python3 tests/check.py lint``, so this file owns the pinned ruff version.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUFF = "ruff@0.17.6"  # pinned: ruff.toml takes preview rules, and preview rules change between releases
STEPS = {
    "lint": ["uvx", RUFF, "check"],
    "tests": ["uv", "run", "--with", "pytest", "--with", "pytest-xdist", "pytest", "tests", "-q", "-n", "auto"],
    "release": [sys.executable, "scripts/release_check.py", "--no-open"],
}


def main(argv: list[str]) -> int:
    unknown = [name for name in argv if name not in STEPS]
    if unknown:
        print(f"unknown step '{unknown[0]}': choose from {', '.join(STEPS)}", file=sys.stderr)
        return 2
    for name in argv or list(STEPS):
        print(f"== {name}", flush=True)
        code = subprocess.run(STEPS[name], cwd=ROOT, check=False).returncode
        if code:
            print(f"{name} failed with exit {code}", file=sys.stderr)
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
