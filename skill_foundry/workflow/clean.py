#!/usr/bin/env python3
"""Remove run directories under reports/ (always keeps the pinned baseline).

Usage:
  python3 -m skill_foundry.workflow.clean                 # remove all run dirs
  python3 -m skill_foundry.workflow.clean --dry-run       # show what would be removed
  python3 -m skill_foundry.workflow.clean --keep 5        # keep the 5 most recent runs
"""

from __future__ import annotations

import argparse
import shutil

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Clean run directories under reports/.")
    ap.add_argument(
        "--dry-run", action="store_true", help="List what would be removed, do nothing."
    )
    ap.add_argument(
        "--keep", type=int, default=0, help="Keep the N most recent runs (default 0)."
    )
    args = ap.parse_args(argv)

    reports = HARNESS / "reports"
    if not reports.exists():
        print("No reports/ directory.")
        return 0

    dirs = sorted(
        [p for p in reports.iterdir() if p.is_dir() and p.name != "baseline"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    to_remove = dirs[args.keep :] if args.keep and args.keep > 0 else dirs

    if not to_remove:
        print("Nothing to clean.")
        return 0

    for d in to_remove:
        if args.dry_run:
            print(f"  would remove {d.name}")
        else:
            shutil.rmtree(d, ignore_errors=True)
            print(f"  removed {d.name}")
    print(
        f"\n{len(to_remove)} run dir(s) {'would be' if args.dry_run else ''} removed (baseline kept)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
