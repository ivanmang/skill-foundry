#!/usr/bin/env python3
"""List configured targets (name, label, repo, enabled suites).

Usage:
  ./harness targets            # human-readable
  ./harness targets --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import targets  # noqa: E402


def collect() -> list[dict]:
    cfg = targets.load_config()
    out = []
    for n in targets.list_targets(cfg):
        t = targets.get_target(n, cfg) or {}
        repo = targets.resolve_repo(t)
        suites = t.get("suites", [])
        out.append({
            "name": n,
            "label": t.get("label") or n,
            "repo_env": t.get("repo_env") or "PTO_ISA_REPO",
            "repo": str(repo),
            "repo_ok": repo.exists(),
            "enabled_suites": sum(1 for s in suites if s.get("enabled")),
            "total_suites": len(suites),
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List configured targets.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rows = collect()
    if args.json:
        print(json.dumps({"targets": rows}, indent=2))
        return 0
    print(f"{len(rows)} target(s):")
    for r in rows:
        ok = "✓" if r["repo_ok"] else "✗"
        print(f"  {r['name']:<14} {r['label']:<32} repo {ok} {r['repo']}")
        print(f"    env {r['repo_env']} · {r['enabled_suites']}/{r['total_suites']} suites enabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())