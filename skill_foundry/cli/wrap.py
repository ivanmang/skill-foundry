#!/usr/bin/env python3
"""Wrap a harness verb, then guide the user to what's next — in one process.

After `./harness run` / `report` / `status` / … finishes, the user gets a
"What next?" menu instead of dropping back to the shell. The verb itself runs
in-process via `skill_foundry.dispatch` (no subprocess), and the menu loop
re-dispatches in the same process.
"""

from __future__ import annotations

import sys

from skill_foundry import dispatch
from skill_foundry.cli import guide

# Natural next steps per verb: (label, argv) — shown first, then generic options.
NEXT: dict[str, list[tuple[str, list[str]]]] = {
    "run": [
        ("📄  open the report", ["report", "--open"]),
        ("🔍  review vs baseline", ["review"]),
        ("🧠  teach a correction", ["teach"]),
        ("📊  status", ["status"]),
    ],
    "report": [
        ("🔍  review vs baseline", ["review"]),
        ("🧠  teach a correction", ["teach"]),
        ("🚀  run again (dry-run)", ["run", "--all-suites", "--dry-run"]),
    ],
    "review": [
        ("🧠  teach a correction", ["teach"]),
        ("📄  open the report", ["report", "--open"]),
    ],
    "teach": [
        ("🟢  publish to main (--direct)", ["promote", "--direct"]),
        ("👀  review the diff first (--propose)", ["promote", "--propose"]),
        ("📚  browse skills", ["skills"]),
    ],
    "promote": [
        ("📚  browse skills (discover what you published)", ["skills"]),
        ("🧠  teach another", ["teach"]),
    ],
    "capture-skill": [
        ("⬆  publish the draft", ["promote-skill"]),
        ("📚  browse skills", ["skills"]),
    ],
    "promote-skill": [
        ("📚  browse skills", ["skills"]),
        ("🛠  capture another", ["capture-skill"]),
    ],
    "skills": [
        ("🛠  capture a new skill", ["capture-skill"]),
        ("⬆  promote pending learnings", ["promote", "--direct"]),
    ],
    "status": [
        ("🚀  run (dry-run preview)", ["run", "--all-suites", "--dry-run"]),
        ("🎬  sandboxed demo", ["demo"]),
        ("🔧  diagnose this machine", ["diagnose"]),
    ],
    "diagnose": [
        ("🚀  run (dry-run preview)", ["run", "--all-suites", "--dry-run"]),
        ("🧭  onboarding", ["onboarding"]),
    ],
    "demo": [
        ("🚀  run the real thing (dry-run)", ["run", "--all-suites", "--dry-run"]),
        ("🧭  guided tour", ["guide"]),
    ],
    "guide": [
        ("📊  status", ["status"]),
        ("🚀  run (dry-run preview)", ["run", "--all-suites", "--dry-run"]),
    ],
    "list": [
        ("🚀  run (dry-run preview)", ["run", "--all-suites", "--dry-run"]),
        ("🔧  diagnose this machine", ["diagnose"]),
    ],
    "cann": [
        ("📊  status", ["status"]),
        ("🚀  run (dry-run preview)", ["run", "--all-suites", "--dry-run"]),
    ],
    "baseline": [
        ("📊  status", ["status"]),
        ("🚀  run", ["run", "--all-suites", "--quiet"]),
    ],
    "onboarding": [
        ("📊  status", ["status"]),
        ("🎬  sandboxed demo", ["demo"]),
    ],
    "history": [
        ("📄  open latest report", ["report", "--open"]),
        ("📊  status", ["status"]),
    ],
    "clean": [("📊  status", ["status"])],
    "validate": [("📊  status", ["status"])],
}

TYPE = "⌨  type a command…"
FULL = "📋  full menu — all verbs"
SHELL = "✕  back to shell"


def _type_command() -> list[str] | None:
    """Let the user type any `./harness …` command freely. Empty/quit -> None."""
    raw = guide.ask("  ./harness ")
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
            ("⬆  promote pending learnings", ["promote", "--direct"]),
            ("📊  status", ["status"]),
        ]
        options = suggestions + [(TYPE, "TYPE"), (FULL, "FULL"), (SHELL, None)]
        status = guide.c("ok", guide.GREEN) if rc == 0 else guide.c(f"exit {rc}", guide.YELLOW)
        choice = guide.select_menu(
            guide.c(f"What next?  (last: {verb} · {status})   ↑/↓ choose · Enter run · q = shell", guide.BOLD),
            options,
        )

        if choice == "TYPE":
            first = _type_command()
            if first is None:
                print()
                return 0
            continue
        if choice == "FULL":
            pick = guide.select_menu(
                guide.c("Run a command:", guide.BOLD),
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