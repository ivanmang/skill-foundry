#!/usr/bin/env python3
"""One-command capture → promote → (optional) PR.

The missing UX for the skill-ops loop: a single verb that logs a correction,
then runs the gated promotion (mechanical gates + SKILL_REVIEWER) and, with
`--pr`, pushes a branch and opens the MR.

Usage:
  ./harness learn "symptom -> fix -> where"          # teach + promote --apply (local)
  ./harness learn "symptom -> fix -> where" --pr     # teach + promote --apply + push + MR
  ./harness learn --wrong "…" --correct "…" --action "…" --propose
"""

from __future__ import annotations

import argparse
import sys

from skill_foundry.cli import promote, teach  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Capture a correction and promote it in one command.")
    ap.add_argument("note", nargs="?", help="Free text: 'wrong → correct → action' (or '->').")
    ap.add_argument("--wrong", default=None)
    ap.add_argument("--correct", default=None)
    ap.add_argument("--action", default=None)
    ap.add_argument("--skill", default=None)
    ap.add_argument("--context", default=None)
    ap.add_argument("--category", default=None)
    ap.add_argument("--branch", default=None)
    ap.add_argument("--file", default=None, help="Learnings file (forwards to teach --file / promote --learnings).")
    ap.add_argument("--propose", action="store_true", help="Stop after printing the proposed diff.")
    ap.add_argument("--apply", action="store_true", help="Apply locally (no commit/push) — default.")
    ap.add_argument("--pr", action="store_true", help="Apply + push a branch + open an MR.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON where supported.")
    args = ap.parse_args(argv)

    if args.note is None and all(getattr(args, f) is None for f in ("wrong", "correct", "action")):
        ap.print_usage(sys.stderr)
        print("learn: provide a note or --wrong/--correct/--action.", file=sys.stderr)
        return 2

    teach_argv: list[str] = []
    if args.note is not None:
        teach_argv.append(args.note)
    for flag, attr in (
        ("--wrong", "wrong"), ("--correct", "correct"), ("--action", "action"),
        ("--skill", "skill"), ("--context", "context"), ("--category", "category"),
    ):
        val = getattr(args, attr)
        if val is not None:
            teach_argv += [flag, val]
    if args.file is not None:
        teach_argv += ["--file", args.file]
    if args.json:
        teach_argv.append("--json")

    rc = teach.main(teach_argv)
    if rc != 0:
        return rc

    if args.propose:
        promo_argv = ["--propose"]
        if args.file is not None:
            promo_argv += ["--learnings", args.file]
        if args.json:
            promo_argv.append("--json")
        return promote.main(promo_argv)
    if args.pr:
        promo_argv = ["--pr"]
        if args.branch:
            promo_argv += ["--branch", args.branch]
    else:
        promo_argv = ["--apply"]
    if args.file is not None:
        promo_argv += ["--learnings", args.file]
    if args.json:
        promo_argv.append("--json")
    return promote.main(promo_argv)


if __name__ == "__main__":
    raise SystemExit(main())
