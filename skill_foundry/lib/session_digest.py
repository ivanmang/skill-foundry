#!/usr/bin/env python3
"""Draft pending learnings from a run record (auto-capture assistant).

Scans a run.json for FAILed cases and emits strict-format entries for anything
not already logged in the learnings file. With --apply it appends them.

Usage:
  python3 -m skill_foundry.lib.session_digest --run reports/<id>/run.json           # print drafts
  python3 -m skill_foundry.lib.session_digest --run reports/<id>/run.json --apply   # append
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from skill_foundry.lib import log_correction  # noqa: E402

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402


def draft_entries(record: dict) -> list[dict]:
    out: list[dict] = []
    run_id = record.get("run_id", "unknown")
    target = record.get("target", "pto-isa")
    for s in record.get("suites", []):
        results = s.get("results") or {}
        for c in results.get("cases", []):
            if c.get("status") != "FAIL":
                continue
            name = c.get("name", "")
            out.append(
                {
                    "category": "error",
                    "context": run_id,
                    "skill": target,
                    "wrong": f"case {name} failed in suite {s.get('name')}",
                    "correct": "triage manually; if reusable, promote to known-failures",
                    "action": f"triage {name}; add to known-failures if reusable",
                }
            )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draft pending learnings from a run.json.")
    ap.add_argument("--run", required=True, help="run.json to scan for failures.")
    ap.add_argument("--file", default=str(HARNESS / "learnings" / "recent.md"))
    ap.add_argument(
        "--apply", action="store_true", help="Append drafts via log_correction."
    )
    args = ap.parse_args(argv)

    record = json.loads(Path(args.run).read_text(encoding="utf-8"))
    existing = (
        Path(args.file).read_text(encoding="utf-8") if Path(args.file).exists() else ""
    )
    drafts = draft_entries(record)
    new = [d for d in drafts if d["wrong"] not in existing]

    if not new:
        print("No new FAIL cases to draft (all already logged).")
        return 0

    for d in new:
        entry = {**d, "id": log_correction.new_id(), "status": "pending"}
        if args.apply:
            log_correction.append_entry(args.file, dict(entry))
        else:
            print(log_correction.format_entry(entry))

    print(f"\n{len(new)} draft(s) {'appended' if args.apply else 'printed'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
