#!/usr/bin/env python3
"""Bare `./harness` entry: a curated interactive menu (falls back to help when piped).

The menu is the *front door*, so it leads with the product (the skill-ops loop)
and keeps the bundled regression workflow to two entries. The rest of the verbs
(status / diagnose / onboarding / history / clean / validate / cann / list /
selfcheck) stay available under `./harness help` and the post-verb "What next?"
menu.

Usage:
  ./harness                # (with no args) shows this menu on a TTY
  ./harness menu           # same, explicitly
"""

from __future__ import annotations

import sys

from skill_foundry import dispatch
from skill_foundry.cli import guide

ITEMS = [
    # ── THE PRODUCT — capture → promote → hub → discover ──
    ("🛠  capture a new skill", ["capture-skill"]),
    ("🧠  log a correction (teach)", ["teach"]),
    ("⬆  promote pending learnings", ["promote", "--direct"]),
    ("📚  browse skills (list/search)", ["skills"]),

    # ── BUNDLED — the regression workflow (the example domain) ──
    ("🚀  run the regression (guided)", ["guide"]),
    ("🎬  sandboxed demo — no hardware", ["demo"]),

    # ── everything else lives under ./harness help ──
    ("❓  help", ["help"]),
]


def main(argv: list[str] | None = None) -> int:
    if not sys.stdin.isatty():
        # piped: fall back to plain help
        return dispatch.dispatch("help", [])

    guide.banner("skill-foundry")
    print("  capture → promote → hub → discover  (regression is a bundled workflow).\n")
    choice = guide.select_menu(
        guide.c("What would you like to do?  (↑/↓ choose · Enter select · q quit)", guide.BOLD),
        ITEMS,
    )
    if not choice:
        return 0
    return dispatch.dispatch(choice[0], choice[1:])


if __name__ == "__main__":
    raise SystemExit(main())