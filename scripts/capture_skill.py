#!/usr/bin/env python3
"""Capture a NEW skill draft into skills/inbox/ for later promotion.

Usage:
  ./harness capture-skill <name>                 # wizard (description + editor for body)
  ./harness capture-skill <name> --description "…"   # skip the description prompt
  ./harness capture-skill <name> --dry-run       # print the SKILL.md without writing
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
INBOX = HARNESS / "skills" / "inbox"
LIVE = HARNESS / ".claude" / "skills"
NAME_RE = re.compile(r"^[a-z0-9-]+$")
LICENSE = "CANN Open Software License Agreement Version 2.0"


def valid_name(name: str) -> str | None:
    if not name or len(name) > 64 or not NAME_RE.match(name):
        return "name must be 1-64 chars, [a-z0-9-], no leading/trailing/consecutive hyphens"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return "name must not start/end with a hyphen or contain consecutive hyphens"
    if (LIVE / name).exists():
        return f"a published skill already exists at {LIVE / name}"
    if (INBOX / name).exists():
        return f"a draft already exists at {INBOX / name}"
    return None


def prompt(field: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        return input(f"  {field}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def editor_for_body(name: str) -> str:
    tmpl = (
        f"# {name}\n\n"
        "# Write the skill instructions below (Markdown). Lines starting with #\n"
        "# in the body are kept as-is; the frontmatter is added for you.\n"
        "\n"
        "## When to use\n"
        "…\n\n"
        "## Steps\n"
        "1. …\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(tmpl)
        path = f.name
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    subprocess.run([editor, path], check=False)
    body = Path(path).read_text(encoding="utf-8")
    Path(path).unlink(missing_ok=True)
    # drop the leading "# <name>" and the guidance comment block (lines starting with #)
    lines = []
    for line in body.splitlines():
        if line.strip() == f"# {name}":
            continue
        if line.strip().startswith("# Write the skill instructions"):
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def render_skill(name: str, description: str, body: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"license: {LICENSE}\n"
        "metadata:\n"
        "  status: draft\n"
        "---\n\n"
        f"{body.strip()}\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Capture a new skill draft into skills/inbox/.")
    ap.add_argument("name", nargs="?", help="Skill name (lowercase-hyphen).")
    ap.add_argument("--description", default=None, help="Description (what + when to use).")
    ap.add_argument("--body", default=None, help="Instructions body (Markdown); skips the editor.")
    ap.add_argument("--dry-run", action="store_true", help="Print the SKILL.md without writing.")
    args = ap.parse_args(argv)

    name = args.name or prompt("Skill name (lowercase-hyphen)")
    err = valid_name(name)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    description = args.description or prompt("Description (what it does + when to use)")
    if not description.strip():
        print("error: description is required", file=sys.stderr)
        return 2
    if len(description) > 1024:
        print(f"error: description exceeds 1024 chars ({len(description)})", file=sys.stderr)
        return 2

    if args.body is not None:
        body = args.body
    elif args.description and not sys.stdin.isatty():
        # non-interactive with --description: empty body is acceptable
        body = ""
    else:
        body = editor_for_body(name)

    text = render_skill(name, description.strip(), body)

    if args.dry_run:
        print(text)
        return 0

    dest = INBOX / name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "SKILL.md").write_text(text, encoding="utf-8")
    print(f"✓ captured draft → {dest / 'SKILL.md'}")
    print(f"  next: ./harness promote-skill {name} --propose   (then --pr to create the MR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())