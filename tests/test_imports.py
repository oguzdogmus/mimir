"""The scripts import each other at the top only, and without a cycle (run: uv run --with pytest pytest tests -q).

A sibling import inside a function hides a cycle; this test refuses both, so a module's dependencies are the
ones its top lists.
"""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
MODULES = {p.stem: p for p in SCRIPTS.glob("*.py")}


def _imports(tree: ast.AST) -> list[tuple[str, int]]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.append((node.module, node.lineno))
    return [(name, line) for name, line in found if name in MODULES]


def _graph() -> dict[str, set[str]]:
    return {name: {m for m, _ in _imports(ast.parse(path.read_text(encoding="utf-8")))}
            for name, path in MODULES.items()}


def test_scripts_import_their_siblings_only_at_the_top():
    nested = []
    for name, path in MODULES.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        top = {line for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.If, ast.Try))
               for _, line in _imports(node)}
        nested += [f"{name}.py:{line} imports {m}" for m, line in _imports(tree) if line not in top]
    assert not nested, nested


def test_the_script_imports_have_no_cycle():
    graph, state, cycles = _graph(), {}, []

    def visit(name: str, path: list[str]) -> None:
        state[name] = "open"
        for dep in sorted(graph[name]):
            if state.get(dep) == "open":
                cycles.append(" -> ".join(path[path.index(dep):] + [dep]))
            elif dep not in state:
                visit(dep, path + [dep])
        state[name] = "done"

    for name in sorted(graph):
        if name not in state:
            visit(name, [name])
    assert not cycles, cycles
