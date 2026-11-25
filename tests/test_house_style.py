"""The Skald house style guide and the visual builder helper that follows it (#93).

Seam 2 of spec #86 (living-doc text checks), plus the guide's own examples
driven through seam 1 (the visual.py command line), so the guide never shows
a builder markup the shell refuses.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
GUIDE = ROOT_DIR / "reference" / "house-style.md"
HELPER = ROOT_DIR / "helpers" / "visual-builder.md"
TOKENS = ROOT_DIR / "assets" / "skald" / "tokens.css"
VIS = ROOT_DIR / "scripts" / "visual.py"
WS = ROOT_DIR / "scripts" / "workspace.py"
TERM, COURSE = "2026-Fall", "CS201 Theory"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _headings(text: str) -> list[str]:
    return [line.lstrip("#").strip().lower() for line in text.splitlines() if line.startswith("#")]


def test_guide_is_a_plain_reference_file_with_every_part_the_spec_names():
    text = _guide()
    assert not text.startswith("---")  # plain reference file, no skill frontmatter
    heads = " | ".join(_headings(text))
    for part in ("feel", "composing", "tokens", "teaching highlight", "motion", "print",
                 "meaning test", "figure kinds", "plots are computed", "field notes"):
        assert part in heads, (part, heads)
    for kind in ("depiction of a real thing", "formal notation", "plot of data or a function",
                 "mimir's own sketch"):
        assert kind in text.lower(), kind


def _blocks(lang: str) -> list[str]:
    return re.findall(rf"^```{lang}\n(.*?)^```", _guide(), re.M | re.S)


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    for cmd, payload in (("init", {}), ("course", {"term": TERM, "course": COURSE})):
        subprocess.run([sys.executable, str(WS), cmd], input=json.dumps(payload).encode(),
                       capture_output=True, env=_env(home), check=True)
    return home


def _env(home: Path) -> dict:
    return {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}


def _build(home: Path, kind: str, payload: dict) -> Path:
    proc = subprocess.run([sys.executable, str(VIS), kind], capture_output=True, env=_env(home),
                          input=json.dumps({"term": TERM, "course": COURSE, **payload}).encode())
    assert proc.returncode == 0, proc.stderr.decode()
    return Path(json.loads(proc.stdout)["path"])


def test_every_page_example_in_the_guide_builds_as_a_page(home):
    blocks = _blocks("html")
    assert blocks
    for k, body in enumerate(blocks, 1):
        page = _build(home, "page", {"name": f"guide-{k}", "title": "Guide example", "body": body})
        assert "sk-chalk" in page.read_text(encoding="utf-8")  # the shell, not the guide, adds the filters


def test_every_svg_example_in_the_guide_builds_as_an_svg(home):
    blocks = _blocks("svg")
    assert blocks
    for k, svg in enumerate(blocks, 1):
        _build(home, "svg", {"name": f"guide-svg-{k}", "svg": svg})


def test_guide_leaves_the_filter_block_to_the_shell():
    """The prototype guide had builders copy the sk-defs filters; the shell injects them (#88)."""
    assert "<feTurbulence" not in _guide() and 'class="sk-defs"' not in _guide()


def test_every_token_and_class_the_guide_names_is_in_the_tokens():
    css = TOKENS.read_text(encoding="utf-8")
    text = _guide()
    for var in set(re.findall(r"`(--[a-z][a-z0-9-]*)", text)):
        assert re.search(rf"(var\(|^\s*|;\s*){re.escape(var)}\b", css, re.M), var
    for cls in set(re.findall(r"`\.([a-z][a-z0-9-]*)`", text)):
        assert re.search(rf"\.{re.escape(cls)}\b", css), cls


def _helper() -> tuple[dict, str]:
    _, head, body = HELPER.read_text(encoding="utf-8").split("---", 2)
    return dict(line.split(": ", 1) for line in head.strip().splitlines()), body


def test_builder_runs_on_the_model_of_the_look_iteration_verdict():
    assert _helper()[0]["model"] == "sonnet"  # #87: Sonnet builds held up against Opus


def test_builder_reads_the_guide_beside_the_script_it_is_given():
    body = _helper()[1]
    match = re.search(r'"\$\(dirname "\$\(dirname "<script>"\)"\)/([\w/.-]+)', body)
    assert match, "the helper must read the guide by a path derived from <script>"
    assert (VIS.parent.parent / match.group(1)).resolve() == GUIDE


def test_builder_builds_with_page_and_svg_only():
    front, body = _helper()
    for old in ("sheet", "steps", "trace"):
        assert not re.search(rf"`{old}`|[<|]{old}[|>]", front["description"] + body), old
    assert re.search(r"<page\|svg>", body)
    assert "figure kind" in body.lower()
