#!/usr/bin/env python3
"""Promote pending learnings into skills / known-failures as a proposal or an edit.

Proposal (default, no writes):
  python3 scripts/promote_recent.py --propose

Apply (writes files, moves entries to promoted.md, logs to corrections.md):
  python3 scripts/promote_recent.py --apply [--branch feat/learnings-YYYYMMDD]

Target resolution:
  - action/correct mentions "known-failure(s)"/"triage corpus"  ->  known-failures.md
  - otherwise a matching .claude/skills/<skill>/SKILL.md          ->  its "## Gotchas"
  - otherwise the entry is skipped as unmapped.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import re
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
FIELD_ORDER = ["id", "category", "context", "skill", "wrong", "correct", "action", "status"]
ENTRY_RE = re.compile(r"^##\s+(LRN-\d{8}-\d{3})")


def one(s: str | None) -> str:
    return " ".join((s or "").split())


def parse_entries(text: str) -> list[dict]:
    entries: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        m = ENTRY_RE.match(line.strip())
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {"id": m.group(1)}
            continue
        if cur is not None:
            kv = re.match(r"^-\s*([a-z_]+):\s*(.*)$", line)
            if kv:
                cur[kv.group(1)] = kv.group(2).strip()
    if cur is not None:
        entries.append(cur)
    return entries


def split_header(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if ENTRY_RE.match(line.strip()):
            return "\n".join(lines[:i]), lines[i:]
    return text.rstrip(), []


def serialize_entries(entries: list[dict]) -> str:
    out: list[str] = []
    for e in entries:
        out.append(f"## {e.get('id', '?')}")
        for k in FIELD_ORDER:
            if k in e:
                out.append(f"- {k}: {e[k]}")
        out.append("")
    return "\n".join(out)


def resolve_target(e: dict, root: Path) -> Path | None:
    skill = (e.get("skill") or "").strip()
    blob = " ".join([e.get("action", ""), e.get("correct", ""), e.get("wrong", "")]).lower()
    kf = root / ".claude" / "skills" / "pto-isa" / "references" / "known-failures.md"
    if "known-failure" in blob or "triage corpus" in blob:
        return kf
    if skill and skill != "harness":
        sk = root / ".claude" / "skills" / skill / "SKILL.md"
        if sk.exists():
            return sk
    return None


def build_snippet(e: dict, target: Path) -> str:
    if target.name == "known-failures.md":
        title = one(e.get("correct") or e.get("action") or "")
        if len(title) > 72:
            title = title[:69].rstrip() + "..."
        return (
            f"\n### {title}\n"
            f"- Symptoms: {one(e.get('wrong'))}\n"
            f"- Correct: {one(e.get('correct'))}\n"
            f"- Action: {one(e.get('action'))}\n"
            f"- Seen in: {one(e.get('context'))}\n"
        )
    bullet = one(e.get("action") or e.get("correct"))
    return f"- {bullet} (was: {one(e.get('wrong'))}) — `{one(e.get('context'))}`"


def append_to_section(content: str, section: str, bullet: str) -> str:
    lines = content.splitlines()
    target = f"## {section}"
    for i, line in enumerate(lines):
        if line.strip().lower() == target.lower():
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("##"):
                j += 1
            insert_at = j
            while insert_at > i + 1 and lines[insert_at - 1].strip() == "":
                insert_at -= 1
            lines.insert(insert_at, bullet)
            return "\n".join(lines) + "\n"
    if lines and lines[-1].strip():
        lines.append("")
    lines += [target, "", bullet]
    return "\n".join(lines) + "\n"


def apply_snippet(content: str, target: Path, snippet: str) -> str:
    if target.name == "known-failures.md":
        if content and not content.endswith("\n"):
            content += "\n"
        return content + snippet
    return append_to_section(content, "Gotchas", snippet.strip())


def _append_md(path: Path, text: str) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    content = content.replace("(No entries yet.)\n", "").replace("(No entries yet.)", "")
    content = content.rstrip()
    if content:
        content += "\n\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + text, encoding="utf-8")


def _promote_log_lines(root: Path, e: dict) -> None:
    date = _dt.datetime.now().strftime("%Y-%m-%d")
    _append_md(
        root / "learnings" / "promoted.md",
        f"- {e['id']} — {e.get('skill', '?')} — {one(e.get('correct'))}\n",
    )
    _append_md(
        root / "learnings" / "corrections.md",
        f"## {date} — {e.get('skill', '?')}\n- Promoted: {e['id']}\n- Action: {one(e.get('action'))}\n",
    )


def propose_all(root: Path, lp: Path, pending: list[dict]) -> int:
    any_diff = False
    for e in pending:
        t = resolve_target(e, root)
        if t is None:
            print(f"SKIP {e['id']}: unmapped (skill={e.get('skill')!r})")
            continue
        old = t.read_text(encoding="utf-8") if t.exists() else ""
        new = apply_snippet(old, t, build_snippet(e, t))
        if new == old:
            print(f"SKIP {e['id']}: no change for {t.relative_to(root)}")
            continue
        any_diff = True
        print(f"\n### {e['id']} → {t.relative_to(root)}")
        print("\n".join(difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile=f"a/{t.relative_to(root)}", tofile=f"b/{t.relative_to(root)}", lineterm="",
        )))
    return 0 if any_diff else 2


def apply_all(root: Path, lp: Path, entries: list[dict], pending: list[dict], branch: str | None) -> int:
    changed: list[Path] = []
    for e in pending:
        t = resolve_target(e, root)
        if t is None:
            print(f"SKIP {e['id']}: unmapped")
            continue
        old = t.read_text(encoding="utf-8") if t.exists() else ""
        new = apply_snippet(old, t, build_snippet(e, t))
        if new != old:
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(new, encoding="utf-8")
            changed.append(t)
            print(f"APPLIED {e['id']} → {t.relative_to(root)}")
        e["status"] = "promoted"
        _promote_log_lines(root, e)

    header, _ = split_header(lp.read_text(encoding="utf-8"))
    lp.write_text(header.rstrip() + "\n\n" + serialize_entries(entries) + "\n", encoding="utf-8")

    if branch:
        subprocess.run(["git", "-C", str(root), "-c", "user.name=regression-harness",
                        "-c", "user.email=harness@example.com", "checkout", "-b", branch], check=True)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=regression-harness",
                        "-c", "user.email=harness@example.com", "commit",
                        "-m", f"chore: promote learnings ({len(changed)} entries)"], check=True)
        print(f"Committed on branch '{branch}' — push and open a PR for review.")

    print(f"\nPromoted {len(changed)} of {len(pending)} pending entries.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote pending learnings into skills.")
    ap.add_argument("--root", default=str(HARNESS), help="Harness root (default this repo).")
    ap.add_argument("--learnings", default=None, help="Path to recent.md (default <root>/learnings/recent.md).")
    ap.add_argument("--propose", action="store_true", help="Print proposed diffs (default).")
    ap.add_argument("--apply", action="store_true", help="Apply edits and mark entries promoted.")
    ap.add_argument("--branch", default=None, help="With --apply: create + commit on this branch.")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    lp = Path(args.learnings).resolve() if args.learnings else root / "learnings" / "recent.md"
    if not lp.exists():
        print(f"No learnings file at {lp}")
        return 0

    entries = parse_entries(lp.read_text(encoding="utf-8"))
    pending = [e for e in entries if e.get("status") == "pending"]
    if not pending:
        print("No pending entries to promote.")
        return 0

    if args.apply:
        return apply_all(root, lp, entries, pending, args.branch)
    return propose_all(root, lp, pending)


if __name__ == "__main__":
    raise SystemExit(main())