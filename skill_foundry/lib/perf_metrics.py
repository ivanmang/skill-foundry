#!/usr/bin/env python3
"""Performance metrics for the skill-foundry — modeled on the vmi-dashboard.

Mirrors `npu_skills/pto-as/ca-instruction-breakdown/scripts/ca_instr_analysis.py`
(the authoritative extractor). "Per side" becomes "per suite" (current run vs
pinned baseline), and the output is **holistic** so an LLM (or human) can reason
about it directly:

  - per-case (per-kernel) detail, not just a suite rollup
  - per-opcode instruction counts (which opcodes exploded)
  - EX subcategory breakdown (cast/broadcast/reduce/…)
  - dual-issue combo breakdown (EX+EX, LD+EX …)
  - latency per unit (max_gap / avg_gap / span)
  - stall sources: stall_targets (which opcodes stall) + top long_stalls chains
  - cycle breakdown: vf_real, vf_compute_span, ex_span, mte2_wait
  - IPC: ipc = total_rvec/vf_compute_span · ex_ipc = ex/ex_span ·
         ex_issue_eff = ex/vf_compute_span
"""

from __future__ import annotations

import glob
import math
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

LINE_RE = re.compile(
    r"^\[info\]\s+\[(\d+)\]\s+\(PC:\s+0x[0-9a-fA-F]+\)\s+([A-Z][A-Z0-9]*)\s*:\s+"
    r"\(Binary:\s+0x[0-9a-fA-F]+\s*\)\s+\(ID:\s+(\d+)\)\s+(\S+)"
)
VF_REAL_RE = re.compile(r"vf_real_execute_time:\s*(\d+)")
VF_EXEC_RE = re.compile(r"vf_execute_time:\s*(\d+)")
VF_INSTR_RE = re.compile(r"instr_num:\s*0x([0-9a-fA-F]+)")

RVEC_UNITS = {"RVECEX", "RVECSU", "RVECLD", "RVECST"}
LONG_STALL_THRESH = {"RVECEX": 4, "RVECLD": 8, "RVECST": 8, "RVECSU": 8}

EX_SUBCAT_KEYS = [
    "ex_arith", "ex_cast", "ex_broadcast", "ex_select_cmp",
    "ex_reduce", "ex_interleave", "ex_pred_setup",
]

CATEGORIES = ("ex", "su", "ld", "st", "pred", "scalar", "dma", "flowctrl", "membar", "control")


def _classify(unit: str, op: str) -> tuple[str | None, str]:
    """Return (category, subcategory) exactly like ca_instr_analysis.categorize."""
    n = op.upper()
    if unit == "PUSHQ":
        if "PUSH_PB" in n:
            return ("pred", "push_pb")
        if n.startswith("VF"):
            return (None, "vf_summary")
        return ("pred", "other_pushq")
    if unit in ("MTE2", "MTE3"):
        return ("dma", unit.lower())
    if unit == "FLOWCTRL":
        if "FLAG" in n:
            return ("membar", "flag_sync")
        if "DCCI" in n or "CACHE" in n:
            return ("membar", "cache_flush")
        return ("flowctrl", "ctrl")
    if unit == "SCALAR":
        return ("scalar", "addr_loop")
    if unit == "RVECEX":
        if n.startswith("SIMT_F"):
            if n.startswith(("SIMT_FCVT", "SIMT_F2F", "SIMT_F2I")):
                return ("ex", "ex_cast")
            if n.startswith(("SIMT_FSEL", "SIMT_FCMP")):
                return ("ex", "ex_select_cmp")
            return ("ex", "ex_arith")
        if n.startswith("SIMT_"):
            return ("control", "addr")
        if n in ("FCVT", "F2F", "F2I", "I2F"):
            return ("ex", "ex_cast")
        if n in ("IMAD", "IMAD_X", "LEA", "MAD"):
            return ("control", "addr")
        if n.startswith("RV_VCVT"):
            return ("ex", "ex_cast")
        if n.startswith(("RV_VCMAX", "RV_VCMIN", "RV_VRSUM", "RV_VRMAX", "RV_VRMIN")):
            return ("ex", "ex_reduce")
        if n.startswith(("RV_VBR", "RV_VDUP", "RV_VDUPS", "RV_VBCAST")):
            return ("ex", "ex_broadcast")
        if n.startswith(("RV_VSEL", "RV_VCMP")):
            return ("ex", "ex_select_cmp")
        if n.startswith(("RV_VINTER", "RV_VDEINT", "RV_VINTLV")):
            return ("ex", "ex_interleave")
        if n.startswith(("RV_PSET", "RV_PRED")):
            return ("ex", "ex_pred_setup")
        return ("ex", "ex_arith")
    if unit == "RVECST":
        return ("st", "send" if n == "RV_SEND" else "vst")
    if unit == "RVECSU":
        return ("su", "send" if n == "RV_SEND" else "su")
    if unit == "RVECLD":
        return ("ld", "vld")
    return (None, "")


def duration_stats(cases: list[dict]) -> dict:
    durs: list[float] = []
    for c in cases:
        d = c.get("duration_s")
        if isinstance(d, (int, float)):
            durs.append(float(d))
    durs.sort()
    if not durs:
        return {"cases": 0, "min": None, "p50": None, "p99": None, "max": None, "mean": None}
    n = len(durs)
    if all(d == 0.0 for d in durs):
        return {"cases": n, "min": None, "p50": None, "p99": None, "max": None, "mean": None}
    return {
        "cases": n,
        "min": round(durs[0], 4),
        "p50": round(durs[math.ceil(n * 0.50) - 1], 4),
        "p99": round(durs[math.ceil(n * 0.99) - 1], 4),
        "max": round(durs[-1], 4),
        "mean": round(sum(durs) / n, 4),
    }


def parse_ca_dump(path: Path) -> dict | None:
    """Parse one core0.veccore0.* dump into the full authoritative CA structure."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    category_counts: Counter = Counter()
    subcategory_counts: Counter = Counter()
    raw_unit_counts: Counter = Counter()
    instr_counts: dict[str, Counter] = defaultdict(Counter)

    vec_records: list[tuple[int, str, str, str | None, str]] = []  # tick,unit,op,cat,sub
    ex_ticks: list[int] = []
    rvec_ticks: list[int] = []
    wait_ticks: list[int] = []
    seen_send: set[tuple[int, int]] = set()
    total_records = 0
    vf_real = vf_execute = instr_num = None

    for line in text.splitlines():
        m = LINE_RE.match(line.strip())
        if m:
            tick = int(m.group(1))
            unit = m.group(2)
            inst_id = int(m.group(3))
            op = m.group(4)
            total_records += 1
            raw_unit_counts[unit] += 1
            instr_counts[unit][op.upper()] += 1
            if op.upper() == "RV_SEND":
                key = (inst_id, tick)
                if key in seen_send:
                    continue
                seen_send.add(key)
            cat, sub = _classify(unit, op)
            if cat:
                category_counts[cat] += 1
            if sub:
                subcategory_counts[sub] += 1
            if unit in RVEC_UNITS:
                vec_records.append((tick, unit, op, cat, sub))
                rvec_ticks.append(tick)
                if cat == "ex":
                    ex_ticks.append(tick)
            if "WAIT_FLAG" in op.upper():
                wait_ticks.append(tick)
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

    # dual-issue (ticks issuing >1 unique-ID instruction, VF vector pipe)
    by_tick: dict[int, list[str]] = defaultdict(list)
    for tick, unit, op, cat, sub in vec_records:
        by_tick[tick].append(unit)
    dual_ticks = {t: v for t, v in by_tick.items() if len(v) > 1}
    dual_issue_count = len(dual_ticks)
    dual_instr_count = sum(len(v) for v in dual_ticks.values())
    combo_counts: Counter = Counter()
    for v in dual_ticks.values():
        combo_counts["+".join(sorted(set(v)))] += 1
    max_per_tick = max((len(v) for v in dual_ticks.values()), default=0)

    # latency + stalls (same-unit tick gaps, thresholds)
    per_unit: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for tick, unit, op, cat, sub in vec_records:
        if unit in RVEC_UNITS:
            per_unit[unit].append((tick, op))
    latency: dict[str, dict] = {}
    long_stalls: list[tuple[str, str, str, int]] = []
    ex_long_stalls: list[tuple[str, str, str, int]] = []
    for unit in sorted(RVEC_UNITS):
        seq = per_unit.get(unit, [])
        gaps = [seq[i][0] - seq[i - 1][0] for i in range(1, len(seq))]
        for i in range(1, len(seq)):
            gap = seq[i][0] - seq[i - 1][0]
            if gap >= LONG_STALL_THRESH.get(unit, 8):
                stall = (unit, seq[i - 1][1], seq[i][1], gap)
                long_stalls.append(stall)
                if unit == "RVECEX":
                    ex_long_stalls.append(stall)
        latency[unit] = {
            "count": len(seq),
            "max_gap": max(gaps) if gaps else 0,
            "avg_gap": round(sum(gaps) / len(gaps), 2) if gaps else 0,
            "span": (seq[-1][0] - seq[0][0]) if len(seq) > 1 else 0,
        }
    long_stalls.sort(key=lambda s: -s[3])
    stall_targets = dict(sorted(Counter(s[2] for s in long_stalls).items(), key=lambda kv: -kv[1])[:12])

    # cycle fields
    vf_compute_span = (max(rvec_ticks) - min(rvec_ticks)) if rvec_ticks else 0
    ex_span = (max(ex_ticks) - min(ex_ticks)) if len(ex_ticks) > 1 else 0
    first_rvec = min(rvec_ticks) if rvec_ticks else None
    last_wait_before = None
    for w in wait_ticks:
        if first_rvec is not None and w < first_rvec:
            last_wait_before = w
    mte2_wait = (first_rvec - last_wait_before) if (first_rvec is not None and last_wait_before is not None) else None

    ex_count = category_counts.get("ex", 0)
    total_rvec = (category_counts.get("ex", 0) + category_counts.get("su", 0)
                  + category_counts.get("ld", 0) + category_counts.get("st", 0))
    if vf_compute_span:
        overall_ipc = round(total_rvec / vf_compute_span, 3)
    elif vf_real:
        overall_ipc = round(total_rvec / vf_real, 3)
    else:
        overall_ipc = None
    ex_ipc = round(ex_count / ex_span, 3) if ex_span else None
    ex_issue_eff = round(ex_count / vf_compute_span, 3) if vf_compute_span else None

    return {
        "dump": path.name,
        "total_records": total_records,
        "vf_records": len(vec_records),
        "category_counts": dict(sorted(category_counts.items(), key=lambda kv: -kv[1])),
        "subcategory_counts": dict(sorted(subcategory_counts.items(), key=lambda kv: -kv[1])),
        "instr_counts": {u: dict(sorted(d.items(), key=lambda kv: -kv[1]))
                         for u, d in sorted(instr_counts.items())},
        "dual_issue": {
            "dual_ticks": dual_issue_count,
            "dual_instr_count": dual_instr_count,
            "combo_counts": dict(sorted(combo_counts.items(), key=lambda kv: -kv[1])),
            "max_per_tick": max_per_tick,
        },
        "latency": latency,
        "stalls": len(long_stalls),
        "ex_stalls": len(ex_long_stalls),
        "long_stalls": long_stalls[:20],
        "ex_long_stalls": ex_long_stalls[:20],
        "stall_targets": stall_targets,
        "timing": {
            "vf_real": vf_real,
            "vf_execute": vf_execute,
            "instr_num": instr_num,
            "vf_compute_span": vf_compute_span,
            "ex_span": ex_span,
            "mte2_wait": mte2_wait,
            "ex": ex_count,
            "total_rvec": total_rvec,
            "ipc": overall_ipc,
            "ex_ipc": ex_ipc,
            "ex_issue_eff": ex_issue_eff,
        },
    }


def _find_dumps(run_dir: Path, suite_name: str) -> list[Path]:
    found: list[Path] = []
    for pattern in ("**/core0.veccore0.instr_log.dump", "**/*instr_log.dump", "**/instr.bin"):
        found.extend(run_dir.glob(pattern))
    return sorted(set(found))


def collect_perf(run_dir: Path, suite_name: str) -> dict | None:
    """Aggregate CA metrics across dumps; returns a flat suite rollup + per_case detail."""
    dumps = _find_dumps(run_dir, suite_name)
    if not dumps:
        return None
    per_case: list[dict] = []
    for p in dumps:
        m = parse_ca_dump(p)
        if m:
            per_case.append(m)
    if not per_case:
        return None

    # ── suite rollup (flat keys for the table) ──
    ex = su = ld = st = pred = scalar = dma = flowctrl = membar = control = 0
    dual = max_issue = stalls = ex_stalls = 0
    vf_real = vf_execute = instr_num = vf_compute_span = ex_span = mte2_wait = 0
    stall_targets: Counter = Counter()
    combo_counts: Counter = Counter()
    subcounts: Counter = Counter()
    top_long_stalls: list[tuple[str, str, str, int]] = []
    max_stall = 0
    for c in per_case:
        k = c["category_counts"]
        ex += k.get("ex", 0)
        su += k.get("su", 0)
        ld += k.get("ld", 0)
        st += k.get("st", 0)
        pred += k.get("pred", 0)
        scalar += k.get("scalar", 0)
        dma += k.get("dma", 0)
        flowctrl += k.get("flowctrl", 0)
        membar += k.get("membar", 0)
        control += k.get("control", 0)
        d = c["dual_issue"]
        dual += d["dual_instr_count"]
        max_issue = max(max_issue, d["max_per_tick"])
        for cb, n in d["combo_counts"].items():
            combo_counts[cb] += n
        stalls += c["stalls"]
        ex_stalls += c["ex_stalls"]
        for t, n in c["stall_targets"].items():
            stall_targets[t] += n
        for s, n in c["subcategory_counts"].items():
            subcounts[s] += n
        top_long_stalls.extend(c["long_stalls"])
        tm = c["timing"]
        vf_real += tm.get("vf_real") or 0
        vf_execute += tm.get("vf_execute") or 0
        instr_num += tm.get("instr_num") or 0
        vf_compute_span += tm.get("vf_compute_span") or 0
        ex_span += tm.get("ex_span") or 0
        if tm.get("mte2_wait") is not None:
            mte2_wait += tm["mte2_wait"]
    top_long_stalls.sort(key=lambda s: -s[3])
    top_stall = (f"{top_long_stalls[0][0]}:{top_long_stalls[0][1]}→"
                 f"{top_long_stalls[0][0]}:{top_long_stalls[0][2]}={top_long_stalls[0][3]}c") if top_long_stalls else None
    max_stall = top_long_stalls[0][3] if top_long_stalls else 0

    total_rvec = ex + su + ld + st
    span = vf_compute_span
    if span:
        ipc = round(total_rvec / span, 3) if total_rvec else None
        ex_issue_eff = round(ex / span, 3) if ex else None
    elif vf_real:
        ipc = round(total_rvec / vf_real, 3) if total_rvec else None
        ex_issue_eff = None
    else:
        ipc = ex_issue_eff = None
    ex_ipc = round(ex / ex_span, 3) if ex_span else None

    return {
        # flat (report table)
        "ex": ex, "su": su, "ld": ld, "st": st, "pred": pred, "scalar": scalar,
        "dma": dma, "dual": dual, "stalls": stalls, "max_issue": max_issue,
        "max_stall": max_stall, "top_stall": top_stall,
        "ipc": ipc, "ex_ipc": ex_ipc, "ex_issue_eff": ex_issue_eff,
        "vf_real": vf_real or None, "vf_execute": vf_execute or None,
        "instr_num": instr_num or None, "vf_compute_span": span or None,
        "ex_span": ex_span or None, "mte2_wait": mte2_wait or None,
        "flowctrl": flowctrl, "membar": membar, "control": control,
        # holistic / LLM-analysis
        "cases": len(per_case),
        "stall_targets": dict(sorted(stall_targets.items(), key=lambda kv: -kv[1])[:12]),
        "dual_combos": dict(sorted(combo_counts.items(), key=lambda kv: -kv[1])),
        "subcategory_counts": dict(sorted(subcounts.items(), key=lambda kv: -kv[1])),
        "long_stalls": top_long_stalls[:20],
        "per_case": per_case,
    }


def copy_perf(repo: Path, run_dir: Path, suite_name: str,
              patterns: list[str] | None, testcase: str | None) -> None:
    if not patterns:
        return
    dest = run_dir / suite_name / "perf"
    dest.mkdir(parents=True, exist_ok=True)
    stem = Path(testcase).stem if testcase else "all"
    sub = {"repo": str(repo), "testcase": testcase or "all", "testcase_stem": stem}
    for pat in patterns:
        g = pat.format(**sub)
        if not Path(g).is_absolute():
            g = str(repo / g)
        matches = sorted(glob.glob(g), key=os.path.getmtime, reverse=True)
        if not matches:
            continue
        if Path(matches[0]).is_dir():
            for f in (Path(matches[0]).iterdir() if Path(matches[0]).is_dir() else []):
                if f.is_file() and f.name.startswith("core0.veccore0"):
                    shutil.copy2(f, dest / f.name)
        else:
            for m in matches:
                if Path(m).name.startswith("core0.veccore0"):
                    shutil.copy2(m, dest / Path(m).name)


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Extract holistic CA metrics from a run dir.")
    ap.add_argument("run_dir", help="reports/<run-id>")
    ap.add_argument("--suite", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--per-case", action="store_true", help="Print per-case detail.")
    args = ap.parse_args()
    perf = collect_perf(Path(args.run_dir), args.suite or "")
    if perf is None:
        print("perf: None")
    elif args.per_case:
        print(json.dumps(perf["per_case"], indent=2))
    else:
        print(json.dumps({k: v for k, v in perf.items() if k != "per_case"}, indent=2))