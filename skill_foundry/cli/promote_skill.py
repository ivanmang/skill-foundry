#!/usr/bin/env python3
"""Promote a skill draft from hub/inbox/ into .claude/skills/ (+ MR).

Usage:
  ./harness promote-skill                 # list drafts and pick one (TTY)
  ./harness promote-skill <name> --propose   # show what would be copied
  ./harness promote-skill <name> --apply     # copy + remove draft (no commit)
  ./harness promote-skill <name> --pr        # copy + commit + push + create MR
"""

from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.cli import promote as PR  # noqa: E402 — reuse remote_web_url / create_mr
from skill_foundry.lib import browser as _browser  # noqa: E402
from skill_foundry.lib import gates  # noqa: E402
from skill_foundry.lib import reviewer  # noqa: E402

INBOX = HARNESS / "hub" / "inbox"
LIVE = HARNESS / ".claude" / "skills"


def drafts() -> list[str]:
    if not INBOX.exists():
        return []
    return sorted(d.name for d in INBOX.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote a skill draft into .claude/skills/.")
    ap.add_argument("name", nargs="?", help="Draft name (default: pick interactively).")
    ap.add_argument("--propose", action="store_true", help="Show what would be copied (no write).")
    ap.add_argument("--apply", action="store_true", help="Copy into .claude/skills/ and remove the draft.")
    ap.add_argument("--pr", action="store_true", help="--apply + commit + push + open an MR (human merges).")
    args = ap.parse_args(argv)

    names = drafts()
    if not names:
        print("No skill drafts in hub/inbox/ — run: ./harness capture-skill <name>")
        return 0

    name = args.name
    if not name:
        if not sys.stdin.isatty():
            print("drafts: " + ", ".join(names), file=sys.stderr)
            print("pass a draft name", file=sys.stderr)
            return 2
        for i, n in enumerate(names, 1):
            print(f"  {i}) {n}")
        sel = input("Pick a draft (name or number): ").strip()
        name = names[int(sel) - 1] if sel.isdigit() and 1 <= int(sel) <= len(names) else sel
    if name not in names:
        print(f"draft '{name}' not found. Drafts: {names}", file=sys.stderr)
        return 2

    src = INBOX / name
    dst = LIVE / name
    if dst.exists():
        print(f"error: {dst} already exists — remove it first", file=sys.stderr)
        return 1

    if args.propose:
        print(f"### promote {name} → .claude/skills/{name}")
        for p in sorted(src.rglob("*")):
            if p.is_file():
                print(f"  + {p.relative_to(src)}")
        print(f"  - {src.relative_to(HARNESS)} (draft removed)")
        return 0

    if not (args.apply or args.pr):
        print("choose --propose / --apply / --pr", file=sys.stderr)
        return 2

    # ── gates: spec conformance + secrets — always enforced ──
    body = (src / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    violations = list(dict.fromkeys(gates.check_skill_spec(src) + gates.check_secrets(body)))
    if violations:
        print("✗ promotion blocked by gates (fix the violation):", file=sys.stderr)
        gates.render(violations)
        return 2

    # ── review (mandatory): builtin judge + optional LLM + interactive fallback ──
    if not reviewer.approve(f"# promote skill: {name}\n\n{body}", added_text=body):
        print("✗ review did not APPROVE — nothing applied.")
        return 0

    shutil.copytree(src, dst)
    shutil.rmtree(src)
    print(f"✓ promoted {name} → {dst}")

    if args.pr:
        branch = f"feat/skill-{name}-{_dt.datetime.now():%Y%m%d}"
        subprocess.run(["git", "-C", str(HARNESS), "add", "-A",
                        str(LIVE.relative_to(HARNESS)), str(INBOX.relative_to(HARNESS))], check=True)
        subprocess.run(["git", "-C", str(HARNESS), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com",
                        "checkout", "-b", branch], check=True)
        subprocess.run(["git", "-C", str(HARNESS), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com",
                        "commit", "-m", f"feat: promote skill {name}"], check=True)
        print(f"Committed on branch '{branch}'.")
        pushed = subprocess.run(["git", "-C", str(HARNESS), "push", "-u", "origin", branch])
        if pushed.returncode == 0:
            web = PR.remote_web_url(HARNESS)
            if web:
                url, created = PR.create_mr(web, branch, "main", f"feat: promote skill {name}")
                print(f"\n{'✓ Opened merge request (human merges)' if created else 'Pushed branch. Open the MR'}:\n  {url}")
                try:
                    _browser.open_browser(url)
                except Exception:
                    pass
        else:
            print(f"\nPush failed (exit {pushed.returncode}) — push manually: git -C {HARNESS} push -u origin {branch}",
                  file=sys.stderr)
    else:
        print("  (--apply: copied locally, not committed. Use --pr to commit + open the MR.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())