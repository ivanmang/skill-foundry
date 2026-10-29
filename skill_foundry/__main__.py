"""`python -m skill_foundry` — single-process entry point for the skill-foundry CLI.

Dispatch is shared with the wrap loop and the menu (see `skill_foundry.dispatch`),
so a verb runs in this process with no per-verb subprocess. Shell verbs
(baseline, selfcheck) remain subprocesses because they are bash scripts.

Set HARNESS_WRAPPED=1 to force a verb past the interactive "What next?" wrap
(this is what the full-screen TUI uses when it launches an action).
"""

from __future__ import annotations

import os
import sys

from skill_foundry import dispatch


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else "menu"

    if (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and not os.environ.get("HARNESS_WRAPPED")
        and cmd not in dispatch.NON_WRAP
    ):
        from skill_foundry.cli import wrap

        return wrap.main([cmd, *args[1:]])

    return dispatch.dispatch(cmd, args[1:])


if __name__ == "__main__":
    raise SystemExit(main())