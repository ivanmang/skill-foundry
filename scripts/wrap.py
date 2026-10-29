#!/usr/bin/env python3
"""Wrap a harness verb, then guide the user to what's next.

In an interactive terminal the dispatcher execs this instead of the verb, so
after `./harness run` / `report` / `status` / … finishes, the user gets a
"What next?" menu instead of dropping back to the shell.

The menu is context-aware (suggests the natural next step for the verb they just
ran) and also lets them type any command themselves, open the full verb menu, or
quit to the shell.

The dispatcher sets HARNESS_WRAPPED=1 before exec'ing this; child verbs inherit
it and run unwrapped, so the loop here is the single one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))
import guide  # noqa: E402 — select_menu / ask
import menu  # noqa: E402 — ITEMS


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
        ("🟢  propose a diff", ["promote", "--propose"]),
        ("📊  status", ["status"]),
    ],
    "promote": [
        ("📊  status", ["status"]),
        ("🧠  teach another", ["teach"]),
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
    "open": [
        ("🔍  review", ["review"]),
        ("🧠  teach a correction", ["teach"]),
    ],
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
        return subprocess.call([str(HARNESS / "harness"), "menu"])

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        # piped/CI: run verb straight through, no menu
        return subprocess.call([str(HARNESS / "harness"), *args])

    env = dict(os.environ)
    env["HARNESS_WRAPPED"] = "1"

    first = args
    while True:
        rc = subprocess.call([str(HARNESS / "harness"), *first], env=env)
        print()

        verb = first[0]
        suggestions = NEXT.get(verb, []) or [
            ("🛠  capture a new skill", ["capture-skill"]),
            ("📊  status", ["status"]),
            ("🚀  run (dry-run preview)", ["run", "--all-suites", "--dry-run"]),
            ("📄  open latest report", ["report", "--open"]),
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
            pick = guide.select_menu(guide.c("Run a command:", guide.BOLD), menu.ITEMS)
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