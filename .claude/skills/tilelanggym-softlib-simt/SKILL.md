---
name: tilelanggym-softlib-simt
description: >
  Use when exploring or closing SoftLib SIMT (__simt_vf__) absmax/Case-3 for a
  gold G — motif classes (warp-redux contig vs within-group contig vs stock);
  schedule matrix LDS.32/64, membar/bar vs fused, vec-misched on/off,
  unroll/pack, LD|abs+REDUX|ST pipeline, sparse STS; forced 1xG SoT ladder
  dual-drain / loadall+absall (all G) / load-ahead, load-4 and load-2 (G32 Case-3) /
  wc-multi / G64-128 dual-drain /
  T in {128,256,512}; SoT cell axis=1xG only; before SoftLib SIMT DONE; forbid
  DONE on t676-class LDS matrix alone; when SoftLib≻SIMD claimed, FORCED PR9
  opcode_lanes_ipc overlays both arms (reject IPC-only). Also when a
  TileLang or SIMT kernel does a per-group reduce and then reuses the loaded
  value (SV8-like): adapt load-ahead (load-4 or load-2) instead of one-thread-one-group.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Pair with tilelanggym-st-explore Done-bar.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
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
| load-ahead | loads issued before the max that uses them | a sliding load/max interleave; a wider memory load |
| load-4 (`simt_load4`) | load-ahead with four groups | a 4-wide memory load; dual-drain's load-all |
| load-2 (`simt_load2`) | load-ahead with two groups | load-4 when four does not divide |
| wc-multi | warp-coop multi (G64/128) | stock alone |

## Forced SoT ladder (or honest stop)

`softlib_simt_loadall_absall` **all G** · `softlib_simt_dual_drain` **G16/32/64/128** ·
`softlib_simt_wc_multi` G64/128 · T∈{128,256,512}. SoftLib SoT cell = **axis=1xG only**.

**Forbidden early DONE:** freeze t676-class LDS/membar/misched only; crown G64/128 on
wc-multi alone while dual_drain untried; close G32 Case-3 SIMT on dual-drain alone
while `simt_load4` is legal and untried.

## When the kernel looks like SV8

Use this when each group reduces on its own, and the output element is that group result applied to a value that was already loaded. Case-3 quant is the measured instance: per-group absmax, then `x * (1 / max(m, eps))`. The same ownership applies to another per-group reduce-then-map. It does not apply to one scale for the whole tile, or to a reduce down the rows.

Follow, in this order. Stop at the first step that fails.

1. Write the group so that lane `t` reads element `t`. If neighboring lanes are a group apart, fix that before any other change. A wider load does not close a stride of one group. That width comparison is a different schedule, and it is not indexed here.
2. If `G=32`, write load-ahead below. Use load-4 when `groups / warps` is divisible by 4, otherwise load-2. Sweep only those thread counts. Do not assume the largest thread count wins.
3. If `G` is not 32, do not call the kernel load-4. Keep lane `t` on element `t` of its own group, and do not let one warp max mix two groups. A warp is 32 lanes. `G=16` is two groups in a warp, so each max stays inside 16 lanes. `G=64` is two warps per group, so one warp max is not the group max. Those adaptations are not the measured body.
4. Compare with dual-drain at the same thread count and the same storage type. Then run the SIMD pack and keeplive ladder before calling the SIMT schedule the winner. The ranking is PRC-SCH-005.

## load-ahead — how to write it

Load-ahead is the schedule. Load-4 and load-2 are its two passes. Use it on Case-3 when the group is one warp (`G=32`, `axis=1xG`). Lane `t` reads element `t` of the group, so the warp load is 32 adjacent columns. The next group's load does not use the current group's max, so those loads go out before any of those maxes.

```text
addr = ((step * 4 + k) * warps + warp) * 32 + lane
held[0..3] = X[addr] for k = 0,1,2,3
then warp-max each held value, with the eps floor, then the reciprocal
then store held[k] * inv[k] at the same addr
```

`warps = threads / 32`. `groups = rows * (cols / 32)`. Load-4 is four groups before the max, not a 4-wide load. The first of the four still waits on its load. The other three were issued during that wait. Load-2 is the same schedule with two groups. A pass of one waits on every group. Load-2 waits on every other group.

Worked addresses, 64×128, 256 threads, 8 warps. Warp 0, lane 0, first pass reads elements 0, 256, 512, 768. Lane 1 reads 1, 257, 513, 769. If the addresses are not those, it is not this schedule.

The compiled body is TileLang `make_warp_f16_unroll` with `factor=4` and float32 storage. A `__simt_vf__` sketch that calls `asc_reduce_max` on each held value is the same address and has not been compiled. Do not treat that sketch as a measured kernel.

On a dump, the `SIMT_LDS` issue count equals the number of groups. A launch whose `groups / warps` is not divisible by 4 is load-2, not load-4. On 64×64 at 2048 threads that count is 2.

The live set is four values per thread, then those four are stored and dropped. Dual-drain keeps every group the warp owns until the max. That is the whole difference. Do not rewrite dual-drain into `float2` loads and call it this schedule: dual-drain's addresses are one float per lane and are not pairs.

### Corner cases

- `cols` must be a multiple of 32, or a group crosses a row. When that holds, the address depends on `groups` and `warps`, not on how the element count is split into rows and columns.
- `threads` is a multiple of 32, from 32 through 2048. `groups` must be a positive multiple of `warps`, and at least one group per warp. This kernel does not park extra threads. More warps than groups is a different program.
- Four must divide `groups / warps`, or the launch is load-2. On 64×64, 2048 threads leaves each warp two groups.
- The number of group-loads stays equal to the number of groups. Doubling the threads does not halve that count, and it does not halve the window. On 64×64 the window shortened from 128 threads to 512 and then stopped. 1024 matched 512.
- Rank it against dual-drain at the same thread count and the same storage type. Float16 storage inserts a conversion on the load and the store. That row is not the float32 comparison. At 128 threads on 64×64, and at 256 threads on 64×128, dual-drain is shorter. From 512 threads up, load-4 is shorter than dual-drain, except the 64×64 launch at 2048 threads, which is load-2. Load-4 is not shorter than keeplive on 64×64, or pack on 64×128.
- The single launch copies `X` and `Out` into one buffer. A shape that does not fit is tiled. It is not this kernel with a bigger allocation.
- Not measured, so not a rule: a sliding pass (load A, load B, max A, load C, max B), a pass of eight, and a compiler fence inside this schedule. Dual-drain's fence result does not transfer.

The measured table is PRC-SCH-005. Do not paste those el/cyc into this file.

## PRC

| Claim | PRC-id |
|-------|--------|
| SoftLib “membar” = compiler memory clobber | PRC-SCH-001 |
| SoftLib≻SIMD overlays | PRC-IPC-001 |
| load-ahead (load-4, load-2) versus dual-drain | PRC-SCH-005 |

Gate: `python3 scripts/check_prc_index.py`
