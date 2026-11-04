---
name: tilelanggym-simd-per-g-mapping
description: >
  Use when optimizing or closing SoftLib/CCE or VMI PTO-DSL SIMD reduce for a
  gold group size G — pick opcode by reduce_axis (inner→VC/VCGMAX, outer→VMAX-only,
  Harness §22); explore per-G VL×datablock×gold G; Case-3 pack_ub/keeplive ladder;
  NG=8-first VL=8×G (t593u) + Top-3 VL×G sensitivity guesses (t591u); stage×VL-util
  (PRC-SCH-003).
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Facts in harness/PRC — no dig el/cyc in this file.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# tilelangGym SIMD per-G mapping

**When:** SoftLib/CCE MicroAPI or VMI PTO-DSL absmax/reduce work for a named **gold G**; or rewriting ANALYSIS that claims SIMD SoT per G.

**Companions:** `tilelanggym-st-semantics-gate`; `tilelanggym-reduce-dual-issue-recipes`; `tilelanggym-vmi-gmap-close`; **`tilelanggym-softlib-simt-schedule`** for SoftLib SIMT (Harness §20).

## Goal

For **each** gold G, find the **most optimized** SIMD version under Aims — usually on **VMI PTO-DSL** first. SoftLib SIMT is a **separate** arm with its own motif/schedule matrix — do not close it with stock or one contig row.

## SoftLib CCE vs SoftLib SIMT vs VMI

| Track | Policy |
|-------|--------|
| **SoftLib / CCE MicroAPI (SIMD)** | **Optional (t646)** when VMI already best. |
| **SoftLib SIMT (A5)** | **Required finish or honest blocker.** Follow **`tilelanggym-softlib-simt-schedule`** / Harness §20. |
| **Do not conflate** | CCE optional ≠ SIMT waived; within-group contig ≠ warp-redux SoT. |

## Reduce-axis → opcode (Harness §22 — first pick)

Before VL×datablock / recipe explore, name **`reduce_axis`**:

| reduce_axis | Layout | Opcode family |
|-------------|--------|---------------|
| **inner** (1×G contiguous) | group `[gG,gG+G)` along VL-friendly axis | **VCMAX / VCGMAX** (+ optional VMAX tree when G > datablock) |
| **outer** (N×1 / column) | `A→(G,E/G)`; `C[c]=max_r |A[r,c]|` | **Elementwise VMAX fold only** — **no** VCGMAX/VCMAX for the reduce |

- Keep **separate SoT tables** for inner vs outer — never copy inner Gmap el/cyc into an Nx1 VMI cell.
- SoftLib SIMT §21 `axis=` labels still apply for SIMT layout; they do **not** replace this SIMD opcode pick.
- The SIMT body for the outer column scale is `skill:tilelanggym-column-scale`. One scale for the whole tile is `skill:tilelanggym-block-scale`.

## SoftLib SIMT (pointer)

| Motif | Note |
|-------|------|
| warp-redux contig | `asc_reduce_max` / SIMT_REDUX — G16-class |
| within-group contig | float2 LDS over gold G, no warp redux — mid-G Case-3; different era/KPI class |
| stock_stream | Baseline only |

Explore: LDS.32/64 · membar/bar · vec-misched on/off · unroll/pack · LD\|abs+REDUX\|ST · sparse STS. Full matrix in companion skill.

## Document axes separately (SIMD)

| Axis | Meaning |
|------|---------|
| **reduce_axis** | inner vs outer (§22) — picks opcode family |
| gold G / datablock G / VL | Need not be equal (**inner** explore) |
| ABS path | i32-VAND vs VABS_FP (§18) |
| Shape / reshape | 2D vs 1D+group (§19) |

## Arms per gold G

| Arm | Explore |
|-----|---------|
| **VMI PTO-DSL** | Primary SIMD close |
| **SoftLib CCE** | Optional if VMI best |
| **SoftLib SIMT** | §20 / softlib-simt-schedule |

## Forbidden

- Shared VF + post-VF gold as G close.
- Citing warp-absmax SoftLib SIMT el/cyc as Case-3 SoftLib SIMT SoT (or reverse).
- Mid-G SoftLib SIMT stock-only or single within-group contig without schedule matrix / stops (§20 / pollution #23).
- Outer-axis VCGMAX/VCMAX reduce, or Nx1 SoT = reused inner Gmap (§22 / pollution #25).
- Case-3 / `era=case3-quant-bcast` SIMD **DONE** on VL-res VSEL paint alone when compact NG available and Legal `pack_ub_vl256`/`keeplive_vbrc_vl256` not covered or cliffed; or close without stage×VL-util (VL|NG|1) table/pointer.

## Done when

VMI SoT or defer **for the named reduce_axis**; SoftLib CCE measured or skipped; SoftLib SIMT per companion skill; SEMANTICS_GATE; era labels.

## Case-3 epilogue ladder (pack-UB / keeplive_vbrc)

**When:** Case-3 / `era=case3-quant-bcast` / scale-epilogue paint suspected (VSEL range-paint of size-1 inv).

**FORCED before closing any SIMD Case-3 arm on VL-res VSEL paint alone** (when `VL % G == 0`, compact NG available):

1. **Cover Legal tags** **`pack_ub_vl256`** and **`keeplive_vbrc_vl256`** — measure both, **or** record **COMPILE_CLIFF** / **wrong-arm** with reason. Paint-only close without that coverage = **FAIL**.
2. **NG=8 preference (t593u):** for each gold G pick **VL=8×G** first (`NG=8`) so **VCG*** is usable; G32→VL256. Prefer that over tiny-NG cells (e.g. VL=64 NG=2 for G32 — known COMPILE_CLIFF); record cliff, do not invent KPI.
3. **Legal expand:** `vbrc(size=VL, group=NG)` / VDUP / e2b UB reload — **forbid** `vcmp`+`vsel` range paint as default when compact NG is available.
4. **Frontend checklist:** no `from __future__ import annotations` on `@pto.jit` kernels with `pto.ptr(...)` formals (stringifies live ptrs). GM formals stay `pto.ptr(...,"gm")`; UB = `castptr` offsets — do not rewrite this stack to pypto.Tensor as a “fix”.
5. **Measure purity:** count `RV_VSEL` **and** `RV_VSELR` separately (TSV VSEL=0 ≠ paint-free).
6. **Stage×VL-util table (FORCED):** name per-stage working size (**VL** | **NG** | **1**) for `S_reduce` / `S_scale` recip / `S_scale` expand / `S_eltwise` on the chosen SIMD arm — fill in TRACE or ANALYSIS, or pointer that TRACE filled one. Map lives in harness §2b (do not paste dig KPI here).

**Harness / PRC (facts + measured cause — open these; do not paste dig tables here):**

- Harness: `HARNESS_CASE3_PACK_UB_SCALE_t548u.md` (§2 VL×gold-G + NG=8 preference · §2b VL-util) — box `/workspace/REGRESSION_salvage_2026-09-17/` · peanut `/mnt/fluxdata/happybot/REGRESSION_salvage_2026-09-17/`
- PRC: `hub/tilelanggym/perf-review-knowledge/sch/PRC-SCH-003-case3-pack-ub-vs-vsel-paint.md`
- **PRC-SCH-003** (checklist) · sibling **PRC-SCH-002** · **PRC-MEM-001** for KEEP-X

No SoT crown without Lok yes. SoftLib dual_drain SoT left alone by this ladder.

## Top-3 sensitivity guesses (FORCED · t591u)

**When:** VL×gold-G or Case-3 pack-expand **sensitivity** is open (new gold G, VL sweep, or expand residual / VSELR still high after pack).

Ordered tries — **pointers only**, no dig el/cyc. Cite harness Legal/candidate table (`HARNESS_CASE3_PACK_UB_SCALE_t548u.md` VL×gold-G candidates). Before DONE on a sensitivity claim: measure or COMPILE_CLIFF/wrong-arm each of the top-3 **or** list which were skipped + why.

1. **`pack_ub` at VL=8×gold_G (NG=8)** when Legal — first pick so compact **VCG*** / `vcmax(group=8)` can fire (t593u). Tag often `pack_ub_vl{8G}` (e.g. G32→`pack_ub_vl256`). If that VL cliffs, next Legal `VL%G==0`.
2. **`keeplive_vbrc_vl256`** (KEEP-X compact scale / vbrc expand).
3. **Next harness VL×G candidate not yet tried/cliffed** — for gold G=32: `pack_ub_vl128` (NG=4); when gold-G sens open: **optional extra** **G8×VL=256** (NG=32 — does **not** replace G8’s NG=8-first VL=64); then VSELR residual / expand-purity dig if pack already measured but expand not paint-free (`RV_VSEL` and `RV_VSELR` both reported).

Harness also lists gold **G=8 × VL=256** as an **optional extra** Legal sensitivity candidate (NG=8-first for G8 is still VL=64) — do not invent KPI until measured.

## Out of scope

Invent el/cyc; redefine Harness §12–§22.
