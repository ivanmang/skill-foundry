#!/usr/bin/env python3
"""Promote pending learnings into skills / known-failures as a proposal or an edit.

Proposal (default, no writes):
  python3 -m skill_foundry.cli.promote --propose

Apply (gated + LLM-reviewed — review is mandatory, publish is MR-only):
  python3 -m skill_foundry.cli.promote --apply          # write locally (no commit)
  python3 -m skill_foundry.cli.promote --pr             # branch + push + open an MR

Every apply runs the gates (add-only · no-secrets · size) AND an LLM judge
(SKILL_REVIEWER) or an interactive prompt; only APPROVE proceeds. There is no
escape hatch: the gates cannot be bypassed, review cannot be skipped, and the
only publish path is an MR that a human merges (no auto-merge, no --direct).
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

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import browser as _browser  # noqa: E402
from skill_foundry.lib import gates  # noqa: E402
from skill_foundry.lib import reviewer  # noqa: E402

FIELD_ORDER = ["id", "category", "context", "skill", "wrong", "correct", "action", "status"]
ENTRY_RE = re.compile(r"^##\s+(LRN-\d{8}-\d{3})")


def one(s: str | None) -> str:
    return " ".join((s or "").split())


def _norm(s: str | None) -> str:
    return one(s).lower()


def _identity_line(e: dict, target: Path | None) -> str:
    """The exact one-line text this entry would append (normalized).

    Used for dedupe + presence checks so they compare whole rendered bullets
    (or known-failures titles) rather than substrings of a field — a short
    `correct` value like "y" must not match "ready" in the target body.
    """
    if target is not None:
        for ln in build_snippet(e, target).splitlines():
            s = one(ln)
            if s:
                return _norm(s)
    return _norm(e.get("correct") or e.get("action") or "")


def dedupe_pending(pending: list[dict], root: Path) -> tuple[list[dict], dict[str, str]]:
    active: list[dict] = []
    skipped: dict[str, str] = {}
    seen: set[str] = set()
    for e in pending:
        t = resolve_target(e, root)
        key = _identity_line(e, t)
        if key and key in seen:
            skipped[e["id"]] = "duplicate of an earlier pending entry"
            continue
        if key:
            seen.add(key)
        if t is not None and t.exists() and key:
            lines = {_norm(ln) for ln in t.read_text(encoding="utf-8", errors="replace").splitlines()}
            if key in lines:
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


def plan_entries(
    root: Path, pending: list[dict]
) -> tuple[list[tuple[Path, str, str, list[dict]]], list[dict]]:
    """Resolve targets and accumulate per-target content across pending entries.

    Returns ``(plan, skipped)``. ``plan`` has one tuple per target file, in
    first-seen order: ``(target, old_content, new_content, entries)``.
    ``new_content`` applies each entry's snippet to a running buffer, so
    entries that share a target (same file, or even the same section) compose
    instead of clobbering one another. ``skipped`` lists entries whose target
    could not be resolved.
    """
    by_target: dict[Path, list[dict]] = {}
    skipped: list[dict] = []
    for e in pending:
        t = resolve_target(e, root)
        if t is None:
            skipped.append(e)
            continue
        by_target.setdefault(t, []).append(e)

    plan: list[tuple[Path, str, str, list[dict]]] = []
    for t, entries in by_target.items():
        old = t.read_text(encoding="utf-8") if t.exists() else ""
        cur = old
        for e in entries:
            cur = apply_snippet(cur, t, build_snippet(e, t))
        plan.append((t, old, cur, entries))
    return plan, skipped


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
    return f"{web}/merge_requests/new?source_branch={branch}&target_branch={base}"


def _line_diff_stats(old: str, new: str) -> str:
    """Return '+a/−d' line-change stats between two texts (for the files table)."""
    sm = difflib.SequenceMatcher(None, old.splitlines(), new.splitlines())
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "replace":
            removed += i2 - i1
            added += j2 - j1
    return f"+{added}/−{removed}"


def build_mr_body(what: str, files: list | None = None, why: str = "", impact: str = "",
                  testing: str = "", rollback: str = "", notes: str = "") -> str:
    """Assemble the standard MR description.

    Sections, in order: What · Files changed (table) · Why · Impact · Testing ·
    Rollback · Notes. ``files`` is a list of dicts:
      {"path": …, "change": added|modified|removed, "detail": …, "stats": "+n/−m"}
    Empty optional sections are omitted.
    """
    parts = [("## What", what)]
    if files:
        header = "| File | Change | What changed | Diff |"
        sep = "|---|---|---|---|"
        rows = []
        for f in files:
            path = f.get("path", "")
            change = f.get("change") or "modified"
            detail = f.get("detail") or "—"
            stats = f.get("stats") or "—"
            rows.append(f"| `{path}` | {change} | {detail} | {stats} |")
        parts.append(("## Files changed", "\n".join([header, sep] + rows)))
    if why:
        parts.append(("## Why", why))
    if impact:
        parts.append(("## Impact", impact))
    if testing:
        parts.append(("## Testing", testing))
    if rollback:
        parts.append(("## Rollback", rollback))
    if notes:
        parts.append(("## Notes", notes))
    return "\n\n".join(f"{h}\n{b}" for h, b in parts).strip()


def _glab_create_mr(branch: str, base: str, title: str, body: str = "") -> str | None:
    glab = shutil.which("glab")
    if not glab:
        return None
    try:
        cmd = [glab, "mr", "create", "--source-branch", branch,
               "--target-branch", base, "--title", title, "--yes"]
        if body:
            cmd += ["--description", body]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            m = re.search(r"https?://\S*merge_requests/\d+", (r.stdout or "") + " " + (r.stderr or ""))
            return m.group(0) if m else None
    except Exception:
        return None
    return None


def _api_create_mr(web: str, branch: str, base: str, title: str, body: str = "") -> str | None:
    """Create a GitLab/GitCode MR via the REST API (human merges; no auto-merge)."""
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
            "description": body,
        }).encode()
        req = urllib.request.Request(
            api, data=payload, method="POST",
            headers={"PRIVATE-TOKEN": token, "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("web_url")
    except Exception:
        return None


def _gitcode_create_pr(owner: str, repo: str, head: str, base: str, title: str, token: str, body: str = "") -> str | None:
    """Create a gitcode pull request via the v5 API; return its html_url.

    gitcode v5 authenticates ONLY via the ``access_token`` query param
    (Authorization headers return 401 — verified live). ``body`` becomes the
    PR description.
    """
    api = (f"https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls"
           f"?access_token={urllib.parse.quote(token)}")
    payload = json.dumps({"title": title, "head": head, "base": base, "body": body}).encode()
    req = urllib.request.Request(api, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data.get("html_url") or data.get("web_url")


def create_mr(web: str, branch: str, base: str, title: str, body: str = "") -> tuple[str, bool]:
    """Create an MR/PR on the platform. Returns (url, created).

    gitcode (this repo's remote) uses its own v5 API with ``access_token`` query
    auth; the standard GitLab API and glab do not work against it. ``body`` (if
    given) is the MR description.
    """
    token = os.environ.get("GITCODE_TOKEN") or os.environ.get("GITLAB_TOKEN")
    m = re.search(r"gitcode\.com/([^/]+)/([^/]+?)(?:\.git)?$", web or "")
    if m and token:
        try:
            url = _gitcode_create_pr(m.group(1), m.group(2), branch, base, title, token, body)
            if url:
                return url, True
        except Exception:
            pass
    url = _glab_create_mr(branch, base, title, body)
    if url:
        return url, True
    url = _api_create_mr(web, branch, base, title, body)
    if url:
        return url, True
    return mr_url(web, branch, base), False


def _mr_url_from_push(stdout: str, stderr: str) -> str | None:
    """Return a *created* MR URL from push output (merge_requests/<number>).

    Deliberately excludes the manual ``merge_requests/new?...`` link gitcode
    prints for a plain push — that means no MR was actually created.
    """
    text = f"{stdout or ''}\n{stderr or ''}"
    for m in re.finditer(r"https?://[^\s]+", text):
        u = m.group(0).rstrip(".,;:()")
        if re.search(r"merge_requests/\d+", u):
            return u
    return None


def _open(url: str | None) -> None:
    """Best-effort open a URL in the user's browser (never raises)."""
    if not url:
        return
    try:
        err = _browser.open_browser(url)
        if err:
            print(err, file=sys.stderr)
    except Exception:
        pass


def propose_all(root: Path, lp: Path, pending: list[dict], json_out: bool = False) -> int:
    plan, skipped = plan_entries(root, pending)
    if json_out:
        print(json.dumps({
            "status": "proposed",
            "changes": [
                {"entries": [e["id"] for e in es], "target": str(t.relative_to(root)),
                 "diff": "\n".join(difflib.unified_diff(
                     old.splitlines(), new.splitlines(),
                     fromfile=f"a/{t.relative_to(root)}", tofile=f"b/{t.relative_to(root)}", lineterm=""))}
                for t, old, new, es in plan if new != old
            ],
            "skipped": [{"id": e["id"], "reason": "unmapped"} for e in skipped],
        }))
        return 0
    for e in skipped:
        print(f"SKIP {e['id']}: unmapped (skill={e.get('skill')!r})")
    for t, old, new, entries in plan:
        ids = ", ".join(e["id"] for e in entries)
        if new == old:
            print(f"SKIP {ids}: no change for {t.relative_to(root)}")
            continue
        print(f"\n### {ids} → {t.relative_to(root)}")
        print("\n".join(difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile=f"a/{t.relative_to(root)}", tofile=f"b/{t.relative_to(root)}", lineterm="",
        )))
    return 0


def apply_all(root: Path, lp: Path, entries: list[dict], pending: list[dict],
              branch: str | None, push: bool, review: bool = True, json_out: bool = False) -> int:
    # 1. build the plan — one element per target file; snippets accumulate in
    #    order so multiple entries sharing a target compose instead of clobbering.
    plan, skipped = plan_entries(root, pending)
    for e in skipped:
        if not json_out:
            print(f"SKIP {e['id']}: unmapped")

    # 2. gates (add-only · secrets · size) — always enforced
    violations: list[str] = []
    for t, old, new, _es in plan:
        violations += gates.gate(old, new)
    violations = list(dict.fromkeys(v for v in violations if v))
    if violations:
        if json_out:
            print(json.dumps({"status": "blocked", "violations": gates.violations_json(violations)}))
        else:
            print("✗ promotion blocked by gates (fix the violation):", file=sys.stderr)
            gates.render(violations)
        return 2

    # 3. review (mandatory: builtin judge + optional LLM + interactive fallback)
    if review:
        diffs = []
        old_texts = []
        for t, old, new, _es in plan:
            if new != old:
                diffs.append("\n".join(difflib.unified_diff(
                    old.splitlines(), new.splitlines(),
                    fromfile=f"a/{t.relative_to(root)}", tofile=f"b/{t.relative_to(root)}", lineterm="",
                )))
                old_texts.append(old)
        if not diffs:
            if json_out:
                print(json.dumps({"status": "noop", "reason": "no pending changes"}))
            else:
                print("nothing to review — no pending changes.")
            return 0
        if not reviewer.approve("\n\n".join(diffs), target_content="\n\n".join(old_texts)):
            if json_out:
                print(json.dumps({"status": "rejected", "reason": "review did not APPROVE"}))
            else:
                print("✗ review did not APPROVE — nothing applied.")
            return 0

    # 4. write
    changed: list[Path] = []
    for t, old, new, entries_for_target in plan:
        if new != old:
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(new, encoding="utf-8")
            changed.append(t)
            if not json_out:
                print(f"APPLIED {', '.join(e['id'] for e in entries_for_target)} → {t.relative_to(root)}")
        for e in entries_for_target:
            e["status"] = "promoted"
            _promote_log_lines(root, e)

    header, _ = split_header(lp.read_text(encoding="utf-8"))
    lp.write_text(header.rstrip() + "\n\n" + serialize_entries(entries) + "\n", encoding="utf-8")

    add_paths = [str(t.relative_to(root)) for t in changed]
    add_paths += [str(lp.relative_to(root)), "learnings/promoted.md", "learnings/corrections.md"]

    mr_url_out: str | None = None
    if branch:
        subprocess.run(["git", "-C", str(root), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com", "checkout", "-b", branch], check=True)
        subprocess.run(["git", "-C", str(root), "add", *add_paths], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=skill-foundry",
                        "-c", "user.email=harness@example.com", "commit",
                        "-m", f"chore: promote learnings ({len(changed)} entries)"], check=True)
        if not json_out:
            print(f"Committed on branch '{branch}' ({len(changed)} file(s) changed).")
        if push:
            title = (f"chore: promote learnings ({len(changed)} entries) — "
                     f"{_dt.datetime.now():%Y-%m-%d}")
            files = []
            for t, old, new, entries_for_target in plan:
                if new != old:
                    detail = "; ".join(
                        (e.get("correct") or e.get("action") or e["id"]).strip()
                        for e in entries_for_target
                    )
                    files.append({
                        "path": str(t.relative_to(root)),
                        "change": "added" if not old.strip() else "modified",
                        "detail": detail,
                        "stats": _line_diff_stats(old, new),
                    })
            files += [
                {"path": "learnings/recent.md", "change": "modified", "detail": "promoted entries marked promoted", "stats": ""},
                {"path": "learnings/promoted.md", "change": "modified", "detail": "promotion summary appended", "stats": ""},
                {"path": "learnings/corrections.md", "change": "modified", "detail": "audit trail appended", "stats": ""},
            ]
            body = build_mr_body(
                what=f"Promote {len(changed)} learning(s) into the skills corpus "
                     f"({', '.join(sorted({e['id'] for e in pending}))}).",
                files=files,
                why="Corrections captured during triage flow into reusable skill "
                    "knowledge; the mechanical gates and LLM judge already passed.",
                impact="Updates the shared skill corpus (SKILL.md / known-failures.md) "
                       "that every future regression run reads — the next run annotates "
                       "these failures as known instead of re-triaging them.",
                testing="./harness selfcheck  (skill spec + reference integrity + "
                        "index freshness + unit tests + demo smoke)",
                rollback="Add-only promotion: revert the merge commit (git revert <sha>) "
                         "to remove the entries cleanly.",
                notes="\n".join(
                    f"- {e['id']} [{e.get('skill') or '?'}]: {e.get('correct') or e.get('action') or ''}"
                    for e in pending),
            )
            # Create the MR directly over the existing SSH transport using
            # GitLab push options — no token/glab needed. If the host rejects
            # them, fall back to a plain push + token/glab (or a manual URL).
            push_opts = ["-o", "merge_request.create",
                         "-o", "merge_request.target=main",
                         "-o", f"merge_request.title={title}"]
            pushed = subprocess.run(["git", "-C", str(root), "push", "-u", "origin", branch] + push_opts,
                                    capture_output=True, text=True)
            mr_url = _mr_url_from_push(pushed.stdout, pushed.stderr) if pushed.returncode == 0 else None
            if mr_url:
                mr_url_out = mr_url
                if not json_out:
                    print(f"\n✓ Created merge request:\n  {mr_url}")
                _open(mr_url)
            else:
                # The remote didn't create an MR (push options unsupported or
                # ignored). Make sure the branch is pushed, then try token/glab,
                # else hand the human the manual URL.
                if pushed.returncode != 0:
                    pushed = subprocess.run(["git", "-C", str(root), "push", "-u", "origin", branch],
                                            capture_output=True, text=True)
                if pushed.returncode == 0:
                    url, created = create_mr(remote_web_url(root) or "", branch, "main", title, body)
                    mr_url_out = url
                    if not json_out:
                        if created:
                            print(f"\n✓ Opened merge request (human merges):\n  {url}")
                        else:
                            print(f"\nPushed branch '{branch}'. Create the merge request manually "
                                  f"(set GITCODE_TOKEN or install glab to auto-open):\n  {url}")
                    _open(url)
                else:
                    if not json_out:
                        print(f"\nPush failed (exit {pushed.returncode}) — push manually:"
                              f"\n  git -C {root} push -u origin {branch}", file=sys.stderr)

    promoted_count = sum(len(es) for _, _, _, es in plan)
    if json_out:
        print(json.dumps({
            "status": "applied",
            "promoted": promoted_count,
            "total": len(pending),
            "files": [str(t.relative_to(root)) for t, old, new, _es in plan if new != old],
            "mr_url": mr_url_out,
        }))
    else:
        print(f"\nPromoted {promoted_count} of {len(pending)} pending entries.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote pending learnings into skills (gated, add-only).")
    ap.add_argument("--root", default=str(HARNESS), help="Harness root (default this repo).")
    ap.add_argument("--learnings", default=None, help="Path to recent.md (default <root>/learnings/recent.md).")
    ap.add_argument("--propose", action="store_true", help="Print proposed diffs (default).")
    ap.add_argument("--apply", action="store_true", help="Apply edits locally and mark entries promoted.")
    ap.add_argument("--branch", default=None, help="With --apply: create + commit on this branch.")
    ap.add_argument("--pr", action="store_true", help="With --apply: push the branch and open an MR (human merges).")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = ap.parse_args(argv)

    if args.pr:
        args.apply = True
        if not args.branch:
            args.branch = f"feat/learnings-{_dt.datetime.now():%Y%m%d}"
        if not (os.environ.get("GITCODE_TOKEN") or os.environ.get("GITLAB_TOKEN")):
            print(
                "\n"
                "⚠️  GITCODE_TOKEN is NOT set — the PR will NOT be auto-created.\n"
                "    `--pr` will push the branch and print a manual PR-new URL instead.\n"
                "    To enable auto PR creation, add to env.sh (gitignored) and re-source:\n"
                "      export GITCODE_TOKEN=<your gitcode access token>   # gitcode → Settings → Access Tokens\n",
                file=sys.stderr,
            )

    root = Path(args.root).resolve()
    lp = Path(args.learnings).resolve() if args.learnings else root / "learnings" / "recent.md"
    if not lp.exists():
        if args.json:
            print(json.dumps({"status": "noop", "reason": "no learnings file"}))
        else:
            print(f"No learnings file at {lp}")
        return 0

    entries = parse_entries(lp.read_text(encoding="utf-8"))
    pending = [e for e in entries if e.get("status") == "pending"]
    if not pending:
        if args.json:
            print(json.dumps({"status": "noop", "reason": "no pending entries"}))
        else:
            print("No pending entries to promote.")
        return 0

    active, skipped = dedupe_pending(pending, root)
    for e in entries:
        if e.get("id") in skipped:
            e["status"] = "rejected"
    for eid, reason in skipped.items():
        if not args.json:
            print(f"SKIP {eid}: {reason}")
    if not active:
        if args.json:
            print(json.dumps({"status": "noop", "reason": "no new pending entries (duplicates/present)"}))
        else:
            print("No new pending entries to promote (all duplicates / already present).")
        return 0

    if args.apply:
        return apply_all(root, lp, entries, active, args.branch, args.pr, json_out=args.json)
    return propose_all(root, lp, active, json_out=args.json)


if __name__ == "__main__":
    raise SystemExit(main())