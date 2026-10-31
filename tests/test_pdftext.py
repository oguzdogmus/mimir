from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_ingest import (CATALOG, FONT, _pages, build_pdf, encrypted_pdf, home, objstm_pdf, root,  # noqa: F401
                         scanned_pdf, stream, text_pdf, ws_ok)

ROOT_DIR = Path(__file__).resolve().parent.parent
PT = ROOT_DIR / "scripts" / "pdftext.py"
sys.path.insert(0, str(ROOT_DIR / "scripts"))
import pdftext  # noqa: E402


@pytest.fixture
def no_poppler(monkeypatch):
    monkeypatch.setattr(pdftext.shutil, "which", lambda _name: None)


def course_pdf(root: Path, data: bytes, name: str = "2024-final.pdf") -> Path:
    path = root / "2026-Fall" / "CS201 Theory" / "past-papers" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def unicode_pdf() -> bytes:
    """A Type0 font whose two-byte codes map to text only through a ToUnicode CMap."""
    cmap = (b"begincmap\n1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
            b"2 beginbfchar <0001> <0044> <0002> <0046> endbfchar\n"
            b"1 beginbfrange <0010> <0012> <0061> endbfrange\nendcmap")
    content = b"BT /F1 12 Tf 72 700 Td <00010002> Tj [<0010> -400 <00110012>] TJ 0 -14 Td <0001> Tj ET"
    objs = {1: CATALOG, 4: stream(content), 6: stream(cmap),
            5: b"<< /Type /Font /Subtype /Type0 /BaseFont /X /Encoding /Identity-H /ToUnicode 6 0 R >>",
            **_pages(1, b"<< /Font << /F1 5 0 R >> >>")}
    return build_pdf(objs)


def test_builtin_reads_a_simple_text_layer(root, no_poppler):
    out = pdftext.cmd_pages({"path": str(course_pdf(root, text_pdf(3))), "first": 2, "last": 3})
    assert out["engine"] == "builtin" and out["pages"] == 3
    assert out["text"] == [{"page": 2, "text": "Pumping lemma"}, {"page": 3, "text": "Pumping lemma"}]
    assert out["line"].startswith("Read pages 2-3 of ") and out["line"].endswith("(builtin).")


def test_builtin_reads_object_streams(root, no_poppler):
    out = pdftext.cmd_pages({"path": str(course_pdf(root, objstm_pdf(2))), "first": 1})
    assert out["last"] == 1 and out["text"] == [{"page": 1, "text": "Regular languages"}]


def test_builtin_maps_two_byte_codes_through_tounicode(root, no_poppler):
    out = pdftext.cmd_pages({"path": str(course_pdf(root, unicode_pdf())), "first": 1})
    assert out["text"][0]["text"] == "DFa bc\nD"


def test_a_scan_comes_back_empty_with_a_hint(root, no_poppler):
    out = pdftext.cmd_pages({"path": str(course_pdf(root, scanned_pdf(1))), "first": 1})
    assert out["text"] == [{"page": 1, "text": ""}]
    assert out["line"].startswith("No text on page 1 of ") and "image" in out["line"]


def test_encrypted_without_poppler_is_refused(root, no_poppler):
    with pytest.raises(pdftext.InputError, match="encrypted"):
        pdftext.cmd_pages({"path": str(course_pdf(root, encrypted_pdf())), "first": 1})


@pytest.mark.parametrize("payload, needle", [
    ({"first": 1}, "path"),
    ({"first": 0}, "first"),
    ({"first": 3, "last": 2}, "before first"),
    ({"first": 1, "last": 21}, "at most 20"),
    ({"first": 9}, "past the last page"),
    ({"first": 1, "extra": 1}, "extra"),
])
def test_bad_page_requests_are_refused(root, no_poppler, payload, needle):
    path = course_pdf(root, text_pdf(2))
    data = payload if needle == "path" else {"path": str(path), **payload}
    with pytest.raises(pdftext.InputError, match=needle):
        pdftext.cmd_pages(data)


def test_files_outside_the_learning_root_are_refused(root, home, no_poppler):
    outside = home / "elsewhere.pdf"
    outside.write_bytes(text_pdf(1))
    with pytest.raises(pdftext.InputError, match="not inside the learning root"):
        pdftext.cmd_pages({"path": str(outside), "first": 1})
    link = root / "2026-Fall" / "link.pdf"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    with pytest.raises(pdftext.InputError, match="not inside the learning root"):
        pdftext.cmd_pages({"path": str(link), "first": 1})


def test_non_pdf_files_are_refused(root, no_poppler):
    notes = root / "2026-Fall" / "notes.txt"
    notes.parent.mkdir(parents=True)
    notes.write_text("hello")
    with pytest.raises(pdftext.InputError, match="not a PDF"):
        pdftext.cmd_pages({"path": str(notes), "first": 1})


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler not installed")
def test_pdftotext_is_preferred_when_installed(root):
    out = pdftext.cmd_pages({"path": str(course_pdf(root, text_pdf(2))), "first": 1, "last": 2})
    assert out["engine"] == "pdftotext"
    assert [t["text"] for t in out["text"]] == ["Pumping lemma", "Pumping lemma"]


def test_cli_prints_one_json_object(root, home):
    path = course_pdf(root, text_pdf(1))
    env = {**os.environ, "HOME": str(home)}
    proc = subprocess.run([sys.executable, str(PT), "pages"], input=json.dumps({"path": str(path), "first": 1}).encode(),
                          capture_output=True, env=env)
    assert proc.returncode == 0 and proc.stderr == b""
    out = json.loads(proc.stdout)
    assert out["text"][0]["text"] == "Pumping lemma"
    bad = subprocess.run([sys.executable, str(PT), "pages"], input=b"{}", capture_output=True, env=env)
    assert bad.returncode == 2 and bad.stdout == b""
    assert bad.stderr.decode().startswith("pdftext.py: ") and bad.stderr.count(b"\n") == 1
