#!/usr/bin/env python3
"""Integrate external skills and libraries into the harness.

Sources are declared in config/imports.json — one entry per external repo,
skill directory, or knowledge library. Each source has a `type` (adapter) that
discovers the source's units and turns them into skill drafts under hub/inbox/.
From there the existing validate -> gates -> review -> promote loop publishes
them unchanged.

Usage:
  ./harness import --list
  ./harness import --add <name> --type <t> --path <loc> [--origin o] [--owner o]
  ./harness import --remove <name>
  ./harness import <source> --scan
  ./harness import <source> --draft
  ./harness import <source> --validate
  ./harness import <source> --pr
  ./harness import <source> --sync
  ./harness import <source> --reject <name> [--undo]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from skill_foundry.lib import importer
from skill_foundry.paths import ROOT

KNOWN_TYPES = importer.KNOWN_TYPES
KNOWN_MODES = importer.KNOWN_MODES

_MARKS = {
    importer.RELEVANT: "✓",
    importer.EXTEND: "→",
    importer.DUPLICATE: "✗",
    importer.IRRELEVANT: "✗",
    importer.HOLD: "?",
}

_SKIP_HINT = {
    importer.EXTEND: "merge into the existing skill (./harness teach), don't fork",
    importer.DUPLICATE: "already covered by an existing skill",
    importer.IRRELEVANT: "out of scope",
    importer.HOLD: "needs human review — check paths/secrets, then --rescan or ./harness teach",
    "rejected": "marked rejected — undo: ./harness import <source> --reject <name> --undo",
    "already-exists": "draft already on disk — delete hub/inbox/<name>/ to re-draft",
    "already-published": "already live in .claude/skills",
}


def _list(args: argparse.Namespace) -> int:
    registry = importer.load_registry()
    sources = registry.get("sources") or {}
    if args.json:
        print(json.dumps({"sources": sources}, indent=2))
        return 0
    if not sources:
        print("no sources registered (config/imports.json missing or empty)")
        print("  add one: ./harness import --add <name> --type <t> --path <loc>")
        return 0
    for name, src in sorted(sources.items()):
        loc = src.get("location") or src.get("git") or "?"
        print(
            f"  {name:<20} type={src.get('type', '?')} "
            f"mode={src.get('mode', 'vendor')} origin={src.get('origin', '?')} {loc}"
        )
    return 0


def _load_source(args):
    """Return (SourceConfig, Adapter) or (None, None) after printing an error."""
    src = importer.source_from_registry(args.source)
    if src is None:
        print(
            f"error: source '{args.source}' not registered (./harness import --list)",
            file=sys.stderr,
        )
        return None, None
    adapter = importer.get_adapter(src.type)
    if adapter is None:
        print(
            f"error: no adapter for source type '{src.type}' "
            f"(implemented: {sorted(importer.ADAPTERS)})",
            file=sys.stderr,
        )
        return None, None
    return src, adapter


def _assess(src, adapter):
    """Discover + relevance-check. Return (candidates, results, any_llm) or
    (None, None, False) after a discovery error."""
    try:
        candidates = adapter.discover(src)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None, None, False

    existing = importer.existing_skills()
    results: list[dict] = []
    any_llm = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(importer.assess, c, src, existing) for c in candidates]
        for c, fut in zip(candidates, futures):
            verdict, reasons, rel_llm, used = fut.result()
            if used:
                any_llm = True
            results.append(
                {
                    "name": c.name,
                    "category": c.category,
                    "entry": c.entry,
                    "verdict": verdict,
                    "reasons": reasons,
                    "llm_verdict": rel_llm,
                    "fingerprint": c.fingerprint,
                    "files": c.files,
                }
            )
    return candidates, results, any_llm


def _overlay_rejected(results: list[dict], source_name: str) -> None:
    """Persist human `--reject` decisions across re-assessments."""
    manifest = importer.read_manifest(source_name)
    if not manifest:
        return
    rejected = {
        c["name"]: bool(c.get("rejected")) for c in manifest.get("candidates", [])
    }
    for r in results:
        if rejected.get(r["name"]):
            r["rejected"] = True


def _print_scan(args, results, any_llm, manifest) -> None:
    if args.json:
        print(json.dumps({"source": args.source, "candidates": results}, indent=2))
        return
    if not results:
        print(f"scan: {args.source} — no candidates (mapping manifest empty?)")
        return
    counts = Counter(r["verdict"] for r in results)
    summary = "  ".join(f"{v}={counts[v]}" for v in importer.VERDICTS if counts[v])
    print(f"scan: {args.source} — {len(results)} candidate(s)  [{summary}]")
    if not any_llm:
        print(
            "  ⚠ IMPORT_REVIEWER not set — LLM semantic check skipped "
            "(deterministic only)"
        )
    print()
    for r in results:
        mark = _MARKS.get(r["verdict"], "?")
        print(f"  {mark} {r['name']:<28} {r['verdict']:<10} {r['category']}")
        for reason in r["reasons"]:
            print(f"      · {reason}")
        if r.get("llm_verdict"):
            print(f"      · LLM judge: {r['llm_verdict']}")
        if r.get("rejected"):
            print(
                f"      · rejected — undo: ./harness import {args.source} "
                f"--reject {r['name']} --undo"
            )
    print()
    print(f"manifest → {manifest.relative_to(ROOT)}")
    print(f"next: ./harness import {args.source} --draft")


def _scan(args) -> int:
    src, adapter = _load_source(args)
    if src is None:
        return 2
    candidates, results, any_llm = _assess(src, adapter)
    if candidates is None:
        return 1
    _overlay_rejected(results, args.source)
    manifest = importer.write_manifest(args.source, results)
    _print_scan(args, results, any_llm, manifest)
    return 0


def _print_draft(args, drafted, skipped, any_llm) -> None:
    if args.json:
        print(
            json.dumps(
                {
                    "source": args.source,
                    "drafted": [n for n, _ in drafted],
                    "skipped": [{"name": n, "verdict": v} for n, v in skipped],
                },
                indent=2,
            )
        )
        return
    print(f"draft: {args.source} — {len(drafted)} drafted, {len(skipped)} skipped")
    if not any_llm:
        print(
            "  ⚠ IMPORT_REVIEWER not set — semantic relevance not checked "
            "(deterministic only; --pr will gate with SKILL_REVIEWER)"
        )
    print()
    for name, _path in drafted:
        print(f"  ✓ {name:<28} → hub/inbox/{name}/")
    for name, verdict in skipped:
        hint = _SKIP_HINT.get(verdict, "")
        line = f"  ✗ {name:<28} {verdict}"
        if hint:
            line += f"  ({hint})"
        print(line)
    print()
    print("next: ./harness import <source> --validate")


def _draft(args) -> int:
    src, adapter = _load_source(args)
    if src is None:
        return 2

    manifest = importer.read_manifest(args.source)
    any_llm = False

    if args.rescan or manifest is None:
        candidates, results, any_llm = _assess(src, adapter)
        if candidates is None:
            return 1
        _overlay_rejected(results, args.source)
    else:
        # Reuse the last scan's verdicts — a non-deterministic judge must not
        # change what a preview said. Re-discover for current files, don't re-judge.
        try:
            candidates = adapter.discover(src)
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        prev_by_name = {c["name"]: c for c in manifest.get("candidates", [])}
        results = []
        for c in candidates:
            prev = prev_by_name.get(c.name, {})
            results.append(
                {
                    "name": c.name,
                    "category": c.category,
                    "entry": c.entry,
                    "verdict": prev.get("verdict", importer.RELEVANT),
                    "reasons": prev.get("reasons", []),
                    "llm_verdict": prev.get("llm_verdict"),
                    "fingerprint": c.fingerprint,
                    "files": c.files,
                    "rejected": prev.get("rejected", False),
                }
            )
        any_llm = any(r.get("llm_verdict") for r in results)

    drafted: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    live = ROOT / ".claude" / "skills"
    for c, r in zip(candidates, results):
        if r.get("rejected"):
            skipped.append((c.name, "rejected"))
            r["action"] = "skipped:rejected"
            continue
        if (live / c.name).exists():
            skipped.append((c.name, "already-published"))
            r["action"] = "skipped:published"
            continue
        if r["verdict"] != importer.RELEVANT:
            skipped.append((c.name, r["verdict"]))
            r["action"] = "skipped"
            continue
        try:
            adapter.build_skill(c, src)
            drafted.append((c.name, f"hub/inbox/{c.name}"))
            r["action"] = "drafted"
        except FileExistsError as exc:
            skipped.append((c.name, "already-exists"))
            r["action"] = "skipped:exists"
            r["reasons"].append(str(exc))
        except Exception as exc:  # pragma: no cover - unexpected
            skipped.append((c.name, f"error: {exc}"))
            r["action"] = "error"
            r["reasons"].append(str(exc))

    importer.write_manifest(args.source, results)
    if not (args.rescan or manifest is None):
        print("  (reusing the last scan's verdicts — add --rescan to re-judge)")
    _print_draft(args, drafted, skipped, any_llm)
    return 0


def _add(args) -> int:
    if not args.type:
        print(
            "error: --add needs --type (knowledge-library | agent-skills | local-dir)",
            file=sys.stderr,
        )
        return 2
    if args.path and args.git:
        print("error: pass exactly one of --path or --git", file=sys.stderr)
        return 2
    location = args.path or args.git
    mapping = args.mapping
    if args.type == "knowledge-library" and not mapping:
        mapping = f"config/imports/{args.add}.json"
        importer.ensure_mapping(args.add, mapping)
    try:
        src = importer.add_source(
            args.add,
            args.type,
            location,
            origin=args.origin,
            owner=args.owner,
            mode=args.mode,
            scope_hint=args.scope_hint,
            mapping=mapping or "",
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"✓ registered '{src.name}' "
        f"(type={src.type}, mode={src.mode}, origin={src.origin})"
    )
    if src.type == "knowledge-library":
        print(
            f"    mapping → {mapping} — edit the 'skills' list, "
            f"then ./harness import {src.name} --scan"
        )
    else:
        print(f"    next: ./harness import {src.name} --scan")
    return 0


def _remove(args) -> int:
    src = importer.source_from_registry(args.remove)
    mapping = src.mapping if src else ""
    try:
        importer.remove_source(args.remove)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"✓ removed source '{args.remove}' (drafts / skills are untouched)")
    if mapping:
        mp = ROOT / mapping
        if mp.exists():
            try:
                data = json.loads(mp.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            if not (data.get("skills") or []):
                mp.unlink()
                print(f"  ✓ removed empty mapping stub {mapping}")
            else:
                print(f"  (kept mapping {mapping} — it has authored skills)")
    return 0


def _reject(args) -> int:
    """Mark candidate(s) rejected (or --undo) so --draft/--sync skip them."""
    names = list(args.reject or [])
    if importer.source_from_registry(args.source) is None:
        print(
            f"error: source '{args.source}' not registered (./harness import --list)",
            file=sys.stderr,
        )
        return 2
    manifest = importer.read_manifest(args.source)
    if manifest is None:
        print(
            f"error: no manifest for '{args.source}' — run --scan first",
            file=sys.stderr,
        )
        return 2
    candidates = manifest.get("candidates", [])
    by_name = {c["name"]: c for c in candidates}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        print(
            f"error: not candidate(s) of '{args.source}': {', '.join(unknown)}",
            file=sys.stderr,
        )
        if by_name:
            print(f"  candidates: {', '.join(sorted(by_name))}", file=sys.stderr)
        return 2

    inbox = ROOT / "hub" / "inbox"
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    changed = False
    for n in names:
        c = by_name[n]
        if args.undo:
            if c.get("rejected"):
                c["rejected"] = False
                c.pop("rejected_at", None)
                changed = True
                print(f"  ↻ {n}: re-enabled (back in scope for --scan/--draft)")
            else:
                print(f"  · {n}: was not rejected")
            continue
        if c.get("rejected"):
            print(f"  · {n}: already rejected (--undo to restore)")
            continue
        c["rejected"] = True
        c["rejected_at"] = now
        changed = True
        if (inbox / n / "SKILL.md").exists():
            shutil.rmtree(inbox / n)
            c["action"] = "rejected"
            print(f"  ✗ {n}: rejected (draft removed)")
        else:
            print(f"  ✗ {n}: rejected")
    if changed:
        importer.write_manifest(args.source, candidates)
    return 0


def _validate(args) -> int:
    from skill_foundry.lib import validate_skills
    from skill_foundry.paths import INBOX

    manifest = importer.read_manifest(args.source)
    if manifest is None:
        print(
            f"error: no manifest for '{args.source}' — run --scan or --draft first",
            file=sys.stderr,
        )
        return 2
    candidates = manifest.get("candidates", [])
    drafted = importer.drafted_candidates(candidates, INBOX)
    if not drafted:
        print(f"validate: {args.source} — no drafts to validate (run --draft first)")
        return 0

    errors: list[str] = []
    for c in drafted:
        folder = INBOX / c["name"]
        if not (folder / "SKILL.md").exists():
            errors.append(
                f"{c['name']}: draft missing (hub/inbox/{c['name']}/SKILL.md)"
            )
            continue
        errors.extend(
            validate_skills.validate_skill(folder)
            + validate_skills.check_skill_metadata(folder)
        )

    if args.json:
        print(
            json.dumps(
                {
                    "source": args.source,
                    "checked": len(drafted),
                    "errors": errors,
                },
                indent=2,
            )
        )
        return 0 if not errors else 1

    for c in drafted:
        name = c["name"]
        bad = [e for e in errors if e.startswith(f"{name}:")]
        print(f"  {'✓' if not bad else '✗'} {name}")
        for e in bad:
            print(f"      · {e}")
    print(
        f"validate: {args.source} — {len(errors)} issue(s) "
        f"across {len(drafted)} draft(s)"
    )
    if not errors:
        print(f"next: ./harness import {args.source} --pr  (or --apply for local)")
    return 0 if not errors else 1


def _promote(args) -> int:
    from skill_foundry.cli import promote as _promote_mod
    from skill_foundry.lib import gates, reviewer

    manifest = importer.read_manifest(args.source)
    if manifest is None:
        print(
            f"error: no manifest for '{args.source}' — run --draft first",
            file=sys.stderr,
        )
        return 2
    candidates = manifest.get("candidates", [])
    inbox = ROOT / "hub" / "inbox"
    live = ROOT / ".claude" / "skills"
    drafted = importer.drafted_candidates(candidates, inbox)
    if not drafted:
        print(f"promote: {args.source} — no drafts to promote (run --draft first)")
        return 0

    # Pre-flight mechanical gates (no writes yet).
    violations: list[str] = []
    bodies: list[tuple[str, str]] = []
    for c in drafted:
        name = c["name"]
        folder = inbox / name
        if not (folder / "SKILL.md").exists():
            violations.append(f"{name}: draft missing (hub/inbox/{name}/SKILL.md)")
            continue
        body = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        for v in gates.check_skill_spec(folder) + gates.check_secrets(body):
            violations.append(f"{name}: {v}")
        if (live / name).exists():
            violations.append(f"{name}: already exists in .claude/skills")
        bodies.append((name, body))
    if violations:
        print("✗ promote blocked by gates:", file=sys.stderr)
        for v in violations:
            print(f"  ✗ {v}", file=sys.stderr)
        return 1

    combined = "\n\n".join(b for _, b in bodies)
    local_skills = {
        d.name for d in live.iterdir() if d.is_dir() and not d.name.startswith(".")
    } | {c["name"] for c in drafted}
    if not reviewer.approve(
        f"# import: promote {len(bodies)} skill(s) from {args.source}\n\n{combined}",
        added_text=combined,
        context={"name": f"import:{args.source}"},
        local_skills=local_skills,
    ):
        print("✗ review did not APPROVE — nothing promoted.")
        return 0

    for name, _body in bodies:
        shutil.copytree(inbox / name, live / name)
        shutil.rmtree(inbox / name)
    for c in candidates:
        if c.get("action") == "drafted":
            c["action"] = "promoted"
    importer.write_manifest(args.source, candidates)

    # Refresh the catalog/index so --apply keeps the tree consistent and --pr
    # commits a publish whose guards (skills --check) pass.
    from skill_foundry.cli import skills as _skills_cli

    _skills_cli.refresh()

    print(f"✓ promoted {len(bodies)} skill(s) from '{args.source}'")
    for name, _body in bodies:
        print(f"  ✓ {name}")

    if not args.pr:
        print("  (--apply: copied locally, not committed. Use --pr to commit + PR.)")
        return 0

    if not any(
        os.environ.get(k)
        for k in ("GITCODE_TOKEN", "GITLAB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
    ):
        print(
            "⚠️  No PR token is set — the PR will NOT be auto-created "
            "(branch will be pushed; open the PR manually).",
            file=sys.stderr,
        )

    branch = f"feat/import-{args.source}-{_dt.datetime.now():%Y%m%d%H%M%S}"
    live_rel = str(live.relative_to(ROOT))
    inbox_rel = str(inbox.relative_to(ROOT))
    subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "add",
            "-A",
            live_rel,
            inbox_rel,
            "hub/imports",
            "hub/catalog.json",
            "docs/SKILLS_INDEX.md",
            "README.md",
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "-c",
            "user.name=skill-foundry",
            "-c",
            "user.email=harness@example.com",
            "checkout",
            "-b",
            branch,
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "-c",
            "user.name=skill-foundry",
            "-c",
            "user.email=harness@example.com",
            "commit",
            "-m",
            f"feat: import {args.source} skills",
        ],
        check=True,
    )
    pushed = subprocess.run(["git", "-C", str(ROOT), "push", "-u", "origin", branch])
    if pushed.returncode == 0:
        web = _promote_mod.remote_web_url(ROOT)
        if web:
            url, created = _promote_mod.create_mr(
                web, branch, "main", f"feat: import {args.source} skills"
            )
            print(
                f"\n{'✓ Opened pull request (human merges)' if created else 'Pushed branch. Open the PR'}:\n  {url}"
            )
        else:
            print("\nPushed branch — no remote URL detected; open the PR manually.")
    else:
        print(
            f"\nPush failed (exit {pushed.returncode}) — push manually: "
            f"git -C {ROOT} push -u origin {branch}",
            file=sys.stderr,
        )
    return 0


def _sync(args) -> int:
    src, adapter = _load_source(args)
    if src is None:
        return 2
    try:
        importer.refresh_source(src)
        candidates = adapter.discover(src)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    manifest = importer.read_manifest(args.source)
    old = {c["name"]: c for c in (manifest or {}).get("candidates", [])}

    inbox = ROOT / "hub" / "inbox"
    changed, added, removed, unchanged, refreshed = [], [], [], [], []
    for c in candidates:
        prev = old.get(c.name)
        if prev is None:
            added.append(c.name)
        elif prev.get("fingerprint") != c.fingerprint:
            changed.append(c.name)
            if (inbox / c.name / "SKILL.md").exists():
                try:
                    adapter.sync_refs(c, src)
                    refreshed.append(c.name)
                except Exception as exc:  # pragma: no cover - adapter bug
                    print(f"  ⚠ {c.name}: sync_refs failed: {exc}", file=sys.stderr)
        else:
            unchanged.append(c.name)
    for name in old:
        if name not in {c.name for c in candidates}:
            removed.append(name)

    # Re-assess and write a fresh manifest, preserving promoted actions.
    existing = importer.existing_skills()
    results: list[dict] = []
    for c in candidates:
        verdict, reasons, rel_llm, _used = importer.assess(c, src, existing)
        prev = old.get(c.name, {})
        action = None
        if (inbox / c.name / "SKILL.md").exists() and verdict == importer.RELEVANT:
            action = "drafted"
        elif prev.get("action") == "promoted":
            action = "promoted"
        results.append(
            {
                "name": c.name,
                "category": c.category,
                "entry": c.entry,
                "verdict": verdict,
                "reasons": reasons,
                "llm_verdict": rel_llm,
                "fingerprint": c.fingerprint,
                "files": c.files,
                "action": action,
            }
        )
    _overlay_rejected(results, args.source)
    importer.write_manifest(args.source, results)

    if args.json:
        print(
            json.dumps(
                {
                    "source": args.source,
                    "unchanged": unchanged,
                    "changed": changed,
                    "added": added,
                    "removed": removed,
                    "refreshed": refreshed,
                },
                indent=2,
            )
        )
        return 0

    print(
        f"sync: {args.source} — {len(candidates)} candidate(s) "
        f"[unchanged={len(unchanged)} changed={len(changed)} "
        f"added={len(added)} removed={len(removed)}]"
    )
    for name in changed:
        tag = "(refreshed)" if name in refreshed else "(no draft)"
        print(f"  ↻ {name:<28} changed  {tag}")
    for name in added:
        print(f"  + {name:<28} new in source (run --draft to draft)")
    for name in removed:
        print(f"  - {name:<28} no longer in source (draft remains — review manually)")
    return 0


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Integrate external skills/libraries into the harness."
    )
    ap.add_argument("source", nargs="?", help="Registered source name.")
    ap.add_argument("--add", metavar="NAME", help="Register an external source.")
    ap.add_argument("--remove", metavar="NAME", help="Deregister a source.")
    ap.add_argument(
        "--type", choices=KNOWN_TYPES, help="Source adapter type (with --add)."
    )
    ap.add_argument("--path", help="Filesystem path to the source (with --add).")
    ap.add_argument("--git", help="Git URL to clone (with --add).")
    ap.add_argument(
        "--mode",
        choices=KNOWN_MODES,
        help="Import mode (with --add): vendor|reference|passthrough.",
    )
    ap.add_argument("--origin", help="origin for imported skills (with --add).")
    ap.add_argument("--owner", help="owner for imported skills (with --add).")
    ap.add_argument(
        "--scope-hint", dest="scope_hint", help="One-line scope hint (with --add)."
    )
    ap.add_argument(
        "--mapping", help="Mapping manifest path (knowledge-library; with --add)."
    )
    ap.add_argument("--list", action="store_true", help="List registered sources.")
    ap.add_argument(
        "--scan", action="store_true", help="Relevance check per candidate."
    )
    ap.add_argument(
        "--draft", action="store_true", help="Convert RELEVANT candidates to drafts."
    )
    ap.add_argument(
        "--rescan",
        action="store_true",
        help="With --draft: re-judge instead of reusing the last scan's verdicts.",
    )
    ap.add_argument(
        "--validate", action="store_true", help="Run the spec gate over the drafts."
    )
    ap.add_argument(
        "--pr",
        action="store_true",
        help="Promote the drafts, then commit + push + open a PR (gated + reviewed).",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Promote the drafts locally (gated + reviewed, no commit / no PR).",
    )
    ap.add_argument(
        "--reject",
        nargs="+",
        metavar="NAME",
        help="Mark candidate(s) rejected — skipped by --draft / --sync.",
    )
    ap.add_argument(
        "--undo", action="store_true", help="With --reject: re-enable the candidate(s)."
    )
    ap.add_argument(
        "--sync",
        action="store_true",
        help="Re-fingerprint the source and refresh drifted snapshots.",
    )
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.list:
        return _list(args)

    if args.undo and not args.reject:
        print("error: --undo only applies to --reject", file=sys.stderr)
        return 2

    needs_source = (
        args.scan
        or args.draft
        or args.validate
        or args.pr
        or args.apply
        or args.sync
        or args.reject
    )
    if needs_source and not args.source:
        print("error: this action needs a <source> argument", file=sys.stderr)
        return 2

    if args.source and args.scan:
        return _scan(args)

    if args.source and args.draft:
        return _draft(args)

    if args.source and args.validate:
        return _validate(args)

    if args.source and (args.pr or args.apply):
        return _promote(args)

    if args.source and args.reject:
        return _reject(args)

    if args.add:
        return _add(args)

    if args.remove:
        return _remove(args)

    if args.source and args.sync:
        return _sync(args)

    if args.source:
        print(
            f"error: no action flag for source '{args.source}' "
            "(use --scan/--draft/--validate/--apply/--pr/--reject/--sync)",
            file=sys.stderr,
        )
        return 2

    # bare `./harness import` → show status + the flow (not an error)
    _list(args)
    if not args.json:
        print()
        print("flow: --add → --scan → --draft → --validate → --apply/--pr → --sync")
        print("guide: docs/IMPORTING_SKILLS.md  (./harness help import for flags)")
        print()
        print(
            "setup:  IMPORT_REVIEWER (scope+relevance) · SKILL_REVIEWER (promotion)\n"
            "        a PR token (GH_TOKEN / GITHUB_TOKEN) so --pr can open the PR automatically"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
