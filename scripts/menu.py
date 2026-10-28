#!/usr/bin/env python3
"""Bare `./harness` entry: a curated interactive menu (falls back to help when piped).

Usage:
  ./harness                # (with no args) shows this menu on a TTY
  ./harness menu           # same, explicitly
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))
import guide  # noqa: E402 — reuse select_menu / banner / c

ITEMS = [
    ("📊  status — one-glance dashboard", ["status"]),
    ("🚀  run tests — guided tour", ["guide"]),
    ("🎬  sandboxed demo — no hardware", ["demo"]),
    ("📄  open the latest report", ["report", "--open"]),
    ("🔍  review latest vs baseline", ["review"]),
    ("🧠  log a correction (teach)", ["teach"]),
    ("🔧  diagnose this machine", ["diagnose"]),
    ("🧭  onboarding — first-run setup", ["onboarding"]),
    ("❓  help", ["help"]),
]


def main(argv: list[str] | None = None) -> int:
    if not sys.stdin.isatty():
        # piped: fall back to plain help
        return subprocess.run([str(HARNESS / "harness"), "help"]).returncode

    guide.banner("regression-harness")
    print("  One entry point for running, reporting, reviewing, and learning.\n")
    choice = guide.select_menu(
        guide.c("What would you like to do?  (↑/↓ choose · Enter select · q quit)", guide.BOLD),
        ITEMS,
    )
    if not choice:
        return 0
    env = dict(os.environ)
    env["HARNESS_WRAPPED"] = "1"
    return subprocess.run([str(HARNESS / "harness"), *choice], env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())