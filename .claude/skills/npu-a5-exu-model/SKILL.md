---
name: npu-a5-exu-model
description: >
  Use when writing or scheduling A5 (NPU_ARCH 3101) CCE vector kernels: deciding
  which EXU an instruction issues on, whether ops dual-issue, why slide-heavy
  loops serialize, or balancing work across EXQ0/EXQ1. A5 facts, sim-validated;
  A6 deltas marked inline (see npu-a6-migration for the full A6 model).
category: ascendc-dev
license: CANN Open Software License Agreement Version 2.0
origin: native
maturity: ready
owner: skill-foundry
---

# A5 EXU issue model (validated on Ascend950PR_9599 sim)

## Structure
- **2 EXUs**: EXQ0 + EXQ1, depth 13 each, dual dispatch (`max_exq_disp_num=2`).
- **SLIDE exists only on EXU0** — it also steals EXU0's arithmetic dispatch slot.
- LSU separate (2 loads/cyc = 512 B/cyc, 1 store/cyc = 256 B/cyc, lat ~9).
- Registers: 32 architectural / 68 physical (OOO rename); 1 VREG write port/cyc.

## Routing (A5)
| Class | Instructions | Queue |
|---|---|---|
| ADD_CONV | vadd/vsub/vmax/vmin/vcvt/vcmp | EXQ0 ⇄ EXQ1 (round-robin) |
| MUL | vmul/vmadd | EXQ0 ⇄ EXQ1 |
| MOV | vand/vor/vmov/vshl/vsel | EXQ0 ⇄ EXQ1 |
| LNEXP | vexp/vln/vdiv/vsqrt (thpt 4 f32 per EXQ, both EXQs) | EXQ0 ⇄ EXQ1 |
| **SLIDE** | vintlv/vdintlv/vcmax/vcgmax/vpack/vselr | **EXQ0 only, 1/cyc, no dual-issue** |

## Working rules (from npu_skills R2/R5, sim-proven)
1. **Minimize SLIDE pressure**: every vintlv/vdintlv/vcmax on EXQ0 serializes and
   blocks EXQ0 arithmetic. Prefer LSU dist-modes (see npu-dist-modes), PART-mode
   converts, vertical (lane-local) folds over horizontal cascades.
2. **Balance remaining non-slide work 50/50 across EXQ0/EXQ1** — check PMU
   `exq0_*/exq1_*` (must not read 320:0).
3. Sub-unit pipelines inside one EXU overlap (`VCADD`(SLIDE)+`VADD`(ADD)
   co-resident on EXQ0); same sub-unit twice = `VALU_THRPUT_CFLT` stall.
4. Effective A5 service = 2 arithmetic lanes + 1 contended slide lane.

## Measured anchor
FP8-quant kernel: `exq0_fu_slide=320, exq1_fu_slide=0` — every demux/cascade op
serialized on one FU while EXU1 idled; demux-heavy kernels show EXUs 70–80% idle.
(A6: slide moved to its own LNQ — EXQ contention gone; see npu-a6-migration.)

## Gotchas

- Drafted hub/inbox/npu-a5-exu-model/SKILL.md: routing table, working rules (R2/R5), measured anchor (exq0_fu_slide=320/exq1=0; demux kernels 70-80% EXU idle). Source: npu_skills kernel-writing-rules + instruction-families. (was: Agents writing A5 vector kernels have no scoped skill stating the 2-EXU issue model (SLIDE pinned to EXQ0 stealing its dispatch slot; ADD/MUL/MOV/LNEXP round-robin both EXQs; effective service = 2 arith lanes + 1 contended slide lane) and schedule slide-heavy loops as if ops dual-issue.) — `dissection of ChanKaLok/npu_skills case-writing (2026-11-04)`
