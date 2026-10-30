---
name: tilelanggym-vmi-gmap
description: >-
  Use when tracking or closing MB-SV*-VMI-Gmap / SoftLib Gmap sweeps — classify
  functional PASS vs tried schedules vs best-sweep DONE per reduce_axis (inner
  VC/VCG vs outer VMAX, Harness §22); outer absmax-vs-Case-3 dual-era + VAND
  no-path → alternate-builder before DONE; measure until DONE or an explicit
  stop reason — never treat UNMEASURED-only as success; dig-vs-live delta
  checklist when el/cyc moves vs prior SoT.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Outer suite gate: sv567-nx1-outer.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---
# tilelangGym VMI / SoftLib Gmap close

**When:** Statusing or closing per-G SIMD mapping sweeps (MB-SV6-VMI-Gmap, MB-SV7-VMI-Gmap, SoftLib Gmap, Nx1 outer VMAX sweep, similar).

**Companions:** `tilelanggym-st-semantics-gate`; `tilelanggym-simd-per-g-mapping`; `tilelanggym-reduce-dual-issue-recipes`.

## Success vs stop (Lok 2026-10-26)

| Outcome | Allowed? |
|---------|----------|
| **best-sweep DONE** with measured el/cyc on SoT tag | **Yes** — normal success |
| **PARTIAL** with ≥1 measured functional PASS + listed open tags | Interim OK; not final deliverable |
| Deliverable that **only** has UNMEASURED / pending tables | **Not success** — keep measuring |
| **Stop** with explicit reason | **Yes** — only the stop reasons below |

### Explicit stop reasons (only)

1. **No path** — required recipe class impossible on this stack (API/ISA/tooling); document why + `skipped` (includes **VAND f32 rejected** by ptoas-vmi — see recipes skill). For outer VAND: only after **alternate-builder** attempt (below).
2. **Cannot execute** — compile/opsim/env blocked after real attempt(s); log error + last command.
3. **Iterate loop, no improvement** — loop guards fired (same tag rerun; third near-noise variant; residual-instr-only noise vs Aims) — stop and keep current measured SoT.

`UNMEASURED` is a **row status while work continues**, not a closing deliverable.

## Three layers (always list separately)

### 1) Functional (arm / recipe)
Compile + gold + SEMANTICS_GATE PASS + el/cyc + VL/datablock/gold + **`reduce_axis`** named → `arm PASS` / `recipe PASS` (≠ sweep DONE).

### 2) Tried schedule inventory
Every compile/opsim attempt listed. Re-running same tag with no new hypothesis = looping — forbidden.

### 3) Best-sweep
OPEN / PARTIAL / DONE from required explore set + loop guards — **per reduce_axis** (inner and outer are separate sweeps).

## Required explore set (default per gold G)

**Always name `reduce_axis=inner|outer` first (Harness §22).**

### Inner (1×G)

1. VCGMAX-oriented (small/mid).
2. Mid gold G: VL=256 + group=8 VCGMAX (or API cannot).
3. half/whole-VL VCMAX if needed (declare opcode from **lowering**; VL<64 often VCGMAX).
4. Large G: VMAX → VCGMAX/VCMAX.
5. Optional: one split-stage VMAX ILP unless it beats SoT.

### Outer (N×1 / column)

1. **Elementwise VMAX fold** (+ abs path) — **required**; VCGMAX/VCMAX as reduce = wrong-arm.
2. Unroll / dual-chain / split-stage VMAX ILP explores.
3. Shape peers as needed (§19); do **not** copy inner Gmap SoT into outer cells.

#### Outer dual-era + VAND alternate-builder (t759u / t760u)

Absmax-only and Case-3 recip are **different eras** — never claim outer SoT comparable across them without `era=`.

Before outer **DONE**:

1. Name **`era=`** on every outer row (`absmax-only` vs `case3-quant-bcast` / recip).
2. If Aims compare to an absmax-only dig SoT (~45 el/cyc class): run **absmax-only** outer suite **or** label Case-3 peer as non-comparable (`era=` + COMPARE caveat).
3. Prefer **i32-VAND** abs path when stack allows (dig/t720 / tip t760 class). **SoT-class i32-VAND** = **fused** `vinterpret_cast(vand(vinterpret_cast(vload,i32), 0x7FFFFFFF), f32)` then elementwise VMAX (instr mix VAND+VMAX; **no** abs-buffer VLD/VST). Tip tag class: `outer_g*_vmax_vand_*`.
   - A bare `vmax` on i32 without cast (`probe_o_vandi_direct`-class) is a known no-path — it does **not** justify skipping the fused interpret_cast recipe.
   - **2-pass UB mirror** (for_loop vload/vand/vstore then f32 fold from mirror) is **not** SoT-class VAND — label `appendix` / `wrong-alternate` only; do not close absmax-only outer SoT on mirror+VABS.
   - If fused VAND **no-path** on the current builder: **Must** try at least one **alternate builder / layout / stack path** (different reshape, epilogue strip, or known working absmax-only outer template — prefer tip fused recipe first) before accepting VABS-only DONE.
   - Document attempt + error in tried table; only then stop reason **No path** for VAND.
4. Do **not** mark outer DONE solely on Case-3+VABS ~36 el/cyc and treat it as the absmax-only ~45 SoT.
5. Do **not** mark outer absmax-only DONE on VABS-only ~40–41 el/cyc when fused i32-VAND tip class was not measured (t792u R0 miss).

SoftLib **CCE** optional when VMI already best (`tilelanggym-simd-per-g-mapping` t646). SoftLib **SIMT** is a separate A5 track — not waived by CCE optional.

## Dig-vs-live delta checklist (glm53 gap #6)

Before calling a live el/cyc a **regression** (or a new superseding SoT) vs a dig / prior SoT, cite **all** of:

| Check | Why |
|-------|-----|
| **reduce_axis** | inner vs outer (§22) — same class? |
| **abs-path** | VAND vs VABS_FP (or other) — same class? |
| **shape** | RxC / E / TILE / T |
| **epilogue** | Case-3 recip vs absmax-only (era) |
| **toolchain** | ptoas-vmi / TileLang / SoftLib tip |
| **VL / NG / datablock** | Same mapping class? |

If any differ → keep **both** numbers with caveat / `era=`; do **not** silently overwrite dig SoT. Prefer COMPARE template VMI delta section.

**Clean regress:** KPI number paste into the runner may stay COMPARE N/A, but still run this checklist as **motif/era coverage** (tag names + era/abs-path/shape) before DONE — see `tilelanggym-st-explore-from-prompt` Motif seed / Coverage COMPARE.

## DONE / PARTIAL / loop guards

DONE when required set covered **for that reduce_axis** (incl. outer dual-era / VAND alternate-builder rules), SoT = max el/cyc among PASS rows **within the same era=**, no open motivated hypothesis, next ideas are noise → do not run.

PARTIAL wording: *arm PASS; best-sweep PARTIAL — tried […]; still open […]*. Never “SIMD closed” while PARTIAL.

Loop guards: same-tag no change; third variant ≤~2% vs SoT; residual-instr-only without Aims; SoftLib ahead + VMI FAIL_GOLD twice same family → stop (reason 3).

## Workflow

1. Tried table (tag `reduce_axis` + `era=`) → 2. Measure → 3. Recompute OPEN/PARTIAL/DONE → 4. If only UNMEASURED left and path exists, **continue** → 5. Close only on DONE or explicit stop reason → 6. If comparing to dig SoT, run **delta checklist** (coverage even when KPI COMPARE N/A).

## Out of scope

Inventing rows; Track B as G-sensitivity SoT; peanut merge without user yes.
