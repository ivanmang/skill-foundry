---
name: tilelanggym-column-scale
description: >
  Use when a TileLang or SIMT kernel has one scale per column:
  scale[col] = max over rows of |X[row, col]|, then
  Out[row, col] = X[row, col] * (1 / scale[col]). Keep the max in the lane,
  take the inverse once, and multiply the held rows. This kernel has no
  reducer and no barrier. One scale for the whole tile is
  skill:tilelanggym-block-scale. A per-group Case-3 reduce is
  skill:tilelanggym-softlib-simt.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Pair with tilelanggym-st-explore Done-bar.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# tilelangGym column scale

**When:** each column has its own scale, and pass 2 multiplies by that column's inverse.

```text
scale[col] = max(eps, max over rows |X[row, col]|)
Out[row, col] = X[row, col] * (1 / scale[col])
```

eps is 1e-6. The measured body is float32. The column never leaves its lane. One scale for the whole tile is `skill:tilelanggym-block-scale`. A per-group reduce-then-map is `skill:tilelanggym-softlib-simt`.

**Companions:** `skill:tilelanggym-block-scale` · `skill:tilelanggym-softlib-simt` · `skill:tilelanggym-simd-per-g-mapping` · `skill:tilelanggym-st-explore`.

The SIMD opcode for this reduce axis is the outer fold in `skill:tilelanggym-simd-per-g-mapping`: elementwise `VMAX`, and `VCMAX` / `VCGMAX` is the wrong family for the reduce. This skill is the SIMT body that matches that formula.

## Portable procedure

Stop at the first step that fails.

1. Read the formula. The scale is one number per column. Pass 2 is `held * inv`.
2. Give one thread one column. `C` is the thread count and a multiple of 32. Walk the rows, keep `held[row]`, take the inverse once in that lane, and multiply the locals.
3. Leave the reducer out. A dump of this schedule has `REDUX` 0 and `BAR` 0. Adding a reducer computes the block scale.
4. Sweep the thread count. The largest count is a candidate, not the winner. The grid is PRC-SCH-007.
5. On the SIMD path, `C` is a multiple of 64. Sixty-four columns are one inverse. A wider tile repeats that walk. 512×32 is outside the measured SIMD body. Reshaping a fixed `N` changes this kernel.
6. If the held rows spill, tile the rows. The measured spill is the 256-row launch on PRC-SCH-007.
7. Rank SIMD against this SIMT body from PRC-SCH-007. A published both-arm claim also cites PRC-IPC-001.

## How to write it

```text
thread col owns column col
m = 0
for row in 0 .. R-1:
    held[row] = X[row, col]
    m = max(m, abs(held[row]))
inv = 1 / max(m, eps)
for row in 0 .. R-1:
    Out[row, col] = held[row] * inv
```

Unroll the row loop into one local per row so pass 2 multiplies that local. There is no `alloc_reducer`, no `reducer_update`, and no `finalize_reducer`. The UB form copies `X` into one shared tile first. The GM form has no shared tile: each local is loaded from `X`.

The inverse is one per lane, issued once per warp. The multiply starts while later warps are still loading. The note splits the max into `FMNMX` and `FMNMX_I`. It does not say those two issue in the same tick.

## Gotchas

- An empty compiler fence is deleted in this body, so it does not measure a stage cut. A volatile flush of the held rows is the slow path. Flushing the one max, or the one inverse, stays near the uncut kernel. Fused and split are different binaries here. On the block scale they compile to one binary. That result does not transfer.
- The flat loop-versus-cross probe, including the eps result past warp 31, belongs to `skill:tilelanggym-block-scale`. This kernel has no cross-thread fold.
- The fence launch and the head-to-head SIMT row are different thread counts. Cite the row on PRC-SCH-007 that matches the launch.
- Do not paste the el/cyc grid into this file. The table is PRC-SCH-007.

## PRC

| Claim | PRC-id |
|-------|--------|
| Column scale: lane-local inverse, keep, thread sweep | PRC-SCH-007 |
| Both-arm compare overlay | PRC-IPC-001 |

Gate: `python3 scripts/check_prc_index.py`
