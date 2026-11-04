---
name: tilelanggym-block-scale
description: >
  Use when a TileLang or SIMT kernel has one scale for the whole tile:
  scale = max(eps, max of |X|), then Out = X / scale. Keep a partial max in
  the thread, finish it with one reducer, and divide the values already held.
  On a flat vector fix 128 threads and stride. A per-column scale is
  skill:tilelanggym-column-scale. A per-group Case-3 reduce is
  skill:tilelanggym-softlib-simt.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Pair with tilelanggym-st-explore Done-bar.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# tilelangGym block scale

**When:** one scale covers every element, and pass 2 divides by that scale.

```text
scale = max(eps, max |X|)
Out = X / scale
```

eps is 1e-6. The measured body is float32. A scale per column is `skill:tilelanggym-column-scale`. A per-group reduce-then-map is `skill:tilelanggym-softlib-simt`.

**Companions:** `skill:tilelanggym-column-scale` · `skill:tilelanggym-softlib-simt` · `skill:tilelanggym-simd-per-g-mapping` · `skill:tilelanggym-st-explore`.

## Portable procedure

Stop at the first step that fails.

1. Read the formula. One number for the whole tile stays one number. Pass 2 is `held / scale`.
2. On a 2D tile, give one thread one column. `C` is the thread count and a multiple of 32. Walk the rows, keep `held[row]`, update one reducer with the column max, then divide the locals by `max(scale, eps)`.
3. On a flat vector, fix the threads at 128. Thread `t` reads `x[t]`, `x[t+128]`, and so on. `N` must be divisible by 128. Then one redux across those four warps.
4. Sweep the 2D thread count. The largest count is a candidate, not the winner. The grid is PRC-SCH-006.
5. If the held rows spill, tile the rows. The measured spill is the 256-row launch on PRC-SCH-006.
6. Rank SIMD against this SIMT body from PRC-SCH-006. A published both-arm claim also cites PRC-IPC-001.

## How to write the 2D kernel

```text
thread col owns column col
m = 0
for row in 0 .. R-1:
    held[row] = X[row, col]
    m = max(m, abs(held[row]))
reducer_update(m)
scale = max(eps, finalize(reducer))
for row in 0 .. R-1:
    Out[row, col] = held[row] / scale
```

Unroll the row loop into one local per row so pass 2 divides that local. The UB form copies `X` into one shared tile first. The GM form has no shared tile: each local is loaded from `X`.

This 2D body is the measured block kernel. It is a different program from the flat cross schedule below. The warp-31 probe was not measured on the 2D kernel.

Issue shape, with `W = threads / 32` and `R = N / threads`. `REDUX = W+1` up to 16 warps, and `REDUX = 2W` at 32 warps. `BAR = 4×W`. Row issues fall as each thread owns fewer rows. Reduce issues grow with the warp count.

## How to write the flat reduce

```text
threads = 128
reps = N / 128
thread t reads x[t + k * 128] for k in 0 .. reps-1
then one redux across these 128 threads
scale = max(eps, that redux)
```

`REDUX` stays 5 and `BAR` stays 16 as `N` grows.

The schedule this skill refuses sets `threads = N`, one element per thread, then a redux of the warp partials. The fold stops after warp 31. The probe sets `X[N-1] = 4` and the rest to 0: at 2048 threads the cross scale is eps, and the 128-thread loop scale is 4.

## SIMD

VL = 64. One `VCMAX`, then `VDUP`. Pass 2 is a vector divide by the one scale. At N=16384 the measured shapes share one VF. That is the only N where the note records it, and it is block-scale only. The column-scale SIMD body does change with the shape. The VF is on PRC-SCH-006.

## Gotchas

- An empty compiler fence is deleted in this body, so it does not measure a stage cut. A volatile flush of the held rows is the slow path. Flushing the single scale stays next to the uncut kernel, because the redux already waits. Fused and split compile to one binary here.
- The 2D kernel at 1024 threads is 32 warps and is a measured SIMT row. Do not describe that row as the flat eps probe.
- The column-scale fence, where fused and split are different binaries, does not transfer.
- Do not paste the el/cyc grid into this file. The table is PRC-SCH-006.

## PRC

| Claim | PRC-id |
|-------|--------|
| Block scale: loop versus cross, keep, thread sweep | PRC-SCH-006 |
| Both-arm compare overlay | PRC-IPC-001 |

Gate: `python3 scripts/check_prc_index.py`
