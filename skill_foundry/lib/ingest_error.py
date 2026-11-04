#!/usr/bin/env python3
"""Draft an LRN entry from a build/test log's first concrete error line.

Best-effort companion to the pto-isa ST runners: `run_st.py` / `run_cpu.py`
invoke this on failure so compile/link errors become pending learnings without
an agent in the loop. The entry is only a *draft* — `./harness promote` still
gates and reviews it before anything reaches a skill.

Usage:
  python3 -m skill_foundry.lib.ingest_error --log build.log --skill pto-isa --apply
  <build log> | python3 -m skill_foundry.lib.ingest_error --log - --skill pto-isa --apply
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

from skill_foundry.lib import log_correction  # noqa: E402
from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

DEFAULT_FILE = HARNESS / "learnings" / "recent.md"

ERROR_PATTERNS = [
    re.compile(r"\berror:", re.I),
    re.compile(r"no matching function for call to", re.I),
    re.compile(r"undefined reference to", re.I),
    re.compile(r"fatal error:|cannot open source file", re.I),
    re.compile(r"does not support the given target feature", re.I),
    re.compile(r"\bbuild failed\b|\brun failed\b", re.I),
]


def extract_first_error(text: str) -> str | None:
    """Return the first likely root-cause line, or None if nothing looks like an error."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(p.search(stripped) for p in ERROR_PATTERNS):
            return stripped[:240]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:240]
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draft a learning from a build/test log.")
    ap.add_argument("--log", default="-", help="Log file path, or '-' to read stdin.")
    ap.add_argument("--skill", default="pto-isa", help="Target skill name.")
    ap.add_argument("--context", default=None, help="Run-id or trigger label.")
    ap.add_argument("--apply", action="store_true", help="Append the draft (default: print only).")
    ap.add_argument("--file", default=str(DEFAULT_FILE), help="learnings file (default learnings/recent.md).")
    args = ap.parse_args(argv)

    if args.log == "-":
        text = sys.stdin.read()
    else:
        p = Path(args.log)
        text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    error = extract_first_error(text)
    if not error:
        print("ingest_error: no error line found.", file=sys.stderr)
        return 0

    existing = Path(args.file).read_text(encoding="utf-8") if Path(args.file).exists() else ""
    if error in existing:
        print(f"ingest_error: already logged ({error[:80]}).", file=sys.stderr)
        return 0

    entry = {
        "category": "error",
        "context": args.context or f"{_dt.datetime.now():%Y-%m-%d} auto-capture",
        "skill": args.skill,
        "wrong": error,
        "correct": "triage manually; if reusable, promote to known-failures",
        "action": f"triage build/test failure: {error}",
    }

    if args.apply:
        eid = log_correction.append_entry(args.file, entry)
        print(f"ingest_error: logged {eid}", file=sys.stderr)
    else:
        print(log_correction.format_entry({**entry, "id": "LRN-YYYYMMDD-NNN", "status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
