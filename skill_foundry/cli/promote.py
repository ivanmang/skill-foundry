#!/usr/bin/env python3
"""Promote pending learnings into skills / known-failures as a proposal or an edit.

Proposal (default, no writes):
  python3 skill_foundry/cli/promote.py --propose

Apply (writes files, marks entries promoted, logs to promoted.md + corrections.md):
  python3 skill_foundry/cli/promote.py --apply [--branch feat/learnings-YYYYMMDD]
  python3 skill_foundry/cli/promote.py --pr            # apply + push + CREATE the MR (remote-gated merge)

The `--pr` flow auto-creates the merge request via `glab` or the GitLab/GitCode
REST API (GITCODE_TOKEN / GITLAB_TOKEN); otherwise it prints the MR-new URL.
The merge itself is gated on the remote (branch protection) — not here.

Target resolution:
  - action/correct mentions "known-failure(s)"/"triage corpus"  ->  known-failures.md
  - otherwise a matching .claude/skills/<skill>/SKILL.md          ->  its "## Gotchas"
  - otherwise the entry is skipped as unmapped.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from skill_foundry.lib import browser as _browser  # noqa: E402

HARNESS = Path(__file__).resolve().parents[2]
FIELD_ORDER = ["id", "category", "context", "skill", "wrong", "correct", "action", "status"]
ENTRY_RE = re.compile(r"^##\s+(LRN-\d{8}-\d{3})")


def one(s: str | None) -> str:
    return " ".join((s or "").split())


def _norm(s: str | None) -> str:
    return one(s).lower()


def dedupe_pending(pending: list[dict], root: Path) -> tuple[list[dict], dict[str, str]]:
    active: list[dict] = []
    skipped: dict[str, str] = {}
    seen: set[str] = set()
    for e in pending:
        key = _norm(e.get("correct"))
        if key and key in seen:
            skipped[e["id"]] = "duplicate of an earlier pending entry"
            continue
        seen.add(key)
        t = resolve_target(e, root)
        if t and t.exists() and key and key in _norm(t.read_text(encoding="utf-8", errors="replace")):
            skipped[e["id"]] = f"already present in {t.relative_to(root)}"
            continue
        active.append(e)
    return active, skipped


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


def remote_web_url(root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=30)
        url = out.stdout.strip()
        if not url:
            return None
        if url.startswith("git@"):
            host, _, path = url.partition(":")
            url = f"https://{host.split('@')[-1]}/{path}"
        return url.rstrip("/").removesuffix(".git")
    except Exception:
        return None


def mr_url(web: str, branch: str, base: str = "main") -> str:
    # gitcode (GitLab-style) — matches gitcode's own "To create a merge request"
    # hint: <web>/merge_requests/new?source_branch=<branch> (no "/-" prefix).
    return f"{web}/merge_requests/new?source_branch={branch}&target_branch={base}"


def _glab_create_mr(branch: str, base: str, title: str) -> str | None:
    glab = shutil.which("glab")
    if not glab:
        return None
    try:
        r = subprocess.run(
            [glab, "mr", "create", "--source-branch", branch,
             "--target-branch", base, "--title", title, "--yes"],
            capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            m = re.search(r"https?://\S*merge_requests/\d+", (r.stdout or "") + " " + (r.stderr or ""))
            return m.group(0) if m else None
    except Exception:
        return None
    return None


def _api_create_mr(web: str, branch: str, base: str, title: str) -> str | None:
    """Create a GitLab/GitCode merge request via the REST API (PRIVATE-TOKEN)."""
    token = os.environ.get("GITCODE_TOKEN") or os.environ.get("GITLAB_TOKEN")
    if not token:
        return None
    try:
        u = urllib.parse.urlsplit(web)
        if not u.scheme or not u.netloc:
            return None
        proj = urllib.parse.quote(u.path.strip("/"), safe="")
        api = f"{u.scheme}://{u.netloc}/api/v4/projects/{proj}/merge_requests"
        payload = urllib.parse.urlencode({
            "source_branch": branch, "target_branch": base, "title": title,
        }).encode()
        req = urllib.request.Request(
            api, data=payload, method="POST",
            headers={"PRIVATE-TOKEN": token, "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("web_url")
    except Exception:
        return None


def create_mr(web: str, branch: str, base: str, title: str) -> tuple[str, bool]:
    """Create (or otherwise locate) an MR URL. Returns (url, created)."""
    url = _glab_create_mr(branch, base, title)
    if url:
        return url, True
    url = _api_create_mr(web, branch, base, title)
    if url:
        return url, True
    return mr_url(web, branch, base), False


def propose_all(root: Path, lp: Path, pending: list[dict]) -> int:
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
        print(f"\n### {e['id']} → {t.relative_to(root)}")
        print("\n".join(difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile=f"a/{t.relative_to(root)}", tofile=f"b/{t.relative_to(root)}", lineterm="",
        )))
    return 0


def apply_all(root: Path, lp: Path, entries: list[dict], pending: list[dict],
              branch: str | None, push: bool, direct: bool = False) -> int:
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

    add_paths = [str(t.relative_to(root)) for t in changed]
    add_paths += [str(lp.relative_to(root)), "learnings/promoted.md", "learnings/corrections.md"]

    if direct:
        # commit on the current branch and push to origin/main directly (SSH, no MR, no token)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com", "add", *add_paths], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com", "commit",
                        "-m", f"chore: promote learnings ({len(changed)} entries)"], check=True)
        print(f"Committed {len(changed)} file(s) on the current branch.")
        pushed = subprocess.run(["git", "-C", str(root), "push", "origin", "HEAD"])
        if pushed.returncode == 0:
            print("Pushed directly to origin/main over SSH — no MR, no token.")
        else:
            print(f"\nPush failed (exit {pushed.returncode}) — push manually:"
                  f"\n  git -C {root} push origin HEAD", file=sys.stderr)
    elif branch:
        subprocess.run(["git", "-C", str(root), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com", "checkout", "-b", branch], check=True)
        subprocess.run(["git", "-C", str(root), "add", *add_paths], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com", "commit",
                        "-m", f"chore: promote learnings ({len(changed)} entries)"], check=True)
        print(f"Committed on branch '{branch}' ({len(changed)} file(s) changed).")
        if push:
            pushed = subprocess.run(["git", "-C", str(root), "push", "-u", "origin", branch])
            if pushed.returncode == 0:
                web = remote_web_url(root)
                if web:
                    title = (f"chore: promote learnings ({len(changed)} entries) — "
                             f"{_dt.datetime.now():%Y-%m-%d}")
                    url, created = create_mr(web, branch, "main", title)
                    if created:
                        print(f"\n✓ Created merge request:\n  {url}")
                    else:
                        print(f"\nPushed branch '{branch}'. To create the MR, visit:\n  {url}\n"
                              f"  (set GITCODE_TOKEN / GITLAB_TOKEN or install glab to auto-create it)")
                    try:
                        err = _browser.open_browser(url)
                        if err:
                            print(err, file=sys.stderr)
                    except Exception:
                        pass
            else:
                print(f"\nPush failed (exit {pushed.returncode}) — push manually:"
                      f"\n  git -C {root} push -u origin {branch}", file=sys.stderr)

    print(f"\nPromoted {len(changed)} of {len(pending)} pending entries.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote pending learnings into skills.")
    ap.add_argument("--root", default=str(HARNESS), help="Harness root (default this repo).")
    ap.add_argument("--learnings", default=None, help="Path to recent.md (default <root>/learnings/recent.md).")
    ap.add_argument("--propose", action="store_true", help="Print proposed diffs (default).")
    ap.add_argument("--apply", action="store_true", help="Apply edits and mark entries promoted.")
    ap.add_argument("--branch", default=None, help="With --apply: create + commit on this branch.")
    ap.add_argument("--pr", action="store_true", help="With --apply: push the branch and create an MR (needs GITCODE_TOKEN/glab).")
    ap.add_argument("--direct", action="store_true", help="With --apply: commit on the current branch and push to origin/main directly over SSH (no MR, no token).")
    args = ap.parse_args(argv)

    if args.direct and args.pr:
        print("--direct and --pr are mutually exclusive", file=sys.stderr)
        return 2
    if args.pr:
        args.apply = True
        if not args.branch:
            args.branch = f"feat/learnings-{_dt.datetime.now():%Y%m%d}"
    if args.direct:
        args.apply = True

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

    active, skipped = dedupe_pending(pending, root)
    for e in entries:
        if e.get("id") in skipped:
            e["status"] = "rejected"
    for eid, reason in skipped.items():
        print(f"SKIP {eid}: {reason}")
    if not active:
        print("No new pending entries to promote (all duplicates / already present).")
        return 0

    if args.apply:
        return apply_all(root, lp, entries, active, args.branch, args.pr, args.direct)
    return propose_all(root, lp, active)


if __name__ == "__main__":
    raise SystemExit(main())