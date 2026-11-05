#!/usr/bin/env python3
"""Cross-platform browser opener with graceful fallback (WSL / headless).

Internal helper used by report.py --open and promote.py --pr.

Strategy:
  1. On WSL, open files/URLs via explorer.exe on the Windows host (best UX).
  2. Otherwise try xdg-open / open / start.
  3. If nothing works, print the path/URL (+ Windows path on WSL) instead of
     spewing xdg-open's noisy error.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        rel = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").strip()
        return "microsoft" in rel or "WSL" in rel
    except Exception:
        return False


def to_windows(path: Path | str) -> str | None:
    wslpath = shutil.which("wslpath")
    if not wslpath:
        return None
    try:
        out = subprocess.run(
            [wslpath, "-w", str(path)], capture_output=True, text=True, timeout=10
        )
        win = out.stdout.strip()
        return win or None
    except Exception:
        return None


def _host_browser_exe() -> str | None:
    exe = shutil.which("explorer.exe")
    if not exe and Path("/mnt/c/Windows/explorer.exe").exists():
        exe = "/mnt/c/Windows/explorer.exe"
    return exe


def open_browser(path: Path | str) -> str | None:
    """Open `path` (a file path or an http(s) URL) in a browser.

    Return an error message if it couldn't be opened, else None.
    """
    target = str(path)
    is_url = target.startswith(("http://", "https://"))
    host_exe = _host_browser_exe()

    # URLs: open in the host browser on WSL, else xdg-open/open/start.
    if is_url:
        if is_wsl() and host_exe:
            r = subprocess.run([host_exe, target], check=False)
            if r.returncode == 0:
                return None
            return (
                f"couldn't open the URL in the host browser. Open manually:\n  {target}"
            )
        opener = (
            shutil.which("xdg-open") or shutil.which("open") or shutil.which("start")
        )
        if opener:
            r = subprocess.run([opener, target], check=False)
            if r.returncode == 0:
                return None
        return f"no browser found — open the URL manually:\n  {target}"

    # Files
    p = Path(target)
    if is_wsl() and host_exe:
        win = to_windows(p)
        if win:
            r = subprocess.run([host_exe, win], check=False)
            if r.returncode == 0:
                return None
            return (
                f"explorer.exe failed to open the report. Open manually:\n  {p}\n"
                f"  (Windows: {win})"
            )

    opener = shutil.which("xdg-open") or shutil.which("open") or shutil.which("start")
    if opener:
        r = subprocess.run([opener, str(p)], check=False)
        if r.returncode == 0:
            return None
        win = to_windows(p) if is_wsl() else None
        msg = f"no GUI browser found — couldn't open the report. It is at:\n  {p}"
        if win:
            msg += f"\n  (Windows: {win} — run: explorer.exe {win})"
        return msg

    return f"no browser opener found. Report is at:\n  {p}"
