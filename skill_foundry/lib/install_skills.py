#!/usr/bin/env python3
"""Make the harness skills discoverable by whichever agents are installed.

Project-level discovery already works via the repo's `.agents/skills/` symlink
(Pi / open-standard) and `.claude/skills/` (Claude Code). This command symlinks
each skill into the *user-level* skills dir of each detected agent, so the
harness's skills are always-on regardless of working directory.

Usage (via the `skills` verb):
  ./harness skills --install    # link skills into each detected agent's skills dir
  ./harness skills --uninstall  # remove the symlinks (never a real dir)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
SKILLS = HARNESS / ".claude" / "skills"

# label, parent config dir (detection), reload hint
AGENTS = [
    ("claude-code", Path.home() / ".claude", "restart Claude Code (or /reload)"),
    ("pi", Path.home() / ".pi", "/reload in Pi"),
    ("open-standard", Path.home() / ".agents", "restart the agent"),
]


def install(agent_label: str, dest_parent: Path, hint: str, args) -> int:
    dest = dest_parent / "skills"
    count = 0
    for sd in sorted(SKILLS.iterdir()):
        if not sd.is_dir() or not (sd / "SKILL.md").exists():
            continue
        link = dest / sd.name
        if args.uninstall:
            if link.is_symlink():
                link.unlink()
                print(f"  ✗ removed {link}")
                count += 1
            continue
        if args.dry_run:
            print(f"  would link {sd.name} -> {link}")
            count += 1
            continue
        dest.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.exists():
            print(f"  skip {link} (a real directory exists there)")
            continue
        link.symlink_to(sd, target_is_directory=True)
        print(f"  ✓ {link.name} -> {sd}")
        count += 1
    if count:
        print(f"    ({agent_label}: {hint})")
    return count


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Install harness skills into each detected agent's skills dir.")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be linked.")
    ap.add_argument("--uninstall", action="store_true", help="Remove harness skill symlinks.")
    args = ap.parse_args(argv)

    skill_dirs = [p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]
    if not skill_dirs:
        print(f"no skills found under {SKILLS}", file=sys.stderr)
        return 1

    total = 0
    verb = "removed" if args.uninstall else ("linked" if not args.dry_run else "would link")
    print(f"Skills ({len(skill_dirs)}) from {SKILLS}\n")
    for label, parent, hint in AGENTS:
        if parent.exists() or label == "open-standard":
            n = install(label, parent, hint, args)
            total += n
    if args.dry_run:
        print(f"dry-run: {total} link(s) would be created.")
    else:
        print(f"{total} skill link(s) {verb}.")
    print("Reload/restart the agent(s) to pick them up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())