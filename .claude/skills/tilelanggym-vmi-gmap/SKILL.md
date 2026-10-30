---
name: tilelanggym-vmi-gmap
description: >
  Use when tracking or closing MB-SV*-VMI-Gmap / SoftLib Gmap sweeps — classify
  functional PASS vs tried schedules vs best-sweep DONE per reduce_axis (inner
  VC/VCG vs outer VMAX); outer absmax-vs-Case-3 dual-era + VAND no-path goes to
  alternate-builder before DONE; measure until DONE or explicit stop — never
  treat UNMEASURED-only as success; dig-vs-live delta checklist when el/cyc
  moves vs prior SoT.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Outer suite gate: sv567-nx1-outer.
category: perf-analysis
origin: native
---

# tilelangGym VMI Gmap close

## reduce_axis

| Axis | Opcode family | Notes |
|------|---------------|-------|
| inner (1×G) | VC / VCGMAX family | From lowering; sub-vreg → VCGMAX not wish-name VCMAX |
| outer (N×1) | **pure VMAX** fold | No VC/VCG as reduce; dual-era required |

## Outer dual-era + VAND

Before outer DONE:

1. `vmi_outer_era_absmax_only` and `vmi_outer_era_case3_recip` tracked separately (`era=`).
2. Prefer `vmi_outer_vand_i32`; if VAND no-path → **required**
   `vmi_outer_vand_alternate_builder` attempt before accepting VABS-only DONE.
3. Never crown Case-3+VABS as absmax-only SoT.

## Gate

```bash
export TILELANGGYM_PACK=/path/to/nx1-pack
python3 -m skill_foundry.workflow.run --target tilelangGym --suite sv567-nx1-outer
```

Motif tags: `hub/tilelanggym/MOTIF_SEED_SV567_absmax.md` (VMI outer section).
