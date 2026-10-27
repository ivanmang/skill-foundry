#!/usr/bin/env python3
"""Interactive, step-by-step guide through the regression harness.

Usage:
  ./harness guide            # guided tour (asks before each step)
  ./harness guide --demo     # jump straight to the sandboxed demo tour
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

CONFIG = HARNESS / "config" / "suites.json"
ARCHES = HARNESS / "config" / "arches.json"
BASELINE = HARNESS / "reports" / "baseline" / "baseline.json"
KNOWN = HARNESS / ".claude" / "skills" / "pto-isa" / "references" / "known-failures.md"


def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if sys.stdout.isatty() else text


def banner(title: str) -> None:
    print(f"\n{c('══ ' + title + ' ' + '═' * (50 - len(title)), BOLD)}")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            val = input(f"  {prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if val:
            return val
        if default:
            return default
        return ""


def ask_yesno(prompt: str, default: str = "n") -> bool:
    suffix = "Y/n" if default == "y" else "y/N"
    while True:
        v = ask(f"{prompt} ({suffix})", default).lower()
        if v in ("y", "yes"):
            return True
        if v in ("n", "no"):
            return False


def check_env() -> None:
    banner("0 · Environment check")
    checks = [
        ("python3", shutil.which("python3") is not None),
        ("git", shutil.which("git") is not None),
        ("ASCEND_HOME_PATH", bool(os.environ.get("ASCEND_HOME_PATH"))),
        ("PTO_ISA_REPO / ~/pto-isa", bool(os.environ.get("PTO_ISA_REPO")) or Path("~/pto-isa").expanduser().exists()),
    ]
    for name, ok in checks:
        mark = c("✓", GREEN) if ok else c("✗", RED)
        print(f"  {mark}  {name}")
    if not checks[2][1]:
        print(c("  → npu/costmodel/comm suites need ASCEND_HOME_PATH — source ./env.sh first.", YELLOW))
    if not checks[3][1]:
        print(c("  → pto-isa checkout not found — export PTO_ISA_REPO=... or clone ~/pto-isa.", YELLOW))
    print()


def choose_target_and_suites() -> tuple[str, list[str], list[str]]:
    banner("1 · Choose what to run")
    subprocess.run([sys.executable, "scripts/run_suite.py", "--list"], cwd=HARNESS, check=False)
    print()
    choice = ask("Suite — 'all' or a name (e.g. cpu-st)", "all").strip()
    if choice.lower() in ("all", ""):
        suite_flags = ["--all-suites"]
    else:
        suite_flags = ["--suite", choice]

    if not os.environ.get("ASCEND_HOME_PATH") and (
        choice.lower() in ("all", "") or choice.lower().startswith(("npu", "costmodel", "comm"))
    ):
        print(c("  ⚠  ASCEND_HOME_PATH is not set — this choice will ERROR. Run 'source ./env.sh' first, or pick a cpu suite.", YELLOW))

    mode = ask("Output mode — normal / quiet / tui", "normal").strip().lower()
    mode_flags = {"normal": [], "quiet": ["--quiet"], "tui": ["--tui"]}.get(mode, [])

    testcase_flags: list[str] = []
    filter_flags: list[str] = []
    if choice.lower() not in ("all", ""):
        testcase = ask("Testcase (blank = all in suite)")
        if testcase:
            testcase_flags = ["--testcase", testcase]
            gfilter = ask("gtest filter (blank = none)")
            if gfilter:
                filter_flags = ["--filter", gfilter]

    run_id = ask("Run id (blank = auto)")
    run_id_flags = ["--run-id", run_id] if run_id else []
    return "pto-isa", suite_flags, mode_flags + run_id_flags + testcase_flags + filter_flags


def run_real_tour() -> int:
    check_env()
    target, suite_flags, extra_flags = choose_target_and_suites()

    banner("2 · Run the suite(s)")
    cmd = [sys.executable, "scripts/run_suite.py", "--target", target, *suite_flags, *extra_flags]
    result = subprocess.run(cmd, cwd=HARNESS)
    if result.returncode != 0:
        print(c("\n  Some suites did not pass — we'll review next.", YELLOW))

    run_dir = subprocess.run(
        ["ls", "-1dt", str(HARNESS / "reports" / "*")],
        capture_output=True, text=True,
    ).stdout.splitlines()
    latest = next((d for d in run_dir if (HARNESS / "reports" / d / "run.json").exists()), None)

    banner("3 · Report")
    if latest and ask_yesno(f"Generate a report for {latest}?", "y"):
        out_base = HARNESS / "reports" / latest / "report"
        subprocess.run([
            sys.executable, "scripts/build_report.py",
            "--run", str(HARNESS / "reports" / latest / "run.json"),
            "--known", str(KNOWN), "--out", str(out_base),
        ], cwd=HARNESS, check=False)
        print(f"  → {out_base}.md / {out_base}.html")

    banner("4 · Review vs baseline")
    if latest and ask_yesno("Diff against the pinned baseline?", "y"):
        subprocess.run([
            sys.executable, "scripts/diff_runs.py",
            "--run", str(HARNESS / "reports" / latest / "run.json"),
            "--baseline", str(BASELINE),
        ], cwd=HARNESS, check=False)

    banner("5 · Teach it (if something new failed)")
    if latest and ask_yesno("Log a correction for any new failure?", "n"):
        subprocess.run([str(HARNESS / "scripts" / "teach")])

    banner("6 · Promote pending learnings")
    if ask_yesno("Propose/promote pending learnings?", "n"):
        if ask_yesno("Apply + push + open a merge request (--pr)? (n = propose only)", "y"):
            subprocess.run([sys.executable, "scripts/promote_recent.py", "--pr"], cwd=HARNESS)
        else:
            subprocess.run([sys.executable, "scripts/promote_recent.py", "--propose"], cwd=HARNESS)

    print(c("\n✓ Done. Next time: ./harness run --all-suites --quiet  and  ./harness promote --pr", GREEN))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--demo" in args:
        return subprocess.run([str(HARNESS / "demo" / "run_demo.sh")]).returncode
    print(c("\n regression-harness · guided tour ", BOLD))
    mode = ask("Start with the sandboxed demo (no hardware) or the real pto-isa tour?", "demo").lower()
    if mode in ("demo", "d"):
        return subprocess.run([str(HARNESS / "demo" / "run_demo.sh")]).returncode
    return run_real_tour()


if __name__ == "__main__":
    raise SystemExit(main())