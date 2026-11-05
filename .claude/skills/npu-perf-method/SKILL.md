---
name: npu-perf-method
description: >
  Use when estimating vector-kernel cycles before measuring, diagnosing which
  resource bounds a kernel (roofline), or reviewing store patterns: resource
  budget model, store-cost cliff, LNEXP per-slot vs per-core, i-cache proof
  pattern. Companion to measurement — never a substitute.
category: perf-optimize
license: CANN Open Software License Agreement Version 2.0
origin: native
maturity: ready
owner: skill-foundry
---

# Performance method: roofline first, then the specific cliff

## Resource budget (A5; A6 adds the LNQ lane)
kernel time ≈ max(EXU_cyc, LSU_load 512 B/c, LSU_store 256 B/c, MTE2/3).
EXU_cyc (A5) = ceil(SLIDE_count) + ceil((ADD+MUL)/2); (A6) =
max(ceil(SLIDE+LNEXP on LNQ), ceil((ADD_CONV+MUL+MOV)/2)).

## Store-cost cliff (R9, measured: predicts within 1–6%)
`per_iter = max(EXU_cyc, ST_count × 5.5)` when stores/iter > 2. ≥3 PK4_B32
stores/iter = 2.4–5.2× measured slowdown; vor-merge PART channels in registers
(3 ADD ≈ 1.5 cyc) before ONE store. A6 constant not re-derived — measure first.

## LNEXP (A6): judge per-core, not per-slot
Per-slot thpt drops (VEXP f16 8→2, f32 4→2 per the VALU table) BUT A5 issues
from both EXQs vs A6's single LNQ; exp now contends only with SLIDE. Core-level
capacity: open re-measurement — do not assume halved.

## I-cache proof pattern (measure → attribute → fix)
Body growth past the i-cache costs exactly the miss cycles: measured
456→926 (+103%) = 441 `c_cycle_icache_miss`; 926−441=485 ≈ the 486-tick
auto-advancing-pointer variant. Arithmetic closes ⇒ causal, not correlational.

## Discipline
Static findings are hypothesis-level: measure E2E after every change; ticks are
data-independent but verdicts are only as real as the golden underneath.

## Gotchas

- Drafted hub/inbox/npu-perf-method/SKILL.md: resource budget (A5+A6 EXU formulas), store cliff, LNEXP framing, i-cache proof pattern, discipline. Sources: npu_skills R6/R9, performance/prediction, pto-vmi measured campaigns. (was: Performance work jumps to micro-tuning without a roofline (fixing EXU instructions on an LSU-bound kernel), uses a flat per_iter=max(EXU,LSU) model that misses the store-queue cliff, reads LNEXP per-slot throughput as core capacity, and accepts correlational icache stories without arithmetic closure.) — `dissection of npu_skills + pto-vmi campaigns (2026-11-04)`
