#!/usr/bin/env python3
"""One-glance dashboard: environment, per-target suites, baseline, learnings, last run.

Usage:
  python3 -m skill_foundry.workflow.status              # all targets
  python3 -m skill_foundry.workflow.status --target X   # one target
  python3 -m skill_foundry.workflow.status --json       # machine-readable
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

from skill_foundry.lib import capabilities  # noqa: E402
from skill_foundry.lib import cann as detect_cann  # noqa: E402
from skill_foundry.lib import install_skills  # noqa: E402
from skill_foundry.lib import runs as _runs  # noqa: E402
from skill_foundry.lib import targets  # noqa: E402
from skill_foundry.lib.term import GREEN, RED, YELLOW, BOLD, c, mark  # noqa: E402


def pending_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        from skill_foundry.cli import promote as promote_recent

        return sum(
            1
            for e in promote_recent.parse_entries(path.read_text(encoding="utf-8"))
            if e.get("status") == "pending"
        )
    except Exception:
        return 0


def promoted_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(re.findall(r"^- LRN-\d{8}-\S+", path.read_text(encoding="utf-8"), re.M))


def _target_rows(cfg: dict, only: str | None) -> list[dict]:
    rows = []
    for name in targets.list_targets(cfg):
        if only and name != only:
            continue
        t = targets.get_target(name, cfg) or {}
        arches = targets.load_arches(t)
        repo = targets.resolve_repo(t)
        suite_rows = []
        for s in t.get("suites", []):
            runnable, reason = capabilities.suite_reason(s, arches)
            suite_rows.append(
                {
                    "name": s.get("name", ""),
                    "mode": s.get("mode", "-"),
                    "enabled": bool(s.get("enabled")),
                    "runnable": runnable,
                    "reason": reason,
                    "milestone": s.get("milestone", ""),
                }
            )
        rows.append(
            {
                "name": name,
                "label": t.get("label") or name,
                "repo_env": t.get("repo_env") or "PTO_ISA_REPO",
                "repo_ok": repo.exists(),
                "repo_path": str(repo),
                "suites": suite_rows,
                "baseline": _baseline_info(name),
            }
        )
    return rows


def _agent_visibility() -> dict:
    """Which harness skills each detected agent can currently see, plus local-only skills."""
    try:
        cat = json.loads((HARNESS / "hub" / "catalog.json").read_text(encoding="utf-8"))
        skills = cat.get("skills", [])
    except (OSError, ValueError):
        skills = []
    hub = {s.get("name", "") for s in skills if s.get("status") == "published"}
    owned = {s.get("name", "") for s in skills if s.get("origin") == "native"}
    visible: set[str] = set()
    per_agent: dict[str, list[str]] = {}
    for label, parent, _hint in install_skills.AGENTS:
        names = install_skills.agent_skill_names(parent)
        per_agent[label] = names
        visible |= set(names)
    harness_seen = sorted(visible & hub)
    return {
        "hub_total": len(hub),
        "owned_total": len(owned),
        "visible_total": len(harness_seen),
        "missing_owned": sorted(owned - visible),
        "local_only": sorted(visible - hub),
        "per_agent": per_agent,
    }


def _baseline_info(name: str) -> dict:
    bpath = targets.baseline_path(name)
    bdata = json.loads(bpath.read_text(encoding="utf-8")) if bpath.exists() else {}
    age = None
    if bdata.get("generated_at"):
        try:
            gen = _dt.datetime.fromisoformat(bdata["generated_at"])
            age = (_dt.datetime.now(_dt.timezone.utc) - gen).days
        except Exception:
            age = None
    return {"exists": bpath.exists(), "run_id": bdata.get("run_id"), "age_days": age}


def collect(only: str | None = None) -> dict:
    cfg = targets.load_config()

    ascend = os.environ.get("ASCEND_HOME_PATH", "")
    ascend_version = None
    if ascend:
        try:
            ascend_version = detect_cann.analyze(
                Path(ascend), detect_cann.load_config()
            )["version"]
        except Exception:
            ascend_version = "?"
    ascend_state, ascend_envsh = capabilities.ascend_state()
    ascend_hint = None
    if not ascend:
        ascend_hint = (
            f"not sourced — env.sh sets {ascend_envsh} (run `source ./env.sh`)"
            if ascend_state == "envsh"
            else "not set"
        )

    # baseline now lives per-target (see _target_rows); no shared baseline block.
    last_info = None
    for p, data in _runs.iter_runs():
        if data.get("run_id", "").startswith("demo-live"):
            continue
        if only and data.get("target") != only:
            continue
        last_info = {
            "run_id": data.get("run_id", p.parent.name),
            "target": data.get("target", ""),
            "suites": ", ".join(
                f"{s.get('name')}:{s.get('status')}" for s in data.get("suites", [])
            ),
            "failed": any(s.get("status") != "PASS" for s in data.get("suites", [])),
        }
        break

    return {
        "env": {
            "python3": bool(shutil.which("python3")),
            "git": bool(shutil.which("git")),
            "ascend": ascend,
            "ascend_version": ascend_version,
            "ascend_state": ascend_state,
            "ascend_hint": ascend_hint,
        },
        "targets": _target_rows(cfg, only),
        "skills": _agent_visibility(),
        "learnings": {
            "pending": pending_count(HARNESS / "learnings" / "recent.md"),
            "promoted": promoted_count(HARNESS / "learnings" / "promoted.md"),
        },
        "last_run": last_info,
    }


def render(data: dict) -> None:
    env = data["env"]
    if env["ascend"]:
        ascend_desc = env["ascend_version"] or env["ascend"]
        ascend_ok = True
    else:
        ascend_desc = env.get("ascend_hint") or "not set"
        ascend_ok = False
    print(c(" environment", BOLD))
    print(f"  {mark(env['python3'])} python3    {mark(env['git'])} git")
    print(
        f"  {mark(ascend_ok)} ASCEND_HOME_PATH  {c(ascend_desc, GREEN if ascend_ok else YELLOW)}"
    )

    for t in data["targets"]:
        print(c(f"\n target: {t['label']}  ({t['name']})", BOLD))
        print(f"  {mark(t['repo_ok'])} repo  {t['repo_path']}  (env {t['repo_env']})")
        b = t["baseline"]
        if b["exists"]:
            age = f"{b['age_days']}d ago" if b["age_days"] is not None else "?"
            print(
                f"  {mark(True)} baseline  {b['run_id']}, {age} — refresh only deliberately"
            )
        else:
            print(
                f"  {mark(False)} baseline  none — bash skill_foundry/workflow/baseline.sh {t['name']}"
            )
        for s in t["suites"]:
            sym = (
                "✓"
                if (s["enabled"] and s["runnable"])
                else ("!" if s["enabled"] else "·")
            )
            color = (
                GREEN
                if (s["enabled"] and s["runnable"])
                else (YELLOW if s["enabled"] else "")
            )
            note = "" if (s["runnable"] or not s["enabled"]) else f"  ← {s['reason']}"
            print(
                f"    [{c(sym, color)}] {s['name']:<14} {s['mode']:<9} {s['milestone']}{note}"
            )

    ln = data["learnings"]
    print(c("\n learnings", BOLD))
    print(
        f"  {ln['pending']} pending · {ln['promoted']} promoted"
        + ("   → ./harness promote --propose" if ln["pending"] else "")
    )

    sk = data["skills"]
    print(c("\n skills", BOLD))
    print(
        f"  agents see {sk['visible_total']} of {sk['hub_total']} harness skills"
        + (
            f" ({sk['owned_total']} owned — missing: {', '.join(sk['missing_owned'])})"
            if sk["missing_owned"]
            else ""
        )
    )
    if sk["local_only"]:
        print(f"  local-only (not in hub): {', '.join(sk['local_only'])}")
    print(
        "  see per-agent: ./harness skills --mine   ·   install owned: ./harness skills --install --scope core"
    )

    lr = data["last_run"]
    print(c("\n last run", BOLD))
    if lr:
        st = c("FAIL" if lr["failed"] else "PASS", RED if lr["failed"] else GREEN)
        print(f"  {lr['run_id']} [{lr['target']}] · {lr['suites']} · {st}")
        print(
            "  next: python3 -m skill_foundry.workflow.report --open"
            + (
                ""
                if lr["failed"]
                else "  (or python3 -m skill_foundry.workflow.review)"
            )
        )
    else:
        print(
            "  none yet — run: python3 -m skill_foundry.workflow.run --all-suites --quiet"
        )

    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-glance status.")
    ap.add_argument("--target", default=None, help="Show only this target.")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args(argv)
    data = collect(args.target)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
