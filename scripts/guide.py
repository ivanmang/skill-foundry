#!/usr/bin/env python3
"""Interactive, step-by-step guide through the regression harness.

Usage:
  ./harness guide            # guided tour (asks before each step)
  ./harness guide --demo     # jump straight to the sandboxed demo tour
"""

from __future__ import annotations

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
import _runs  # noqa: E402
import targets  # noqa: E402

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

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


def choose_testcase(suite: str, tdirs: dict, repo: Path) -> str:
    """Dropdown of testcases in the chosen suite; '' means run all in the suite."""
    rel = tdirs.get(suite)
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


def choose_filter(suite: str, testcase: str, tdirs: dict, repo: Path) -> str:
    """Dropdown of gtest cases in the chosen testcase; '' = no filter."""
    rel = tdirs.get(suite)
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


def check_env(target: dict) -> None:
    banner("0 · Environment check")
    repo = targets.resolve_repo(target)
    repo_env = target.get("repo_env") or "PTO_ISA_REPO"
    checks = [
        ("python3", shutil.which("python3") is not None),
        ("git", shutil.which("git") is not None),
        ("ASCEND_HOME_PATH", bool(os.environ.get("ASCEND_HOME_PATH"))),
        (f"{repo_env} / {repo.name}", bool(os.environ.get(repo_env)) or repo.exists()),
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
        print(c(f"  → checkout not found — export {repo_env}=... or clone {repo}.", YELLOW))
    print()


def choose_target_and_suites(name: str, target: dict) -> tuple[str, list[str], list[str]]:
    banner("1 · Choose what to run")

    arches = targets.load_arches(target)
    print("Arches (soc → march):")
    for arch_name, a in arches.items():
        print(f"  {arch_name:<8} {a.get('soc','-'):<18} {a.get('march') or '-'}")
    print()

    suites = target.get("suites", [])
    tdirs = target.get("testcase_dirs", {})
    repo = targets.resolve_repo(target)
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
    print(c("  ✓ = enabled+runnable   ! = enabled but missing prereqs   (blank) = disabled", BOLD))
    print(c("  npu-sim needs BOTH compile headers AND the simulator; --all-suites auto-skips the rest.", YELLOW))
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
        testcase = choose_testcase(choice, tdirs, repo)
        if testcase:
            testcase_flags = ["--testcase", testcase]
            gfilter = choose_filter(choice, testcase, tdirs, repo)
            if gfilter:
                filter_flags = ["--filter", gfilter]

    mode = select_menu("Output mode (↑/↓ + Enter):", ["normal", "quiet", "tui"]) or "normal"
    mode_flags = {"normal": [], "quiet": ["--quiet"], "tui": ["--tui"]}.get(mode, [])

    run_id = ask("Run id (blank = auto)")
    run_id_flags = ["--run-id", run_id] if run_id else []
    return name, suite_flags, mode_flags + run_id_flags + testcase_flags + filter_flags


def run_real_tour(name: str, target: dict) -> int:
    check_env(target)
    tname, suite_flags, extra_flags = choose_target_and_suites(name, target)

    banner("2 · Run the suite(s)")
    print(c("  Every run records context (git ref, dirty flag, host, env) in run.json — reproducible on any machine.", YELLOW))
    cmd = [sys.executable, "scripts/run_suite.py", "--target", tname, *suite_flags, *extra_flags]
    result = subprocess.run(cmd, cwd=HARNESS)
    if result.returncode != 0:
        print(c("\n  Some suites did not pass — we'll review next.", YELLOW))

    # Find the run we just produced (skip demo-live artifacts).
    # NOTE: use python globbing, not `ls reports/*` — ls does NOT expand globs
    # when exec'd directly (no shell), so it silently returned nothing.
    latest = None
    for _p, _data in _runs.iter_runs():
        if not _data.get("run_id", "").startswith("demo-live"):
            latest = _p.parent.name
            break

    banner("3 · Report")
    if latest:
        print(c(f"  latest run: {latest}", GREEN))
        if ask_yesno("Generate report.md/.html for it?", "y"):
            out_base = HARNESS / "reports" / latest / "report"
            known = HARNESS / ".claude" / "skills" / tname / "references" / "known-failures.md"
            kargs = ["--known", str(known)] if known.exists() else []
            subprocess.run([
                sys.executable, "scripts/build_report.py",
                "--run", str(HARNESS / "reports" / latest / "run.json"),
                *kargs, "--out", str(out_base),
            ], cwd=HARNESS, check=False)
            print(f"  → {out_base}.md / {out_base}.html")
    else:
        print(c("  (no run.json found — nothing to report)", YELLOW))

    banner("4 · Review vs baseline")
    print(c("  'Regression' = diff vs the PINNED baseline — refresh the baseline only deliberately (new suites / arch changes).", BOLD))
    print(c("  Perf: p99 > +15% flags even if average looks stable — never trust average alone.", YELLOW))
    if latest:
        print(c(f"  latest run: {latest}", GREEN))
        if ask_yesno("Diff it against the pinned baseline?", "y"):
            baseline = targets.baseline_path(tname)
            subprocess.run([
                sys.executable, "scripts/diff_runs.py",
                "--run", str(HARNESS / "reports" / latest / "run.json"),
                "--baseline", str(baseline),
            ], cwd=HARNESS, check=False)
    else:
        print(c("  (no run.json found — nothing to review)", YELLOW))

    banner("5 · Teach it (if something new failed)")
    print(c("  Capture is automatic + append-only: it writes to learnings/recent.md (your memory).", YELLOW))
    print(c("    Auto-APPEND is safe — the harness logs lessons freely, nothing else changes.", YELLOW))
    if latest and ask_yesno("Log a correction for any new failure?", "n"):
        subprocess.run([str(HARNESS / "scripts" / "teach")])

    banner("6 · Promote pending learnings")
    print(c("  Capture is automatic; promotion is HUMAN-GATED.", BOLD))
    print("    🟢 '--propose' only DRAFTS a diff (no write) — review it freely.")
    print("    🟡 '--pr' writes it on a branch + pushes + prints an MR — a reviewer merges.")
    print(c("    (Auto-edit of shared skills is NOT automatic — like Claude Code auto-writing memory\n"
            "     but never auto-editing CLAUDE.md.)", YELLOW))
    print(c("  RED line: the harness never auto-REMOVES or auto-CHANGES an existing check — it only ADDS.", RED))
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
        return subprocess.run([sys.executable, str(HARNESS / "scripts" / "demo_tour.py")]).returncode
    print(c("\n regression-harness · guided tour ", BOLD))
    mode = select_menu(
        "Start with:",
        [("Sandboxed demo (no hardware, step-by-step)", "demo"), ("Real target tour", "real")],
    ) or "demo"
    if mode == "demo":
        return subprocess.run([sys.executable, str(HARNESS / "scripts" / "demo_tour.py")]).returncode

    cfg = targets.load_config()
    names = targets.list_targets(cfg)
    if len(names) <= 1:
        tname = names[0] if names else "pto-isa"
    else:
        opts = [(targets.target_label(targets.get_target(n, cfg) or {}), n) for n in names]
        tname = select_menu("Which target?", opts) or names[0]
    return run_real_tour(tname, targets.get_target(tname, cfg) or {})


if __name__ == "__main__":
    raise SystemExit(main())