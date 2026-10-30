---
name: tilelanggym-semantics-gate
description: >
  Use before any SoftLib/SIMD close-loop claim in a tilelangGym ST ANALYSIS or
  RESULT — run SEMANTICS_GATE S1-S4 and emit PASS|INCONCLUSIVE|wrong-arm; reject
  shared-VF + post-VF-gold as G-sensitivity; opcode must match lowering (VCMAX
  wish-name vs VCGMAX); no SoftLib/VMI ranking without era=; reject unlabeled
  SoftLib SIMT Nx1 vs 1xG merge; reject outer-axis Nx1 using VCGMAX/VCMAX or
  reused inner Gmap SoT. SoftLib≻SIMD publish still requires st-report PR9
  overlays both arms.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Pair with tilelanggym-st-report.
category: perf-analysis
---

# tilelangGym SEMANTICS_GATE

**When:** Before any SoftLib / SIMD / ST sentence that says closed / SoT / G-sensitivity done.

## Verdict line

```
SEMANTICS_GATE: PASS | INCONCLUSIVE | wrong-arm — <one clause why>
```

## Checks

| # | Check | Fail |
|---|-------|------|
| S1 | Gold vs Aims gold G | Wrong G packed |
| S2 | VF body changes with G | Only GOLD_G / post-VF tree-max → wrong-arm |
| S3 | Instr mix from lowering; opcode matches reduce_axis | Outer uses VC/VCG as reduce → wrong-arm |
| S4 | Log ↔ compute | Flat VF_cyc across G when Aims need G-dep → INCONCLUSIVE |

## Forbidden

- SoftLib÷VMI ranking without `era=` (Case-3 recip ≠ absmax-only).
- Outer Nx1 SoT reusing inner 1×G Gmap or VCGMAX/VCMAX as reduce.
- SoftLib≻SIMD publish without PR9 both arms (`tilelanggym-st-report`).
