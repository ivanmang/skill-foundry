#!/usr/bin/env python3
"""List recent runs with a per-suite pass/fail summary.

Usage:
  ./harness history               # recent runs, newest first
  ./harness history --limit 10
  ./harness history --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _runs  # noqa: E402


def suite_summary(data: dict) -> str:
    parts = []
    for s in data.get("suites", []):
        parts.append(f"{s.get('name')}:{s.get('status', '?')}")
    return " ".join(parts) if parts else "-"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List recent runs.")
    ap.add_argument("--limit", "-n", type=int, default=20, help="Max runs to show (default 20).")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args(argv)

    runs = _runs.iter_runs()[: args.limit]
    if not runs:
        print("No runs found under reports/.", file=sys.stderr)
        return 1

    if args.json:
        out = [
            {"run_id": d.get("run_id"), "target": d.get("target"),
             "generated_at": d.get("generated_at"), "host": d.get("host"),
             "suites": [{"name": s.get("name"), "status": s.get("status")} for s in d.get("suites", [])]}
            for _, d in runs
        ]
        print(json.dumps(out, indent=2))
        return 0

    print(f"{'run_id':<26} {'target':<10} {'date':<20} suites")
    for _, d in runs:
        print(f"{d.get('run_id','?'):<26} {d.get('target','?'):<10} "
              f"{(d.get('generated_at') or '')[:19]:<20} {suite_summary(d)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())