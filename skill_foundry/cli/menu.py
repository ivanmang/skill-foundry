#!/usr/bin/env python3
"""Bare `./harness` entry: a curated interactive menu (falls back to help when piped).

Usage:
  ./harness                # (with no args) shows this menu on a TTY
  ./harness menu           # same, explicitly
"""

from __future__ import annotations

import sys

from skill_foundry import dispatch
from skill_foundry.cli import guide

ITEMS = [
    ("🛠  capture a new skill", ["capture-skill"]),
    ("📚  browse skills (list/search)", ["skills"]),
    ("🧠  log a correction (teach)", ["teach"]),
    ("🚀  run tests — guided tour", ["guide"]),
    ("📊  status — one-glance dashboard", ["status"]),
    ("🔍  review latest vs baseline", ["review"]),
    ("🎬  sandboxed demo — no hardware", ["demo"]),
    ("🔧  diagnose this machine", ["diagnose"]),
    ("🧭  onboarding — first-run setup", ["onboarding"]),
    ("❓  help", ["help"]),
]


def main(argv: list[str] | None = None) -> int:
    if not sys.stdin.isatty():
        # piped: fall back to plain help
        return dispatch.dispatch("help", [])

    guide.banner("skill-foundry")
    print("  One entry point for capturing skills and running the regression workflow.\n")
    choice = guide.select_menu(
        guide.c("What would you like to do?  (↑/↓ choose · Enter select · q quit)", guide.BOLD),
        ITEMS,
    )
    if not choice:
        return 0
    return dispatch.dispatch(choice[0], choice[1:])


if __name__ == "__main__":
    raise SystemExit(main())