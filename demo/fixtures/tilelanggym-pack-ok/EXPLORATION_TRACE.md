# EXPLORATION_TRACE — fixture pack (skill-foundry selfcheck)

## Meta
- ST: sv567-fixture
- tip/toolchain: fixture
- session: skill-foundry-demo
- start: 2026-10-30 Asia/Hong_Kong

## Aims lock
- P1 absmax SoftLib vs VMI
- P2 G16/32/64/128 SoftLib 1xG + optional outer appendix
- P3 ANALYSIS + PR9 + TRACE
- P4 SoT / Coverage COMPARE
- P5 clean regress; no dig el/cyc paste

## Motif seed
Tag names only (from hub/tilelanggym/MOTIF_SEED_SV567_absmax.md):
- softlib_simt_stock_stream
- softlib_simt_wg_lds_matrix
- softlib_simt_wc_lds_matrix
- softlib_simt_loadall_absall
- softlib_simt_dual_drain (G16/G32/G64/G128)
- softlib_simt_wc_multi
- softlib_simt_T128 / softlib_simt_T256 / softlib_simt_T512
SoftLib SoT cell = axis=1xG only. Nx1 wr_* appendix.

Outer (appendix when suite needs it):
- vmi_outer_vmax_fold
- vmi_outer_era_absmax_only
- vmi_outer_era_case3_recip
- vmi_outer_vand_i32
- vmi_outer_vand_alternate_builder
reduce_axis=outer / Nx1; pure VMAX.

## Decision log
| step | skill | arm | action | result | next | stop? |
|------|-------|-----|--------|--------|------|-------|
| 1 | semantics-gate | both | S1–S4 | PASS | measure | no |

## Tried / skipped + why
- All SoftLib ladder rungs marked measured in Coverage COMPARE.
- Outer dual-era + VAND alternate-builder attempted.

## Best-sweep board
SoftLib SIMT G16–128: DONE (fixture)
VMI inner: DONE (fixture)
VMI outer dual-era: DONE (fixture)
MB_STATUS: DONE

## SEMANTICS_GATE
SEMANTICS_GATE: PASS — fixture gold matches Aims; opcode family matches reduce_axis.

## Coverage COMPARE
| seed tag | G | status |
|----------|---|--------|
| softlib_simt_stock_stream | 16/32/64/128 | ✓ |
| softlib_simt_wg_lds_matrix | mid | ✓ |
| softlib_simt_wc_lds_matrix | all | ✓ |
| softlib_simt_loadall_absall | all | ✓ |
| softlib_simt_dual_drain (G16) | 16 | ✓ |
| softlib_simt_dual_drain (G32) | 32 | ✓ |
| softlib_simt_dual_drain (G64) | 64 | ✓ |
| softlib_simt_dual_drain (G128) | 128 | ✓ |
| softlib_simt_wc_multi | 64/128 | ✓ |
| softlib_simt_T128 | win | ✓ |
| softlib_simt_T256 | win | ✓ |
| softlib_simt_T512 | win | ✓ |
| vmi_outer_vmax_fold | Nx1 | ✓ |
| vmi_outer_era_absmax_only | outer | ✓ |
| vmi_outer_era_case3_recip | outer | ✓ |
| vmi_outer_vand_i32 | outer | ✓ |
| vmi_outer_vand_alternate_builder | outer | ✓ |

KPI COMPARE: N/A (clean fixture).

## What-if next
- None — fixture closed for gate selfcheck.
