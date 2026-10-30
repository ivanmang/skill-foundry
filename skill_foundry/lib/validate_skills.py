#!/usr/bin/env python3
"""Validate SKILL.md files against the open Agent Skills spec.

Usage:
  python3 -m skill_foundry.lib.validate_skills [--root <skills-dir>] [--quiet]

Reference: https://agentskills.io/specification

Checks:
  - every skill folder has a SKILL.md
  - name: 1-64 chars, [a-z0-9-] only, no leading/trailing/consecutive hyphens,
    and MUST match the parent directory name
  - description: required, 1-1024 chars
  - compatibility: <=500 chars if present
  - license / metadata / allowed-tools: optional (parsed, not further constrained)
  - category: optional per the Agent Skills spec, but required by hub discovery —
    reported as a non-fatal warning when absent (does not affect the exit code).
  - reference integrity: every skill: URI, ../<name>/SKILL.md link and
    skills/<name>/ path reference must resolve to a local skill or a declared
    external (config/externals.json); unknown names are fatal.

Exit codes: 0 valid, 1 invalid, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
DEFAULT_ROOT = HARNESS / ".claude" / "skills"
EXTERNALS_FILE = HARNESS / "config" / "externals.json"

NAME_RE = re.compile(r"^[a-z0-9-]+$")
FRONT_RE = re.compile(r"^---\s*\n(.*?)^---\s*$", re.MULTILINE | re.DOTALL)

# Patterns that unambiguously name another skill (exclude bare backtick names —
# too noisy). `(?<![a-z0-9_-])` keeps "cannbot-skills/…" and "npu_skills/…" from
# matching the literal "skills/".
REF_PATTERNS = (
    re.compile(r"skill:([a-z0-9][a-z0-9-]*)"),
    re.compile(r"\.\./([a-z0-9][a-z0-9-]*)/SKILL\.md"),
    re.compile(r"(?<![a-z0-9_-])skills/([a-z0-9][a-z0-9-]*)/"),
)


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


def load_external_names(path: Path = EXTERNALS_FILE) -> set[str]:
    """Return the declared external skill names (empty when no manifest)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    skills = data.get("skills") if isinstance(data, dict) else None
    return {str(n) for n in skills} if isinstance(skills, dict) else set()


def check_references(root: Path, externals: set[str] | None = None) -> list[str]:
    """Return dangling cross-skill reference violations.

    Scans SKILL.md and references/*.md for ``skill:`` URIs, ``../<name>/SKILL.md``
    links and ``skills/<name>/`` path references. Each referenced name must be a
    local skill or a declared external; anything else is a dangling reference.
    """
    if externals is None:
        externals = load_external_names()
    local = {d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")}
    errors: list[str] = []
    for sk in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        files = [sk / "SKILL.md"]
        refdir = sk / "references"
        if refdir.is_dir():
            files += sorted(refdir.glob("*.md"))
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            for pat in REF_PATTERNS:
                for m in pat.finditer(text):
                    name = m.group(1)
                    if name in local or name in externals:
                        continue
                    errors.append(
                        f"{sk.name}: reference to unknown skill '{name}' in {f.name} "
                        "(declare it in config/externals.json if external)")
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
    all_warnings: list[str] = []
    for d in skill_dirs:
        errs = validate_skill(d)
        if errs:
            all_errors.extend(errs)
        sm = d / "SKILL.md"
        if sm.exists():
            fm, _err = parse_frontmatter(sm.read_text(encoding="utf-8", errors="replace"))
            if not (fm.get("category") or "").strip():
                all_warnings.append(
                    f"{d.name}: frontmatter 'category' is missing "
                    "(optional per spec, but required by hub discovery)")

    ref_errors = check_references(root)

    if not args.quiet:
        for w in all_warnings:
            print(f"  ⚠ {w}")

    total_issues = len(all_errors) + len(ref_errors)
    if total_issues:
        print(f"skill validation: {total_issues} issue(s) across {len(skill_dirs)} skill(s)")
        for e in all_errors:
            print(f"  ✗ {e}")
        for e in ref_errors:
            print(f"  ✗ {e}")
        return 1

    if not args.quiet:
        print(f"skill validation: OK — {len(skill_dirs)} skill(s) valid "
              "(spec + reference integrity)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())