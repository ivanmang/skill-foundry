---
name: tilelanggym-softlib-simt
description: >
  Use when exploring or closing SoftLib SIMT (__simt_vf__) absmax/Case-3 for a
  gold G — motif classes (warp-redux contig vs within-group contig vs stock);
  schedule matrix LDS.32/64, membar/bar vs fused, vec-misched on/off,
  unroll/pack, LD|abs+REDUX|ST pipeline, sparse STS; forced 1xG SoT ladder
  dual-drain / loadall+absall (all G) / wc-multi / G64-128 dual-drain /
  T in {128,256,512}; SoT cell axis=1xG only; before SoftLib SIMT DONE; forbid
  DONE on t676-class LDS matrix alone; when SoftLib≻SIMD claimed, FORCED PR9
  opcode_lanes_ipc overlays both arms (reject IPC-only).
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Pair with tilelanggym-st-explore Done-bar.
category: perf-analysis
---

# tilelangGym SoftLib SIMT schedule

**When:** SoftLib / CCE **SIMT** (`__simt_vf__`) absmax or Case-3.

**Companions:** `tilelanggym-semantics-gate` · `tilelanggym-st-explore` · Motif seed
`hub/tilelanggym/MOTIF_SEED_SV567_absmax.md`.

## Motif classes — do not conflate

| Motif | Is | Not |
|-------|----|-----|
| warp-redux contig | contig LDS + redux | mid-G within-group |
| within-group contig | packed over gold G | G16 warp SoT |
| stock_stream | bank-stride stream | SoftLib SIMT SoT |
| dual-drain / loadall+absall | full-warp load+abs then redux | LDS.32 T128-only matrix |
| wc-multi | warp-coop multi (G64/128) | stock alone |

## Forced SoT ladder (or honest stop)

`softlib_simt_loadall_absall` **all G** · `softlib_simt_dual_drain` **G16/32/64/128** ·
`softlib_simt_wc_multi` G64/128 · T∈{128,256,512}. SoftLib SoT cell = **axis=1xG only**.

**Forbidden early DONE:** freeze t676-class LDS/membar/misched only; crown G64/128 on
wc-multi alone while dual_drain untried.

## PRC

| Claim | PRC-id |
|-------|--------|
| SoftLib “membar” = compiler memory clobber | PRC-SCH-001 |
| SoftLib≻SIMD overlays | PRC-IPC-001 |

Gate: `python3 scripts/check_prc_index.py`
