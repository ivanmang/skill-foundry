#!/usr/bin/env python3
"""Diagnose what's missing / broken on this machine and print the exact fix.

Usage:
  python3 -m skill_foundry.workflow.diagnose            # check everything, print ✓/✗ + fixes
  python3 -m skill_foundry.workflow.diagnose --json     # machine-readable
  python3 -m skill_foundry.workflow.diagnose --strict   # exit 1 if any issue (for CI)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

from skill_foundry.lib import capabilities  # noqa: E402
from skill_foundry.lib import targets  # noqa: E402
from skill_foundry.lib.term import GREEN, YELLOW, BOLD, c, mark  # noqa: E402


def collect_issues() -> list[dict]:
    """Return a list of findings: {check, ok, detail, fix}."""
    issues: list[dict] = []

    issues.append({
        "check": "python3",
        "ok": shutil.which("python3") is not None,
        "detail": shutil.which("python3") or "not on PATH",
        "fix": "install python3",
    })
    issues.append({
        "check": "git",
        "ok": shutil.which("git") is not None,
        "detail": shutil.which("git") or "not on PATH",
        "fix": "install git",
    })

    env_sh = HARNESS / "env.sh"
    issues.append({
        "check": "env.sh",
        "ok": env_sh.exists(),
        "detail": "present" if env_sh.exists() else "missing",
        "fix": "cp env.example.sh env.sh && edit the repo + CANN paths && source ./env.sh",
    })

    issues.append({
        "check": "compiler (clang++>=15 / g++>=13)",
        "ok": capabilities.has_compiler(),
        "detail": "clang++>=15 or g++>=13" if capabilities.has_compiler() else "neither found",
        "fix": "install clang++ (>=15) or g++ (>=13) — or run cpu-st on ecs/yellow/b10",
    })

    ascend = os.environ.get("ASCEND_HOME_PATH", "")
    issues.append({
        "check": "ASCEND_HOME_PATH",
        "ok": bool(ascend),
        "detail": ascend or "not set",
        "fix": "cp env.example.sh env.sh && source ./env.sh  (or pick one in python3 -m skill_foundry.workflow.guide)",
    })

    # per target: repo checkout + each enabled suite's prereqs
    cfg = targets.load_config()
    for name in targets.list_targets(cfg):
        t = targets.get_target(name, cfg) or {}
        repo = targets.resolve_repo(t)
        repo_env = t.get("repo_env") or "PTO_ISA_REPO"
        issues.append({
            "check": f"{name} checkout",
            "ok": repo.exists(),
            "detail": str(repo),
            "fix": f"clone to {repo} or export {repo_env}=<path>",
        })
        arches = targets.load_arches(t)
        for s in t.get("suites", []):
            if not s.get("enabled"):
                continue
            ok, reason = capabilities.suite_reason(s, arches)
            if not ok:
                mode = s.get("mode") or ""
                if mode == "cpu":
                    fix = "install clang++ (>=15) or g++ (>=13) — or run cpu-st on ecs/yellow/b10"
                elif mode in ("npu-sim", "npu", "costmodel", "comm"):
                    fix = "set ASCEND_HOME_PATH (npu-sim also needs BOTH headers and simulator — python3 -m skill_foundry.lib.cann)"
                else:
                    fix = "see python3 -m skill_foundry.workflow.run --list"
                issues.append({
                    "check": f"{name}/{s['name']}",
                    "ok": False,
                    "detail": reason,
                    "fix": fix,
                })

    # per-target pinned baseline
    for name in targets.list_targets(cfg):
        bpath = targets.baseline_path(name)
        issues.append({
            "check": f"baseline {name}",
            "ok": bpath.exists(),
            "detail": "present" if bpath.exists() else "missing",
            "fix": f"run: bash skill_foundry/workflow/baseline.sh {name}  (on a canonical machine where all suites PASS)",
        })

    return issues


def render(issues: list[dict], strict: bool) -> int:
    print(c(" diagnose", BOLD))
    bad = 0
    for it in issues:
        mark_ = mark(it["ok"])
        detail = c(it["detail"], GREEN if it["ok"] else YELLOW)
        print(f"  {mark_} {it['check']:<30} {detail}")
        if not it["ok"]:
            bad += 1
            print(f"      fix → {it['fix']}")
    print()
    if bad == 0:
        print(c("  all clear — this machine is ready to run everything it has enabled.", GREEN))
    else:
        print(c(f"  {bad} issue(s) to fix before all enabled suites can run.", YELLOW))
    return 1 if (strict and bad) else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Diagnose harness environment.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any issue (for CI).")
    args = ap.parse_args(argv)
    issues = collect_issues()
    if args.json:
        print(json.dumps({"issues": issues}, indent=2))
        return 1 if (args.strict and any(not i["ok"] for i in issues)) else 0
    return render(issues, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())