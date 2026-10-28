#!/usr/bin/env python3
"""Interactive, step-by-step guide through the regression harness.

Usage:
  ./harness guide            # guided tour (asks before each step)
  ./harness guide --demo     # jump straight to the sandboxed demo tour
"""

from __future__ import annotations

import json
import os
import re
import select
import shutil
import subprocess
import sys
import termios
import time
import tty
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import detect_cann  # noqa: E402
import capabilities  # noqa: E402

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


def _read_key() -> str:
    """Read one keypress in raw mode.

    Uses os.read on the fd directly (not the buffered TextIOWrapper), reads the
    full escape sequence, and accepts both 'ESC [ A' and 'ESC O A' arrow forms.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd, termios.TCSADRAIN)  # don't flush keys that arrived just before the read
        first = os.read(fd, 1)  # exactly one byte — never over-read buffered keys
        if not first:
            return ""
        if first == b"\x1b":
            seq = b""
            deadline = time.time() + 0.08
            while len(seq) < 2 and time.time() < deadline:
                r, _, _ = select.select([fd], [], [], 0.02)
                if not r:
                    break
                seq += os.read(fd, 1)
            mapping = {
                "[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT",
                "OA": "UP", "OB": "DOWN", "OC": "RIGHT", "OD": "LEFT",
            }
            return mapping.get(seq.decode("latin-1"), "ESC")
        if first in (b"\r", b"\n"):
            return "ENTER"
        if first in (b"q", b"Q"):
            return "q"
        if first == b"\x03":
            return "CTRL_C"
        return first.decode("latin-1")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def select_menu(title: str, options: list, default_index: int = 0, height: int = 12):
    """Arrow-key menu with highlighted selection + a scrollable window.

    options is a list of str labels or (label, value) tuples. Returns the value
    (or the label when a bare string). Enter selects, Up/Down navigate (window
    scrolls), number jumps, q/Esc cancels (None). Falls back to a numbered
    prompt on non-TTY stdin.
    """
    if not options:
        return None
    labels = [o[0] if isinstance(o, tuple) else o for o in options]
    values = [o[1] if isinstance(o, tuple) else o for o in options]

    if not sys.stdin.isatty():
        print(c(title, BOLD))
        for i, lab in enumerate(labels, 1):
            print(f"  {i}) {lab}")
        choice = ask("Choose [1-%d] or name (Enter = skip)" % len(labels))
        if choice.isdigit() and 1 <= int(choice) <= len(labels):
            return values[int(choice) - 1]
        low = choice.lower()
        for i, v in enumerate(values):
            if v is not None and str(v).lower() == low:
                return v
        return None

    idx = max(0, min(default_index, len(labels) - 1))
    n = len(labels)
    visible = min(n, height)
    top = 0

    def render() -> str:
        nonlocal top
        if idx < top:
            top = idx
        elif idx >= top + visible:
            top = idx - visible + 1
        top = max(0, min(top, n - visible))
        lines = []
        for i in range(visible):
            j = top + i
            lab = labels[j]
            if j == idx:
                lines.append("  \033[7m ▶ " + lab + " \033[0m\033[K")
            else:
                lines.append("    " + lab + " \033[K")
        return "\n".join(lines)

    sys.stdout.write(c(title, BOLD) + "\n")
    sys.stdout.write(render() + "\n")

    while True:
        key = _read_key()
        if key == "UP":
            idx = (idx - 1) % n
        elif key == "DOWN":
            idx = (idx + 1) % n
        elif key == "ENTER":
            return values[idx]
        elif key in ("q", "ESC", "CTRL_C"):
            sys.stdout.write("\n")
            return None
        elif isinstance(key, str) and key.isdigit():
            di = int(key) - 1
            if 0 <= di < n:
                idx = di
            else:
                continue
        else:
            continue
        sys.stdout.write(f"\033[{visible}A\r")
        sys.stdout.write(render() + "\n")


def choose_cann() -> str | None:
    """List installed CANN toolkits with their arch support and let the user pick one."""
    cfg = detect_cann.load_config()
    roots = [r for r in detect_cann.candidates() if detect_cann.looks_like_toolkit(r)]
    if not roots:
        return None
    infos = [detect_cann.analyze(r, cfg) for r in roots]
    options = []
    for info in infos:
        hdr = " ".join(info["headers"]) if info["headers"] else "-"
        sim = " ".join(info["simulators"]) if info["simulators"] else "-"
        label = f"{info['path']}  ·  v{info['version']}  ·  headers {hdr}  ·  sim {sim}"
        options.append((label, info["path"]))
    title = c("  No ASCEND_HOME_PATH set. Choose a CANN package (↑/↓ + Enter, q = skip):", YELLOW)
    return select_menu(title, options)


TESTCASE_DIRS = {
    "cpu-st": "tests/cpu/st/testcase",
    "npu-sim-a3": "tests/npu/a2a3/src/st/testcase",
    "npu-hw-a3": "tests/npu/a2a3/src/st/testcase",
    "npu-sim-a5": "tests/npu/a5/src/st/testcase",
    "npu-hw-a5": "tests/npu/a5/src/st/testcase",
    "npu-sim-a6": "tests/npu/a6/src/st/testcase",
    "npu-hw-a6": "tests/npu/a6/src/st/testcase",
}


def choose_testcase(suite: str) -> str:
    """Dropdown of testcases in the chosen suite; '' means run all in the suite."""
    repo = Path(os.environ.get("PTO_ISA_REPO", "~/pto-isa")).expanduser()
    rel = TESTCASE_DIRS.get(suite)
    d = repo / rel if rel else None
    if not d or not d.exists():
        return ask("Testcase (blank = all in suite)").strip()
    names = sorted(p.name for p in d.iterdir() if p.is_dir())
    if not names:
        return ""
    options = [("all testcases", "")] + [(name, name) for name in names]
    sel = select_menu("Choose a testcase (↑/↓ + Enter, q = all):", options)
    return sel if sel is not None else ""


GTEST_RE = re.compile(r"TEST(?:_F|_P)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)")


def choose_filter(suite: str, testcase: str) -> str:
    """Dropdown of gtest cases in the chosen testcase; '' = no filter."""
    repo = Path(os.environ.get("PTO_ISA_REPO", "~/pto-isa")).expanduser()
    rel = TESTCASE_DIRS.get(suite)
    d = repo / rel / testcase if rel else None
    main = d / "main.cpp" if d else None
    if not main or not main.exists():
        return ask("gtest filter (blank = none)").strip()
    text = main.read_text(encoding="utf-8", errors="replace")
    cases = sorted({f"{m.group(1)}.{m.group(2)}" for m in GTEST_RE.finditer(text)})
    if not cases:
        return ask("gtest filter (blank = none)").strip()
    options = [("all cases (no filter)", "")] + [(c, c) for c in cases]
    sel = select_menu(f"Choose a filter for {testcase} (↑/↓ + Enter, q = all):", options)
    return sel if sel is not None else ""


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
        chosen = choose_cann()
        if chosen:
            os.environ["ASCEND_HOME_PATH"] = chosen
            print(c(f"  ✓  using {chosen}", GREEN))
        else:
            print(c("  → npu/costmodel/comm suites need ASCEND_HOME_PATH — pick a CANN above or source ./env.sh.", YELLOW))
    if not checks[3][1]:
        print(c("  → pto-isa checkout not found — export PTO_ISA_REPO=... or clone ~/pto-isa.", YELLOW))
    print()


def choose_target_and_suites() -> tuple[str, list[str], list[str]]:
    banner("1 · Choose what to run")

    # print arch context (soc → march) — informational, then pick the suite
    arches = json.loads(ARCHES.read_text(encoding="utf-8"))
    print("Arches (soc → march):")
    for name, a in arches.items():
        print(f"  {name:<8} {a.get('soc','-'):<18} {a.get('march') or '-'}")
    print()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    suites = cfg["targets"]["pto-isa"]["suites"]
    options = [("all runnable suites", "all")]
    for s in suites:
        runnable, reason = capabilities.suite_reason(s, arches)
        if s.get("enabled") and runnable:
            mark = "✓ "
        elif s.get("enabled"):
            mark = "! "
        else:
            mark = "  "
        note = "" if (runnable or not s.get("enabled")) else f"  ← {reason}"
        label = f"{mark}{s['name']:<14} {s.get('mode','-'):<9} {s.get('description','')}{note}"
        options.append((label, s["name"]))
    choice = select_menu("Choose a suite (↑/↓ + Enter):", options) or "all"

    if choice == "all":
        suite_flags = ["--all-suites"]
    else:
        suite_flags = ["--suite", choice]
        for s in suites:
            if s["name"] == choice:
                runnable, reason = capabilities.suite_reason(s, arches)
                if not runnable:
                    print(c(f"  ⚠  {choice}: {reason} — it will ERROR when run.", YELLOW))
                break

    testcase_flags: list[str] = []
    filter_flags: list[str] = []
    if choice.lower() not in ("all", ""):
        testcase = choose_testcase(choice)
        if testcase:
            testcase_flags = ["--testcase", testcase]
            gfilter = choose_filter(choice, testcase)
            if gfilter:
                filter_flags = ["--filter", gfilter]

    mode = select_menu("Output mode (↑/↓ + Enter):", ["normal", "quiet", "tui"]) or "normal"
    mode_flags = {"normal": [], "quiet": ["--quiet"], "tui": ["--tui"]}.get(mode, [])

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
    mode = select_menu(
        "Start with:",
        [("Sandboxed demo (no hardware)", "demo"), ("Real pto-isa tour", "real")],
    ) or "demo"
    if mode == "demo":
        return subprocess.run([str(HARNESS / "demo" / "run_demo.sh")]).returncode
    return run_real_tour()


if __name__ == "__main__":
    raise SystemExit(main())