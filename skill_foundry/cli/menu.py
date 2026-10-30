#!/usr/bin/env python3
"""Bare `./harness` entry: a curated interactive menu (falls back to help when piped).

The harness is ONLY the skill-ops loop (capture → promote → hub → discover),
so this front door lists exactly that. The bundled regression workflow lives as
directly-runnable scripts the skills reference (see .claude/skills/), not here.

Usage:
  ./harness                # (with no args) shows this menu on a TTY
  ./harness menu           # same, explicitly
"""

from __future__ import annotations

import sys

from skill_foundry import dispatch
from skill_foundry.lib import ui

ITEMS = [
    ("🛠  capture a new skill", ["capture-skill"]),
    ("🧠  log a correction (teach)", ["teach"]),
    ("⬆  promote pending learnings", ["promote", "--direct"]),
    ("📚  browse skills (list/search)", ["skills"]),
    ("❓  help", ["help"]),
]


def main(argv: list[str] | None = None) -> int:
    if not sys.stdin.isatty():
        # piped: fall back to plain help
        return dispatch.dispatch("help", [])

    ui.banner("skill-foundry")
    print("  capture → promote → hub → discover.\n")
    choice = ui.select_menu(
        ui.c("What would you like to do?  (↑/↓ choose · Enter select · q quit)", ui.BOLD),
        ITEMS,
    )
    if not choice:
        return 0
    return dispatch.dispatch(choice[0], choice[1:])


if __name__ == "__main__":
    raise SystemExit(main())