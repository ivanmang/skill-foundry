#!/usr/bin/env python3
"""`./harness learnings` — manage the learnings ledger (`learnings/recent.md`).

Subcommands:
  rotate   Archive the current `recent.md` (full history) and start a fresh one.
           Refuses if any entry is still `pending` — promote/reject first.
  status   Print pending/promoted/rejected counts (default when no subcommand).

Rotation is **append-only and versioned**: `recent.md` is moved, never deleted,
to `learnings/archive/recent-<YYYYMMDD-HHMMSS>.md`, so the audit trail (including
`rejected` entries) is preserved; the fresh `recent.md` starts with only the
standard header.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import sys

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.cli import promote  # noqa: E402

LEARNINGS = HARNESS / "learnings"
RECENT = LEARNINGS / "recent.md"
ARCHIVE = LEARNINGS / "archive"

FRESH_STUB = "# Recent — pending learnings\n\n(No entries yet.)\n"


def _entries() -> list[dict]:
    if not RECENT.exists():
        return []
    return promote.parse_entries(RECENT.read_text(encoding="utf-8"))


def _counts() -> dict[str, int]:
    c = {"pending": 0, "promoted": 0, "rejected": 0}
    for e in _entries():
        s = str(e.get("status", "pending"))
        c[s] = c.get(s, 0) + 1
    return c


def _status() -> int:
    c = _counts()
    total = sum(c.values())
    print(
        f"recent.md: {total} entries — pending {c['pending']} · "
        f"promoted {c['promoted']} · rejected {c['rejected']}"
    )
    return 0


def _rotate() -> int:
    if not RECENT.exists():
        print("recent.md does not exist — nothing to rotate.")
        return 0
    pending = _counts()["pending"]
    if pending:
        print(
            f"refusing to rotate: {pending} pending entr"
            f"{'y' if pending == 1 else 'ies'} remain — "
            f"promote or reject them first (./harness promote).",
            file=sys.stderr,
        )
        return 2
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = ARCHIVE / f"recent-{stamp}.md"
    shutil.move(str(RECENT), str(dst))
    RECENT.write_text(FRESH_STUB, encoding="utf-8")
    print(f"archived {dst.relative_to(HARNESS)}")
    print("fresh recent.md created (0 entries)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Manage the learnings ledger (recent.md).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("rotate", help="Archive recent.md (history) and start a fresh one.")
    sub.add_parser("status", help="Show pending/promoted/rejected counts.")
    args = ap.parse_args(argv)

    if args.cmd == "rotate":
        return _rotate()
    return _status()


if __name__ == "__main__":
    raise SystemExit(main())
