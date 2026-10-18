#!/usr/bin/env python3
"""Mimir ingest core: scan the inbox, detect fidelity, index filed files.

Standard library only, Python 3.11+. Shares the JSON contract and helpers of
``workspace.py`` (same folder). Run as::

    python3 ingest.py <scan|index>  < input.json

Each subcommand reads ONE JSON object on stdin (unknown fields are rejected)
and prints ONE JSON object on stdout: structured data plus a ready-to-print
``line``. Every path in the output is absolute. Both subcommands need a
workspace at the learning root (see ``workspace.py``); without one they exit 2.
Filing itself is ``workspace.py file``.

Everything under ``_inbox/`` is untrusted data. This script never prints file
contents, never executes anything it finds, and never deletes or renames a
student file.

Kinds and fidelity (detected, never asked)
------------------------------------------
* ``pdf`` (``.pdf``): fidelity ``text`` when the file has a font resource, no
  invisible-text (``3 Tr``) OCR layer, and is not encrypted; else ``ocr``.
  Inspection that cannot finish leans to ``ocr``: a content stream with a
  filter other than a single FlateDecode, a corrupt or truncated stream, an
  exhausted PDF_INFLATE_BUDGET, or a file larger than PDF_INFLATE_BUDGET
  (not read at all; pages null). ``pages`` is the page-tree ``/Count`` (else
  the page-object count; null if unknown). A ``.pdf`` without a ``%PDF-``
  header is skipped as "not a valid PDF".
* ``image`` (jpg, jpeg, png, heic, heif, webp, gif, tif, tiff, bmp): ``ocr``,
  pages 1.
* ``text`` (md, txt, tex) and ``document`` (docx, pptx, odt, odp): ``text``,
  pages null.
* Anything else is skipped as "unsupported type".

Subcommands and examples (paths shown for root /home/u/learning)
----------------------------------------------------------------
scan -- unpack archives, list inbox items, list existing courses.
    in : {}
    out: {"root": "/home/u/learning", "inbox": "/home/u/learning/_inbox",
          "items": [{"path": "/home/u/learning/_inbox/pack/2024-final.pdf",
                     "kind": "pdf", "fidelity": "text", "pages": 4}],
          "skipped": [{"path": "/home/u/learning/_inbox/setup.exe",
                       "reason": "unsupported type"}],
          "unpacked": [{"archive": "/home/u/learning/_inbox/pack.zip",
                        "dir": "/home/u/learning/_inbox/pack", "new": true}],
          "courses": [{"term": "2026-Fall", "course": "CS201 Theory",
                       "course_dir": "/home/u/learning/2026-Fall/CS201 Theory"}],
          "line": "Found 1 item in /home/u/learning/_inbox/ (1 skipped)."}
    With no items, ``line`` says there is nothing to ingest. A missing
    ``_inbox/`` is empty; an ``_inbox`` that is a symlink, not a folder, or
    unreadable exits 2.
    The walk is recursive (iterative, any depth) and ignores dot-entries and
    ``__MACOSX``. These go to ``skipped`` and the walk continues: symlinks
    (never followed), entries whose name has control characters, newlines or
    non-UTF-8 bytes ("unsafe file name"; the path is shown with escapes), and
    entries that cannot be read ("unreadable (<reason>)").
    Each ``X.zip`` (any case of ``.zip``) is extracted to the sibling folder
    ``X/`` through a temporary dot-folder and one rename; if ``X/`` already
    exists the archive counts as unpacked (``new`` false) and nothing is
    extracted. Nested archives are unpacked the same way up to
    ARCHIVE_MAX_DEPTH levels. A whole archive is refused (nothing extracted,
    listed in ``skipped``) if any member is absolute, contains ``..``, is a
    symlink or has control characters in its name, if it is encrypted, uses
    an unsupported compression method or is unreadable, or if it has more
    than ARCHIVE_MAX_MEMBERS members or more than ARCHIVE_MAX_BYTES
    uncompressed. The same two limits are also one budget for the whole scan,
    nested archives included: an archive that would pass the remaining budget
    is refused. Archives are never deleted. ``courses`` lists
    ``<term>/<course>`` folders (not symlinks) holding an ``INDEX.md``.

index -- upsert one course's INDEX.md registry and topic rows.
    in : {"term": "2026-Fall", "course": "CS201 Theory", "files": [
            {"path": "/home/u/learning/2026-Fall/CS201 Theory/past-papers/2024-final.pdf",
             "topics": [{"topic": "Pumping lemma", "anchor": "page=3"}]}]}
    out: {"index": "/home/u/learning/2026-Fall/CS201 Theory/INDEX.md",
          "course_dir": "...", "files": [{"path": "...", "role": "past-papers",
          "pages": 4, "fidelity": "text", "new": true}], "topics_added": 1,
          "line": "Indexed 1 file in /home/u/learning/2026-Fall/CS201 Theory/INDEX.md
          (1 new, 1 topic added)."}
    The term and course folders must exist and not be symlinks. Each ``path``
    (absolute or ``~``) must be an existing regular file inside
    ``<course>/<role>/`` that also resolves there. Role, pages and fidelity are
    computed here, never taken from input. Entries naming the same file are
    merged (topics combined). Registry rows are keyed by the course-relative
    path: an existing row is replaced in place, a new one appended. ``topics``
    is optional; each topic row ``| topic | <path>#<anchor> |`` is appended
    unless an identical row exists. ``topic`` is required, ``anchor`` may be
    empty (then the cell is just the path). Both must be one line without
    control characters, at most TOPIC_MAX_CHARS characters; ``|`` is stored as
    ``\\|``. For a PDF a non-empty anchor is ``page=N`` (1 <= N <= pages when
    known); otherwise it is a heading slug (no whitespace). All input is
    validated before INDEX.md is written; INDEX.md must be UTF-8 and is
    replaced atomically through a unique temp file. The rest of the file is
    preserved. Table headers match loosely (cells trimmed, any case, any
    alignment row), so an existing table is never duplicated; a ``##
    Registry`` or ``## Topics`` heading missing its header gets the template
    header above its existing rows, a foreign header is replaced by the
    template's, and a missing section is appended.

Exit codes: invalid input, a refused operation, a usage error or a filesystem
error exits 2 with one line on stderr (``ingest.py: <message>``) and nothing
on stdout. An unexpected internal error exits 1 with ``ingest.py: internal
error (<Type>)``. No traceback is ever printed.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
import zipfile
import zlib
from pathlib import Path

import workspace
from workspace import (InputError, _check_keys, _has_control, _short, parse_path, parse_segment,
                       parse_term)

ARCHIVE_MAX_DEPTH = 3
ARCHIVE_MAX_MEMBERS = 2000
ARCHIVE_MAX_BYTES = 500 * 1024 * 1024
TOPIC_MAX_CHARS = 120
PDF_INFLATE_BUDGET = 128 * 1024 * 1024  # bytes inflated per PDF; larger PDF files are not read

_IMAGE_EXT = {"jpg", "jpeg", "png", "heic", "heif", "webp", "gif", "tif", "tiff", "bmp"}
_TEXT_EXT = {"md", "txt", "tex"}
_DOCUMENT_EXT = {"docx", "pptx", "odt", "odp"}

_REGISTRY = ("Registry", ("path", "term", "role", "pages", "fidelity"))
_TOPICS = ("Topics", ("topic", "file#anchor"))


# --- PDF inspection ----------------------------------------------------------------

_OBJ = re.compile(rb"(?<![0-9])([0-9]+)\s+([0-9]+)\s+obj\b")
_STREAM_KW = re.compile(rb"(?<![A-Za-z])stream(?:\r\n|\n|\r)")
_FILTER = re.compile(rb"/Filter\s*(\[[^\]]*\]|/[^\s/<>\[\]()]+)")
_FILTER_NAME = re.compile(rb"/([^\s/<>\[\]()]+)")
_LENGTH = re.compile(rb"/Length\s+([0-9]+)(?!\s+[0-9]+\s+R)")
_OBJSTM = re.compile(rb"/Type\s*/ObjStm(?![A-Za-z])")
_NOT_CONTENT = re.compile(rb"/Type\s*/(?:XRef|Metadata|EmbeddedFile)(?![A-Za-z])|/Subtype\s*/Image(?![A-Za-z])"
                          rb"|/Length[123]\b|/Subtype\s*/(?:Type1C|CIDFontType0C|OpenType)(?![A-Za-z])")
_PAGES_NODE = re.compile(rb"/Type\s*/Pages(?![A-Za-z])")
_PAGE_LEAF = re.compile(rb"/Type\s*/Page(?![A-Za-z])")
_COUNT = re.compile(rb"/Count\s+([0-9]+)")
_FONT = re.compile(rb"/Font(?![A-Za-z0-9])")
_ENCRYPT = re.compile(rb"/Encrypt(?![A-Za-z0-9])")
_INVISIBLE = re.compile(rb"(?<![0-9A-Za-z.\-])3\s+Tr(?![A-Za-z0-9])")
_INT = re.compile(rb"/(N|First)\s+([0-9]+)")


class _Budget:
    def __init__(self, limit: int):
        self.left = limit
        self.exhausted = False

    def inflate(self, data: bytes) -> bytes | None:
        """Inflated bytes, or None when the data is corrupt, truncated or past the budget."""
        if self.left <= 0:
            self.exhausted = True
            return None
        inflater = zlib.decompressobj()
        try:
            out = inflater.decompress(data, self.left)
        except zlib.error:
            return None
        self.left -= len(out)
        if inflater.unconsumed_tail or (not inflater.eof and self.left <= 0):
            self.exhausted = True
            return None
        return out if inflater.eof else None


def _decode(head: bytes, data: bytes, budget: _Budget) -> bytes | None:
    """Decoded stream data, or None when it cannot be decoded completely."""
    found = _FILTER.search(head)
    if found is None:
        return data
    names = _FILTER_NAME.findall(found.group(1))
    if not names:
        return data
    if names == [b"FlateDecode"]:
        return budget.inflate(data)
    return None  # other filters and filter chains are not decoded


def _raw_objects(data: bytes):
    """Yield (number, dict_bytes, stream_bytes | None) for each top-level object."""
    pos = 0
    while (m := _OBJ.search(data, pos)):
        start = m.end()
        end = data.find(b"endobj", start)
        end = len(data) if end < 0 else end
        s = _STREAM_KW.search(data, start, end)
        if s is None:
            yield int(m.group(1)), data[start:end], None
            pos = end + 6
            continue
        head = data[start:s.start()]
        body_start = s.end()
        stream_end = -1
        if (length := _LENGTH.search(head)):
            cand = body_start + int(length.group(1))
            if data[cand:cand + 32].lstrip().startswith(b"endstream"):
                stream_end = cand
        if stream_end < 0:
            stream_end = data.find(b"endstream", body_start)
            stream_end = len(data) if stream_end < 0 else stream_end
        yield int(m.group(1)), head, data[body_start:stream_end]
        after = data.find(b"endobj", stream_end)
        pos = len(data) if after < 0 else after + 6


def _objstm_objects(head: bytes, decoded: bytes):
    """Yield (number, body) for each object inside a decoded object stream."""
    ints = {k: int(v) for k, v in _INT.findall(head)}
    first, count = ints.get(b"First"), ints.get(b"N")
    if first is None or count is None:
        return
    try:
        nums = [int(t) for t in decoded[:first].split()]
    except ValueError:
        return
    pairs = list(zip(nums[0::2], nums[1::2]))[:count]
    for i, (num, off) in enumerate(pairs):
        nxt = pairs[i + 1][1] if i + 1 < len(pairs) else len(decoded) - first
        yield num, decoded[first + off:first + nxt]


def pdf_info(path: Path) -> tuple[str, int | None] | None:
    """Return (fidelity, pages) for a PDF, or None if it is not a PDF."""
    with open(path, "rb") as handle:
        if b"%PDF-" not in handle.read(1024):
            return None
        size = os.fstat(handle.fileno()).st_size
    if size > PDF_INFLATE_BUDGET:
        return "ocr", None
    data = path.read_bytes()
    encrypted = bool(_ENCRYPT.search(data))
    budget = _Budget(PDF_INFLATE_BUDGET)
    objects: dict[int, bytes] = {}
    invisible = incomplete = False
    for num, head, raw in _raw_objects(data):
        objects[num] = head
        if raw is None or encrypted:
            continue
        objstm = bool(_OBJSTM.search(head))
        if not objstm and _NOT_CONTENT.search(head):
            continue  # images, fonts, xref, metadata: never an OCR layer
        decoded = _decode(head, raw, budget)
        if decoded is None:
            incomplete = True
        elif objstm:
            for inner_num, body in _objstm_objects(head, decoded):
                objects[inner_num] = body
        elif _INVISIBLE.search(decoded):
            invisible = True
    has_font = any(_FONT.search(body) for body in objects.values())
    counts = [int(c) for body in objects.values() if _PAGES_NODE.search(body)
              for c in _COUNT.findall(body)[:1]]
    if counts:
        pages = max(counts)
    else:
        pages = sum(1 for body in objects.values() if _PAGE_LEAF.search(body))
    text = has_font and not (invisible or encrypted or incomplete or budget.exhausted)
    return ("text" if text else "ocr"), (pages or None)


def detect(path: Path) -> dict | str:
    """Return {"kind", "fidelity", "pages"} for a supported file, else a skip reason."""
    ext = path.suffix[1:].lower()
    if ext == "pdf":
        info = pdf_info(path)
        if info is None:
            return "not a valid PDF"
        return {"kind": "pdf", "fidelity": info[0], "pages": info[1]}
    if ext in _IMAGE_EXT:
        return {"kind": "image", "fidelity": "ocr", "pages": 1}
    if ext in _TEXT_EXT:
        return {"kind": "text", "fidelity": "text", "pages": None}
    if ext in _DOCUMENT_EXT:
        return {"kind": "document", "fidelity": "text", "pages": None}
    return "unsupported type"


# --- Archives ------------------------------------------------------------------------

def _is_zip_name(name: str) -> bool:
    return len(name) > 4 and name.lower().endswith(".zip")


def _member_parts(name: str) -> list[str] | str:
    """Clean path parts of a zip member, or a refusal reason."""
    if _has_control(name):
        return "unsafe archive: member name with control characters"
    if name.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", name):
        return f"unsafe archive: absolute member {_short(name)}"
    parts = [p for p in re.split(r"[/\\]", name) if p not in ("", ".")]
    if ".." in parts:
        return f"unsafe archive: member {_short(name)} leaves the folder"
    return parts


def _check_archive(zf: zipfile.ZipFile, budget: dict) -> list[tuple[zipfile.ZipInfo, list[str]]] | str:
    infos = zf.infolist()
    size = sum(i.file_size for i in infos)
    if len(infos) > ARCHIVE_MAX_MEMBERS:
        return f"archive too large: more than {ARCHIVE_MAX_MEMBERS} members"
    if size > ARCHIVE_MAX_BYTES:
        return f"archive too large: over {ARCHIVE_MAX_BYTES // (1024 * 1024)} MB uncompressed"
    if len(infos) > budget["members"] or size > budget["bytes"]:
        return (f"archive limit for one scan reached ({ARCHIVE_MAX_MEMBERS} members or "
                f"{ARCHIVE_MAX_BYTES // (1024 * 1024)} MB uncompressed in total)")
    plan = []
    for info in infos:
        parts = _member_parts(info.filename)
        if isinstance(parts, str):
            return parts
        if stat.S_ISLNK(info.external_attr >> 16):
            return f"unsafe archive: symlink member {_short(info.filename)}"
        if info.flag_bits & 0x1:
            return "encrypted archive"
        plan.append((info, parts))
    budget["members"] -= len(infos)
    budget["bytes"] -= size
    return plan


def _extract(archive: Path, dest: Path, budget: dict) -> str | None:
    """Extract ``archive`` to ``dest`` (absent) via a temp dir; return a refusal reason or None."""
    try:
        with zipfile.ZipFile(archive) as zf:
            plan = _check_archive(zf, budget)
            if isinstance(plan, str):
                return plan
            tmp = Path(tempfile.mkdtemp(prefix=f".{dest.name}.", suffix=".mimir-tmp", dir=dest.parent))
            try:
                for info, parts in plan:
                    if not parts or "__MACOSX" in parts:
                        continue
                    target = tmp.joinpath(*parts)
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(target, "wb") as out:
                        shutil.copyfileobj(src, out)
                os.rename(tmp, dest)
            except BaseException:
                shutil.rmtree(tmp, ignore_errors=True)
                raise
    except (zipfile.BadZipFile, EOFError, zlib.error):
        return "not a valid zip archive"
    except NotImplementedError:
        return "archive uses an unsupported compression method"
    except RuntimeError as exc:
        if type(exc) is RuntimeError and "encrypted" in str(exc):
            return "encrypted archive"
        raise  # RecursionError or another bug: an internal error, not a refusal
    except OSError as exc:
        return f"could not extract ({exc.strerror or type(exc).__name__})"
    return None


# --- scan ----------------------------------------------------------------------------

def _ignored(name: str) -> bool:
    return name.startswith(".") or name == "__MACOSX"


def _display(path: Path) -> str:
    """The path as printable UTF-8: undecodable bytes and control characters escaped."""
    text = os.fsencode(path).decode("utf-8", "backslashreplace")
    return "".join(f"\\x{ord(c):02x}" if unicodedata.category(c) == "Cc" else c for c in text)


def _skip(out: dict, path: Path, reason: str) -> None:
    out["skipped"].append({"path": _display(path), "reason": reason})


def _unreadable(exc: OSError) -> str:
    return f"unreadable ({exc.strerror or type(exc).__name__})"


def _listing(folder: Path) -> list[Path]:
    return sorted(e for e in folder.iterdir() if not _ignored(e.name))


def _unpack(entry: Path, depth: int, out: dict, budget: dict) -> None:
    if entry.is_symlink() or not entry.is_file() or not _is_zip_name(entry.name):
        return
    target = entry.with_name(entry.name[:-4])
    if target.is_dir() and not target.is_symlink():
        out["unpacked"].append({"archive": str(entry), "dir": str(target), "new": False})
    elif target.exists() or target.is_symlink():
        _skip(out, entry, f"{target.name} exists and is not a folder")
    elif depth + 1 > ARCHIVE_MAX_DEPTH:
        _skip(out, entry, f"nested archive deeper than {ARCHIVE_MAX_DEPTH} levels")
    elif (reason := _extract(entry, target, budget)) is not None:
        _skip(out, entry, reason)
    else:
        out["unpacked"].append({"archive": str(entry), "dir": str(target), "new": True})


def _visit(entry: Path, depth: int, zip_stems: set[str], out: dict, stack: list) -> None:
    if entry.is_symlink():
        _skip(out, entry, "symlink, not followed")
    elif entry.is_dir():
        stack.append((entry, depth + (1 if entry.name in zip_stems else 0)))
    elif not entry.is_file():
        _skip(out, entry, "not a regular file")
    elif not _is_zip_name(entry.name):
        found = detect(entry)
        if isinstance(found, str):
            _skip(out, entry, found)
        else:
            out["items"].append({"path": str(entry), **found})


def _walk(inbox: Path, out: dict) -> None:
    """Scan the inbox iteratively; a stack entry's depth = archive levels it sits inside."""
    budget = {"members": ARCHIVE_MAX_MEMBERS, "bytes": ARCHIVE_MAX_BYTES}
    stack: list[tuple[Path, int]] = [(inbox, 0)]
    while stack:
        folder, depth = stack.pop()
        try:
            entries = _listing(folder)
        except OSError as exc:
            if folder == inbox:
                raise  # only an unusable inbox stops the scan
            _skip(out, folder, _unreadable(exc))
            continue
        for entry in entries:
            if _has_control(entry.name):
                _skip(out, entry, "unsafe file name")
                continue
            try:
                _unpack(entry, depth, out, budget)
            except OSError as exc:
                _skip(out, entry, _unreadable(exc))
        try:
            entries = [e for e in _listing(folder) if not _has_control(e.name)]  # with new folders
        except OSError as exc:
            _skip(out, folder, _unreadable(exc))
            continue
        zip_stems = {e.name[:-4] for e in entries if _is_zip_name(e.name)}
        for entry in entries:
            try:
                _visit(entry, depth, zip_stems, out, stack)
            except OSError as exc:
                _skip(out, entry, _unreadable(exc))


def _workspace_root() -> Path:
    root, _ = workspace.resolve_root()
    if not workspace.has_tree(root):
        raise InputError(f"no workspace at {root}; run workspace.py init first")
    return root


def _courses(root: Path) -> list[dict]:
    out = []
    for term in sorted(root.iterdir()):
        if _ignored(term.name) or term.is_symlink() or not term.is_dir() or not workspace._TERM.fullmatch(term.name):
            continue
        try:
            courses = sorted(term.iterdir())
        except OSError:
            continue
        for course in courses:
            if (not _ignored(course.name) and not course.is_symlink() and course.is_dir()
                    and (course / "INDEX.md").is_file() and not _has_control(course.name)):
                out.append({"term": term.name, "course": course.name, "course_dir": str(course)})
    return out


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def cmd_scan(data: dict) -> dict:
    _check_keys(data, set())
    root = _workspace_root()
    inbox = root / "_inbox"
    out: dict = {"items": [], "skipped": [], "unpacked": []}
    if inbox.is_symlink():
        raise InputError(f"{inbox} is a symlink; the inbox must be a real folder inside the workspace")
    if inbox.exists() and not inbox.is_dir():
        raise InputError(f"{inbox} exists and is not a folder")
    if inbox.is_dir():
        _walk(inbox, out)
    for key in out:
        out[key].sort(key=lambda e: e.get("path", e.get("archive")))
    if out["items"]:
        line = f"Found {_plural(len(out['items']), 'item')} in {inbox}/"
    else:
        line = f"Nothing to ingest in {inbox}/"
    extras = []
    if out["skipped"]:
        extras.append(f"{len(out['skipped'])} skipped")
    new = sum(1 for u in out["unpacked"] if u["new"])
    if new:
        extras.append(f"{_plural(new, 'archive')} unpacked")
    line += f" ({', '.join(extras)})." if extras else "."
    return {"root": str(root), "inbox": str(inbox), **out, "courses": _courses(root), "line": line}


# --- index ---------------------------------------------------------------------------

_ALIGN_ROW = re.compile(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?")


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _split_row(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def _unescape(cell: str) -> str:
    return cell.replace("\\|", "|")


def _is_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def _is_align(line: str) -> bool:
    return _is_row(line) and bool(_ALIGN_ROW.fullmatch(line.strip()))


def _line_field(entry: dict, field: str, where: str, required: bool) -> str:
    value = entry.get(field, "")
    if not isinstance(value, str):
        raise InputError(f"{where}: {field} must be a string")
    if _has_control(value):
        raise InputError(f"{where}: {field} must be one line without control characters")
    value = value.strip()
    if required and not value:
        raise InputError(f"{where}: {field} is required")
    if len(value) > TOPIC_MAX_CHARS:
        raise InputError(f"{where}: {field} is longer than {TOPIC_MAX_CHARS} characters")
    return value


def _course_file(entry: dict, course_dir: Path, where: str) -> tuple[Path, str, str]:
    path = parse_path(entry, "path")
    if path.is_symlink() or not path.is_file():
        raise InputError(f"{where}: not an existing regular file: {path}")
    if not path.is_relative_to(course_dir):
        raise InputError(f"{where}: {path} is not inside {course_dir}/<role>/")
    rel = path.relative_to(course_dir)
    role = rel.parts[0]
    if role not in workspace._ROLES or len(rel.parts) < 2:
        raise InputError(f"{where}: {path} is not inside a role folder "
                         f"({', '.join(workspace._ROLES)}) of {course_dir}")
    if not path.resolve().is_relative_to(course_dir.resolve() / role):
        raise InputError(f"{where}: {path} resolves outside {course_dir / role}/")
    return path, rel.as_posix(), role


def _section_table(lines: list[str], section: tuple[str, tuple[str, ...]]) -> tuple[int, int]:
    """Return (first_row, end) of the section's table, repairing its header if needed."""
    title, names = section
    header = "| " + " | ".join(names) + " |"
    align = "|" + "---|" * len(names)
    heading = re.compile(rf"##\s+{title}\s*", re.IGNORECASE)
    h = next((i for i, l in enumerate(lines) if heading.fullmatch(l.strip())), None)
    if h is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", f"## {title}", header, align]
        return len(lines), len(lines)
    i = h + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _is_row(lines[i]) and not _is_align(lines[i]) \
            and i + 1 < len(lines) and _is_align(lines[i + 1]):
        if [c.lower() for c in _split_row(lines[i])] != list(names):
            lines[i:i + 2] = [header, align]  # foreign header: restore the template's
    elif i < len(lines) and _is_align(lines[i]):
        lines.insert(i, header)  # alignment row without its header
    elif i < len(lines) and _is_row(lines[i]):
        lines[i:i] = [header, align]  # rows without a header: keep them in the table
    else:
        lines[h + 1:h + 1] = [header, align]
        return h + 3, h + 3
    first = end = i + 2
    while end < len(lines) and _is_row(lines[end]):
        end += 1
    return first, end


def read_text(path: Path) -> str | None:
    """UTF-8 text of a file, None when absent; a non-UTF-8 file is refused."""
    if not path.is_file():
        return None
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(f"{path} is not valid UTF-8; fix or remove it, nothing was changed") from None


def registry(index: Path) -> dict[str, tuple[str, int | None, str]]:
    """Registry rows of an INDEX.md as {path: (role, pages, fidelity)}; the file is never changed.

    ``path`` is the course-relative path with ``\\|`` unescaped, ``role`` and
    ``fidelity`` lowercase, ``pages`` an int >= 1 (None when the cell is blank,
    ``0`` or anything else that is not a positive whole number). A
    missing INDEX.md has no rows; a non-UTF-8 one is refused (``InputError``).
    """
    text = read_text(index)
    if text is None:
        return {}
    copy = text.splitlines()
    first, end = _section_table(copy, _REGISTRY)  # repairs only the copy
    rows = {}
    for row in copy[first:end]:
        cells = _split_row(row) + [""] * 5
        pages = cells[3].strip()
        rows[_unescape(cells[0])] = (cells[2].strip().lower(),
                                     int(pages) if re.fullmatch(r"[1-9][0-9]*", pages) else None,
                                     cells[4].strip().lower())
    return rows


def _write_atomic(index: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{index.name}.", suffix=".tmp", dir=index.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.chmod(tmp, stat.S_IMODE(index.stat().st_mode))
        os.replace(tmp, index)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def cmd_index(data: dict) -> dict:
    _check_keys(data, {"term", "course", "files"})
    term, course = parse_term(data), parse_segment(data, "course")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise InputError("files is required (a non-empty list)")
    root = _workspace_root()
    term_dir, course_dir = root / term, root / term / course
    for folder, what in ((term_dir, "term"), (course_dir, "course")):
        if folder.is_symlink():
            raise InputError(f"{what} folder {folder} is a symlink; refusing to index through it")
    if not course_dir.is_dir():
        raise InputError(f"no course folder at {course_dir}")
    plan: dict[str, list] = {}  # rel -> [path, role, found, cells]
    for n, entry in enumerate(files, 1):
        where = f"files[{n}]"
        if not isinstance(entry, dict):
            raise InputError(f"{where} must be an object")
        _check_keys(entry, {"path", "topics"})
        path, rel, role = _course_file(entry, course_dir, where)
        found = plan[rel][2] if rel in plan else detect(path)
        if isinstance(found, str):
            raise InputError(f"{where}: {path} cannot be indexed ({found})")
        topics = entry.get("topics", [])
        if not isinstance(topics, list):
            raise InputError(f"{where}: topics must be a list")
        cells = plan.setdefault(rel, [path, role, found, []])[3]
        for k, t in enumerate(topics, 1):
            twhere = f"{where}.topics[{k}]"
            if not isinstance(t, dict):
                raise InputError(f"{twhere} must be an object")
            _check_keys(t, {"topic", "anchor"})
            topic = _line_field(t, "topic", twhere, required=True)
            anchor = _line_field(t, "anchor", twhere, required=False)
            if anchor and found["kind"] == "pdf":
                m = re.fullmatch(r"page=([1-9][0-9]*)", anchor)
                if not m:
                    raise InputError(f"{twhere}: a PDF anchor is page=N: {_short(anchor)}")
                if found["pages"] is not None and int(m.group(1)) > found["pages"]:
                    raise InputError(f"{twhere}: page {m.group(1)} is past the last page ({found['pages']})")
            elif anchor and re.search(r"\s", anchor):
                raise InputError(f"{twhere}: an anchor is a heading slug without spaces: {_short(anchor)}")
            target = f"{rel}#{anchor}" if anchor else rel
            cell = f"| {_cell(topic)} | {_cell(target)} |"
            if cell not in cells:
                cells.append(cell)

    created: list[str] = []
    workspace.build_course(root, term, course, created)  # restores a missing INDEX.md
    index = course_dir / "INDEX.md"
    try:
        text = index.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(f"{index} is not valid UTF-8; fix or remove it, nothing was changed") from None
    lines = text.splitlines()
    results, added = [], 0
    for rel, (path, role, found, cells) in plan.items():
        pages = "" if found["pages"] is None else str(found["pages"])
        row = f"| {_cell(rel)} | {term} | {role} | {pages} | {found['fidelity']} |"
        first, end = _section_table(lines, _REGISTRY)
        hit = next((i for i in range(first, end) if _unescape(_split_row(lines[i])[0]) == rel), None)
        if hit is None:
            lines.insert(end, row)
        else:
            lines[hit] = row
        results.append({"path": str(path), "role": role, "pages": found["pages"],
                        "fidelity": found["fidelity"], "new": hit is None})
        for cell in cells:
            first, end = _section_table(lines, _TOPICS)
            if not any(_split_row(lines[i])[:2] == _split_row(cell) for i in range(first, end)):
                lines.insert(end, cell)
                added += 1
    new_text = "\n".join(lines) + "\n"
    if new_text != text:
        _write_atomic(index, new_text)
    new = sum(1 for r in results if r["new"])
    line = (f"Indexed {_plural(len(results), 'file')} in {index} "
            f"({new} new, {_plural(added, 'topic')} added).")
    return {"index": str(index), "course_dir": str(course_dir), "files": results,
            "topics_added": added, "line": line}


COMMANDS = {
    "scan": (cmd_scan, "unpack inbox archives and list items with kind, fidelity and pages"),
    "index": (cmd_index, "upsert registry and topic rows in one course's INDEX.md"),
}


def main(argv: list[str] | None = None) -> int:
    return workspace.run_cli("ingest.py",
                             ("Mimir ingest core. Subcommands: scan, index. Reads one JSON object on "
                              "stdin and prints one JSON object on stdout."),
                             COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
