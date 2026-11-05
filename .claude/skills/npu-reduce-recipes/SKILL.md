---
name: npu-reduce-recipes
description: >
  Use when writing or optimizing vector reductions (per-group absmax, row
  reduce, cascade/pack) on A5 or A6: choosing vcmax/vcgmax/vmax-tree recipes,
  deferring packs, or porting A5 reduce intrinsics to A6 v2 instructions.
category: ascendc-dev
license: CANN Open Software License Agreement Version 2.0
origin: local
maturity: draft
owner: skill-foundry
---

# Reduce recipes

## A5: monolithic reduces (SLIDE/VEC, EXQ0-only, lat 9–15)
One instruction does lane-reduce + cascade/pack. Monolithic = serial on the one
slide FU. **Recipe (R2)**: collapse with vmax-trees (ADD, dual-issuable, 5-cyc)
and a *single* vcmax at the very end — never vcmax-per-VL.

## A6: every A5 reduce splits into 2 instructions on 2 units
| A5 call | A6 emits | Stage-1 (unit) | Stage-2 (unit) |
|---|---|---|---|
| vcmax() | vcgmaxv2 + vcmaxv2 | EXQ (ADD_CONV, lat 5–6) | **LNQ** (SLIDE, lat 10) |
| vcgmax() | vcgmaxv2 + vpackv2 | EXQ | LNQ (lat 8) |
| vcadd() | vcgaddv2 + vcaddv2 | EXQ | LNQ (lat 10–13) |

Group-stage moved to fast ADD_CONV — cross-lane reduces are now cheap and the
two stages overlap across units in the OOO engine.

## Patterns
- **Deferred pack (A6)**: `vcgmaxv2` in-loop (wide, in place), ONE `vpackv2`
  after the loop. Calling A5 `vcgmax()` blindly force-emits the pack per iteration.
- **Cross-unit overlap**: stage-1 (EXQ) of group N+1 runs under stage-2 (LNQ) of N.
- **Costing**: 1 A5 reduce = 1 EXQ + 1 LNQ slot on A6 — feeds the 2:1 budget.

## Measured anchors (a5 sim)
- vmax-chain: dependent consumer issues 2 cyc after producer (EXU bypass);
  dual-issued dependent vmax pairs sustain steady gap=1.
- AbsReduceMax 128×256: A5 462 (monolithic) / A6 naive 553 (+19.7%, serial
  EXQ→LNQ hop) / A6 unroll×2 488 (+5.6%). Unroll ×4 worse (+26%): write port.

## Gotchas

- Drafted hub/inbox/npu-reduce-recipes/SKILL.md: compiler-lowering table, patterns, measured anchors (AbsReduceMax 462/553/488; vmax bypass gap=1). Source: npu_skills reduce-patterns + a6-notes §3. (was: A5 reduce recipes (vcmax-per-VL, monolithic calls) applied verbatim on A6; no record that A6 splits every A5 reduce into 2 instructions on 2 units or that the deferred-pack pattern exists.) — `dissection of npu_skills case-writing (2026-11-04)`
