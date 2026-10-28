#!/usr/bin/env python3
"""Performance metrics for the regression harness — modeled on the vmi-dashboard.

The vmi-dashboard compares CCE vs VMI per kernel on cycle-accurate (CA) metrics:
  - unit counts:      EX (RVECEX) / SU / LD / ST / predicate / scalar / dma / flowctrl / membar
  - EX subcategories: arith / cast / broadcast / select_cmp / reduce / interleave / pred_setup / control
  - pipeline:         dual-issue width, stalls, ex_stalls, max_stall, top_stall string
  - IPC / cycles:     ipc, ex_ipc, vf_real (VF real cycles), instr_num, mte2_wait

For the harness, "per side" becomes "per suite" (current run vs pinned baseline).
Where the CA simulator writes `core0.veccore0.instr_log.dump`, `collect_perf()`
extracts the same metrics; where it doesn't (e.g. cpu-st, or no dump), the
perf section is simply omitted (None).

Also provides `duration_stats()` for per-case timing (p50/p99/max) from the
normalized case list, which is always available for gtest-style runs.
"""

from __future__ import annotations

import glob
import math
import os
import re
import shutil
from pathlib import Path

# Line in a core0.veccore0 instr dump:
#   [info] [tick] (PC: 0x…) UNIT: (Binary: 0x…) (ID: N) OPCODE
LINE_RE = re.compile(
    r"^\[info\]\s+\[(\d+)\]\s+\(PC:\s+0x[0-9a-fA-F]+\)\s+([A-Z][A-Z0-9]*)\s*:\s+"
    r"\(Binary:\s+0x[0-9a-fA-F]+\s*\)\s+\(ID:\s+(\d+)\)\s+(\S+)"
)
VF_REAL_RE = re.compile(r"vf_real_execute_time:\s*(\d+)")
VF_EXEC_RE = re.compile(r"vf_execute_time:\s*(\d+)")
VF_INSTR_RE = re.compile(r"instr_num:\s*0x([0-9a-fA-F]+)")

UNIT_CATEGORY = {
    "RVECEX": "ex",
    "RVECSU": "su",
    "RVECLD": "ld",
    "RVECST": "st",
    "PUSHQ": "pred",
    "MTE2": "dma",
    "FLOWCTRL": "flowctrl",
    "SCALAR": "scalar",
}

EX_SUBCAT_KEYS = [
    "ex_arith", "ex_cast", "ex_broadcast", "ex_select_cmp",
    "ex_reduce", "ex_interleave", "ex_pred_setup", "ex_control",
]

PERF_KEYS = [
    "ex", "su", "ld", "st", "pred", "scalar", "dma", "flowctrl", "membar",
    "dual", "max_issue", "stalls", "ex_stalls", "max_stall", "top_stall",
    "ipc", "ex_ipc", "vf_real", "vf_execute", "instr_num",
    *EX_SUBCAT_KEYS, "cases",
]


def _ex_subcat(op: str) -> str:
    """Classify an RVECEX opcode into a subcategory (mirrors ca_instr_analysis.py)."""
    n = op.upper()
    if n.startswith("SIMT_F"):
        if n.startswith(("SIMT_FCVT", "SIMT_F2F", "SIMT_F2I")):
            return "ex_cast"
        if n.startswith(("SIMT_FSEL", "SIMT_FCMP")):
            return "ex_select_cmp"
        return "ex_arith"
    if n.startswith("SIMT_"):
        return "ex_control"
    if n in ("FCVT", "F2F", "F2I", "I2F"):
        return "ex_cast"
    if n.startswith("RV_VCVT"):
        return "ex_cast"
    if n.startswith(("RV_VCMAX", "RV_VCMIN", "RV_VRSUM", "RV_VRMAX", "RV_VRMIN")):
        return "ex_reduce"
    if n.startswith(("RV_VBR", "RV_VDUP", "RV_VDUPS", "RV_VBCAST")):
        return "ex_broadcast"
    if n.startswith(("RV_VSEL", "RV_VCMP")):
        return "ex_select_cmp"
    if n.startswith(("RV_VINTER", "RV_VDEINT", "RV_VINTLV")):
        return "ex_interleave"
    if n.startswith(("RV_PSET", "RV_PRED")):
        return "ex_pred_setup"
    return "ex_arith"


def duration_stats(cases: list[dict]) -> dict:
    """Per-case timing stats: min/p50/p99/max/mean + count of measured cases."""
    durs = sorted(c.get("duration_s") for c in cases if c.get("duration_s") is not None)
    if not durs:
        return {"cases": 0, "min": None, "p50": None, "p99": None, "max": None, "mean": None}
    n = len(durs)
    p50 = durs[math.ceil(n * 0.50) - 1]
    p99 = durs[math.ceil(n * 0.99) - 1]
    return {
        "cases": n,
        "min": round(durs[0], 4),
        "p50": round(p50, 4),
        "p99": round(p99, 4),
        "max": round(durs[-1], 4),
        "mean": round(sum(durs) / n, 4),
    }


def parse_ca_dump(path: Path) -> dict | None:
    """Parse one core0.veccore0.* dump into vmi-dashboard-style metrics, or None."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    counts = {k: 0 for k in UNIT_CATEGORY.values()}
    counts["membar"] = 0
    ex_sub = {k: 0 for k in EX_SUBCAT_KEYS}
    tick_buckets: dict[int, int] = {}
    ex_ticks: list[int] = []
    vec_ticks: list[tuple[int, str, str]] = []  # (tick, unit, op) on the vector pipe
    vf_real = vf_execute = instr_num = None

    for line in text.splitlines():
        m = LINE_RE.match(line.strip())
        if m:
            tick = int(m.group(1))
            unit = m.group(2)
            op = m.group(4)
            cat = UNIT_CATEGORY.get(unit)
            if cat == "ex":
                counts["ex"] += 1
                ex_sub[_ex_subcat(op)] += 1
                ex_ticks.append(tick)
            elif cat:
                counts[cat] += 1
            if unit == "FLOWCTRL" and ("FLAG" in op.upper() or "CACHE" in op.upper() or "DCCI" in op.upper()):
                counts["membar"] += 1
            if unit in ("RVECEX", "RVECSU", "RVECLD", "RVECST"):
                vec_ticks.append((tick, unit, op))
                tick_buckets[tick] = tick_buckets.get(tick, 0) + 1
            continue
        m = VF_REAL_RE.search(line)
        if m:
            vf_real = int(m.group(1))
            continue
        m = VF_EXEC_RE.search(line)
        if m:
            vf_execute = int(m.group(1))
            continue
        m = VF_INSTR_RE.search(line)
        if m:
            instr_num = int(m.group(1), 16)

    # dual-issue: instrs sharing a tick
    dual = sum(v - 1 for v in tick_buckets.values() if v > 1)
    max_issue = max(tick_buckets.values()) if tick_buckets else 0

    # stalls: gaps between consecutive vector-pipe instrs (same pipe, tick gap > 1)
    stalls = 0
    ex_stalls = 0
    max_stall = 0
    top_stall = None
    for i in range(1, len(vec_ticks)):
        t0, u0, op0 = vec_ticks[i - 1]
        t1, u1, op1 = vec_ticks[i]
        gap = t1 - t0
        if gap > 1:
            stalls += 1
            if u0 == u1 == "RVECEX":
                ex_stalls += 1
            if gap > max_stall:
                max_stall = gap
                top_stall = f"{u0}:{op0}→{u1}:{op1}={gap}c"

    ipc = ex_ipc = None
    if vf_real:
        if instr_num:
            ipc = round(instr_num / vf_real, 3)
        if counts["ex"]:
            ex_ipc = round(counts["ex"] / vf_real, 3)

    out = {
        **counts,
        **ex_sub,
        "dual": dual,
        "max_issue": max_issue,
        "stalls": stalls,
        "ex_stalls": ex_stalls,
        "max_stall": max_stall,
        "top_stall": top_stall,
        "ipc": ipc,
        "ex_ipc": ex_ipc,
        "vf_real": vf_real,
        "vf_execute": vf_execute,
        "instr_num": instr_num,
        "cases": 1,
    }
    return out if counts["ex"] or counts["ld"] or counts["st"] else None


def _find_dumps(run_dir: Path, suite_name: str) -> list[Path]:
    """Locate CAModel instruction dumps for the given suite run."""
    found: list[Path] = []
    for pattern in ("**/core0.veccore0.instr_log.dump", "**/*instr_log.dump", "**/instr.bin"):
        found.extend(run_dir.glob(pattern))
    return sorted(set(found))


def collect_perf(run_dir: Path, suite_name: str) -> dict | None:
    """Aggregate CA metrics across all dumps found for a suite; None if absent."""
    dumps = _find_dumps(run_dir, suite_name)
    if not dumps:
        return None
    agg: dict = {k: 0 for k in PERF_KEYS if k not in ("top_stall",)}
    agg["cases"] = 0
    for p in dumps:
        m = parse_ca_dump(p)
        if not m:
            continue
        agg["cases"] += 1
        for k in agg:
            if k == "top_stall":
                continue
            v = m.get(k)
            if isinstance(v, (int, float)):
                agg[k] += v
    if not agg["cases"]:
        return None
    # ratios recomputed over the aggregate
    vf_real = agg.get("vf_real")
    instr_num = agg.get("instr_num")
    if vf_real:
        agg["ipc"] = round(instr_num / vf_real, 3) if instr_num else None
        agg["ex_ipc"] = round(agg["ex"] / vf_real, 3) if agg["ex"] else None
    return agg


def copy_perf(repo: Path, run_dir: Path, suite_name: str,
              patterns: list[str] | None, testcase: str | None) -> None:
    """Copy the newest CAModel dumps (core0.veccore0.*) into run_dir/<suite>/perf/.

    patterns are globs relative to `repo`, supporting {repo}, {testcase},
    {testcase_stem}. A dir glob takes its newest matching directory; a file glob
    copies the newest matching files (filtered to core0.veccore0.* so the
    vector-pipe core is the one parsed).
    """
    if not patterns:
        return
    dest = run_dir / suite_name / "perf"
    dest.mkdir(parents=True, exist_ok=True)
    stem = Path(testcase).stem if testcase else "all"
    sub = {"repo": str(repo), "testcase": testcase or "all", "testcase_stem": stem}
    for pat in patterns:
        g = pat.format(**sub)
        matches = sorted(glob.glob(g), key=os.path.getmtime, reverse=True)
        if not matches:
            continue
        if Path(matches[0]).is_dir():
            src = Path(matches[0])
            for f in src.iterdir():
                if f.is_file() and f.name.startswith("core0.veccore0"):
                    shutil.copy2(f, dest / f.name)
        else:
            for f in matches:
                if Path(f).name.startswith("core0.veccore0"):
                    shutil.copy2(f, dest / Path(f).name)


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Extract CA metrics / timing from a run dir.")
    ap.add_argument("run_dir", help="reports/<run-id>")
    ap.add_argument("--suite", default=None, help="suite name")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rd = Path(args.run_dir)
    perf = collect_perf(rd, args.suite or "")
    print("perf:", None if perf is None else json.dumps(perf, indent=2))