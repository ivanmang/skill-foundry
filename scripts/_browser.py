#!/usr/bin/env python3
"""Cross-platform browser opener with graceful fallback (WSL / headless).

Internal helper used by build_report.py --open and open_report.py.

Strategy:
  1. On WSL, open via explorer.exe on the Windows host (best UX).
  2. Otherwise try xdg-open / open / start.
  3. If nothing works, print the path (+ Windows path on WSL) instead of
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
        out = subprocess.run([wslpath, "-w", str(path)], capture_output=True, text=True, timeout=10)
        win = out.stdout.strip()
        return win or None
    except Exception:
        return None


def open_browser(path: Path | str) -> str | None:
    """Open `path` in a browser. Return an error message if it couldn't, else None."""
    p = Path(path)

    if is_wsl():
        exe = shutil.which("explorer.exe")
        if not exe and Path("/mnt/c/Windows/explorer.exe").exists():
            exe = "/mnt/c/Windows/explorer.exe"
        if exe:
            win = to_windows(p)
            if win:
                r = subprocess.run([exe, win], check=False)
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