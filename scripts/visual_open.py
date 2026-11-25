"""Mimir visual builder, part 5: opening a built file in the default browser (``visual.py open``).

Standard library only, Python 3.11+. ``open_in_browser`` tries the platform's own opener, never a console
browser (see the docstring of ``visual.py``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

OPEN_WAIT_SECONDS = 5


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _launch(argv: list[str], ignore_exit: bool) -> bool:
    env = {k: v for k, v in os.environ.items() if k != "BROWSER"}
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=env, start_new_session=True)
    except OSError:
        return False
    try:
        code = proc.wait(timeout=OPEN_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        return True  # still running: the browser is starting in the foreground
    return ignore_exit or code == 0


def detect_platform() -> str:
    """Return macos, windows, wsl, linux or other."""
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "wsl" if _is_wsl() else "linux"
    return "other"


def open_in_browser(path: Path) -> bool:
    """Try the platform's own opener (never a console browser); True when it reports success."""
    platform = detect_platform()
    if platform == "macos":
        return _launch(["open", str(path)], ignore_exit=False)
    if platform == "windows":
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except (OSError, AttributeError):
            return False
        return True
    if platform == "wsl":
        if shutil.which("wslview"):
            return _launch(["wslview", str(path)], ignore_exit=False)
        explorer, wslpath = shutil.which("explorer.exe"), shutil.which("wslpath")
        if not explorer or not wslpath:
            return False
        try:
            win = subprocess.run([wslpath, "-w", str(path)], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, timeout=OPEN_WAIT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if win.returncode != 0 or not win.stdout.strip():
            return False
        return _launch([explorer, win.stdout.strip()], ignore_exit=True)
    if platform == "linux" and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        opener = shutil.which("xdg-open")
        return bool(opener) and _launch([opener, str(path)], ignore_exit=False)
    return False
