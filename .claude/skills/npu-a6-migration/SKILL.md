---
name: npu-a6-migration
description: >
  Use when porting A5 kernels to A6 (NPU_ARCH 9201 / DavidV121 / dav_9201) or
  writing A6-native kernels: 3-EXU model, v2 instruction split, bank/service-rule
  deltas, i-cache, sync, and split-arch build flags.
category: ascendc-dev
license: CANN Open Software License Agreement Version 2.0
origin: native
maturity: ready
owner: skill-foundry
---

# A5 → A6 migration deltas

## EXU: 2 → 3 (the one fact that changes everything)
EXQ0+EXQ1 (ADD_CONV/MUL/MOV round-robin) **+ LNQ/EXU2 (SLIDE+LNEXP)**, depth 16/16/13.
SLIDE no longer steals EXQ0 slots; it contends with LNEXP on EXU2. Reduce v2
group-stage moved SLIDE→ADD_CONV (lat 9–15 → 4–6).

## Budget: EXQ:LNQ ≈ 2:1 by service time (issue-weighted)
Both EXQs serve arithmetic at 2/cyc; LNQ serves slide+exp at thpt 1. Band
1.6–2.7:1 ⇒ tri-issue ≥20% (measured across 16 shape variants). BUT: below 2 IPC
demand the EXQs alone suffice — LNQ idle is optimal (measured +19.2% the wrong
way when forcing balance).

## v2 instructions (compiler splits every A5 reduce; see npu-reduce-recipes)
vintlv→2×vintlvv2 (LNQ); W* instructions dropped; FMA family added (7 variants,
lat 6, dual-issuable); VSELRv2; PART_P0..P3 + MODE_MERGING (A6-only convert modes).

## Memory deltas (dump-verified 2026-10)
| | A5 | A6 |
|---|---|---|
| UB | 256 KB | **384 KB** (2×192 KB, full-range) |
| Banks | 16 (8 BG × 2) | **32 (8 BG × 4)** |
| Subbank | 8 B | **16 B** |
| BG service/cyc | 2R or 1R+1W | **2R + 1W concurrent** |
| Vector i-cache | 16 KB / 4-way | **8 KB / 2-way** (body-growth cliff measured: 456→926 cyc, +103%, from 441 icache-miss cycles) |

## Build & sync
- `--cce-aicore-arch=dav-920r1-vec` + `dav-920r1-cube` (A5: single dav-c310);
  `pto-isa/include` FIRST (SDK headers lack A6 branches); `--cce-auto-sync=off`.
- A5 cross-core sync (`TSync_Custom` flag+16) **DEADLOCKS on A6** → `set/wait_intra_block`.
- L0C→VEC reads +3 cyc (6→9); TMOV `SingleModeVec0`.

## Naming cross-map
A5 = 3101 = dav-c310 = Ascend950PR_9599 (sim) / 9579 (silicon) · A6 = 9201 =
davidV121 = dav_9201 (camodel) = dav-920r1 (bisheng arch).

## Gotchas

- Drafted hub/inbox/npu-a6-migration/SKILL.md: 3-EXU model, budget+third gate, v2 table, memory-delta table (dump-verified), build/sync, naming cross-map. Sources: npu_skills a6-* + pto-vmi A6-box campaigns. (was: A6 porting knowledge scattered/contradictory: LNEXP 'throughput halved' stated per-slot as if per-core (3 docs disagree: thpt 4 vs authoritative 2), A6 bank count marked 'not in config' with no service rule, no naming cross-map (3101/dav-c310/950PR vs 9201/dav_9201/dav-920r1), and sync/build pitfalls (TSync deadlocks, pto-isa include order) buried in notes.) — `dissection of npu_skills + pto-vmi A6-box dumps (2026-11-04)`
