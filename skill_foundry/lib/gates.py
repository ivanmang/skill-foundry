"""Promotion gates — mechanical checks run before a skill/learning is published.

Enforced invariants (make every promotion safe):
  - **add-only**: a promotion only *adds* to the shared corpus; it never removes
    or modifies an existing check.
  - **no secrets**: token / private-key patterns are rejected.
  - **size cap**: diffs stay small and reviewable.
  - **Agent Skills spec**: promote-skill validates the new SKILL.md.

`--ci` runs the same checks against `git diff <base>...HEAD` for the CI/MR
gate, restricted to the shared-source-of-truth paths (.claude/skills + learnings).
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

from skill_foundry.paths import ROOT
from skill_foundry.lib import validate_skills

SECRET_PATTERNS = [
    re.compile(r"glpat-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"(?:sk|rk)-[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
]

MAX_DIFF_LINES = 500


def unified_diff(old: str, new: str) -> list[str]:
    return list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm=""))


def check_add_only(old: str, new: str) -> list[str]:
    violations = []
    for line in unified_diff(old, new):
        if line.startswith("-") and not line.startswith("---"):
            violations.append(f"removed/modified line: {line[1:].strip()[:80]}")
    return violations


def check_secrets(text: str) -> list[str]:
    violations = []
    for pat in SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            violations.append(f"possible secret: {m.group(0)[:24]}…")
    return violations


def check_size(old: str, new: str, max_lines: int = MAX_DIFF_LINES) -> list[str]:
    added = sum(
        1
        for line in unified_diff(old, new)
        if line.startswith("+") and not line.startswith("+++")
    )
    if added > max_lines:
        return [f"diff adds {added} lines (max {max_lines})"]
    return []


def check_skill_spec(folder: Path) -> list[str]:
    return validate_skills.validate_skill(
        folder
    ) + validate_skills.check_skill_metadata(folder)


def gate(
    old: str,
    new: str,
    skill_folder: Path | None = None,
    max_lines: int = MAX_DIFF_LINES,
) -> list[str]:
    """Run all gates on an old→new transformation. Returns [] when clean."""
    v = check_add_only(old, new) + check_secrets(new) + check_size(old, new, max_lines)
    if skill_folder is not None:
        v += check_skill_spec(skill_folder)
    return v


def ci_check(base: str = "origin/main") -> list[str]:
    """Gate the current branch's diff vs <base> (for the CI/MR gate).

    If <base> can't be resolved (no fetch), the add-only diff is skipped — the
    spec and secret checks still run on the working tree.
    """
    violations: list[str] = []
    diff = ""
    r = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            f"{base}...HEAD",
            "--",
            ".claude/skills",
            "learnings",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        diff = r.stdout
    for line in diff.splitlines():
        if line.startswith("-") and not line.startswith("---") and line[1:].strip():
            violations.append(f"removed/modified line: {line[1:].strip()[:80]}")
    violations += check_secrets(diff)
    skills_dir = ROOT / ".claude" / "skills"
    for d in sorted(skills_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            violations += validate_skills.validate_skill(
                d
            ) + validate_skills.check_skill_metadata(d)
    return violations


def _dedupe(v: list[str]) -> list[str]:
    return list(dict.fromkeys(v))


def _fix_hint(violation: str) -> str:
    if "frontmatter '" in violation and "is required" in violation:
        m = re.search(r"frontmatter '(\w+)' is required", violation)
        return f"add `{m.group(1) if m else '…'}: <value>` to the SKILL.md frontmatter"
    if "origin '" in violation and "invalid" in violation:
        return f"set `origin` to one of {sorted(validate_skills.KNOWN_ORIGINS)}"
    if "maturity '" in violation and "invalid" in violation:
        return f"set `maturity` to one of {sorted(validate_skills.KNOWN_MATURITY)}"
    if "possible secret" in violation:
        return "remove the credential/token from the content"
    if "removed/modified line" in violation:
        return "promotion is add-only — restore the line and append instead"
    if "diff adds" in violation:
        return "split into smaller, reviewable diffs"
    if "does not match parent directory" in violation:
        return "make the `name` field match the folder name"
    if "invalid" in violation and "name" in violation:
        return "rename to [a-z0-9-], no leading/trailing/consecutive hyphens"
    if "description" in violation:
        return "set a description (≤1024 chars) stating what + when"
    return ""


def violations_json(violations: list[str]) -> list[dict]:
    return [{"violation": v, "fix": _fix_hint(v)} for v in _dedupe(violations)]


def render(violations: list[str]) -> None:
    for item in violations_json(violations):
        print(f"  ✗ {item['violation']}", file=sys.stderr)
        if item["fix"]:
            print(f"    ↳ fix: {item['fix']}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Promotion gates (add-only · secrets · size · spec)."
    )
    ap.add_argument(
        "--ci", action="store_true", help="Check current branch vs a base ref (for CI)."
    )
    ap.add_argument("--base", default="origin/main", help="Base ref for --ci.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = ap.parse_args(argv)

    if args.ci:
        v = ci_check(args.base)
    else:
        data = sys.stdin.read()
        if "--- GATE-SPLIT ---" in data:
            old, _, new = data.partition("\n--- GATE-SPLIT ---\n")
        else:
            old, new = "", data
        v = gate(old, new)

    if v:
        if args.json:
            print(json.dumps({"status": "blocked", "violations": violations_json(v)}))
        else:
            for item in violations_json(v):
                print(f"✗ {item['violation']}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"status": "ok"}))
    else:
        print("gates: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
