#!/usr/bin/env python3
"""Make the harness skills discoverable by whichever agents are installed.

Project-level discovery already works via the repo's `.agents/skills/` symlink
(Pi / open-standard) and `.claude/skills/` (Claude Code). This command symlinks
skills into the *user-level* skills dir of each detected agent, so the harness's
skills are always-on regardless of working directory.

Selective install — you almost never want all skills always-on:

  ./harness skills --install --scope core     # the owned (origin: native) skills
  ./harness skills --install --origin native  # same, spelled out
  ./harness skills --install --category regression
  ./harness skills --install --entry          # entry points only
  ./harness skills --install --name pto-isa --name pto-vmi
  ./harness skills --uninstall                # remove ALL harness skill symlinks
  ./harness skills --uninstall --origin cannbot   # remove only the imported ones

`--scope core` is shorthand for `--origin native` (the skills skill-foundry owns).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import validate_skills  # noqa: E402

SKILLS = HARNESS / ".claude" / "skills"

_TRUTHY = {"true", "yes", "1", "on"}

# label, parent config dir (detection), reload hint
AGENTS = [
    ("claude-code", Path.home() / ".claude", "restart Claude Code (or /reload)"),
    ("pi", Path.home() / ".pi", "/reload in Pi"),
    ("open-standard", Path.home() / ".agents", "restart the agent"),
]


def agent_skill_names(parent: Path) -> list[str]:
    """Skill names visible to an agent via its user skills dir (any dir/symlink)."""
    d = parent / "skills"
    if not d.exists():
        return []
    return sorted(
        p.name for p in d.iterdir()
        if (p.is_dir() or p.is_symlink()) and not p.name.startswith(".")
    )


def select_dirs(args) -> list[Path]:
    """Return the skill dirs matching the selection flags (all when none)."""
    dirs: list[Path] = []
    need_fm = bool(args.origin or args.category or args.entry or args.maturity or args.owner)
    for sd in sorted(SKILLS.iterdir()):
        sm = sd / "SKILL.md"
        if not sd.is_dir() or not sm.exists():
            continue
        if need_fm:
            fm, _err = validate_skills.parse_frontmatter(sm.read_text(encoding="utf-8", errors="replace"))
        else:
            fm = {}
        if args.name and sd.name not in args.name:
            continue
        if args.origin and (fm.get("origin") or "").strip() != args.origin:
            continue
        if args.owner and (fm.get("owner") or "").strip() != args.owner:
            continue
        if args.maturity and (fm.get("maturity") or "ready").strip() != args.maturity:
            continue
        if args.category and (fm.get("category") or "").strip() != args.category:
            continue
        if args.entry and (fm.get("entry") or "").strip().lower() not in _TRUTHY:
            continue
        dirs.append(sd)
    return dirs


def install(agent_label: str, dest_parent: Path, hint: str, args, dirs: list[Path]) -> int:
    dest = dest_parent / "skills"
    count = 0
    for sd in dirs:
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
    ap.add_argument("--scope", choices=["core", "all"], default=None,
                    help="Preset: 'core' = the owned (origin: native) skills; 'all' = everything.")
    ap.add_argument("--origin", default=None, help="Only skills with this origin (native|cannbot).")
    ap.add_argument("--owner", default=None, help="Only skills with this owner (skill-foundry|cannbot|…).")
    ap.add_argument("--maturity", default=None, help="Only skills with this maturity (ready|draft|deprecated).")
    ap.add_argument("--category", default=None, help="Only skills in this category.")
    ap.add_argument("--entry", action="store_true", help="Only entry-point skills.")
    ap.add_argument("--name", action="append", default=None, help="Only this skill (repeatable).")
    args = ap.parse_args(argv)

    if args.scope == "core":
        args.origin = "native"

    dirs = select_dirs(args)
    if not dirs:
        print("no skills match the selection (check --origin/--category/--entry/--name)", file=sys.stderr)
        return 1

    total = 0
    verb = "removed" if args.uninstall else ("linked" if not args.dry_run else "would link")
    print(f"Skills ({len(dirs)}) from {SKILLS}\n")
    for label, parent, hint in AGENTS:
        if parent.exists() or label == "open-standard":
            total += install(label, parent, hint, args, dirs)
    if args.dry_run:
        print(f"dry-run: {total} link(s) would be created.")
    else:
        print(f"{total} skill link(s) {verb}.")
    print("Reload/restart the agent(s) to pick them up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
