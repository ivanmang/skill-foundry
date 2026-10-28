#!/usr/bin/env python3
"""Validate SKILL.md files against the open Agent Skills spec.

Usage:
  python3 scripts/validate_skills.py [--root <skills-dir>] [--quiet]

Reference: https://agentskills.io/specification

Checks:
  - every skill folder has a SKILL.md
  - name: 1-64 chars, [a-z0-9-] only, no leading/trailing/consecutive hyphens,
    and MUST match the parent directory name
  - description: required, 1-1024 chars
  - compatibility: <=500 chars if present
  - license / metadata / allowed-tools: optional (parsed, not further constrained)

Exit codes: 0 valid, 1 invalid, 2 usage.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = HARNESS / ".claude" / "skills"

NAME_RE = re.compile(r"^[a-z0-9-]+$")
FRONT_RE = re.compile(r"^---\s*\n(.*?)^---\s*$", re.MULTILINE | re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str | None]:
    """Return ({key: value}, error). Handles inline scalars and block scalars."""
    m = FRONT_RE.search(text)
    if not m:
        return {}, "missing YAML frontmatter (--- ... ---)"
    body = m.group(1)
    out: dict[str, str] = {}
    i = 0
    lines = body.splitlines()
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line[:1] in (" ", "\t"):
            i += 1  # continuation of an unparsed nested block (e.g. metadata)
            continue
        kv = re.match(r"^([A-Za-z0-9_-]+):(.*)$", line)
        if not kv:
            i += 1
            continue
        key = kv.group(1).strip()
        rest = kv.group(2).strip()
        if rest in (">", "|", ">-", "|-"):
            # block scalar: collect indented continuation lines
            buf = []
            j = i + 1
            while j < n and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
                if lines[j].strip():
                    buf.append(lines[j].strip())
                j += 1
            out[key] = (" " if rest[0] == ">" else "\n").join(buf)
            i = j
            continue
        out[key] = rest
        i += 1
    return out, None


def validate_skill(folder: Path) -> list[str]:
    errors: list[str] = []
    sm = folder / "SKILL.md"
    if not sm.exists():
        return [f"{folder.name}: SKILL.md missing"]

    text = sm.read_text(encoding="utf-8", errors="replace")
    fm, err = parse_frontmatter(text)
    if err:
        return [f"{folder.name}: {err}"]

    name = fm.get("name", "").strip()
    desc = fm.get("description", "").strip()

    # name
    if not name:
        errors.append(f"{folder.name}: frontmatter 'name' is required")
    else:
        if len(name) > 64:
            errors.append(f"{folder.name}: name '{name}' exceeds 64 chars")
        if not NAME_RE.match(name) or name.startswith("-") or name.endswith("-") or "--" in name:
            errors.append(
                f"{folder.name}: name '{name}' invalid — must be [a-z0-9-], no leading/trailing/consecutive hyphens")
        if name != folder.name:
            errors.append(f"{folder.name}: name '{name}' does not match parent directory")

    # description
    if not desc:
        errors.append(f"{folder.name}: frontmatter 'description' is required")
    elif len(desc) > 1024:
        errors.append(f"{folder.name}: description is {len(desc)} chars (max 1024)")

    # compatibility
    if "compatibility" in fm and fm["compatibility"] is not None:
        if len(fm["compatibility"].strip()) > 500:
            errors.append(f"{folder.name}: compatibility exceeds 500 chars")

    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate SKILL.md files against the Agent Skills spec.")
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="Path to the skills dir (default .claude/skills).")
    ap.add_argument("--quiet", action="store_true", help="Only print errors.")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"skills dir not found: {root}")
        return 2

    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not skill_dirs:
        print("no skill folders found")
        return 1

    all_errors: list[str] = []
    for d in skill_dirs:
        errs = validate_skill(d)
        if errs:
            all_errors.extend(errs)

    if all_errors:
        print(f"skill conformance: {len(all_errors)} issue(s) in {len(skill_dirs)} skill(s)")
        for e in all_errors:
            print(f"  ✗ {e}")
        return 1

    if not args.quiet:
        print(f"skill conformance: OK — {len(skill_dirs)} skill(s) valid per agentskills.io/specification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())