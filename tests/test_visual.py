"""Boundary tests for scripts/visual.py (run: uv run --with pytest pytest tests -q)."""

from __future__ import annotations

import ast
import base64
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT_DIR / "scripts"
VIS = SCRIPTS / "visual.py"
WS = SCRIPTS / "workspace.py"
KATEX = ROOT_DIR / "assets" / "vendor" / "katex"

sys.path.insert(0, str(SCRIPTS))
import session  # noqa: E402
import visual  # noqa: E402

TERM, COURSE = "2026-Fall", "CS201 Theory"
ROWS = [("past-papers/q.jpg", "past-papers", "1", "ocr"),
        ("past-papers/s.pdf", "past-papers", "4", "ocr"),
        ("past-papers/big.png", "past-papers", "1", "ocr"),
        ("past-papers/nopages.pdf", "past-papers", "", "text"),
        ("past-papers/missing.jpg", "past-papers", "1", "ocr"),
        ("/etc/passwd", "past-papers", "1", "text"),
        ("past-papers/../../outside.jpg", "past-papers", "1", "ocr"),
        ("past-papers/link.jpg", "past-papers", "1", "ocr")]
JPEG = b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes" * 4
INJECT = "</p><script>alert(1)</script>"
SVG_OK = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
          'viewBox="0 0 200 80" role="img">\n'
          '  <title>DFA for an even number of 0s</title>\n'
          '  <desc>Two states q0 (start, accepting, double circle) and q1; 0 moves between them.</desc>\n'
          '  <defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" '
          'markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z"/></marker>'
          '<linearGradient id="g"><stop offset="0" stop-color="#fff"/></linearGradient></defs>\n'
          '  <style>circle { fill: url(#g); stroke: currentColor; } text { font: 14px sans-serif; }</style>\n'
          '  <circle cx="40" cy="40" r="18"/><circle cx="40" cy="40" r="14"/>\n'
          '  <circle cx="160" cy="40" r="18"/>\n'
          '  <line x1="58" y1="40" x2="142" y2="40" stroke="black" marker-end="url(#arrow)"/>\n'
          '  <text x="40" y="45" text-anchor="middle">q0</text><text x="160" y="45">q<tspan>1</tspan></text>\n'
          '  <text x="100" y="32">0 &amp; ε</text>\n'
          '  <use href="#arrow"/><use xlink:href="#arrow"/>\n'
          '</svg>\n')


# --- fixtures and helpers ----------------------------------------------------------

@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def root(home):
    ws_ok(home, "init", {})
    return home / "learning"


@pytest.fixture
def cdir(home, root, tmp_path):
    ws_ok(home, "course", {"term": TERM, "course": COURSE})
    cdir = root / TERM / COURSE
    index = cdir / "INDEX.md"
    lines = index.read_text().splitlines()
    at = lines.index("## Topics") - 1
    lines[at:at] = [f"| {p} | {TERM} | {r} | {n} | {f} |" for p, r, n, f in ROWS]
    index.write_text("\n".join(lines) + "\n")
    pp = cdir / "past-papers"
    (pp / "q.jpg").write_bytes(JPEG)
    (pp / "s.pdf").write_bytes(b"%PDF-1.7\n")
    (pp / "nopages.pdf").write_bytes(b"%PDF-1.7\n")
    (pp / "big.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    (tmp_path / "outside.jpg").write_bytes(JPEG)
    (pp / "link.jpg").symlink_to(tmp_path / "outside.jpg")
    return cdir


def _env(home: Path, **extra) -> dict:
    return {**os.environ, "HOME": str(home), **extra}


def _run(home: Path, cmd: str, payload, env: dict | None = None) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.run([sys.executable, str(VIS), cmd], input=stdin, capture_output=True,
                          env=env or _env(home))


def ok(home: Path, cmd: str, payload, env: dict | None = None) -> dict:
    proc = _run(home, cmd, payload, env)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stderr == b"" and proc.stdout.count(b"\n") == 1
    out = json.loads(proc.stdout)
    assert isinstance(out["line"], str) and out["line"]
    return out


def fails(home: Path, cmd: str, payload, needle: str = "") -> str:
    proc = _run(home, cmd, payload)
    assert proc.returncode == 2, proc.stderr.decode()
    assert proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("visual.py: ") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert needle in err, err
    return err


def ws_ok(home: Path, cmd: str, payload) -> dict:
    proc = subprocess.run([sys.executable, str(WS), cmd], input=json.dumps(payload).encode(),
                          capture_output=True, env=_env(home))
    assert proc.returncode == 0, proc.stderr.decode()
    return json.loads(proc.stdout)


def _add_original(cdir: Path, name: str, data: bytes) -> None:
    """File ``past-papers/<name>`` with an ``ocr`` registry row of 1 page."""
    (cdir / "past-papers" / name).write_bytes(data)
    index = cdir / "INDEX.md"
    lines = index.read_text().splitlines()
    at = lines.index("## Topics") - 1
    lines[at:at] = [f"| past-papers/{name} | {TERM} | past-papers | 1 | ocr |"]
    index.write_text("\n".join(lines) + "\n")


def sheet(*blocks, name="demo", title="Pumping lemma") -> dict:
    return {"term": TERM, "course": COURSE, "name": name, "title": title, "blocks": list(blocks)}


def svg(doc: str = SVG_OK, name="dfa") -> dict:
    return {"term": TERM, "course": COURSE, "name": name, "svg": doc}


def build(home: Path, payload) -> tuple[dict, str]:
    out = ok(home, "sheet", payload)
    return out, Path(out["path"]).read_text(encoding="utf-8")


BASIC = (sheet({"heading": "Setup"}, {"text": r"Let \(x\) be the length."}, {"math": r"\frac{a}{b}"}))


def scripts(page: str) -> list[str]:
    return re.findall(r"<script>(.*?)</script>", page, re.S)


def main_part(page: str) -> str:
    """The page body that holds content (the inlined KaTeX code is outside it)."""
    return page.split("<main>", 1)[1].split("</main>", 1)[0]


def csp(page: str) -> str:
    match = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">', page)
    assert match
    return html.unescape(match.group(1))


# --- sheet ---------------------------------------------------------------------------

def test_constants_are_the_spec_values():
    assert visual.BLOCK_MAX_CHARS == 4000 and visual.SHEET_MAX_BLOCKS == 200
    assert visual.ORIGINAL_EMBED_MAX_BYTES == 10 * 1024 * 1024 and visual.SVG_MAX_BYTES == 1024 * 1024
    assert visual.TITLE_MAX_CHARS == 120 and visual.HEADING_MAX_CHARS == 120
    assert visual.NAME_MAX_CHARS == 60 and visual.OPEN_WAIT_SECONDS == 5
    version = (KATEX / "VERSION").read_text().splitlines()
    assert version[0] == "0.19.0"
    assert "source: https://registry.npmjs.org/katex/-/katex-0.19.0.tgz" in version
    assert any(line.startswith("sha512: v6Tznz3zJ7u3niRCoDTsumM2+HA2XXcCu+WAacCeHD2z3p9A9Ks987o5FzfTGBN0e8A0vjE"
                               "gIDvLbICrXpdw/Q==") for line in version)
    assert "MIT License" in (KATEX / "LICENSE").read_text()


def test_sheet_written_to_out(home, cdir):
    out, page = build(home, BASIC)
    path = cdir / ".state" / "out" / "demo.html"
    assert out["path"] == str(path) and out["course_dir"] == str(cdir)
    assert out["line"] == f"Built {path}."
    assert "<h2>Setup</h2>" in page and r"<p>Let \(x\) be the length.</p>" in page
    assert r'<div class="mimir-display" tabindex="0">\frac{a}{b}</div>' in page
    assert "<title>Pumping lemma</title>" in page and "<h1>Pumping lemma</h1>" in page
    assert '<html lang="en">' in page and "<main>" in page
    assert not re.search(r"\{\{[A-Z_]+\}\}", page)
    assert sorted(p.name for p in path.parent.iterdir()) == ["demo.html"]  # no temp file left


def test_out_created_if_missing_and_rebuild_replaces(home, cdir):
    (cdir / ".state" / "out").rmdir()
    build(home, BASIC)
    _, page = build(home, sheet({"text": "second"}))
    assert "<p>second</p>" in page
    assert [p.name for p in (cdir / ".state" / "out").iterdir()] == ["demo.html"]


def test_page_is_offline_and_self_contained(home, cdir):
    _, page = build(home, BASIC)
    assert not re.search(r"""(?:src|href)\s*=\s*["']?\s*(?:https?:)?//""", page, re.I)
    assert not re.search(r"url\(\s*['\"]?(?!data:)", page)
    assert not re.search(r"@import", page)
    assert "url(fonts/" not in page and ".woff)" not in page and ".ttf)" not in page
    fonts = sorted(p.name for p in (KATEX / "fonts").glob("*.woff2"))
    assert len(fonts) == 20
    assert page.count("url(data:font/woff2;base64,") == len(fonts)
    assert 'format("woff")' not in page and 'format("truetype")' not in page
    for font in fonts:
        assert base64.b64encode((KATEX / "fonts" / font).read_bytes()).decode() in page


def test_csp_hashes_match_inline_scripts(home, cdir):
    _, page = build(home, BASIC)
    policy = csp(page)
    bodies = scripts(page)
    assert len(bodies) == 3 and page.count("<script") == 3
    assert bodies[0] == (KATEX / "katex.min.js").read_text()
    assert bodies[1] == (KATEX / "contrib" / "auto-render.min.js").read_text()
    hashes = {"'sha256-" + base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() + "'"
              for b in bodies}
    directives = dict(d.strip().split(" ", 1) for d in policy.split(";"))
    assert set(directives["script-src"].split()) == hashes
    assert directives["default-src"] == "'none'"
    assert directives["font-src"] == "data:" and directives["img-src"] == "data:"
    assert directives["style-src"] == "'unsafe-inline'"
    assert "connect-src" not in directives and "http" not in policy


def test_katex_options_and_delimiters(home, cdir):
    _, page = build(home, BASIC)
    init = scripts(page)[2]
    assert 'output: "htmlAndMathml"' in init and "throwOnError: false" in init and "trust: false" in init
    assert re.findall(r'left: "([^"]*)"', init) == [r"\\(", r"\\["]
    assert "innerHTML" not in init and "innerHTML" not in page.split("<script>")[0]


def test_accessible_shell(home, cdir):
    _, page = build(home, BASIC)
    assert "color-scheme: light dark" in page and "prefers-color-scheme: dark" in page
    assert "text-decoration: underline" in page
    assert "@keyframes" not in page.split("</style>", 1)[1].split("<script>")[0]


@pytest.mark.parametrize("field", ["title", "heading", "text", "math"])
def test_injection_is_escaped(home, cdir, field):
    blocks = [{"text": "plain"}] if field == "title" else [{field: f"x {INJECT}"}]
    payload = sheet(*blocks, title=f"T {INJECT}" if field == "title" else "T")
    _, page = build(home, payload)
    assert page.count("<script") == 3 and "alert(1)</script>" not in page
    assert "&lt;/p&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in page
    hashes = set(re.findall(r"'sha256-[^']+'", csp(page)))
    assert len(hashes) == 3


def test_attribute_breakout_is_escaped(home, cdir):
    _, page = build(home, sheet({"text": "\" onmouseover=\"alert(1)"}, {"heading": "<img src=x onerror=alert(1)>"}))
    assert "&quot; onmouseover=&quot;alert(1)" in page and "&lt;img src=x onerror=alert(1)&gt;" in page
    assert "<img" not in main_part(page)


def test_template_filled_in_one_pass(home, cdir):
    _, page = build(home, sheet({"text": "{{KATEX_JS}} {{CSP}}"}, title="{{BLOCKS}}"))
    assert "<p>{{KATEX_JS}} {{CSP}}</p>" in page and "<title>{{BLOCKS}}</title>" in page
    assert page.count("<script") == 3


def test_original_photo_is_embedded(home, cdir):
    _, page = build(home, sheet({"text": "Q2 transcription"},
                                {"original": {"path": "past-papers/q.jpg", "page": 1}}))
    data = base64.b64encode(JPEG).decode()
    assert f'<img src="data:image/jpeg;base64,{data}" alt="Original: past-papers/q.jpg, p.1">' in page
    assert "file://" not in main_part(page)


@pytest.mark.parametrize("name,mime", [("p.png", "image/png"), ("UP.JPG", "image/jpeg")])
def test_original_image_types_are_embedded(home, cdir, name, mime):
    _add_original(cdir, name, b"\x89PNG-or-JPEG-bytes")
    _, page = build(home, sheet({"original": {"path": f"past-papers/{name}", "page": 1}}))
    data = base64.b64encode(b"\x89PNG-or-JPEG-bytes").decode()
    assert f'<img src="data:{mime};base64,{data}" alt="Original: past-papers/{name}, p.1">' in page


@pytest.mark.parametrize("size,embedded", [(32, True), (33, False)])
def test_embed_size_boundary(home, cdir, monkeypatch, size, embedded):
    monkeypatch.setattr(visual, "ORIGINAL_EMBED_MAX_BYTES", 32)
    _add_original(cdir, "edge.png", b"x" * size)
    out = visual.cmd_sheet(sheet({"original": {"path": "past-papers/edge.png", "page": 1}}))
    body = main_part(Path(out["path"]).read_text())
    assert ("data:image/png;base64," in body) is embedded and ("file://" in body) is not embedded


def test_original_pdf_is_a_file_link(home, cdir):
    _, page = build(home, sheet({"original": {"path": "past-papers/s.pdf", "page": 3}}))
    uri = (cdir / "past-papers" / "s.pdf").resolve().as_uri() + "#page=3"
    assert f'<a href="{html.escape(uri)}">Original: past-papers/s.pdf, p.3</a>' in page
    assert "<img" not in main_part(page)


def test_original_without_known_pages_accepts_any_page(home, cdir):
    _, page = build(home, sheet({"original": {"path": "past-papers/nopages.pdf", "page": 9}}))
    assert "Original: past-papers/nopages.pdf, p.9" in page


def test_big_image_becomes_a_link(home, cdir, monkeypatch):
    monkeypatch.setattr(visual, "ORIGINAL_EMBED_MAX_BYTES", 16)
    out = visual.cmd_sheet(sheet({"original": {"path": "past-papers/big.png", "page": 1}}))
    page = Path(out["path"]).read_text()
    assert "<img" not in main_part(page) and "file://" in page and "Original: past-papers/big.png, p.1" in page


@pytest.mark.parametrize("ref,needle", [
    ({"path": "past-papers/unindexed.jpg", "page": 1}, "blocks[2].original.path"),
    ({"path": "/etc/passwd", "page": 1}, "blocks[2].original.path"),
    ({"path": "past-papers/../../outside.jpg", "page": 1}, "blocks[2].original.path"),
    ({"path": "past-papers/link.jpg", "page": 1}, "blocks[2].original.path"),
    ({"path": "past-papers/missing.jpg", "page": 1}, "blocks[2].original.path"),
    ({"path": "past-papers/s.pdf", "page": 5}, "blocks[2].original.page"),
    ({"path": "past-papers/q.jpg", "page": 2}, "blocks[2].original.page"),
    ({"path": "past-papers/q.jpg", "page": 0}, "blocks[2].original.page"),
    ({"path": "past-papers/q.jpg", "page": True}, "blocks[2].original.page"),
    ({"path": "past-papers/q.jpg"}, "blocks[2].original.page is required"),
    ({"page": 1}, "blocks[2].original.path is required"),
    ({"path": "past-papers/q.jpg", "page": 1, "crop": [0, 0, 1, 1]}, "blocks[2].original: unknown field"),
    ("past-papers/q.jpg", "blocks[2].original must be an object"),
])
def test_bad_original(home, cdir, ref, needle):
    fails(home, "sheet", sheet({"text": "t"}, {"original": ref}), needle)
    assert not (cdir / ".state" / "out" / "demo.html").exists()


@pytest.mark.parametrize("block,needle", [
    ({"text": "a", "math": "b"}, "blocks[1] must be an object with exactly one of"),
    ({}, "blocks[1] must be an object with exactly one of"),
    ("text", "blocks[1] must be an object"),
    ({"image": "x"}, "blocks[1]: unknown field 'image'"),
    ({"text": ""}, "blocks[1].text is required"),
    ({"text": 3}, "blocks[1].text must be a string"),
    ({"math": "a\nb"}, "blocks[1].math must be one line"),
    ({"text": "a\x1bb"}, "blocks[1].text must be one line"),
    ({"text": "x" * 4001}, "blocks[1].text is longer than 4000"),
    ({"math": "x" * 4001}, "blocks[1].math is longer than 4000"),
    ({"heading": "x" * 121}, "blocks[1].heading is longer than 120"),
    ({"text": r"see \[x\]"}, "blocks[1].text: inline math only"),
    ({"text": r"ends \]"}, "blocks[1].text: inline math only"),
    ({"heading": r"Step \[x\]"}, "blocks[1].heading: inline math only"),
    ({"heading": r"a \] b"}, "blocks[1].heading: inline math only"),
])
def test_bad_blocks(home, cdir, block, needle):
    fails(home, "sheet", sheet(block), needle)


def test_limits_accept_the_maximum(home, cdir):
    build(home, sheet(*([{"math": "x" * 4000}] * 200), title="t" * 120))


@pytest.mark.parametrize("payload,needle", [
    ({**sheet({"text": "a"}), "blocks": [{"text": "a"}] * 201}, "at most 200"),
    ({**sheet({"text": "a"}), "blocks": []}, "blocks is required"),
    ({**sheet({"text": "a"}), "title": "t" * 121}, "title is longer than 120"),
    ({**sheet({"text": "a"}), "title": "a\tb"}, "title must be one line"),
    ({**sheet({"text": "a"}), "title": r"Sum \[x\]"}, "title: inline math only"),
    ({**sheet({"text": "a"}), "title": r"x \]"}, "title: inline math only"),
    ({k: v for k, v in sheet({"text": "a"}).items() if k != "title"}, "title is required"),
    ({**sheet({"text": "a"}), "lang": "tr"}, "unknown field 'lang'"),
    ({**sheet({"text": "a"}), "name": "Bad_Name"}, "name must match"),
    ({**sheet({"text": "a"}), "name": "a--b"}, "name must match"),
    ({**sheet({"text": "a"}), "name": "-a"}, "name must match"),
    ({**sheet({"text": "a"}), "name": "../x"}, "name must match"),
    ({**sheet({"text": "a"}), "name": "a" * 61}, "at most 60"),
    ({**sheet({"text": "a"}), "term": "Fall"}, "term must be"),
    ({**sheet({"text": "a"}), "course": "CS999 Missing"}, "no course folder"),
])
def test_bad_sheet_payload(home, cdir, payload, needle):
    fails(home, "sheet", payload, needle)


def test_name_at_the_limit(home, cdir):
    out = ok(home, "sheet", sheet({"text": "a"}, name="a" * 60))
    assert out["path"].endswith("/" + "a" * 60 + ".html")


# --- svg -----------------------------------------------------------------------------

def test_svg_written_byte_for_byte(home, cdir):
    out = ok(home, "svg", svg())
    path = cdir / ".state" / "out" / "dfa.svg"
    assert out["path"] == str(path) and out["line"] == f"Built {path}."
    assert path.read_bytes() == SVG_OK.encode("utf-8")


def _swap(old: str, new: str) -> str:
    assert old in SVG_OK
    return SVG_OK.replace(old, new, 1)


DESC = '  <desc>Two states q0 (start, accepting, double circle) and q1; 0 moves between them.</desc>\n'


@pytest.mark.parametrize("doc,needle", [
    (_swap("<circle cx=\"160\"", "<script>alert(1)</script><circle cx=\"160\""), "element <script>"),
    (_swap('role="img"', 'role="img" onload="alert(1)"'), "event attribute onload"),
    (_swap("<circle cx=\"160\"", "<circle onclick=\"x()\" cx=\"160\""), "event attribute onclick"),
    (_swap("<circle cx=\"160\"", "<foreignObject><p xmlns=\"http://www.w3.org/1999/xhtml\">x</p>"
                                 "</foreignObject><circle cx=\"160\""), "element <foreignObject>"),
    (_swap("<circle cx=\"160\"", "<a href=\"#x\"><circle/></a><circle cx=\"160\""), "element <a>"),
    (_swap("<circle cx=\"160\"", "<image href=\"#x\"/><circle cx=\"160\""), "element <image>"),
    (_swap("<circle cx=\"160\"", "<animate attributeName=\"x\"/><circle cx=\"160\""), "element <animate>"),
    (_swap("<circle cx=\"160\"", "<h:script xmlns:h=\"http://www.w3.org/1999/xhtml\">x</h:script>"
                                 "<circle cx=\"160\""), "is not allowed"),
    (_swap('<use href="#arrow"/>', '<use href="https://evil.example/x.svg#a"/>'), "must start with #"),
    (_swap('<use xlink:href="#arrow"/>', '<use xlink:href="other.svg#a"/>'), "must start with #"),
    (_swap('<use href="#arrow"/>', '<use href="javascript:alert(1)"/>'), "must start with #"),
    (_swap('<use href="#arrow"/>', '<use href=" #arrow"/>'), "must start with #"),
    (_swap('role="img"', 'role="img" data-x="java&#x0A;script:alert(1)"'), "javascript:"),
    (_swap("fill: url(#g)", "fill: url(http://evil.example/a.png)"), "url("),
    (_swap("fill: url(#g)", "fill: URL( 'x.svg#g' )"), "url("),
    (_swap('marker-end="url(#arrow)"', 'marker-end="url(https://evil.example/m.svg#a)"'), "url("),
    (_swap("<style>", "<style>@import 'https://evil.example/a.css';"), "@import"),
    (_swap("<style>", "<style>@IMPORT url(#x);"), "@import"),
    (_swap("fill: url(#g)", "mask-image: image-set('https://evil.example/a.png' 1x)"), "image-set("),
    (_swap("fill: url(#g)", r"fill: u\72l(http://evil.example/a)"), "backslash"),
    (_swap("<style>", "<style><![CDATA[@import 'x.css';]]>"), "@import"),
    ('<!DOCTYPE svg [<!ENTITY a "b">]>' + SVG_OK.split("\n", 1)[1], "DOCTYPE"),
    (SVG_OK.replace("<svg ", '<!ENTITY a "b"><svg ', 1), "ENTITY"),
    (SVG_OK.replace("<svg ", '<?xml-stylesheet href="https://evil.example/a.css"?><svg ', 1),
     "processing instructions"),
    (SVG_OK.replace(DESC, ""), "child element 2 of the root must be <desc>"),
    (SVG_OK.replace("DFA for an even number of 0s", " "), "<title> must not be empty"),
    (SVG_OK.replace("Two states q0 (start, accepting, double circle) and q1; 0 moves between them.", ""),
     "<desc> must not be empty"),
    (SVG_OK.replace(DESC, "").replace("  <title>", DESC + "  <title>"), "child element 1 of the root must be <title>"),
    (SVG_OK.replace('xmlns="http://www.w3.org/2000/svg" ', ""), "root element must be svg"),
    ('<html xmlns="http://www.w3.org/2000/svg"><title>t</title><desc>d</desc></html>', "root element must be svg"),
    (SVG_OK.replace("</svg>", ""), "not well-formed"),
    (SVG_OK.replace("&amp;", "&nbsp;"), "not well-formed"),
    (SVG_OK.replace("q0</text>", "q0\x07</text>"), "control characters"),
    ("", "svg is required"),
])
def test_unsafe_svg_refused(home, cdir, doc, needle):
    fails(home, "svg", svg(doc), needle)
    assert not (cdir / ".state" / "out" / "dfa.svg").exists()


def test_svg_too_large(home, cdir):
    fails(home, "svg", svg(SVG_OK.replace("</svg>", "<!--" + "x" * (1024 * 1024) + "--></svg>")),
          "at most 1048576")
    assert not (cdir / ".state" / "out" / "dfa.svg").exists()


@pytest.mark.parametrize("encoding", ["ISO-8859-1", "latin1", "UTF-16", "us-ascii"])
def test_svg_non_utf8_declaration_refused(home, cdir, encoding):
    doc = SVG_OK.replace('encoding="UTF-8"', f"encoding='{encoding}'", 1)
    fails(home, "svg", svg(doc), "encoding must be UTF-8")
    assert not (cdir / ".state" / "out" / "dfa.svg").exists()


@pytest.mark.parametrize("encoding", ["utf-8", "UTF8", "Utf-8"])
def test_svg_utf8_declaration_spellings_accepted(home, cdir, encoding):
    doc = SVG_OK.replace('encoding="UTF-8"', f'encoding="{encoding}"', 1)
    ok(home, "svg", svg(doc))
    assert (cdir / ".state" / "out" / "dfa.svg").read_bytes() == doc.encode("utf-8")


def test_svg_without_xml_declaration_and_with_crlf(home, cdir):
    doc = SVG_OK.split("\n", 1)[1].replace("\n", "\r\n")
    ok(home, "svg", svg(doc))
    assert (cdir / ".state" / "out" / "dfa.svg").read_bytes() == doc.encode()


@pytest.mark.parametrize("payload,needle", [
    ({**svg(), "svg": 5}, "svg is required"),
    ({**svg(), "width": 3}, "unknown field 'width'"),
    ({**svg(), "name": "A"}, "name must match"),
])
def test_bad_svg_payload(home, cdir, payload, needle):
    fails(home, "svg", payload, needle)


# --- output placement -------------------------------------------------------------------

@pytest.mark.parametrize("cmd,payload", [("sheet", BASIC), ("svg", svg())])
def test_symlinked_out_refused(home, cdir, tmp_path, cmd, payload):
    out = cdir / ".state" / "out"
    out.rmdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out.symlink_to(elsewhere)
    fails(home, cmd, payload, "is a symlink")
    assert list(elsewhere.iterdir()) == []


@pytest.mark.parametrize("cmd,payload,name", [("sheet", BASIC, "demo.html"), ("svg", svg(), "dfa.svg")])
def test_symlinked_target_refused(home, cdir, tmp_path, cmd, payload, name):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    (cdir / ".state" / "out" / name).symlink_to(victim)
    fails(home, cmd, payload, "is a symlink")
    assert victim.read_text() == "keep"


def test_out_that_is_a_file_refused(home, cdir):
    out = cdir / ".state" / "out"
    out.rmdir()
    out.write_text("x")
    fails(home, "sheet", BASIC, "is not a folder")


def test_target_that_is_a_folder_refused(home, cdir):
    (cdir / ".state" / "out" / "demo.html").mkdir()
    fails(home, "sheet", BASIC, "is not a regular file")


@pytest.mark.parametrize("which", ["term", "course", ".state"])
def test_symlinked_course_folders_refused(home, root, tmp_path, which):
    ws_ok(home, "course", {"term": TERM, "course": COURSE})
    target = {"term": root / TERM, "course": root / TERM / COURSE,
              ".state": root / TERM / COURSE / ".state"}[which]
    elsewhere = tmp_path / "elsewhere"
    target.rename(elsewhere)
    target.symlink_to(elsewhere)
    for cmd, payload in (("sheet", BASIC), ("svg", svg()),
                         ("open", {"term": TERM, "course": COURSE, "file": "demo.html"})):
        fails(home, cmd, payload, "is a symlink")


def test_requires_workspace(home):
    fails(home, "sheet", BASIC, "no workspace")
    fails(home, "svg", svg(), "no workspace")


# --- open ----------------------------------------------------------------------------

def _fake_bin(tmp_path: Path, name: str, body: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    tool = bin_dir / name
    tool.write_text(f"#!/bin/sh\n{body}\n")
    tool.chmod(0o755)
    return bin_dir


def _clean_env(home: Path, path: str, **extra) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("DISPLAY", "WAYLAND_DISPLAY", "WSL_DISTRO_NAME", "BROWSER")}
    return {**env, "HOME": str(home), "PATH": path, **extra}


OPEN = {"term": TERM, "course": COURSE, "file": "demo.html"}


@pytest.fixture
def built(home, cdir):
    return Path(ok(home, "sheet", BASIC)["path"])


@pytest.mark.skipif(not sys.platform.startswith("linux") or visual._is_wsl(), reason="plain Linux only")
def test_open_headless_falls_back_to_the_path(home, built, tmp_path):
    called = tmp_path / "called"
    bin_dir = _fake_bin(tmp_path, "xdg-open", f'touch "{called}"')
    out = ok(home, "open", OPEN, env=_clean_env(home, str(bin_dir)))
    assert out == {"path": str(built), "opened": False, "line": f"Open `{built}` in your browser."}
    assert not called.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux") or visual._is_wsl(), reason="plain Linux only")
@pytest.mark.parametrize("code,opened", [(0, True), (3, False)])
def test_open_with_display_uses_xdg_open(home, built, tmp_path, code, opened):
    log = tmp_path / "args"
    bin_dir = _fake_bin(tmp_path, "xdg-open", f'printf "%s|%s" "$1" "${{BROWSER:-none}}" > "{log}"; exit {code}')
    out = ok(home, "open", OPEN, env=_clean_env(home, str(bin_dir), DISPLAY=":0", BROWSER="w3m"))
    assert out["opened"] is opened
    assert out["line"] == (f"Opened `{built}` in your browser." if opened else f"Open `{built}` in your browser.")
    assert log.read_text() == f"{built}|none"  # BROWSER (a console browser) is never passed on


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_open_wsl_prefers_wslview(home, built, tmp_path):
    log = tmp_path / "args"
    bin_dir = _fake_bin(tmp_path, "wslview", f'printf "%s" "$1" > "{log}"')
    out = ok(home, "open", OPEN, env=_clean_env(home, str(bin_dir), WSL_DISTRO_NAME="Ubuntu"))
    assert out["opened"] is True and log.read_text() == str(built)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_open_wsl_explorer_fallback_ignores_its_exit_code(home, built, tmp_path):
    log = tmp_path / "args"
    _fake_bin(tmp_path, "wslpath", 'printf "C:\\\\out\\\\demo.html\\n"')
    bin_dir = _fake_bin(tmp_path, "explorer.exe", f'printf "%s" "$1" > "{log}"; exit 1')
    out = ok(home, "open", OPEN, env=_clean_env(home, str(bin_dir), WSL_DISTRO_NAME="Ubuntu"))
    assert out["opened"] is True and log.read_text() == "C:\\out\\demo.html"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_open_wsl_without_any_opener(home, built, tmp_path):
    out = ok(home, "open", OPEN, env=_clean_env(home, str(tmp_path), WSL_DISTRO_NAME="Ubuntu"))
    assert out["opened"] is False


def test_open_macos_and_windows(home, built, monkeypatch):
    calls = []
    monkeypatch.setattr(visual, "_platform", lambda: "macos")
    monkeypatch.setattr(visual, "_launch", lambda argv, ignore_exit: calls.append((argv, ignore_exit)) or True)
    assert visual.cmd_open(dict(OPEN))["opened"] is True
    assert calls == [(["open", str(built)], False)]
    monkeypatch.setattr(visual, "_platform", lambda: "windows")
    started = []
    monkeypatch.setattr(visual.os, "startfile", started.append, raising=False)
    assert visual.cmd_open(dict(OPEN))["opened"] is True and started == [str(built)]

    def refuse(path):
        raise OSError("no association")

    monkeypatch.setattr(visual.os, "startfile", refuse, raising=False)
    assert visual.cmd_open(dict(OPEN))["opened"] is False
    monkeypatch.setattr(visual, "_platform", lambda: "other")
    assert visual.cmd_open(dict(OPEN))["opened"] is False


def test_launch_waits_at_most_the_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(visual, "OPEN_WAIT_SECONDS", 0.2)
    assert visual._launch([sys.executable, "-c", "import time; time.sleep(5)"], ignore_exit=False) is True
    assert visual._launch([sys.executable, "-c", "raise SystemExit(2)"], ignore_exit=False) is False
    assert visual._launch([sys.executable, "-c", "raise SystemExit(1)"], ignore_exit=True) is True
    assert visual._launch([str(tmp_path / "nope")], ignore_exit=False) is False


@pytest.mark.parametrize("file,needle", [
    ("missing.html", "is not an existing file"),
    ("demo.pdf", "file must be"),
    ("../INDEX.md", "file must be"),
    ("Demo.html", "file must be"),
    ("demo", "file must be"),
    ("", "file is required"),
])
def test_open_bad_file(home, built, file, needle):
    fails(home, "open", {**OPEN, "file": file}, needle)


def test_open_symlinked_file_refused(home, built, tmp_path):
    (tmp_path / "x.html").write_text("x")
    (built.parent / "link.html").symlink_to(tmp_path / "x.html")
    fails(home, "open", {**OPEN, "file": "link.html"}, "is not an existing file")


def test_open_without_out_folder(home, cdir):
    (cdir / ".state" / "out").rmdir()
    fails(home, "open", OPEN, "no output folder")


# --- contract ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [b"", b"not json", b"[1]", b"\xff\xfe", b'"x"'])
def test_bad_json_exits_2(home, cdir, raw):
    for cmd in ("sheet", "svg", "open"):
        fails(home, cmd, raw)


@pytest.mark.parametrize("argv", [["pdf"], [], ["sheet", "extra"]])
def test_usage_errors_are_one_line(home, argv):
    proc = subprocess.run([sys.executable, str(VIS), *argv], input=b"{}", capture_output=True, env=_env(home))
    assert proc.returncode == 2 and proc.stdout == b""
    err = proc.stderr.decode()
    assert err.startswith("visual.py: ") and err.count("\n") == 1, err


def test_internal_error_exits_1(home, monkeypatch, capsys):
    def boom(data):
        raise KeyError("bug")

    monkeypatch.setitem(visual.COMMANDS, "sheet", (boom, "x"))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    assert visual.main(["sheet"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "visual.py: internal error (KeyError)\n"


def test_stdlib_plus_own_scripts_only():
    tree = ast.parse(VIS.read_text())
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            tops.add(node.module.split(".")[0])
    ours = {"workspace", "ingest", "verify", "plan", "session"}
    assert ours <= tops
    assert tops - ours <= set(sys.stdlib_module_names) | {"__future__"}, tops


def test_vendored_katex_is_the_subset():
    files = sorted(str(p.relative_to(KATEX)) for p in KATEX.rglob("*") if p.is_file())
    fonts = [f for f in files if f.startswith("fonts/")]
    assert all(f.endswith(".woff2") for f in fonts) and len(fonts) == 20
    assert sorted(set(files) - set(fonts)) == ["LICENSE", "VERSION", "contrib/auto-render.min.js",
                                               "katex.min.css", "katex.min.js"]


# --- shared page checks ------------------------------------------------------------

def assert_safe_page(page: str, plain_scripts: int) -> None:
    """Offline, hash-pinned scripts only, no network, data blocks not executable."""
    bodies = scripts(page)
    assert len(bodies) == plain_scripts
    hashes = {"'sha256-" + base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() + "'" for b in bodies}
    directives = dict(d.strip().split(" ", 1) for d in csp(page).split(";"))
    assert set(directives["script-src"].split()) == hashes and directives["default-src"] == "'none'"
    assert not re.search(r"""(?:src|href)\s*=\s*["']?\s*(?:https?:)?//""", page, re.I)
    assert "prefers-color-scheme: dark" in page and "animation: none" in page
    assert not re.search(r"\{\{[A-Z_]+\}\}", page)
    for data in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', page, re.S):
        assert "<" not in data and ">" not in data and "&" not in data
        json.loads(data)


def json_data(page: str, ident: str):
    match = re.search(rf'<script type="application/json" id="{ident}">(.*?)</script>', page, re.S)
    assert match
    return json.loads(match.group(1))


# --- steps ---------------------------------------------------------------------------

def steps_payload(*steps, blocks=None, name="q2-steps", title="Q2 worked answer") -> dict:
    return {"term": TERM, "course": COURSE, "name": name, "title": title,
            "blocks": blocks or [{"text": "[practice] Show that L is not regular."}],
            "steps": list(steps)}


THREE_STEPS = steps_payload([{"text": r"Assume \(L\) is regular."}], [{"math": "s = a^p b^p"}],
                            [{"text": f"Contradiction {INJECT}"}, {"math": r"\frac{1}{2}"}])


def test_steps_page(home, cdir):
    out = ok(home, "steps", THREE_STEPS)
    page = Path(out["path"]).read_text(encoding="utf-8")
    assert out["path"] == str(cdir / ".state" / "out" / "q2-steps.html")
    assert_safe_page(page, 4)
    body = main_part(page)
    assert body.count('<li class="step"') == 3 and "<h2>Step 3</h2>" in body
    assert "&lt;/p&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in body and "alert(1)</script>" not in page
    assert '<div class="mimir-display" tabindex="0">s = a^p b^p</div>' in body
    assert "<p>[practice] Show that L is not regular.</p>" in body.split('<ol class="steps">')[0]
    ui = scripts(page)[3]
    for key in ("ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"):
        assert f'"{key}"' in ui
    assert 'id="mimir-next"' in body and 'role="status" aria-live="polite"' in body
    assert 'id="mimir-controls" hidden' in body  # shown by the script, so no-JS readers see every step


def test_steps_original_beside_question(home, cdir):
    payload = steps_payload([{"text": "one"}], blocks=[{"text": "[real, from photo/scan, wording may be off]"},
                                                       {"original": {"path": "past-papers/q.jpg", "page": 1}}])
    page = Path(ok(home, "steps", payload)["path"]).read_text(encoding="utf-8")
    assert 'alt="Original: past-papers/q.jpg, p.1"' in page


@pytest.mark.parametrize("payload, needle", [
    (steps_payload(), "steps is required"),
    (steps_payload([]), "steps[1] must be a non-empty list"),
    (steps_payload([{"heading": "x"}]), "steps[1][1]: unknown field 'heading'"),
    (steps_payload([{"text": "a"}], [{"original": {"path": "past-papers/q.jpg", "page": 1}}]),
     "steps[2][1]: unknown field 'original'"),
    (steps_payload([{"text": "x"}] * 21), "steps[1] has 21 blocks"),
    (steps_payload(*[[{"text": "x"}]] * 51), "steps has 51 steps"),
    (steps_payload([{"text": r"\[x\]"}]), "steps[1][1].text: inline math only"),
    ({**steps_payload([{"text": "x"}]), "blocks": []}, "blocks is required"),
])
def test_bad_steps(home, cdir, payload, needle):
    fails(home, "steps", payload, needle)


def test_steps_limits_accept_the_maximum(home, cdir):
    ok(home, "steps", steps_payload(*[[{"text": "x"}] * 20] * 50))


# --- trace ---------------------------------------------------------------------------

def _diagram(n: int, extra: str = "") -> str:
    circles = "".join(f'<circle id="state-{i}" cx="{40 * i}" cy="40" r="15"/>' for i in range(1, n + 1))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 80" role="img"><title>M</title>'
            f"<desc>States and moves.</desc>{circles}{extra}</svg>")


def _moves(*triples, pda=False):
    if pda:
        return [{"from": f, "read": r, "pop": po, "push": pu, "to": t} for f, r, po, pu, t in triples]
    return [{"from": f, "read": r, "to": t} for f, r, t in triples]


DFA = {"kind": "dfa", "states": ["q0", "q1"], "start": "q0", "accept": ["q0"],
       "transitions": _moves(("q0", "0", "q1"), ("q1", "0", "q0"), ("q0", "1", "q0"), ("q1", "1", "q1"))}
DFA_PARTIAL = {**DFA, "transitions": _moves(("q0", "0", "q1"), ("q1", "1", "q0"))}
NFA = {"kind": "nfa", "states": ["s", "a", "b"], "start": "s", "accept": ["b"],
       "transitions": _moves(("s", "", "a"), ("s", "", "b"), ("a", "x", "a"), ("b", "y", "b"))}
PDA = {"kind": "pda", "states": ["p", "q", "f"], "start": "p", "accept": ["f"], "stack_start": "Z",
       "transitions": _moves(("p", "a", "", "A", "p"), ("p", "", "", "", "q"), ("q", "b", "A", "", "q"),
                             ("q", "", "Z", "Z", "f"), pda=True)}
LOOP = {"kind": "pda", "states": ["p"], "start": "p", "accept": [], "stack_start": "Z",
        "transitions": _moves(("p", "", "", "A", "p"), pda=True)}
TREE = {"kind": "tree", "states": ["root", "c", "ca", "cat", "d"], "start": "root", "accept": ["ca", "cat"],
        "transitions": _moves(("root", "c", "c"), ("c", "a", "ca"), ("ca", "t", "cat"), ("root", "d", "d"))}


def trace(machine, *, svg_doc=None, name="machine", **extra) -> dict:
    return {"term": TERM, "course": COURSE, "name": name, "title": "Step through",
            "machine": machine, "svg": svg_doc or _diagram(len(machine["states"])), **extra}


def build_trace(home, machine, **extra) -> str:
    return Path(ok(home, "trace", trace(machine, **extra))["path"]).read_text(encoding="utf-8")


def test_trace_page(home, cdir):
    page = build_trace(home, PDA, example="aabb")
    assert_safe_page(page, 2)
    data = json_data(page, "mimir-machine")
    assert data["kind"] == "pda" and data["stack_start"] == "Z" and data["states"] == ["p", "q", "f"]
    assert data["max_configs"] == 256 and data["max_stack"] == 64 and data["max_symbols"] == 64
    assert data["transitions"][1] == {"from": "p", "read": "", "to": "q", "pop": "", "push": ""}
    body = main_part(page)
    assert 'value="aabb"' in body and 'id="state-3"' in body and "<title>M</title>" in body
    assert "<th scope=\"col\">Pop</th>" in body and "<td>ε</td>" in body
    assert "PDA, accepting by final state" in body
    ui = scripts(page)[1]
    assert '"ArrowRight"' in ui and '"ArrowLeft"' in ui and "mimir-current" in ui and "innerHTML" not in page


def test_trace_escapes_names_and_example(home, cdir):
    machine = {**DFA, "states": ["<b>q0", "q1"], "start": "<b>q0", "accept": ["<b>q0"],
               "transitions": _moves(("<b>q0", "<", "q1"))}
    page = build_trace(home, machine, example='"><script>x</script>')
    assert "<b>q0" not in page and "&lt;b&gt;q0" in page
    assert 'value="&quot;&gt;&lt;script&gt;x&lt;/script&gt;"' in page
    assert page.count("<script") == 3


def test_trace_svg_is_reserialized(home, cdir):
    doc = _diagram(2, '<text x="1" y="1"><![CDATA[</svg><script>alert(1)</script>]]></text><!-- c -->')
    page = build_trace(home, DFA, svg_doc=doc)
    assert "alert(1)</script>" not in page and "CDATA" not in page and "<!-- c -->" not in page
    assert "&lt;/svg&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in page


@pytest.mark.parametrize("machine, svg_doc, needle", [
    ({**DFA, "transitions": _moves(("q0", "", "q1"))}, None, "machine.transitions[1].read must be one character"),
    ({**DFA, "transitions": _moves(("q0", "0", "q1"), ("q0", "0", "q0"))}, None,
     "machine.transitions[2]: a second move from 'q0' on '0'"),
    ({**TREE, "transitions": TREE["transitions"] + _moves(("d", "x", "cat"))}, None,
     "tree node 'cat' has 2 incoming edges"),
    ({**TREE, "transitions": TREE["transitions"] + _moves(("c", "r", "root"))}, None,
     "the root 'root' of a tree has an incoming edge"),
    ({**TREE, "states": TREE["states"] + ["x", "y"],
      "transitions": TREE["transitions"] + _moves(("x", "y", "y"), ("y", "x", "x"))}, None, "tree node 'x' cannot be reached from the root"),
    ({**TREE, "transitions": TREE["transitions"] + _moves(("root", "", "d"))}, None, "transitions[5].read"),
    (DFA, _diagram(1), 'no element with id "state-2" for machine.states[2] \'q1\''),
    (NFA, _diagram(2), 'no element with id "state-3" for machine.states[3] \'b\''),
    (DFA, _diagram(2, '<rect id="state-1"/>'), "id 'state-1' is used twice"),
    (DFA, _diagram(2, '<rect id="mimir-next"/>'), "reserved for the page"),
    (DFA, _diagram(2, '<a href="#x"/>'), "element <a> is not allowed"),
    ({**DFA, "states": ["q0", "q0"]}, None, "machine.states[2]: 'q0' is listed twice"),
    ({**DFA, "start": "zz"}, None, "machine.start: 'zz' is not one of machine.states"),
    ({**DFA, "accept": ["q9"]}, None, "machine.accept[1]: 'q9'"),
    ({**DFA, "kind": "turing"}, None, "machine.kind must be one of"),
    ({**DFA, "stack_start": "Z"}, None, "machine.stack_start is only for a pda"),
    ({**DFA, "transitions": [{"from": "q0", "read": "0", "to": "q1", "pop": "A"}]}, None,
     "machine.transitions[1].pop is only for a pda"),
    ({k: v for k, v in PDA.items() if k != "stack_start"}, None, "machine.stack_start is required"),
    ({**PDA, "transitions": _moves(("p", "a", "AB", "", "p"), pda=True)}, None, "transitions[1].pop"),
    ({**PDA, "transitions": _moves(("p", "a", "", "A B", "p"), pda=True)}, None, "transitions[1].push"),
    ({**DFA, "transitions": _moves(("q0", "ab", "q1"))}, None, "transitions[1].read"),
    ({**DFA, "states": ["q" * 21]}, None, "machine.states[1] is longer than 20"),
    ({**DFA, "states": [f"s{i}" for i in range(61)]}, None, "machine.states has 61 states"),
    ({**DFA, "transitions": _moves(*[("q0", "0", "q1")] * 401)}, None, "machine.transitions has 401 moves"),
])
def test_bad_machine(home, cdir, machine, svg_doc, needle):
    fails(home, "trace", trace(machine, svg_doc=svg_doc), needle)


def test_trace_example_limit(home, cdir):
    ok(home, "trace", trace(DFA, example="0 " * 64))
    fails(home, "trace", trace(DFA, example="0" * 65), "example has 65 symbols; at most 64")


NODE = __import__("shutil").which("node")


def simulate(tmp_path: Path, page: str, inputs: list[str]) -> list[dict]:
    """Run the page's own simulator script under node; return the verdict and frames per input."""
    harness = tmp_path / "harness.js"
    machine = json_data(page, "mimir-machine")
    harness.write_text(scripts(page)[0] + "\n" + f"""
var machine = {json.dumps(machine)};
var out = {json.dumps(inputs)}.map(function (text) {{
  var r = MimirSim.run(machine, text);
  return {{verdict: MimirSim.verdict(machine, r),
           frames: r.frames.map(function (f) {{
             return {{read: f.read, limited: f.limited,
                      configs: f.configs.map(function (c) {{ return c.state + "/" + c.stack; }})}}; }})}};
}});
console.log(JSON.stringify(out));
""")
    proc = subprocess.run([NODE, str(harness)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_simulator_dfa(home, cdir, tmp_path):
    full, partial = (build_trace(home, m, name=n) for m, n in ((DFA, "full"), (DFA_PARTIAL, "partial")))
    accepted, rejected = simulate(tmp_path, full, ["0101", "0 1"])
    assert accepted["verdict"] == {"result": "accepted"}
    assert [f["configs"] for f in accepted["frames"]] == [["q0/"], ["q1/"], ["q1/"], ["q0/"], ["q0/"]]
    assert rejected["verdict"] == {"result": "rejected"}
    (stuck,) = simulate(tmp_path, partial, ["00"])
    assert stuck["verdict"] == {"result": "stuck", "symbol": "0", "read": 2}


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_simulator_nfa_epsilon(home, cdir, tmp_path):
    (empty, ys, xs) = simulate(tmp_path, build_trace(home, NFA), ["", "yy", "xy"])
    assert empty["frames"][0]["configs"] == ["s/", "a/", "b/"] and empty["verdict"]["result"] == "accepted"
    assert ys["verdict"]["result"] == "accepted" and ys["frames"][-1]["configs"] == ["b/"]
    assert xs["verdict"]["result"] == "stuck"


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_simulator_pda(home, cdir, tmp_path):
    good, short, extra = simulate(tmp_path, build_trace(home, PDA), ["aabb", "aab", "abb"])
    assert good["verdict"] == {"result": "accepted"}
    assert "f/Z" in good["frames"][-1]["configs"] and "p/AAZ" in good["frames"][2]["configs"]
    assert short["verdict"] == {"result": "rejected"}
    assert extra["verdict"]["result"] == "stuck"
    (loop,) = simulate(tmp_path, build_trace(home, LOOP, name="loop"), [""])
    frame = loop["frames"][0]
    assert frame["limited"] is True and len(frame["configs"]) == 64  # stack depths 1..64; deeper is cut
    assert max(len(c.split("/")[1]) for c in frame["configs"]) == 64


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_simulator_tree(home, cdir, tmp_path):
    ca, c, cx = simulate(tmp_path, build_trace(home, TREE), ["ca", "c", "cx"])
    assert [f["configs"] for f in ca["frames"]] == [["root/"], ["c/"], ["ca/"]]
    assert ca["verdict"]["result"] == "accepted" and c["verdict"]["result"] == "rejected"
    assert cx["verdict"] == {"result": "stuck", "symbol": "x", "read": 2}


# --- delay ---------------------------------------------------------------------------

def _route(cdir: Path, root: Path, exam: str | None, topics=("Heaps", "Graphs")) -> None:
    mastery = cdir / ".state" / "mastery.md"
    mastery.write_text(mastery.read_text() + "".join(f"| {t} | unseen | | | | 0 | 0 | |\n" for t in topics))
    if exam is not None:
        profile = root / ".state" / "profile.md"
        text = profile.read_text().replace("| course | exam | date |\n|---|---|---|\n",
                                           f"| course | exam | date |\n|---|---|---|\n| CS201 | final | {exam} |\n")
        profile.write_text(text)


NOW = "2026-10-17T09:00:00+03:00"
DELAY = {"term": TERM, "course": COURSE, "name": "cost-of-delay", "now": NOW}


def test_delay_pages(home, root, cdir):
    _route(cdir, root, "2026-11-05")
    out = ok(home, "delay", DELAY)
    start = session.cmd_start({"now": NOW, "term": TERM, "course": COURSE})
    assert out["delay_line"] == start["delay_line"]
    html_path, svg_path = Path(out["html"]), Path(out["svg"])
    assert html_path == cdir / ".state" / "out" / "cost-of-delay.html" and svg_path.suffix == ".svg"
    assert out["line"] == f"Built {html_path} and {svg_path}."
    page = html_path.read_text(encoding="utf-8")
    assert_safe_page(page, 1)
    texts = json_data(page, "mimir-rows")
    assert len(texts) == 19 and page.count("<tr><td>") == 19
    assert texts[0] == "Start today: 19 days × 1–4 min."
    assert texts[-1] == "Start Wed Nov 4: 1 day × 25–75 min."
    assert 'type="range"' in page and 'max="18"' in page and f'aria-valuetext="{texts[0]}"' in page
    assert "<label for=\"mimir-start-day\">Start day</label>" in page
    assert "Confidence: rough: no topics timed yet, ±50%." in page and "Sat Oct 17 (today)" in page
    chart = svg_path.read_bytes()
    visual.check_svg(chart)
    text = chart.decode()
    assert text.count('<rect class="low"') == 19 and text.count('<rect class="high"') == 19
    assert "<desc>" in text and texts[0] in text and "Solid: low estimate. Outline: high estimate." in text
    assert ">Today</text>" in text and ">Wed Nov 4</text>" in text


def test_delay_one_row(home, root, cdir):
    _route(cdir, root, "2026-10-18")
    out = ok(home, "delay", DELAY)
    assert len(json_data(Path(out["html"]).read_text(encoding="utf-8"), "mimir-rows")) == 1
    visual.check_svg(Path(out["svg"]).read_bytes())


def test_delay_without_exam(home, root, cdir):
    _route(cdir, root, None)
    fails(home, "delay", DELAY, "no exam date for CS201 Theory")


def test_delay_without_route(home, root, cdir):
    _route(cdir, root, "2026-11-05", topics=())
    fails(home, "delay", DELAY, "no topics left on the route")


@pytest.mark.parametrize("payload, needle", [
    ({k: v for k, v in DELAY.items() if k != "now"}, "now is required"),
    ({**DELAY, "extra": 1}, "unknown field 'extra'"),
    ({**DELAY, "name": "Bad Name"}, "name must match"),
])
def test_bad_delay_payload(home, root, cdir, payload, needle):
    _route(cdir, root, "2026-11-05")
    fails(home, "delay", payload, needle)


def test_new_commands_require_workspace(home):
    fails(home, "steps", THREE_STEPS, "no workspace")
    fails(home, "trace", trace(DFA), "no workspace")
    fails(home, "delay", DELAY, "no workspace")


def test_new_constants_are_the_spec_values():
    assert visual.STEPS_MAX == 50 and visual.STEP_MAX_BLOCKS == 20
    assert visual.TRACE_MAX_STATES == 60 and visual.TRACE_MAX_TRANSITIONS == 400
    assert visual.STATE_NAME_MAX_CHARS == 20 and visual.TRACE_MAX_SYMBOLS == 64
    assert visual.TRACE_MAX_CONFIGS == 256 and visual.TRACE_MAX_STACK == 64


# --- review regressions --------------------------------------------------------------

def test_trace_diagram_css_is_scoped(home, cdir):
    style = ("<style>/* c */ text, button { display: none } "
             "@media (prefers-color-scheme: dark) { circle { stroke: #eee } }</style>")
    page = build_trace(home, DFA, svg_doc=_diagram(2, style))
    assert "#mimir-diagram text,#mimir-diagram button{ display: none }" in page
    assert "@media (prefers-color-scheme: dark){#mimir-diagram circle{ stroke: #eee }}" in page
    assert "/* c */" not in page


@pytest.mark.parametrize("style, needle", [
    ("<style>@font-face { font-family: x }</style>", "allows only top-level @media"),
    ("<style>a { b { c: d } }</style>", "nested in a rule"),
    ("<style>a { c: d </style>", "unbalanced"),
    ("<style>{ c: d }</style>", "without a selector"),
])
def test_trace_diagram_css_refused(home, cdir, style, needle):
    fails(home, "trace", trace(DFA, svg_doc=_diagram(2, style)), needle)


@pytest.mark.parametrize("field, machine", [
    ("transitions[1].read", {**DFA, "transitions": _moves(("q0", "\U0001d44d", "q1"))}),
    ("stack_start", {**PDA, "stack_start": "\U0001d44d"}),
])
def test_symbols_outside_the_bmp_refused(home, cdir, field, machine):
    fails(home, "trace", trace(machine), f"machine.{field} must be one character")


def test_example_total_length_capped(home, cdir):
    fails(home, "trace", trace(DFA, example="0" + " " * 4000 + "0"), "example is longer than 4000")


CAP = {"kind": "pda", "states": [f"s{i}" for i in range(5)], "start": "s0", "accept": [], "stack_start": "Z",
       "transitions": _moves(*[(f"s{i}", "", "", "A", f"s{j}") for i in range(5) for j in range(5)], pda=True)}
CUT = {"kind": "pda", "states": ["p", "q"], "start": "p", "accept": ["q"], "stack_start": "Z",
       "transitions": _moves(("p", "", "", "A", "p"), ("p", "x", "A", "", "q"), pda=True)}


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_simulator_config_cap_and_limited_carry_over(home, cdir, tmp_path):
    (cap,) = simulate(tmp_path, build_trace(home, CAP, name="cap", svg_doc=_diagram(5)), [""])
    assert len(cap["frames"][0]["configs"]) == 256 and cap["frames"][0]["limited"] is True
    (cut,) = simulate(tmp_path, build_trace(home, CUT, name="cut"), ["x"])
    assert cut["frames"][0]["limited"] is True
    assert len(cut["frames"][1]["configs"]) == 63 and cut["frames"][1]["limited"] is True


DOM_STUB = r"""
function El(id) {
  this.id = id; this.hidden = false; this.textContent = ""; this.value = ""; this.attrs = {};
  this.listeners = {}; this.children = []; this.classes = {};
  var self = this;
  this.classList = {add: function (c) { self.classes[c] = true; }, remove: function (c) { delete self.classes[c]; },
                    contains: function (c) { return !!self.classes[c]; }};
}
El.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
El.prototype.removeAttribute = function (k) { delete this.attrs[k]; };
El.prototype.addEventListener = function (t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); };
El.prototype.fire = function (t, ev) { (this.listeners[t] || []).forEach(function (f) { f(ev || {}); }); };
El.prototype.click = function () { this.fire("click"); };
El.prototype.appendChild = function (c) { this.children.push(c); return c; };
El.prototype.removeChild = function (c) { this.children.splice(this.children.indexOf(c), 1); };
Object.defineProperty(El.prototype, "firstChild", {get: function () { return this.children[0] || null; }});
El.prototype.scrollIntoView = function () {};
var byId = {}, lists = {}, docListeners = [];
var body = new El("body");
global.document = {
  getElementById: function (id) { return byId[id] || (byId[id] = new El(id)); },
  querySelectorAll: function (sel) { return lists[sel] || []; },
  createElement: function () { return new El(null); },
  addEventListener: function (t, f) { if (t === "keydown") docListeners.push(f); }
};
function key(name, target) {
  docListeners.forEach(function (f) { f({key: name, target: target || body, preventDefault: function () {}}); });
}
function list(sel, n) { lists[sel] = []; for (var i = 0; i < n; i++) lists[sel].push(new El(null)); return lists[sel]; }
"""


def run_ui(tmp_path: Path, code: str, setup: str, actions: str) -> dict:
    harness = tmp_path / "ui.js"
    harness.write_text(DOM_STUB + setup + "\n" + code + "\n" + "var out = {};\n" + actions
                       + "\nconsole.log(JSON.stringify(out));\n")
    proc = subprocess.run([NODE, str(harness)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_step_reveal_ui(home, cdir, tmp_path):
    page = Path(ok(home, "steps", THREE_STEPS)["path"]).read_text(encoding="utf-8")
    out = run_ui(tmp_path, scripts(page)[-1], 'var steps = list(".step", 3);', r"""
function snap(tag) { out[tag] = {hidden: steps.map(function (s) { return s.hidden; }),
                                 status: byId["mimir-status"].textContent}; }
out.controls = byId["mimir-controls"].hidden; snap("load");
key("ArrowRight"); snap("one");
byId["mimir-next"].click(); key("ArrowDown"); snap("three");
byId["mimir-next"].click(); snap("past");
key("ArrowLeft"); snap("back");
var formula = new El(null); formula.classList.add("mimir-display"); key("ArrowRight", formula); snap("formula");
key("ArrowUp"); byId["mimir-back"].click(); byId["mimir-back"].click(); snap("none");
""")
    assert out["controls"] is False
    assert out["load"] == {"hidden": [True, True, True], "status": "3 steps to reveal."}
    assert out["one"] == {"hidden": [False, True, True], "status": "Step 1 of 3."}
    assert out["three"] == {"hidden": [False, False, False], "status": "Step 3 of 3, the last step."}
    assert out["past"]["status"] == "All 3 steps are shown."
    assert out["back"] == {"hidden": [False, False, True], "status": "Step 2 of 3 is the last one shown."}
    assert out["formula"] == out["back"]
    assert out["none"] == {"hidden": [True, True, True], "status": "No steps are shown."}


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_slider_ui(home, root, cdir, tmp_path):
    _route(cdir, root, "2026-11-05")
    page = Path(ok(home, "delay", DELAY)["html"]).read_text(encoding="utf-8")
    texts = json_data(page, "mimir-rows")
    setup = (f'var rows = list("tbody tr", {len(texts)});\n'
             f'document.getElementById("mimir-rows").textContent = {json.dumps(json.dumps(texts))};\n'
             'document.getElementById("mimir-start-day").value = "0";')
    out = run_ui(tmp_path, scripts(page)[-1], setup, r"""
var slider = byId["mimir-start-day"];
function snap(tag) { out[tag] = {output: byId["mimir-row"].textContent, valuetext: slider.attrs["aria-valuetext"],
  current: rows.map(function (r, i) { return r.attrs["aria-current"] ? i : -1; }).filter(function (i) { return i >= 0; })}; }
out.controls = byId["mimir-controls"].hidden; snap("load");
slider.value = "9"; slider.fire("input"); snap("nine");
""")
    assert out["controls"] is False
    assert out["load"] == {"output": texts[0], "valuetext": texts[0], "current": [0]}
    assert out["nine"] == {"output": texts[9], "valuetext": texts[9], "current": [9]}


def trace_ui(tmp_path: Path, page: str, text: str, actions: str) -> dict:
    data = json.dumps(json.dumps(json_data(page, "mimir-machine")))
    setup = (f'document.getElementById("mimir-machine").textContent = {data};\n'
             f'document.getElementById("mimir-input").value = {json.dumps(text)};')
    helpers = r"""
function snap(tag) { out[tag] = {status: byId["mimir-status"].textContent,
  history: byId["mimir-history"].children.map(function (c) { return c.textContent; }),
  current: Object.keys(byId).filter(function (k) { return k.indexOf("state-") === 0 && byId[k].classList.contains("mimir-current"); })}; }
"""
    bodies = scripts(page)
    return run_ui(tmp_path, bodies[0] + "\n" + bodies[1], setup, helpers + actions)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_step_through_ui(home, cdir, tmp_path):
    page = build_trace(home, DFA)
    out = trace_ui(tmp_path, page, "0101", r"""
out.controls = byId["mimir-controls"].hidden; snap("load");
byId["mimir-start"].click(); snap("start");
key("ArrowRight"); snap("one");
key("ArrowRight"); key("ArrowRight"); byId["mimir-next"].click(); snap("end");
byId["mimir-back"].click(); snap("back");
key("ArrowRight", byId["mimir-input"]); snap("typing");
byId["mimir-input"].fire("input"); snap("edited");
""")
    assert out["controls"] is False and out["load"]["status"] == "Type an input and press Start."
    assert out["start"] == {"status": "Start: in q0. Remaining: 0101.", "history": ["Start: in q0. Remaining: 0101."],
                            "current": ["state-1"]}
    assert out["one"]["status"] == "Read '0' (1 of 4): in q1. Remaining: 101." and out["one"]["current"] == ["state-2"]
    assert out["end"]["status"].endswith("Accepted: the whole input was read and an accepting state was reached.")
    assert len(out["end"]["history"]) == 5
    assert out["back"]["status"] == "Read '0' (3 of 4): in q0. Remaining: 1." and len(out["back"]["history"]) == 4
    assert out["typing"] == out["back"]
    assert out["edited"] == {"status": "Press Start to run the new input.", "history": [], "current": []}


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("machine, text, ending", [
    (DFA, "011", "Rejected: the whole input was read, but no accepting state was reached."),
    (DFA_PARTIAL, "00", "Stuck on '0': no move from the previous state, so the input is rejected."),
    (CUT, "", "No verdict: the search was cut, so an accepting path may have been missed. "
              "Search limit reached: some paths were not followed."),
])
def test_step_through_verdicts(home, cdir, tmp_path, machine, text, ending):
    page = build_trace(home, machine)
    out = trace_ui(tmp_path, page, text, 'byId["mimir-start"].click(); for (var i = 0; i < 5; i++) key("ArrowRight"); snap("end");')
    assert out["end"]["status"].endswith(ending), out["end"]["status"]


def test_delay_chart_geometry(home, root, cdir):
    _route(cdir, root, "2026-11-05")
    chart = Path(ok(home, "delay", DELAY)["svg"]).read_text()
    rects = re.findall(r'<rect class="(low|high)" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/>', chart)
    highs = [(float(x), float(h)) for c, x, _, _, h in rects if c == "high"]
    lows = [(float(x), float(h)) for c, x, _, _, h in rects if c == "low"]
    assert [x for x, _ in highs] == sorted(x for x, _ in highs) and [x for x, _ in lows] == [x for x, _ in highs]
    assert highs[-1][1] == 190.0 and all(lo <= hi for (_, lo), (_, hi) in zip(lows, highs))
    assert [h for _, h in highs] == sorted(h for _, h in highs)  # waiting longer never needs less a day
    assert abs(lows[-1][1] - 190 / 3) < 0.01  # low end is a third of the high end (±50 % of the point)
