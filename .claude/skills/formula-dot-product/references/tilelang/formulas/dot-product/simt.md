# dot-product — SIMT

The mode is SIMT, the language is TileLang, the target is Ascend. Other languages and modes are not held in this library yet.

## Write — warp per output

A warp is 32 lanes. The 32 lanes split the K axis of one output, each lane multiply-accumulates its share, then one warp reduction produces the sum. Lane 0 stores.

When `K ≤ 32`, only the first `K` lanes load and the rest add 0. When `K > 32`, each lane walks in steps of 32.

```text
lane t, for one output n:
    acc = 0
    for step in 0 .. ceil(K/32) - 1:
        k = t + step * 32
        if k < K: acc += A[n, k] * x[k]
    redux across the 32 lanes
    lane 0 stores Out[n]
```

Compile with `tilelang/run/ascend.md` from the spelling above.

## Refuse — thread per output as the warp body

A thread-per-output spelling gives each thread a whole row of `A` and no warp reduction. It is a different schedule of the same formula, measured separately. It is not the warp body with fewer lanes.

## Load width

One `LDS` issue is one warp of 32 lanes. The lane width sets the bytes in one issue: 32-bit is 128 bytes per issue, 64-bit is 256, 128-bit is 512. A wider lane cuts the issue count, and the bytes per cycle rise only when the wider issue does not stall longer than the extra bytes are worth. Loading two elements per thread does not become one wider load; it issues two narrower loads.
