#!/usr/bin/env python3
"""Full-screen dashboard (TUI): status + action menu in one view.

Usage:
  ./harness tui           # interactive dashboard
  ./harness status        # non-interactive one-glance (same data)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))
import guide  # noqa: E402 — reuse _read_key
import status  # noqa: E402 — reuse collect()

BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"

ACTIONS: list[tuple[str, list[str] | None]] = [
    ("🚀  run tests — guided", ["guide"]),
    ("🎬  sandboxed demo", ["demo"]),
    ("📊  status", ["status"]),
    ("📄  open the latest report", ["report", "--open"]),
    ("🔍  review vs baseline", ["review"]),
    ("🧠  teach / promote a learning", ["teach"]),
    ("🔧  diagnose this machine", ["diagnose"]),
    ("🧭  onboarding", ["onboarding"]),
    ("❓  help", ["help"]),
]


def _ok(b: bool) -> str:
    return (GREEN + "✓" if b else RED + "✗") + RESET


def render(selected: int) -> None:
    data = status.collect()
    env = data["env"]
    asc = env["ascend_version"] or env["ascend"] or "unset"
    lines: list[str] = []
    lines.append(BOLD + "══ regression-harness · dashboard ══" + RESET)
    lines.append(
        f"  env      python3 {_ok(env['python3'])}  git {_ok(env['git'])}  "
        f"ASCEND {asc}  pto-isa {_ok(env['pto_isa'])}"
    )
    suite_bits = []
    for s in data["suites"]:
        if not s["enabled"]:
            continue
        suite_bits.append(f"{s['name']} {_ok(s['runnable'])}")
    lines.append("  suites   " + "  ".join(suite_bits))
    b, ln, lr = data["baseline"], data["learnings"], data["last_run"]
    lines.append(
        f"  baseline {_ok(b['exists'])} · learnings {ln['pending']} pending / {ln['promoted']} promoted"
    )
    if lr:
        lines.append(f"  last     {lr['run_id']}  {lr['suites']}")
    lines.append("")
    lines.append(BOLD + "  What next?" + RESET)
    for i, (label, _) in enumerate(ACTIONS):
        if i == selected:
            lines.append("  \033[7m ▶ " + label + " \033[0m")
        else:
            lines.append("    " + label)
    lines.append("")
    lines.append("  ↑/↓ move · Enter run · q quit")
    sys.stdout.write("\033[2J\033[H" + "\n".join(lines) + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    if not sys.stdin.isatty():
        return subprocess.run([str(HARNESS / "harness"), "status"]).returncode

    selected = 0
    while True:
        render(selected)
        key = guide._read_key()
        if key == "UP":
            selected = (selected - 1) % len(ACTIONS)
        elif key == "DOWN":
            selected = (selected + 1) % len(ACTIONS)
        elif key == "ENTER":
            action = ACTIONS[selected][1]
            if action is None:
                return 0
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            subprocess.run([str(HARNESS / "harness"), *action])
            try:
                input("\n  Press Enter to return to the dashboard...")
            except (EOFError, KeyboardInterrupt):
                return 0
        elif key in ("q", "ESC", "CTRL_C"):
            print()
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())