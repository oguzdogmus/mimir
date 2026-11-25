"""The Skald showcase (#95): the README pictures' pages, rebuilt from synthetic content only."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "docs" / "showcase"
SHOOT = SHOWCASE / "shoot.py"
PIECES = sorted((SHOWCASE / "pieces").glob("*.json"))
NAMES = ["bacterium-envelope", "cfg-language", "even-as-dfa", "pda-parts"]
# the one piece outside engineering: a depiction revealed layer by layer, in a second made-up course
COURSES = {"bacterium-envelope": ("2026-Fall", "BIO110 Microbiology")}


def test_the_four_pieces_are_kept():
    assert [p.stem for p in PIECES] == NAMES


def test_pieces_come_from_made_up_courses():
    """The fixture course of tests/acceptance, or the one made-up biology course: never real material."""
    for path in PIECES:
        piece = json.loads(path.read_text(encoding="utf-8"))
        want = COURSES.get(path.stem, ("2026-Fall", "CS301 Automata"))
        assert (piece["term"], piece["course"]) == want, path.name


def test_every_piece_builds_through_the_shell(tmp_path):
    proc = subprocess.run([sys.executable, str(SHOOT), "--html-only", str(tmp_path / "out")],
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    built = sorted((tmp_path / "out").glob("*.html"))
    assert [p.stem for p in built] == NAMES
    for page in built:
        html = page.read_text(encoding="utf-8")
        assert 'data-motion="none"' in html and "Content-Security-Policy" in html
        assert "data-step=" in html, page.name
    assert 'id="mimir-sim"' in (tmp_path / "out" / "even-as-dfa.html").read_text(encoding="utf-8")


def test_readme_shows_each_piece_in_light_and_dark():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in NAMES:
        light, dark = f"assets/showcase/{name}-light.png", f"assets/showcase/{name}-dark.png"
        assert f'<source media="(prefers-color-scheme: dark)" srcset="{dark}">' in readme, name
        assert f'<img src="{light}"' in readme, name
        for rel in (light, dark):
            assert (ROOT / rel).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", rel
