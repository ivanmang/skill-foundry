#!/usr/bin/env python3
"""Diagnose what's missing / broken on this machine and print the exact fix.

Usage:
  ./harness diagnose            # check everything, print ✓/✗ + fixes
  ./harness diagnose --json     # machine-readable
  ./harness diagnose --strict   # exit 1 if any issue (for CI)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import capabilities  # noqa: E402
import _runs  # noqa: E402

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if sys.stdout.isatty() else text


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _mark(ok: bool) -> str:
    return c("✓" if ok else "✗", GREEN if ok else RED)


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
        "fix": "cp env.example.sh env.sh && edit PTO_ISA_REPO / ASCEND_HOME_PATH && source ./env.sh",
    })

    pto = Path(os.environ.get("PTO_ISA_REPO") or "~/pto-isa").expanduser()
    issues.append({
        "check": "pto-isa checkout",
        "ok": pto.exists(),
        "detail": str(pto),
        "fix": f"clone pto-isa to {pto} or export PTO_ISA_REPO=<path>",
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
        "fix": "cp env.example.sh env.sh && source ./env.sh  (or pick one in ./harness guide)",
    })

    # per enabled suite, check its prereqs
    cfg = _load(HARNESS / "config" / "suites.json")
    arches = _load(HARNESS / "config" / "arches.json")
    suites = (cfg.get("targets", {}).get("pto-isa", {}) or {}).get("suites", [])
    for s in suites:
        if not s.get("enabled"):
            continue
        ok, reason = capabilities.suite_reason(s, arches)
        if not ok:
            mode = s.get("mode") or ""
            if mode == "cpu":
                fix = "install clang++ (>=15) or g++ (>=13) — or run cpu-st on ecs/yellow/b10"
            elif mode in ("npu-sim", "npu", "costmodel", "comm"):
                fix = "set ASCEND_HOME_PATH (npu-sim also needs BOTH headers and simulator — ./harness cann)"
            else:
                fix = "see ./harness list"
            issues.append({
                "check": f"suite {s['name']}",
                "ok": False,
                "detail": reason,
                "fix": fix,
            })

    baseline = HARNESS / "reports" / "baseline" / "baseline.json"
    issues.append({
        "check": "pinned baseline",
        "ok": baseline.exists(),
        "detail": "present" if baseline.exists() else "missing",
        "fix": "run: ./harness baseline pto-isa  (on a canonical machine where all suites PASS)",
    })

    return issues


def render(issues: list[dict], strict: bool) -> int:
    print(c(" harness diagnose", BOLD))
    bad = 0
    for it in issues:
        mark = _mark(it["ok"])
        detail = c(it["detail"], GREEN if it["ok"] else YELLOW)
        print(f"  {mark} {it['check']:<30} {detail}")
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