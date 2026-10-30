#!/usr/bin/env python3
"""Interactive, step-by-step guide through the regression workflow (a tour).

Usage:
  python3 -m skill_foundry.workflow.guide            # guided tour (asks before each step)
  python3 -m skill_foundry.workflow.guide --demo     # jump straight to the sandboxed demo tour
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import capabilities  # noqa: E402
from skill_foundry.lib import runs as _runs  # noqa: E402
from skill_foundry.lib import targets  # noqa: E402
from skill_foundry.lib import ui  # noqa: E402


def check_env(target: dict) -> None:
    ui.banner("0 · Environment check")
    repo = targets.resolve_repo(target)
    repo_env = target.get("repo_env") or "PTO_ISA_REPO"
    checks = [
        ("python3", shutil.which("python3") is not None),
        ("git", shutil.which("git") is not None),
        ("ASCEND_HOME_PATH", bool(os.environ.get("ASCEND_HOME_PATH"))),
        (f"{repo_env} / {repo.name}", bool(os.environ.get(repo_env)) or repo.exists()),
    ]
    for name, ok in checks:
        mark = ui.c("✓", ui.GREEN) if ok else ui.c("✗", ui.RED)
        print(f"  {mark}  {name}")
    if not checks[2][1]:
        chosen = ui.choose_cann()
        if chosen:
            os.environ["ASCEND_HOME_PATH"] = chosen
            print(ui.c(f"  ✓  using {chosen}", ui.GREEN))
        else:
            print(ui.c("  → npu/costmodel/comm suites need ASCEND_HOME_PATH — pick a CANN above or source ./env.sh.", ui.YELLOW))
    if not checks[3][1]:
        print(ui.c(f"  → checkout not found — export {repo_env}=... or clone {repo}.", ui.YELLOW))
    print()


def choose_target_and_suites(name: str, target: dict) -> tuple[str, list[str], list[str]]:
    ui.banner("1 · Choose what to run")

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
    print(ui.c("  ✓ = enabled+runnable   ! = enabled but missing prereqs   (blank) = disabled", ui.BOLD))
    print(ui.c("  npu-sim needs BOTH compile headers AND the simulator; --all-suites auto-skips the rest.", ui.YELLOW))
    choice = ui.select_menu("Choose a suite (↑/↓ + Enter):", options) or "all"

    if choice == "all":
        suite_flags = ["--all-suites"]
    else:
        suite_flags = ["--suite", choice]
        for s in suites:
            if s["name"] == choice:
                runnable, reason = capabilities.suite_reason(s, arches)
                if not runnable:
                    print(ui.c(f"  ⚠  {choice}: {reason} — it will ERROR when run.", ui.YELLOW))
                break

    testcase_flags: list[str] = []
    filter_flags: list[str] = []
    if choice.lower() not in ("all", ""):
        smap = {s["name"]: s for s in suites}
        suite_obj = smap.get(choice) or {}
        testcase = ui.choose_testcase(choice, tdirs, repo, suite_obj.get("testcase_kind", "dir"))
        if testcase:
            testcase_flags = ["--testcase", testcase]
            gfilter = ui.choose_filter(choice, testcase, tdirs, repo)
            if gfilter:
                filter_flags = ["--filter", gfilter]

    mode = ui.select_menu("Output mode (↑/↓ + Enter):", ["normal", "quiet", "tui"]) or "normal"
    mode_flags = {"normal": [], "quiet": ["--quiet"], "tui": ["--tui"]}.get(mode, [])

    run_id = ui.ask("Run id (blank = auto)")
    run_id_flags = ["--run-id", run_id] if run_id else []
    return name, suite_flags, mode_flags + run_id_flags + testcase_flags + filter_flags


def pending_learning_count() -> int:
    """Number of status:pending entries in learnings/recent.md (0 if none/missing)."""
    try:
        from skill_foundry.cli import promote as promote_recent
        p = HARNESS / "learnings" / "recent.md"
        if not p.exists():
            return 0
        return sum(1 for e in promote_recent.parse_entries(p.read_text(encoding="utf-8"))
                   if e.get("status") == "pending")
    except Exception:
        return 0


def run_real_tour(name: str, target: dict) -> int:
    check_env(target)
    tname, suite_flags, extra_flags = choose_target_and_suites(name, target)

    ui.banner("2 · Run the suite(s)")
    print(ui.c("  Every run records context (git ref, dirty flag, host, env) in run.json — reproducible on any machine.", ui.YELLOW))
    cmd = [sys.executable, "-m", "skill_foundry.workflow.run", "--target", tname, *suite_flags, *extra_flags]
    result = subprocess.run(cmd, cwd=HARNESS)
    if result.returncode != 0:
        print(ui.c("\n  Some suites did not pass — we'll review next.", ui.YELLOW))

    latest = None
    for _p, _data in _runs.iter_runs():
        if not _data.get("run_id", "").startswith("demo-live"):
            latest = _p.parent.name
            break

    ui.banner("3 · Report")
    if latest:
        print(ui.c(f"  latest run: {latest}", ui.GREEN))
        if ui.ask_yesno("Generate report.md/.html for it?", "y"):
            out_base = HARNESS / "reports" / latest / "report"
            known = HARNESS / ".claude" / "skills" / tname / "references" / "known-failures.md"
            kargs = ["--known", str(known)] if known.exists() else []
            subprocess.run([
                sys.executable, "-m", "skill_foundry.workflow.report",
                "--run", str(HARNESS / "reports" / latest / "run.json"),
                *kargs, "--out", str(out_base), "--open",
            ], cwd=HARNESS, check=False)
            print(f"  → {out_base}.md / {out_base}.html")
    else:
        print(ui.c("  (no run.json found — nothing to report)", ui.YELLOW))

    ui.banner("4 · Review vs baseline")
    print(ui.c("  'Regression' = diff vs the PINNED baseline — refresh the baseline only deliberately (new suites / arch changes).", ui.BOLD))
    print(ui.c("  Perf: p99 > +15% flags even if average looks stable — never trust average alone.", ui.YELLOW))
    if latest:
        print(ui.c(f"  latest run: {latest}", ui.GREEN))
        if ui.ask_yesno("Diff it against the pinned baseline?", "y"):
            baseline = targets.baseline_path(tname)
            subprocess.run([
                sys.executable, "-m", "skill_foundry.workflow.review",
                "--run", str(HARNESS / "reports" / latest / "run.json"),
                "--baseline", str(baseline),
            ], cwd=HARNESS, check=False)
    else:
        print(ui.c("  (no run.json found — nothing to review)", ui.YELLOW))

    ui.banner("5 · Teach it (if something new failed)")
    print(ui.c("  Capture is automatic + append-only: it writes to learnings/recent.md (your memory).", ui.YELLOW))
    print(ui.c("    Auto-APPEND is safe — the harness logs lessons freely, nothing else changes.", ui.YELLOW))
    if latest and ui.ask_yesno("Log a correction for any new failure?", "n"):
        subprocess.run([sys.executable, "-m", "skill_foundry.cli.teach"], cwd=HARNESS)

    ui.banner("6 · Promote pending learnings")
    print(ui.c("  Capture is automatic; promotion is AUTO — `--direct` pushes to main (no token), `--pr` opens an MR.", ui.BOLD))
    print("    🟢 '--propose' DRAFTS a diff (no write) — optional review.")
    print("    🟢 '--direct' applies + commits + pushes straight to origin/main (no token).")
    print("    🟢 '--pr' applies + branch + push + AUTO-CREATES the MR (glab / GITCODE_TOKEN).")
    print("    🟡 with `--pr`, you merge the MR on the remote (branch protection gates it).")
    print(ui.c("  RED line: the harness never auto-REMOVES or auto-CHANGES an existing check — it only ADDS.", ui.RED))
    pending = pending_learning_count()
    if pending == 0:
        print(ui.c("  no pending learnings — nothing to promote. (./harness teach \"…\" to capture one)", ui.YELLOW))
    else:
        print(ui.c(f"  {pending} pending learning(s) ready to promote.", ui.GREEN))
        if ui.ask_yesno("Promote them?", "y"):
            if ui.ask_yesno("Push straight to main (--direct)? (n = --pr for an MR)", "y"):
                subprocess.run([sys.executable, "-m", "skill_foundry.cli.promote", "--direct"], cwd=HARNESS)
            else:
                subprocess.run([sys.executable, "-m", "skill_foundry.cli.promote", "--pr"], cwd=HARNESS)

    nxt = "python3 -m skill_foundry.workflow.run --all-suites --quiet" + ("  and  ./harness promote --direct" if pending else "")
    print(ui.c(f"\n✓ Done. Next time: {nxt}", ui.GREEN))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--demo" in args:
        return subprocess.run([sys.executable, "-m", "skill_foundry.workflow.demo"], cwd=HARNESS).returncode
    print(ui.c("\n skill-foundry · guided tour ", ui.BOLD))
    mode = ui.select_menu(
        "Start with:",
        [("Sandboxed demo (no hardware, step-by-step)", "demo"), ("Real target tour", "real")],
    ) or "demo"
    if mode == "demo":
        return subprocess.run([sys.executable, "-m", "skill_foundry.workflow.demo"], cwd=HARNESS).returncode

    cfg = targets.load_config()
    names = targets.list_targets(cfg)
    if len(names) <= 1:
        tname = names[0] if names else "pto-isa"
    else:
        opts = [(targets.target_label(targets.get_target(n, cfg) or {}), n) for n in names]
        tname = ui.select_menu("Which target?", opts) or names[0]
    return run_real_tour(tname, targets.get_target(tname, cfg) or {})


if __name__ == "__main__":
    raise SystemExit(main())