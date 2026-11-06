#!/usr/bin/env python3
"""Append a human/agent correction to learnings/recent.md in strict format.

Internal — prefer `./harness teach` (wizard / shorthand / editor).

Usage:
  python3 -m skill_foundry.lib.log_correction \
    --category correction --context demo-live-... --skill pto-isa \
    --wrong "device vcvt round-field mismatch" \
    --correct "known vcvt pattern; annotate instead of re-triage" \
    --action "promote vcvt round-field swap into known-failures"

The entry is assigned the next LRN-YYYYMMDD-NNN id automatically.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import uuid
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

DEFAULT_FILE = HARNESS / "learnings" / "recent.md"
CATEGORIES = {"correction", "error", "knowledge_gap", "feature"}
PLACEHOLDER = "(No entries yet.)"


def new_id() -> str:
    """Globally-unique LRN id: wall-clock + random, collision-proof across
    concurrent teammates (the old per-file counter could collide)."""
    now = _dt.datetime.now()
    return f"LRN-{now:%Y%m%d}-{now:%H%M%S}-{uuid.uuid4().hex[:8]}"


def flatten(value: str | None) -> str:
    return (value or "").replace("\r", " ").replace("\n", " ").strip()


def format_entry(entry: dict) -> str:
    return (
        f"## {entry['id']}\n"
        f"- id: {entry['id']}\n"
        f"- category: {entry['category']}\n"
        f"- context: {flatten(entry.get('context'))}\n"
        f"- skill: {flatten(entry.get('skill'))}\n"
        f"- wrong: {flatten(entry.get('wrong'))}\n"
        f"- correct: {flatten(entry.get('correct'))}\n"
        f"- action: {flatten(entry.get('action'))}\n"
        f"- status: {entry.get('status', 'pending')}\n"
    )


def append_entry(path: str | Path, entry: dict) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = (
        p.read_text(encoding="utf-8")
        if p.exists()
        else "# Recent — pending learnings\n\n(No entries yet.)\n"
    )

    entry["id"] = entry.get("id") or new_id()
    entry.setdefault("status", "pending")
    entry["category"] = (entry.get("category") or "correction").lower()

    if PLACEHOLDER in text:
        text = text.replace(f"{PLACEHOLDER}\n", "").replace(PLACEHOLDER, "")
    if text and not text.endswith("\n"):
        text += "\n"

    p.write_text(text + "\n" + format_entry(entry) + "\n", encoding="utf-8")
    return entry["id"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Log a correction to learnings/recent.md.")
    ap.add_argument("--category", default="correction", choices=sorted(CATEGORIES))
    ap.add_argument("--context", default="manual", help="Run-id or trigger.")
    ap.add_argument("--skill", default="harness", help="Target skill name.")
    ap.add_argument(
        "--wrong", default="", help="What the flow previously did / symptom."
    )
    ap.add_argument("--correct", default="", help="What it should do instead.")
    ap.add_argument("--action", default="", help="Precise edit or where to add.")
    ap.add_argument(
        "--id", default=None, help="Optional explicit LRN id (else auto-assigned)."
    )
    ap.add_argument(
        "--file",
        default=str(DEFAULT_FILE),
        help="learnings file (default learnings/recent.md).",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Print the entry without writing."
    )
    args = ap.parse_args(argv)

    entry = {
        "category": args.category,
        "context": args.context,
        "skill": args.skill,
        "wrong": args.wrong,
        "correct": args.correct,
        "action": args.action,
    }
    if args.id:
        entry["id"] = args.id

    if args.dry_run:
        entry.setdefault("id", f"LRN-{_dt.datetime.now():%Y%m%d}-DRY")
        print(format_entry(entry))
        return 0

    eid = append_entry(args.file, entry)
    print(f"Logged {eid} ({args.category}) to {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
