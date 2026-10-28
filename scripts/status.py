#!/usr/bin/env python3
"""One-glance dashboard: environment, suites, baseline, learnings, last run.

Usage:
  ./harness status            # human-readable dashboard
  ./harness status --json     # machine-readable
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import capabilities  # noqa: E402
import detect_cann  # noqa: E402
import _runs  # noqa: E402

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

LRN_ID_RE = re.compile(r"^## LRN-\d{8}-\d{3}", re.M)


def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if sys.stdout.isatty() else text


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pending_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        import promote_recent  # reuse its strict LRN parser
        return sum(1 for e in promote_recent.parse_entries(path.read_text(encoding="utf-8"))
                   if e.get("status") == "pending")
    except Exception:
        return 0


def promoted_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(re.findall(r"^- LRN-\d{8}-\d{3}", path.read_text(encoding="utf-8"), re.M))


def pto_isa_path() -> Path:
    return Path(os.environ.get("PTO_ISA_REPO") or "~/pto-isa").expanduser()


def collect() -> dict:
    cfg = _load(HARNESS / "config" / "suites.json")
    arches = _load(HARNESS / "config" / "arches.json")
    suites = (cfg.get("targets", {}).get("pto-isa", {}) or {}).get("suites", [])

    ascend = os.environ.get("ASCEND_HOME_PATH", "")
    ascend_version = None
    if ascend:
        try:
            ascend_version = detect_cann.analyze(Path(ascend), detect_cann.load_config())["version"]
        except Exception:
            ascend_version = "?"

    suite_rows = []
    for s in suites:
        runnable, reason = capabilities.suite_reason(s, arches)
        suite_rows.append({
            "name": s.get("name", ""),
            "mode": s.get("mode", "-"),
            "enabled": bool(s.get("enabled")),
            "runnable": runnable,
            "reason": reason,
            "milestone": s.get("milestone", ""),
        })

    baseline_path = HARNESS / "reports" / "baseline" / "baseline.json"
    baseline = _load(baseline_path)
    baseline_age = None
    if baseline.get("generated_at"):
        try:
            gen = _dt.datetime.fromisoformat(baseline["generated_at"])
            baseline_age = (_dt.datetime.now(_dt.timezone.utc) - gen).days
        except Exception:
            baseline_age = None

    last = None
    for p, data in _runs.iter_runs():
        if data.get("run_id", "").startswith("demo-live"):
            continue  # ignore sandbox demo runs when reporting "last real run"
        last = (p, data)
        break
    last_info = None
    if last:
        p, data = last
        suites_status = ", ".join(
            f"{s.get('name')}:{s.get('status')}" for s in data.get("suites", [])
        )
        last_info = {
            "run_id": data.get("run_id", p.parent.name),
            "target": data.get("target", ""),
            "suites": suites_status,
            "failed": any(s.get("status") != "PASS" for s in data.get("suites", [])),
        }

    return {
        "env": {
            "python3": bool(shutil.which("python3")),
            "git": bool(shutil.which("git")),
            "ascend": ascend,
            "ascend_version": ascend_version,
            "pto_isa": pto_isa_path().exists(),
            "pto_isa_path": str(pto_isa_path()),
        },
        "suites": suite_rows,
        "baseline": {
            "exists": baseline_path.exists(),
            "run_id": baseline.get("run_id"),
            "age_days": baseline_age,
        },
        "learnings": {
            "pending": pending_count(HARNESS / "learnings" / "recent.md"),
            "promoted": promoted_count(HARNESS / "learnings" / "promoted.md"),
        },
        "last_run": last_info,
    }


def mark(ok: bool) -> str:
    return c("✓" if ok else "✗", GREEN if ok else RED)


def render(data: dict) -> None:
    env = data["env"]
    ascend_desc = env["ascend_version"] or env["ascend"] or "not set"
    print(c(" environment", BOLD))
    print(f"  {mark(env['python3'])} python3    {mark(env['git'])} git")
    print(f"  {mark(bool(env['ascend']))} ASCEND_HOME_PATH  {c(ascend_desc, GREEN if env['ascend'] else YELLOW)}")
    print(f"  {mark(env['pto_isa'])} pto-isa  {env['pto_isa_path']}")

    print(c("\n suites (what can run here)", BOLD))
    for s in data["suites"]:
        sym = "✓" if (s["enabled"] and s["runnable"]) else ("!" if s["enabled"] else "·")
        color = GREEN if (s["enabled"] and s["runnable"]) else (YELLOW if s["enabled"] else "")
        note = "" if (s["runnable"] or not s["enabled"]) else f"  ← {s['reason']}"
        print(f"  [{c(sym, color)}] {s['name']:<14} {s['mode']:<9} {s['milestone']}{note}")

    b = data["baseline"]
    age = f"{b['age_days']}d ago" if b["age_days"] is not None else "?"
    print(c("\n baseline", BOLD))
    if b["exists"]:
        print(f"  {mark(True)} pinned ({b['run_id']}), {age} — refresh only deliberately")
    else:
        print(f"  {mark(False)} no baseline yet — run: ./harness baseline pto-isa")

    ln = data["learnings"]
    print(c("\n learnings", BOLD))
    print(f"  {ln['pending']} pending · {ln['promoted']} promoted"
          + (f"   → ./harness promote --propose" if ln["pending"] else ""))

    lr = data["last_run"]
    print(c("\n last run", BOLD))
    if lr:
        st = c("FAIL" if lr["failed"] else "PASS", RED if lr["failed"] else GREEN)
        print(f"  {lr['run_id']} · {lr['suites']} · {st}")
        print(f"  next: ./harness report --open" + ("" if lr["failed"] else "  (or ./harness review)"))
    else:
        print(f"  none yet — run: ./harness run --all-suites --quiet")

    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-glance harness status.")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args(argv)
    data = collect()
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())