#!/usr/bin/env python3
"""Friendly entry point for logging a correction.

Usage:
  python3 -m skill_foundry.cli.teach                                    # interactive wizard
  python3 -m skill_foundry.cli.teach "symptom -> correct -> action"       # free-text shorthand
  python3 -m skill_foundry.cli.teach "symptom -> fix"                    # 2 parts: wrong + action
  python3 -m skill_foundry.cli.teach --edit                             # open $EDITOR with a template
  python3 -m skill_foundry.cli.teach --wrong "…" --correct "…" --action "…"   # explicit flags

Smart defaults: context defaults to the latest reports/*/run.json run-id, and
skill defaults to that run's target (falling back to pto-isa). Under the hood
this delegates to log_correction.py.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import log_correction  # noqa: E402

DEFAULT_SKILL = "pto-isa"


def latest_run() -> tuple[str | None, str | None]:
    """Return (run_id, target) of the most recent reports/*/run.json."""
    best: tuple[object, str | None, str | None] | None = None
    for p in sorted((HARNESS / "reports").glob("*/run.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        key = data.get("generated_at") or str(p.stat().st_mtime)
        if best is None or key > best[0]:
            best = (key, data.get("run_id"), data.get("target"))
    return (best[1], best[2]) if best else (None, None)


def default_skill(target: str | None) -> str:
    if target and (HARNESS / ".claude" / "skills" / target / "SKILL.md").exists():
        return target
    return DEFAULT_SKILL


def split_note(note: str) -> tuple[str, str, str]:
    # Only split on arrows — semicolons/pipes are natural prose inside a segment.
    parts = [p.strip() for p in re.split(r"\s*(?:→|->)\s*", note) if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], parts[1]
    if len(parts) == 1:
        return "", parts[0], parts[0]
    return "", "", ""


def prompt(field: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            val = input(f"  {field}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)
        if val:
            return val
        if default:
            return default
        return ""


def wizard(context: str, skill: str) -> dict:
    print("Log a correction — press Enter to keep the default.\n")
    entry = {
        "category": prompt("category", "correction") or "correction",
        "context": prompt("context", context) or context or "manual",
        "skill": prompt("skill", skill) or skill or DEFAULT_SKILL,
        "wrong": prompt("what was wrong (symptom)"),
        "correct": prompt("what should happen instead"),
        "action": prompt("what to change / where"),
    }
    return entry


def edit_template(context: str, skill: str) -> dict:
    tmpl = (
        "# Log a correction. Lines starting with # are ignored.\n"
        "# wrong   = symptom / what happened\n"
        "# correct = what should happen instead\n"
        "# action  = what to change / where\n"
        f"category: correction\n"
        f"context: {context}\n"
        f"skill: {skill}\n"
        "wrong: \n"
        "correct: \n"
        "action: \n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(tmpl)
        path = f.name
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    subprocess.run([editor, path], check=False)
    txt = Path(path).read_text(encoding="utf-8")
    Path(path).unlink(missing_ok=True)

    entry: dict = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        if key.strip() in {"category", "context", "skill", "wrong", "correct", "action"}:
            entry[key.strip()] = val.strip()
    return entry


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Log a correction (friendly wrapper over log_correction.py).")
    ap.add_argument("note", nargs="?", help="Free text: 'wrong → correct → action' (or '->').")
    ap.add_argument("--edit", action="store_true", help="Open $EDITOR with a prefilled template.")
    ap.add_argument("--category", default=None)
    ap.add_argument("--context", default=None)
    ap.add_argument("--skill", default=None)
    ap.add_argument("--wrong", default=None)
    ap.add_argument("--correct", default=None)
    ap.add_argument("--action", default=None)
    ap.add_argument("--file", default=str(log_correction.DEFAULT_FILE))
    ap.add_argument("--id", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    run_id, target = latest_run()
    ctx_default = run_id or "manual"
    sk_default = default_skill(target)

    if args.edit:
        entry = edit_template(ctx_default, sk_default)
    elif args.note:
        w, c, a = split_note(args.note)
        entry = {"category": "correction", "context": ctx_default, "skill": sk_default,
                 "wrong": w, "correct": c, "action": a}
    elif any(x is not None for x in (args.wrong, args.correct, args.action)):
        entry = {"category": "correction", "context": ctx_default, "skill": sk_default,
                 "wrong": args.wrong or "", "correct": args.correct or "", "action": args.action or ""}
    else:
        entry = wizard(ctx_default, sk_default)

    # explicit flags override anything derived or entered
    if args.category is not None:
        entry["category"] = args.category
    if args.context is not None:
        entry["context"] = args.context
    if args.skill is not None:
        entry["skill"] = args.skill
    if args.wrong is not None:
        entry["wrong"] = args.wrong
    if args.correct is not None:
        entry["correct"] = args.correct
    if args.action is not None:
        entry["action"] = args.action
    if args.id is not None:
        entry["id"] = args.id

    if not any(entry.get(k) for k in ("wrong", "correct", "action")):
        print("Nothing to log (wrong/correct/action are all empty).", file=sys.stderr)
        return 1

    entry.setdefault("category", "correction")
    if args.dry_run:
        entry.setdefault("id", f"LRN-{_dt.datetime.now():%Y%m%d}-DRY")
        print(log_correction.format_entry(entry))
        return 0

    eid = log_correction.append_entry(args.file, entry)
    print(f"✓ logged {eid} ({entry.get('category', 'correction')}) → {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())