"""Every refusal of a symlink goes through workspace.refuse_symlinks (run: uv run --with pytest pytest tests -q).

A hand-written ``if path.is_symlink(): raise ...`` is the copy the #96 review found six times; the helper keeps
one wording and one check. Reading ``is_symlink()`` inside a wider condition (skip it, or test it with is_dir) is
fine; only the refusal itself is refused here.
"""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _is_symlink_call(node: ast.expr) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "is_symlink" and not node.args)


def test_scripts_refuse_symlinks_only_through_the_workspace_helper():
    copies = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if path.name == "workspace.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.If) and _is_symlink_call(node.test) and isinstance(node.body[0], ast.Raise):
                copies.append(f"{path.name}:{node.lineno}")
    assert not copies, f"use workspace.refuse_symlinks: {copies}"
