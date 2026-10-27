#!/usr/bin/env python3
"""Diff a run record against the pinned baseline (or another run).

Detects pass->fail regressions, fail->pass fixes, new/removed cases, and perf
regressions (avg + p99). Perf rule: flag when p99 rises >15% even if avg stays
stable.

Usage:
  python3 scripts/diff_runs.py --run reports/<run-id>/run.json
  python3 scripts/diff_runs.py --run reports/<run-id>/run.json \
      --baseline reports/<other>/run.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _runs  # noqa: E402

HARNESS = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = HARNESS / "reports" / "baseline" / "baseline.json"
P99_PCT = 15.0


def load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def suite_cases(record: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for s in record.get("suites", []):
        cases = (s.get("results") or {}).get("cases", [])
        out[s["name"]] = cases
    return out


def stats(cases: list[dict]) -> dict:
    durs = [c.get("duration_s", 0.0) for c in cases if c.get("duration_s")]
    if not durs:
        return {"avg": None, "p99": None, "n": len(durs)}
    durs_sorted = sorted(durs)
    avg = sum(durs_sorted) / len(durs_sorted)
    idx = max(0, math.ceil(len(durs_sorted) * 0.99) - 1)  # 99th percentile
    return {"avg": round(avg, 4), "p99": round(durs_sorted[idx], 4), "n": len(durs_sorted)}


def pct(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return round((new - old) / old * 100.0, 2)


def diff(new: dict, base: dict) -> dict:
    new_cases = suite_cases(new)
    base_cases = suite_cases(base)

    regressions: list[dict] = []
    fixes: list[dict] = []
    new_only: list[dict] = []
    removed: list[dict] = []
    perf_flags: list[dict] = []

    for suite, entries in new_cases.items():
        base_map = {c["name"]: c for c in base_cases.get(suite, [])}
        new_by_name = {c["name"]: c for c in entries}

        for name, nc in sorted(new_by_name.items()):
            if name not in base_map:
                new_only.append({"suite": suite, "name": name, "status": nc.get("status")})
                continue
            bc = base_map[name]
            ns, bs = nc.get("status"), bc.get("status")
            if ns == "FAIL" and bs != "FAIL":
                regressions.append({"suite": suite, "name": name, "before": bs, "after": ns})
            elif ns != "FAIL" and bs == "FAIL":
                fixes.append({"suite": suite, "name": name, "before": bs, "after": ns})

        for name, bc in sorted(base_map.items()):
            if name not in new_by_name:
                removed.append({"suite": suite, "name": name, "status": bc.get("status")})

        # per-suite perf: avg + p99
        ns = stats(entries)
        bs = stats(base_cases.get(suite, []))
        if ns["p99"] is not None and bs["p99"] is not None:
            dp99 = pct(ns["p99"], bs["p99"])
            if dp99 is not None and dp99 > P99_PCT:
                perf_flags.append({
                    "suite": suite,
                    "metric": "p99",
                    "before_s": bs["p99"],
                    "after_s": ns["p99"],
                    "delta_pct": dp99,
                    "avg_delta_pct": pct(ns["avg"], bs["avg"]),
                })

    return {
        "regressions": regressions,
        "fixes": fixes,
        "new": new_only,
        "removed": removed,
        "perf_flags": perf_flags,
        "summary": {
            "regressions": len(regressions),
            "fixes": len(fixes),
            "new": len(new_only),
            "removed": len(removed),
            "perf_flags": len(perf_flags),
        },
    }


def print_human(d: dict) -> None:
    s = d["summary"]
    print(f"regressions: {s['regressions']}  fixes: {s['fixes']}  "
          f"new: {s['new']}  removed: {s['removed']}  perf_flags: {s['perf_flags']}")
    if d["regressions"]:
        print("\nREGRESSIONS (PASS -> FAIL):")
        for r in d["regressions"]:
            print(f"  {r['suite']}/{r['name']}  ({r['before']} -> {r['after']})")
    if d["perf_flags"]:
        print(f"\nPERF FLAGS (p99 > +{P99_PCT}%):")
        for p in d["perf_flags"]:
            print(f"  {p['suite']}: p99 {p['before_s']}s -> {p['after_s']}s "
                  f"({p['delta_pct']:+}%, avg {p['avg_delta_pct']:+}%)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Diff a run against the pinned baseline.")
    ap.add_argument("--run", default=None, help="Run record (run.json); default = latest run.")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="Baseline run.json.")
    ap.add_argument("--out", help="Write the machine-readable delta JSON to this path.")
    args = ap.parse_args(argv)

    if args.run:
        run_path = args.run
    else:
        latest = _runs.latest_run()
        if not latest:
            print("No runs found under reports/. Pass --run <path>.", file=sys.stderr)
            return 1
        run_path = str(latest[0])

    new = load(Path(run_path))
    base = load(Path(args.baseline))
    if new is None:
        raise SystemExit(f"run not found: {run_path}")
    if base is None:
        raise SystemExit(f"baseline not found: {args.baseline}")

    if base.get("generated") is False:
        print("NOTE: baseline is a seed (generated=false). First real run should be "
              "promoted via scripts/make_baseline.sh, not diffed.")
        if not base.get("suites"):
            return 0

    result = diff(new, base)
    print_human(result)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())