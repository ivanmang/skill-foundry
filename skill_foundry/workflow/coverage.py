#!/usr/bin/env python3
"""Render skill-usage health from the agent-agnostic telemetry (.cache/metrics.jsonl).

Answers the improvement question — "which skills did the AI use / search for and
miss, and how often a human had to intervene" — from events recorded at the two
shared boundaries (MCP tools + harness verbs), not from any agent transcript.

Usage:
  python3 -m skill_foundry.workflow.coverage            # markdown to stdout
  python3 -m skill_foundry.workflow.coverage --json     # machine-readable
  python3 -m skill_foundry.workflow.coverage --write    # also write docs/SKILL_HEALTH.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import metrics  # noqa: E402

REPORT = HARNESS / "docs" / "SKILL_HEALTH.md"


def render_markdown(h: dict) -> str:
    lines = [
        "# Skill Health",
        "",
        "_Auto-generated from `.cache/metrics.jsonl` (operational telemetry — local, "
        "not committed). Regenerate with `python3 -m skill_foundry.workflow.coverage --write`._",
        "",
    ]

    # ── skills loaded (used) ──
    loads = h.get("skill_loads") or {}
    lines.append("## Skills loaded (used)")
    if loads:
        lines += ["", "| skill | loads |", "|---|---|"]
        for sk, n in sorted(loads.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| `{sk}` | {n} |")
    else:
        lines += ["", "_(no loads recorded yet)_"]
    lines.append("")

    lm = h.get("skill_load_misses") or []
    if lm:
        lines.append("### Load misses (asked for a skill that does not exist)")
        lines.append("")
        for sk, n in Counter(lm).most_common():
            lines.append(f"- `{sk}` ×{n}")
        lines.append("")

    # ── searches ──
    searches = h.get("skill_searches") or {}
    lines.append("## Skill searches")
    if searches:
        lines += ["", "| query | searches | zero-hit |", "|---|---|---|"]
        for q, s in sorted(searches.items(), key=lambda kv: -kv[1]["count"]):
            lines.append(f"| {q} | {s['count']} | {s['zero_hit']} |")
    else:
        lines += ["", "_(no searches recorded yet)_"]
    lines.append("")

    missing = h.get("missing_skill_queries") or []
    if missing:
        lines.append("## Missing skills (gap candidates → new skills)")
        lines.append("")
        for q in missing:
            lines.append(
                f"- `{q}` → `./harness capture-skill <name> --description \"…\"`"
            )
        lines.append("")

    # ── interventions ──
    inter = h.get("interventions") or {}
    by_att = inter.get("by_attribution") or {}
    lines.append("## Human interventions")
    lines += ["", f"total: {inter.get('total', 0)}"]
    if by_att:
        lines += ["", "| attribution | count |", "|---|---|"]
        for a, n in sorted(by_att.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {a} | {n} |")
        by_skill = inter.get("by_skill") or {}
        if by_skill:
            lines += ["", "| skill | interventions |", "|---|---|"]
            for sk, n in sorted(by_skill.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"| `{sk}` | {n} |")
    else:
        lines.append("")
        lines.append(
            "_(none yet — pass `--attribution` to `./harness teach`/`learn` or the MCP `teach` tool)_"
        )
    lines.append("")

    # ── daily trend ──
    by_day = (h.get("trend") or {}).get("by_day") or {}
    if by_day:
        lines.append("## Daily trend")
        lines += [
            "",
            "| day | loads | searches | interventions | captures | promotes |",
            "|---|---|---|---|---|---|",
        ]
        for day in sorted(by_day):
            d = by_day[day]
            lines.append(
                f"| {day} | {d.get('loads', 0)} | {d.get('searches', 0)} | "
                f"{d.get('interventions', 0)} | {d.get('captures', 0)} | {d.get('promotes', 0)} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render skill-usage health from agent-agnostic telemetry."
    )
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    ap.add_argument(
        "--write", action="store_true", help="Also write docs/SKILL_HEALTH.md."
    )
    args = ap.parse_args(argv)

    h = metrics.skill_health()
    if args.json:
        print(json.dumps(h, indent=2))
        return 0

    md = render_markdown(h)
    print(md)
    if args.write:
        REPORT.write_text(md, encoding="utf-8")
        print(f"✓ wrote {REPORT.relative_to(HARNESS)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
