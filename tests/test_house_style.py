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
from test_visual import link_pack

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
                 "meaning test", "figure kinds", "plots are computed", "cross-field recipes"):
        assert part in heads, (part, heads)
    assert "field notes" not in heads  # #103: field conventions live in field packs
    for kind in ("depiction of a real thing", "formal notation", "plot of data or a function",
                 "mimir's own sketch"):
        assert kind in text.lower(), kind


# Rules of one field that #87 put in the guide and #103 moved to field packs. The
# examples that name a field's subject (a heart, a DFA) stay: they teach the look.
FIELD_RULES = re.compile(
    r"anatomy|anterior view|microbiolog|envelope order|length-to-width|not to scale"
    r"|erd notation|time axis|input tape|automata|double circles?|start arrow from nowhere"
    r"|textbook convention", re.I)


def test_guide_holds_no_field_specific_rules():
    text = " ".join(_guide().split())  # a rule may wrap across lines
    hits = [text[max(m.start() - 40, 0):m.end() + 40] for m in FIELD_RULES.finditer(text)]
    assert not hits, "field rules belong in field packs:\n" + "\n".join(hits)


def test_guide_keeps_the_cross_field_graph_geometry():
    section = _guide().lower().split("### cross-field recipes", 1)[1]
    for recipe in ("arrowhead", "11 long and 8 wide", "edges between neighbours", "±25°",
                   "0.45 × the centre distance", "self-loop", "−115°", "2.6r", "12 units above the apex"):
        assert recipe in section, recipe


def _blocks(lang: str) -> list[str]:
    return re.findall(rf"^```{lang}\n(.*?)^```", _guide(), re.M | re.S)


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    for cmd, payload in (("init", {}), ("course", {"term": TERM, "course": COURSE})):
        subprocess.run([sys.executable, str(WS), cmd], input=json.dumps(payload).encode(),
                       capture_output=True, env=_env(home), check=True)
    link_pack(home, TERM, COURSE)
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


def test_builder_offers_the_machine_of_a_page():
    """#94 (follow-up from #93): the page kind takes a machine (#90); the helper passes it on and the
    guide says how the diagram names its states."""
    body = _helper()[1]
    assert '`"machine"`' in body and '`"example"`' in body and 'id="state-<i>"' in body
    for field in ("kind", "states", "start", "accept", "transitions", "stack_start", "pop", "push"):
        assert f'"{field}"' in body, field
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## A machine page" in guide and 'id="state-<i>"' in guide


def test_builder_reads_the_core_guide_the_field_packs_and_the_notation_section():
    """#100: every builder reads the core guide, the course's field packs and its notation section,
    from ``visual.py inputs``, which refuses a course with no pack before anything is composed."""
    body = _helper()[1]
    given = body.split("\n## Input\n", 1)[1].split("\n## ", 1)[0]
    for part in ("core house style guide", "field pack", "notation section"):
        assert part in given, part
    run = body.index('python3 "<script>" inputs')
    assert body.index("## Read the house style guide") < run < body.index("## Compose")
    assert "`packs`" in body and "`notation`" in body
    refusal = body[run:body.index("## Compose")]
    assert "`visual.py: field pack missing" in refusal and "stop" in refusal


def test_builder_puts_the_professor_first_then_the_field_pack_then_the_core_guide():
    order = _helper()[1].split("\n## Precedence\n", 1)[1].split("\n## ", 1)[0]
    own, pack, guide = (order.index(s) for s in ("course's own materials", "field pack", "core guide"))
    assert own < pack < guide
    assert "notation section" in order[own:pack] and "slides" in order[own:pack]
    assert "the professor always wins" in order.lower()


def test_guide_says_the_builder_reads_the_field_packs_beside_it():
    head = _guide().split("\n## ", 1)[0]
    assert "no other file" not in head
    assert "field pack" in head and "notation section" in head
