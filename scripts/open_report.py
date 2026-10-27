#!/usr/bin/env python3
"""Open the report.html for a run (generates it first if needed).

Usage:
  ./harness open               # latest run
  ./harness open <run-id>      # a specific run
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _runs  # noqa: E402

HARNESS = Path(__file__).resolve().parent.parent
KNOWN = HARNESS / ".claude" / "skills" / "pto-isa" / "references" / "known-failures.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Open a run's report.html in the browser.")
    ap.add_argument("run_id", nargs="?", help="Run id (default: latest).")
    args = ap.parse_args(argv)

    if args.run_id:
        run_json = HARNESS / "reports" / args.run_id / "run.json"
        run_id = args.run_id
    else:
        latest = _runs.latest_run()
        if not latest:
            print("No runs found under reports/.", file=sys.stderr)
            return 1
        run_json, _ = latest
        run_id = run_json.parent.name

    if not run_json.exists():
        print(f"Run '{run_id}' not found.", file=sys.stderr)
        return 1

    html = run_json.parent / "report.html"
    if not html.exists():
        subprocess.run([
            sys.executable, "scripts/build_report.py",
            "--run", str(run_json), "--known", str(KNOWN),
            "--out", str(run_json.parent / "report"),
        ], cwd=HARNESS, check=False)

    opener = shutil.which("xdg-open") or shutil.which("open") or shutil.which("start")
    if opener:
        subprocess.run([opener, str(html)], check=False)
    print(f"Report: {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())