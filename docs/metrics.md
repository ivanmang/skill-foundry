# Report metrics — reference

The report now captures **performance metrics**, modeled on the
`vmi-dashboard` (CCE-vs-VMI CA report). This page is the reference for what
each metric means and how it's derived.

## Where the metrics come from

The `vmi-dashboard` compares **CCE vs VMI** per kernel on cycle-accurate (CA)
metrics extracted from `core0.veccore0.instr_log.dump` (and the popped log) by
`npu_skills/pto-as/ca-instruction-breakdown/scripts/ca_instr_analysis.py`.

The harness reuses the same vocabulary, but "per side" becomes **per suite**,
and the comparison becomes **current run vs pinned baseline**:

```text
vmi-dashboard:   CCE kernel  vs  VMI kernel        (same functionality, two lowerings)
regression:      current run vs  baseline          (same suite, two points in time)
```

## Metric schema (per suite)

Recorded in `run.json` under `suites[].perf` when a CA instruction dump is
present (`skill_foundry/lib/perf_metrics.py`); omitted otherwise.

### Instruction counts (by unit)

| Key | CA unit | Category | Meaning |
|---|---|---|---|
| `ex` | `RVECEX` | vec_compute | vector compute (VMUL/VCVT/VDINTLV/PSET…) |
| `su` | `RVECSU` | store_desc | scalar store-descriptor setup |
| `ld` | `RVECLD` | vec_load | vector load (VLD) |
| `st` | `RVECST` | vec_store | vector store data (VST) |
| `pred` | `PUSHQ` | predicate | push predicate block |
| `scalar` | `SCALAR` | scalar | addr / loop setup |
| `dma` | `MTE2` | dma | GM↔UB DMA |
| `flowctrl` / `membar` | `FLOWCTRL` | flowctrl / membar | control flow + memory barriers |

### EX subcategories (`ex_arith`, `ex_cast`, `ex_broadcast`, `ex_select_cmp`, `ex_reduce`, `ex_interleave`, `ex_pred_setup`, `ex_control`)

Where the vector-compute instructions went — critical for understanding an
"EX explosion" (e.g. extra casts from a missing fused op).

### Pipeline & stalls

| Key | Meaning |
|---|---|
| `dual` | instructions issued in the same tick (dual-issue pairs) |
| `max_issue` | max instructions issued at one tick (issue width) |
| `stalls` | tick gaps >1 between consecutive vector-pipe instructions |
| `ex_stalls` | gaps between consecutive `RVECEX` instructions |
| `max_stall` | largest gap (cycles) |
| `top_stall` | `UNIT:op→UNIT:op=Nc` for the largest gap (e.g. `ST:RV_VST→RV_VST=18c`) |

### IPC & cycles

| Key | Meaning |
|---|---|
| `vf_real` | `vf_real_execute_time` — VF real cycles (the true latency) |
| `vf_execute` | `vf_execute_time` |
| `instr_num` | VF instruction count (hex from the summary line) |
| `ipc` | `instr_num / vf_real` |
| `ex_ipc` | `ex / vf_real` — compute-only IPC |

### Timing (always available)

`suites[].timing` — per-case duration stats from the normalized case list:
`cases`, `min`, `p50`, `p99`, `max`, `mean`. Present for any gtest-style run,
even when no CA dump exists.

## Regression thresholds (diff vs baseline)

`skill_foundry/workflow/review.py` flags a perf regression when:

| Metric | Direction | Threshold |
|---|---|---|
| `p99` (case duration) | up | > +15% (even if avg is stable) |
| `vf_real` (cycles) | up | > +15% |
| `ex` (instructions) | up | > +15% |
| `ipc` | down | < -15% |
| `ex_ipc` | down | < -15% |

## Report sections

`python3 -m skill_foundry.workflow.report` renders:

1. **Summary** — per-suite pass/fail/skip/total/status/duration.
2. **Failures** — failed cases, annotated **known** when matched.
3. **Timing (per-case)** — min / p50 / p99 / max per suite.
4. **Performance (CA metrics)** — the table above, only when dumps are present.

## Why these metrics (the important ones)

From the vmi-dashboard, the metrics that actually catch regressions are:

- **Correctness** (PASS/FAIL) — the hard signal (already tracked).
- **`vf_real`** — real cycles; wall-clock hides this on noisy machines.
- **`ex` + EX subcategories** — an instruction-count jump means the lowering got
  worse (e.g. lost a fused op, or extra casts), even if cycles happen to stay flat.
- **`ipc` / `ex_ipc`** — issue efficiency; a drop means the scheduler is stalling.
- **`dual` / `stalls` / `top_stall`** — *where* the cycles went (PLT vs VDUPS etc.).

Rule: never trust wall-clock alone — the same "p99 +15%" discipline applies to
`vf_real`, `ex`, and `ipc`.
