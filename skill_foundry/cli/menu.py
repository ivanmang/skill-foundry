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
    ("🛠  capture a new skill         · draft into hub/inbox/", ["capture-skill"]),
    ("🧠  log a correction           · learnings/recent.md", ["teach"]),
    ("⬆  promote pending learnings  · gated + reviewed → MR", ["promote", "--pr"]),
    (
        "📚  browse skills              · list / search / grouped by category",
        ["skills"],
    ),
    ("❓  help", ["help"]),
]


def _counts() -> tuple[int, int, int]:
    """(published skills, inbox drafts, pending learnings) for the subtitle."""
    from skill_foundry.cli import skills as skills_cli
    from skill_foundry.paths import ROOT

    sk = skills_cli.collect()
    published = sum(1 for s in sk if s["status"] == "published")
    drafts = sum(1 for s in sk if s["status"] == "draft")
    pending = 0
    lr = ROOT / "learnings" / "recent.md"
    if lr.exists():
        for line in lr.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("- status: pending"):
                pending += 1
    return published, drafts, pending


def main(argv: list[str] | None = None) -> int:
    if not sys.stdin.isatty():
        # piped: fall back to plain help
        return dispatch.dispatch("help", [])

    ui.banner("skill-foundry")
    published, drafts, pending = _counts()
    print("  capture → promote → hub → discover.")
    print(f"  {published} skills · {drafts} draft(s) · {pending} pending learning(s)\n")
    choice = ui.select_menu(
        ui.c(
            "What would you like to do?  (↑/↓ choose · Enter select · q quit)", ui.BOLD
        ),
        ITEMS,
    )
    if not choice:
        return 0
    return dispatch.dispatch(choice[0], choice[1:])


if __name__ == "__main__":
    raise SystemExit(main())
