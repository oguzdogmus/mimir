#!/usr/bin/env python3
"""Mimir workspace builder: learning root, course trees, filing, relocation.

Standard library only, Python 3.11+. Run as::

    python3 workspace.py <root|init|course|file|relocate>  < input.json

Each subcommand reads ONE JSON object on stdin (``{}`` when it takes no
fields; unknown fields are rejected) and prints ONE JSON object on stdout:
structured data plus a ready-to-print ``line``. Every path in the output is
absolute. Input paths may start with ``~``; after expansion they must be
absolute.

Learning root and pointer rule
------------------------------
The root is the path in the pointer file POINTER_PATH (one line, an absolute
path) when that file exists, else DEFAULT_ROOT. The pointer exists only when
the root differs from the default: setting the root to the default removes it.
A workspace (a "tracked tree") exists at a root when ``<root>/.state/profile.md``
is a file. ``setup_done`` is reported only when it is a ``YYYY-MM-DD`` date.

Tree
----
``init`` makes ``<root>/``, ``_inbox/``, ``.state/profile.md``. ``course``
(which implies ``init``) adds ``<root>/<YYYY-Term>/<CODE Name>/`` with
``INDEX.md``, ``outline/``, ``slides/``, ``past-papers/``, ``notes/`` and
``.state/{mastery,fingerprint,save,forecast}.md``, ``.state/logs/``,
``.state/out/``. Both only create what is missing and never overwrite a file.
New memory files are instances of ``assets/templates/*``: comment lines are
kept; table rows, bullets and ``##`` blocks whose heading holds a
``<placeholder>`` are dropped; ``key: <placeholder>`` becomes ``key:``.

Names: ``term`` is ``YYYY-<word>`` (e.g. "2026-Fall", "2027-Q2"); ``course``
is one safe folder name ("CS201 Theory"): not empty, no ``/``, ``\\``, ``..``,
leading ``.``, leading or trailing space, control characters or ``<>:"|?*``.
``role`` is one of outline, slides, past-papers, notes.

Subcommands and examples (paths shown for HOME=/home/u)
-------------------------------------------------------
root -- where the learning root is and whether setup finished.
    in : {}
    out: {"root": "/home/u/learning", "source": "default", "exists": false,
          "setup_done": null, "line": "Learning root: /home/u/learning
          (default, no workspace yet)."}
    ``source`` is "default" or "pointer"; ``exists`` is true when a workspace
    is there; ``setup_done`` is the profile's ``setup_done:`` value or null.

init -- create the root, ``_inbox/`` and the profile.
    in : {} or {"root": "~/Documents/uni"}
    out: {"root": "/home/u/Documents/uni", "created": ["/home/u/Documents/uni",
          ...], "line": "Workspace ready at /home/u/Documents/uni."}
    With ``root``, the pointer is set (or removed for the default); this also
    repairs a malformed pointer file, which makes every other subcommand exit
    2. If a workspace already exists at another root (compared by resolved
    path, so a symlinked alias counts as the same root), init refuses: use
    relocate. ``root`` may not be the home directory, a filesystem root, or an
    ancestor of the pointer file.

course -- create one course tree (runs init on the current root first).
    in : {"term": "2026-Fall", "course": "CS201 Theory"}
    out: {"root": "...", "course_dir": "/home/u/learning/2026-Fall/CS201
          Theory", "created": [...], "line": "Course folder ready:
          /home/u/learning/2026-Fall/CS201 Theory/"}

file -- move one regular file into ``<course>/<role>/``, same basename.
    in : {"source": "/home/u/learning/_inbox/2024-final.pdf", "term":
          "2026-Fall", "course": "CS201 Theory", "role": "past-papers"}
    out: {"source": "...", "dest": "/home/u/learning/2026-Fall/CS201
          Theory/past-papers/2024-final.pdf", "course_dir": "...", "created":
          [...], "line": "Saved 2024-final.pdf to /home/u/learning/2026-Fall/
          CS201 Theory/past-papers/"}
    The course is created if new. A file of the same name already there is a
    collision: nothing moves. The source must be an existing regular file
    (not a directory or a symlink) and not a Mimir memory file (``INDEX.md``
    or anything under a ``.state`` directory inside the root). If a move
    across filesystems fails while the source still exists, the partial
    destination file is removed.

relocate -- move the whole tree to a new root, then update the pointer.
    in : {"to": "~/Documents/uni"}
    out: {"from": "/home/u/learning", "root": "/home/u/Documents/uni",
          "line": "Moved the learning folder from /home/u/learning to
          /home/u/Documents/uni."}
    Needs a workspace at the current root, which may not itself be a symlink.
    The target must be absent or an empty directory, not inside the current
    root, and not the home directory, a filesystem root, or an ancestor of the
    pointer file. Symlinks inside the tree are kept as symlinks. Order:
    * one filesystem: rename the tree, then update the pointer. If the pointer
      write fails, the tree is renamed back and the error is reported.
    * across filesystems: copy the tree, update the pointer, then delete the
      old tree. If the copy or the pointer write fails, the partial copy is
      removed (an existing empty target is emptied again), the old tree and
      pointer stay as they were, and the error is reported. If only the
      final delete fails, the move has succeeded: exit 0 with a ``warning``
      field, and ``line`` says the old folder was not fully removed.

Exit codes: invalid input, a refused operation, or a usage error (unknown or
missing subcommand) exits 2 with one line on stderr
(``workspace.py: <message>``) and nothing on stdout; a filesystem error (e.g.
permission denied) also exits 2. Paths and names with control characters or
lone surrogates are rejected. An unexpected internal error
(a bug) exits 1 with ``workspace.py: internal error (<Type>)`` and nothing on
stdout. No traceback is ever printed.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

DEFAULT_ROOT = "~/learning"
POINTER_PATH = "~/.config/mimir/root"

_ROLES = ("outline", "slides", "past-papers", "notes")
_COURSE_MEMORY = ("mastery.md", "fingerprint.md", "save.md", "forecast.md")
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"

_TERM = re.compile(r"[0-9]{4}-\w+")
_PLACEHOLDER = re.compile(r"<[^<>]+>")
_KEY_LINE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*):\s.*")
_UNSAFE_CHARS = set('/\\<>:"|?*')


class InputError(Exception):
    """Invalid input or refused operation; one stderr line, exit code 2."""


# --- Input -----------------------------------------------------------------------

def read_input(raw: bytes) -> dict:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError("input is not valid UTF-8") from None
    try:
        data = json.loads(text)
    except RecursionError:
        raise InputError("input is too deeply nested") from None
    except json.JSONDecodeError as exc:
        raise InputError(f"input is not valid JSON ({exc.msg}, line {exc.lineno} column {exc.colno})") from None
    except ValueError:
        raise InputError("input is not valid JSON (number out of range)") from None
    if not isinstance(data, dict):
        raise InputError("input must be one JSON object")
    return data


def _short(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text if len(text) <= 40 else text[:37] + "..."
    return repr(text)


def _check_keys(data: dict, allowed: set[str]) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        raise InputError(f"unknown field {_short(extra[0])}")


def _has_control(text: str) -> bool:
    """True for control characters and lone surrogates (which cannot be encoded)."""
    return any(unicodedata.category(c) in ("Cc", "Cs") for c in text)


def _abs_path(text: str) -> Path:
    return Path(os.path.normpath(os.path.expanduser(text)))


def parse_path(data: dict, field: str) -> Path:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} is required (a path string)")
    if _has_control(value):
        raise InputError(f"{field} contains control characters or lone surrogates")
    path = _abs_path(value)
    if not path.is_absolute():
        raise InputError(f"{field} must be an absolute path or start with ~: {_short(value)}")
    return path


def parse_segment(data: dict, field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise InputError(f"{field} is required (a folder name)")
    if (value.startswith(".") or ".." in value or value != value.strip()
            or _has_control(value) or any(c in _UNSAFE_CHARS for c in value)):
        raise InputError(f"{field} is not a safe folder name: {_short(value)}")
    return value


def parse_term(data: dict) -> str:
    term = parse_segment(data, "term")
    if not _TERM.fullmatch(term):
        raise InputError(f"term must be YYYY-<word>, e.g. 2026-Fall: {_short(term)}")
    return term


def parse_role(data: dict) -> str:
    role = data.get("role")
    if role not in _ROLES:
        raise InputError(f"role must be one of {', '.join(_ROLES)}: {_short(role)}")
    return role


# --- Root and pointer ----------------------------------------------------------

def default_root() -> Path:
    return _abs_path(DEFAULT_ROOT)


def pointer_path() -> Path:
    return _abs_path(POINTER_PATH)


def resolve_root() -> tuple[Path, str]:
    """Return (root, source) where source is "pointer" or "default"."""
    pointer = pointer_path()
    if not pointer.is_file():
        return default_root(), "default"
    lines = pointer.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    if len(lines) != 1 or _has_control(lines[0]) or not _abs_path(lines[0].strip()).is_absolute():
        raise InputError(f"pointer file {pointer} must hold one absolute path "
                         "(run init with an explicit root to rewrite it)")
    return _abs_path(lines[0].strip()), "pointer"


def check_safe_root(path: Path, field: str) -> None:
    """Refuse the home directory, a filesystem root, or an ancestor of the pointer file."""
    home, pointer = _abs_path("~"), pointer_path()
    for candidate in {path, path.resolve()}:
        if candidate in (home, home.resolve()) or candidate == Path(candidate.anchor):
            raise InputError(f"{field} {candidate} is not allowed: pick a dedicated folder, not the "
                             "home directory or a filesystem root")
        if pointer.is_relative_to(candidate) or pointer.resolve().is_relative_to(candidate):
            raise InputError(f"{field} {candidate} is not allowed: it contains the pointer file {pointer}")


def set_pointer(root: Path) -> None:
    pointer = pointer_path()
    if root == default_root():
        if pointer.exists() or pointer.is_symlink():
            pointer.unlink()
        return
    pointer.parent.mkdir(parents=True, exist_ok=True)
    tmp = pointer.with_name(pointer.name + ".tmp")
    tmp.write_text(f"{root}\n", encoding="utf-8")
    os.replace(tmp, pointer)


def has_tree(root: Path) -> bool:
    return (root / ".state" / "profile.md").is_file()


def course_folder(root: Path, term: str, course: str, what: str = "course") -> Path:
    """``<root>/<term>/<course>``; refuses a symlinked term, course or course ``.state`` folder."""
    term_dir, course_dir = root / term, root / term / course
    for folder, kind in ((term_dir, "term"), (course_dir, what), (course_dir / ".state", f"{what} .state")):
        if folder.is_symlink():
            raise InputError(f"{kind} folder {folder} is a symlink; refusing to work through it")
    return course_dir


def read_setup_done(root: Path) -> str | None:
    profile = root / ".state" / "profile.md"
    if not profile.is_file():
        return None
    for line in profile.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.fullmatch(r"setup_done:(.*)", line.strip())
        if match:
            value = match.group(1).strip()
            return value if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) else None
    return None


# --- Templates and tree building -------------------------------------------------

def instance_template(text: str) -> str:
    """Strip a template's placeholders: see the module docstring."""
    out: list[str] = []
    dropping = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<!--"):
            out.append(line)
            continue
        if stripped.startswith("#"):
            dropping = stripped.startswith("## ") and bool(_PLACEHOLDER.search(stripped))
            if dropping:
                continue
        elif dropping:
            continue
        if not _PLACEHOLDER.search(stripped):
            out.append(line)
        elif stripped.startswith("|") or stripped.startswith(("- ", "* ")):
            continue
        elif (key := _KEY_LINE.fullmatch(stripped)):
            out.append(f"{key.group(1)}:")
        else:
            raise RuntimeError("template line with an unhandled placeholder")
    collapsed: list[str] = []
    for line in out:
        if line.strip() == "" and (not collapsed or collapsed[-1].strip() == ""):
            continue
        collapsed.append(line)
    while collapsed and collapsed[-1].strip() == "":
        collapsed.pop()
    return "\n".join(collapsed) + "\n"


def _mkdir(path: Path, created: list[str]) -> None:
    if path.is_dir():
        return
    if path.exists() or path.is_symlink():
        raise InputError(f"{path} exists and is not a directory")
    path.mkdir()
    created.append(str(path))


def _write_template(dest: Path, template: str, created: list[str]) -> None:
    if dest.exists() or dest.is_symlink():
        return
    text = instance_template((_TEMPLATE_DIR / template).read_text(encoding="utf-8"))
    with open(dest, "x", encoding="utf-8") as handle:
        handle.write(text)
    created.append(str(dest))


def build_root(root: Path, created: list[str]) -> None:
    root.parent.mkdir(parents=True, exist_ok=True)
    _mkdir(root, created)
    _mkdir(root / "_inbox", created)
    _mkdir(root / ".state", created)
    _write_template(root / ".state" / "profile.md", "profile.md", created)


def build_course(root: Path, term: str, course: str, created: list[str]) -> Path:
    build_root(root, created)
    course_dir = root / term / course
    _mkdir(root / term, created)
    _mkdir(course_dir, created)
    _write_template(course_dir / "INDEX.md", "INDEX.md", created)
    for role in _ROLES:
        _mkdir(course_dir / role, created)
    state = course_dir / ".state"
    _mkdir(state, created)
    for name in _COURSE_MEMORY:
        _write_template(state / name, name, created)
    _mkdir(state / "logs", created)
    _mkdir(state / "out", created)
    return course_dir


def _is_within(path: Path, parent: Path) -> bool:
    return path.resolve() == parent.resolve() or path.resolve().is_relative_to(parent.resolve())


def _empty_dir(path: Path) -> None:
    """Remove everything inside ``path`` (used only on a target this run filled)."""
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass


def _is_memory_file(source: Path, root: Path) -> bool:
    """True for INDEX.md or anything under a .state directory inside the root."""
    for src, base in ((source, root), (source.resolve(), root.resolve())):
        if src.is_relative_to(base):
            rel = src.relative_to(base)
            if rel.name == "INDEX.md" or ".state" in rel.parts[:-1]:
                return True
    return False


# --- Subcommands -------------------------------------------------------------------

def cmd_root(data: dict) -> dict:
    _check_keys(data, set())
    root, source = resolve_root()
    exists = has_tree(root)
    setup_done = read_setup_done(root)
    if setup_done:
        state = f"setup done {setup_done}"
    elif exists:
        state = "setup not done yet"
    else:
        state = "no workspace yet"
    return {"root": str(root), "source": source, "exists": exists, "setup_done": setup_done,
            "line": f"Learning root: {root} ({source}, {state})."}


def cmd_init(data: dict) -> dict:
    _check_keys(data, {"root"})
    if "root" in data:
        root = parse_path(data, "root")
        check_safe_root(root, "root")
        try:
            current, _ = resolve_root()
        except InputError:  # malformed pointer: the explicit root rewrites it
            current = None
    else:
        current, _ = resolve_root()
        root = current
    if (current is not None and root.resolve() != current.resolve() and has_tree(current)):
        raise InputError(f"a workspace already exists at {current}; use relocate to move it to {root}")
    created: list[str] = []
    build_root(root, created)
    if "root" in data:
        set_pointer(root)
    line = f"Workspace ready at {root}." if created else f"Workspace already set up at {root}."
    return {"root": str(root), "created": created, "line": line}


def cmd_course(data: dict) -> dict:
    _check_keys(data, {"term", "course"})
    term, course = parse_term(data), parse_segment(data, "course")
    root, _ = resolve_root()
    created: list[str] = []
    course_dir = build_course(root, term, course, created)
    verb = "ready" if created else "already set up"
    return {"root": str(root), "course_dir": str(course_dir), "created": created,
            "line": f"Course folder {verb}: {course_dir}/"}


def cmd_file(data: dict) -> dict:
    _check_keys(data, {"source", "term", "course", "role"})
    source = parse_path(data, "source")
    term, course, role = parse_term(data), parse_segment(data, "course"), parse_role(data)
    if source.is_symlink() or not source.is_file():
        raise InputError(f"source is not an existing regular file: {source}")
    root, _ = resolve_root()
    if _is_memory_file(source, root):
        raise InputError(f"source is a Mimir memory file and cannot be filed: {source}")
    dest_dir = root / term / course / role
    dest = dest_dir / source.name
    if dest.exists() or dest.is_symlink():
        raise InputError(f"{dest} already exists; nothing was moved")
    created: list[str] = []
    course_dir = build_course(root, term, course, created)
    try:
        shutil.move(source, dest)
    except BaseException:
        # A failed cross-filesystem copy can leave a partial dest; the source is the original.
        if source.exists() and (dest.exists() or dest.is_symlink()):
            try:
                dest.unlink()
            except OSError:
                pass
        raise
    return {"source": str(source), "dest": str(dest), "course_dir": str(course_dir),
            "created": created, "line": f"Saved {source.name} to {dest_dir}/"}


def cmd_relocate(data: dict) -> dict:
    _check_keys(data, {"to"})
    target = parse_path(data, "to")
    check_safe_root(target, "to")
    current, _ = resolve_root()
    if current.is_symlink():
        raise InputError(f"the current root {current} is a symlink; move its target by hand")
    if not has_tree(current):
        raise InputError(f"no workspace at {current} to relocate")
    check_safe_root(current, "current root")
    if _is_within(target, current):
        if target.resolve() == current.resolve():
            raise InputError(f"the workspace is already at {current}")
        raise InputError(f"{target} is inside the current workspace {current}")
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise InputError(f"{target} exists and is not a directory")
    if target.is_dir() and any(target.iterdir()):
        raise InputError(f"{target} is not empty; nothing was moved")
    target_existed = target.is_dir()
    target.parent.mkdir(parents=True, exist_ok=True)
    result = {"from": str(current), "root": str(target),
              "line": f"Moved the learning folder from {current} to {target}."}
    try:
        os.rename(current, target)  # POSIX rename may replace an empty directory
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
    else:
        try:
            set_pointer(target)
        except BaseException:  # never leave the tree moved while the pointer names the old root
            os.rename(target, current)
            if target_existed:
                try:
                    target.mkdir()
                except OSError:
                    pass
            raise
        return result
    # Across filesystems: copy, then pointer, then delete the old tree.
    try:
        shutil.copytree(current, target, symlinks=True, dirs_exist_ok=True)
        set_pointer(target)
    except BaseException:  # remove the partial copy so a retry is not refused; source untouched
        if target_existed:
            _empty_dir(target)
        elif target.is_dir() and not target.is_symlink():
            shutil.rmtree(target, ignore_errors=True)
        raise
    try:
        shutil.rmtree(current)
    except OSError as exc:  # the move itself succeeded
        detail = exc.strerror or type(exc).__name__
        result["warning"] = f"old folder {current} was not fully removed ({detail})"
        result["line"] += f" The old folder {current} was not fully removed ({detail}); delete it by hand."
    return result


COMMANDS = {
    "root": (cmd_root, "where the learning root is and whether setup finished"),
    "init": (cmd_init, "create the root, _inbox/ and .state/profile.md"),
    "course": (cmd_course, "create a course tree under <root>/<YYYY-Term>/<CODE Name>/"),
    "file": (cmd_file, "move one file into <course>/<role>/"),
    "relocate": (cmd_relocate, "move the whole tree to a new root"),
}


def _fail(prog: str, message: str, code: int = 2) -> int:
    sys.stderr.write(f"{prog}: {message}\n")
    return code


class _Parser(argparse.ArgumentParser):
    """Usage errors print one ``<script>: <msg>`` line and exit 2."""

    def error(self, message: str):
        sys.stderr.write(f"{self.prog.split()[0]}: {message}\n")
        sys.exit(2)


def run_cli(prog: str, description: str, commands: dict, argv: list[str] | None = None) -> int:
    """Shared runner: one subcommand, one JSON object in, one JSON object out.

    ``commands`` maps a name to ``(handler, help)``; a handler takes the input
    dict and returns the output dict. ``InputError`` and ``OSError`` exit 2,
    anything else exits 1 as an internal error; never a traceback.
    """
    parser = _Parser(prog=prog, description=description)
    names = ",".join(commands)
    sub = parser.add_subparsers(dest="command", required=True, metavar=f"{{{names}}}")
    for name, (_, help_text) in commands.items():
        sub.add_parser(name, help=help_text)
    args = parser.parse_args(argv)
    try:
        result = commands[args.command][0](read_input(sys.stdin.buffer.read()))
        output = (json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8")
    except InputError as exc:
        return _fail(prog, str(exc))
    except OSError as exc:
        detail = exc.strerror or type(exc).__name__
        where = f": {exc.filename}" if exc.filename else ""
        return _fail(prog, f"filesystem error ({detail}){where}")
    except Exception as exc:  # a bug, not bad input; still never a traceback
        return _fail(prog, f"internal error ({type(exc).__name__})", code=1)
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_cli("workspace.py",
                   ("Mimir workspace builder. Subcommands: root, init, course, file, relocate. "
                    "Reads one JSON object on stdin and prints one JSON object on stdout."),
                   COMMANDS, argv)


if __name__ == "__main__":
    sys.exit(main())
