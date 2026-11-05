#!/usr/bin/env python3
"""Wrap a harness verb, then guide the user to what's next — in one process.

After `./harness capture-skill` / `teach` / `promote` / … finishes, the user
gets a "What next?" menu instead of dropping back to the shell. The verb runs
in-process via `skill_foundry.dispatch`; the menu re-dispatches in-process.
"""

from __future__ import annotations

import sys

from skill_foundry import dispatch
from skill_foundry.lib import ui

# Natural next steps for the skill-ops loop (the whole product surface).
NEXT: dict[str, list[tuple[str, list[str]]]] = {
    "capture-skill": [
        ("⬆  publish the draft", ["promote-skill"]),
        ("📚  browse skills", ["skills"]),
    ],
    "teach": [
        ("🟢  open a pull request (--pr)", ["promote", "--pr"]),
        ("👀  review the diff first (--propose)", ["promote", "--propose"]),
        ("📚  browse skills", ["skills"]),
    ],
    "promote": [
        ("📚  browse skills (discover what you published)", ["skills"]),
        ("🧠  teach another", ["teach"]),
    ],
    "promote-skill": [
        ("📚  browse skills", ["skills"]),
        ("🛠  capture another", ["capture-skill"]),
    ],
    "skills": [
        ("🛠  capture a new skill", ["capture-skill"]),
        ("⬆  promote pending learnings", ["promote", "--pr"]),
    ],
}

TYPE = "⌨  type a command…"
FULL = "📋  full menu — all verbs"
SHELL = "✕  back to shell"


def _type_command() -> list[str] | None:
    """Let the user type any `./harness …` command freely. Empty/quit -> None."""
    raw = ui.ask("  ./harness ")
    if not raw:
        return None
    parts = raw.split()
    if parts[0].lower() in ("q", "quit", "exit", "shell"):
        return None
    return parts


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        return dispatch.dispatch("menu", [])

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        # piped/CI: run verb straight through, no menu
        return dispatch.dispatch(args[0], args[1:])

    first = args
    while True:
        rc = dispatch.dispatch(first[0], first[1:])
        print()

        verb = first[0]
        suggestions = NEXT.get(verb, []) or [
            ("🛠  capture a new skill", ["capture-skill"]),
            ("📚  browse skills", ["skills"]),
            ("⬆  promote pending learnings", ["promote", "--pr"]),
        ]
        options = suggestions + [(TYPE, "TYPE"), (FULL, "FULL"), (SHELL, None)]
        status = ui.c("ok", ui.GREEN) if rc == 0 else ui.c(f"exit {rc}", ui.YELLOW)
        choice = ui.select_menu(
            ui.c(f"What next?  (last: {verb} · {status})   ↑/↓ choose · Enter run · q = shell", ui.BOLD),
            options,
        )

        if choice == "TYPE":
            typed = _type_command()
            if typed is None:
                print()
                return 0
            first = typed
            continue
        if choice == "FULL":
            pick = ui.select_menu(
                ui.c("Run a command:", ui.BOLD),
                [(v, [v]) for v in dispatch.verbs()],
            )
            if not pick:
                continue
            first = pick
            continue
        if not choice:
            print()
            return 0
        first = choice
    return 0


if __name__ == "__main__":
    raise SystemExit(main())