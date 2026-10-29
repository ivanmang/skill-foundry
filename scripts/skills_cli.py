#!/usr/bin/env python3
"""List/search skills and refresh the catalog.

Sources:
  - published: .claude/skills/*/SKILL.md   (live skills)
  - drafts:    skills/inbox/*/SKILL.md     (pending promotion)

Usage:
  ./harness skills                 # list all
  ./harness skills --inbox         # drafts only
  ./harness skills --search <q>    # filter by name/description/tags
  ./harness skills --refresh       # regenerate skills/catalog.json from the live skills
  ./harness skills --json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_skills  # noqa: E402 — reuse its frontmatter parser

LIVE = HARNESS / ".claude" / "skills"
INBOX = HARNESS / "skills" / "inbox"
CATALOG = HARNESS / "skills" / "catalog.json"


def collect() -> list[dict]:
    out: list[dict] = []
    for base, status in ((LIVE, "published"), (INBOX, "draft")):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            sm = d / "SKILL.md"
            if not d.is_dir() or not sm.exists():
                continue
            fm, _err = validate_skills.parse_frontmatter(sm.read_text(encoding="utf-8", errors="replace"))
            out.append({
                "name": fm.get("name") or d.name,
                "description": (fm.get("description") or "").strip(),
                "status": status,
                "path": str(d.relative_to(HARNESS)),
            })
    return out


def refresh_catalog() -> None:
    skills = [
        {"name": s["name"], "description": s["description"], "status": s["status"]}
        for s in collect()
    ]
    CATALOG.write_text(
        json.dumps({
            "version": 1,
            "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "skills": skills,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✓ catalog refreshed — {len(skills)} skill(s) → {CATALOG}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List/search skills and refresh the catalog.")
    ap.add_argument("--search", default=None, help="Filter by name/description substring.")
    ap.add_argument("--inbox", action="store_true", help="Show drafts only.")
    ap.add_argument("--refresh", action="store_true", help="Regenerate skills/catalog.json.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.refresh:
        refresh_catalog()
        return 0

    skills = collect()
    if args.inbox:
        skills = [s for s in skills if s["status"] == "draft"]
    if args.search:
        q = args.search.lower()
        skills = [s for s in skills if q in s["name"].lower() or q in s["description"].lower()]

    if args.json:
        print(json.dumps({"skills": skills}, indent=2))
        return 0

    published = [s for s in skills if s["status"] == "published"]
    drafts = [s for s in skills if s["status"] == "draft"]
    print(f"{len(published)} published · {len(drafts)} draft(s)")
    for s in skills:
        mark = "✓" if s["status"] == "published" else "◷"
        desc = s["description"].split(".", 1)[0].rstrip(".")
        print(f"  [{mark}] {s['name']:<24} {desc}")
        if s["status"] == "draft":
            print(f"       draft → ./harness promote-skill {s['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())