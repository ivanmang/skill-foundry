#!/usr/bin/env python3
"""Normalize gtest / ctest / run_cpu.py / run_st.py logs into a results object.

Internal — used by run.py. Prefer `./harness run` over running this directly.

Output shape:
{
  "suite": "<name>",
  "summary": {"passed": int, "failed": int, "skipped": int, "total": int, "status": "PASS|FAIL|UNKNOWN"},
  "cases": [{"name": str, "status": "PASS|FAIL|SKIP", "duration_s": float}],
  "evidence": [str]
}
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# gtest final summary lines
GTEST_PASSED_RE = re.compile(r"^\[\s*PASSED\s*\]\s+(\d+)\s+tests?\.?")
GTEST_FAILED_RE = re.compile(r"^\[\s*FAILED\s*\]\s+(\d+)\s+tests?,", re.I)
GTEST_PASSED_LISTED_RE = re.compile(r"^\[\s*PASSED\s*\]\s+(\d+)\s+test[s]?\.?", re.I)

# run_cpu.py per-case lines (logged at the Python level, present even when gtest
# output is suppressed):  [PASS] tadd (0.12s)  /  [FAIL] tadd (1.20s)
# Also run_st.py style:    [PASS] case ...
CASE_RE = re.compile(r"^\[(PASS|FAIL|SKIP|SKIPPED)\]\s+(\S+?)\s*(?:\(([\d.]+)[sm]s?\))?\s*$", re.I)

# gtest per-case state machine
RUN_RE = re.compile(r"^\[\s*RUN\s*\]\s+(\S+)")
OK_RE = re.compile(r"^\[\s*OK\s*\]\s+(\S+)")
FAILED_CASE_RE = re.compile(r"^\[\s*FAILED\s*\]\s+(\S+)")
# "1 test, listed below" => the failing names follow after a blank-ish separator

DEMO_RE = re.compile(r"^\[(PASS|FAIL)\]\s+demo(?::|\s)(\S+)")

# sim_dsl.sh / pto-vmi style per-case line:  PASS case0_...  compile=0.014s launch=72.536s
SIMDSL_RE = re.compile(
    r"^(PASS|FAIL|SKIP|SKIPPED)\s+(\S+?)\s*"
    r"(?:compile=(\d+(?:\.\d+)?)\S*\s+launch=(\d+(?:\.\d+)?)\S*)?$"
)


def parse_text(text: str, suite: str = "") -> dict:
    cases: dict[str, dict] = {}  # name -> {status, duration_s}
    order: list[str] = []
    summary = {"passed": 0, "failed": 0, "skipped": 0, "total": 0, "status": "UNKNOWN"}
    evidence: list[str] = []
    have_counts = False  # True once a gtest final summary line gave explicit counts

    def add_case(name: str, status: str, duration_s: float | None = None):
        if not name:
            return
        if name not in cases:
            cases[name] = {"name": name, "status": status, "duration_s": duration_s or 0.0}
            order.append(name)
        else:
            # later, more specific status wins over a tentative one
            if status != "UNKNOWN":
                cases[name]["status"] = status
            if duration_s is not None:
                cases[name]["duration_s"] = duration_s

    for raw in text.splitlines():
        line = raw.rstrip()

        m = GTEST_FAILED_RE.match(line)
        if m:
            summary["failed"] = int(m.group(1))
            evidence.append(line)
            have_counts = True
            continue

        m = GTEST_PASSED_RE.match(line)
        if m:
            summary["passed"] = int(m.group(1))
            evidence.append(line)
            have_counts = True
            continue

        # gtest state machine: RUN -> OK/FAILED for a specific test name
        m = RUN_RE.match(line)
        if m:
            continue
        m = OK_RE.match(line)
        if m:
            add_case(m.group(1), "PASS")
            continue
        m = FAILED_CASE_RE.match(line)
        if m:
            add_case(m.group(1), "FAIL")
            continue

        # run_cpu.py / run_st.py per-case summary lines
        m = CASE_RE.match(line)
        if m:
            status = m.group(1).upper().replace("SKIPPED", "SKIP")
            name = m.group(2).rstrip(":")
            dur = float(m.group(3)) if m.group(3) else None
            add_case(name, status, dur)
            continue

        m = DEMO_RE.match(line)
        if m:
            add_case(f"demo:{m.group(2)}", m.group(1).upper())
            continue

        # sim_dsl.sh / pto-vmi per-case line: `PASS case0_…  compile=… launch=…`
        m = SIMDSL_RE.match(line)
        if m:
            status = m.group(1).upper().replace("SKIPPED", "SKIP")
            name = m.group(2)
            dur = float(m.group(4)) if m.group(4) else None
            add_case(name, status, dur)
            evidence.append(line)
            continue

    # Resolve summary from the case list when no gtest final-summary lines were seen.
    if not have_counts:
        passed = sum(1 for c in cases.values() if c["status"] == "PASS")
        failed = sum(1 for c in cases.values() if c["status"] == "FAIL")
        skipped = sum(1 for c in cases.values() if c["status"] == "SKIP")
        summary.update({"passed": passed, "failed": failed, "skipped": skipped})

    if "passed" not in summary:
        summary["passed"] = 0
    summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"]
    summary["status"] = "PASS" if summary["failed"] == 0 and summary["passed"] > 0 else (
        "FAIL" if summary["failed"] > 0 else "UNKNOWN"
    )

    return {
        "suite": suite,
        "summary": summary,
        "cases": [cases[n] for n in order],
        "evidence": evidence,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize a test log into a results JSON object.")
    ap.add_argument("--log", required=True, help="Raw log file to parse.")
    ap.add_argument("--suite", default="", help="Suite name to embed in the result.")
    ap.add_argument("--out", help="Write JSON to this path instead of stdout.")
    args = ap.parse_args(argv)

    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    result = parse_text(text, args.suite)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())