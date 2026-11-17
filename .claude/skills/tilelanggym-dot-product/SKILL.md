---
name: tilelanggym-dot-product
description: >
  Use when the user's math is a dot product — one sum per output row over the
  inner K axis, multiply-accumulate, no scale and no eps floor. Write the
  TileLang SIMT warp-per-output body, or the hand-written CCE __simt_vf__ body
  staged through the buffer, and read their measured grids. A per-group
  reduce-then-map is skill:tilelanggym-softlib-simt; a max-scale is
  skill:tilelanggym-block-scale or skill:tilelanggym-column-scale.
license: CANN Open Software License Agreement Version 2.0
compatibility: >
  Requires the TileLang Ascend backend for the generated body; the CCE body is a
  .asc compiled per skill:npu-cce-run. Measured rows live in
  references/measure.md.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# Dot product

One sum per output row, over the K axis.

```text
Out[n] = sum_k A[n, k] * x[k]
```

`A` is `(N, K)`, `x` has length `K`, `Out` has length `N`.

## Signature (match by structure, never by name)

**Match** when all of these hold:

- one value per output row, produced by a sum over the inner axis
- the combine is a multiply-accumulate, not a max
- there is no scale, no broadcast of a reduced value, and no eps floor

**Reject** — these are different formulas:

- a max of absolute values into one value, then divide → `skill:tilelanggym-block-scale`
- one value per column → `skill:tilelanggym-column-scale`
- one value per group, then broadcast → `skill:tilelanggym-softlib-simt`

**Correctness check:** each output equals the dot product of its row of `A`
with `x`. Accumulation order within a row does not change the math.

## TileLang SIMT — write (warp per output)

A warp is 32 lanes. The 32 lanes split the K axis of one output, each lane
multiply-accumulates its share, then one warp reduction produces the sum. Lane 0
stores.

When `K ≤ 32`, only the first `K` lanes load and the rest add 0. When `K > 32`,
each lane walks in steps of 32.

```text
lane t, for one output n:
    acc = 0
    for step in 0 .. ceil(K/32) - 1:
        k = t + step * 32
        if k < K: acc += A[n, k] * x[k]
    redux across the 32 lanes
    lane 0 stores Out[n]
```

Compile with the TileLang Ascend backend.

### Refuse — thread per output as the warp body

A thread-per-output spelling gives each thread a whole row of `A` and no warp
reduction. It is a different schedule of the same formula, measured separately.
It is not the warp body with fewer lanes.

## Load width

One `LDS` issue is one warp of 32 lanes. The lane width sets the bytes in one
issue: 32-bit is 128 bytes, 64-bit is 256, 128-bit is 512. A wider lane cuts the
issue count, and the bytes per cycle rise only when the wider issue does not
stall longer than the extra bytes are worth. Loading two elements per thread
does not become one wider load; it issues two narrower loads.

Measured grid (64×128 float tile): above 128 threads the 64-bit lane moves more
bytes per cycle than the 128-bit lane — a wider lane is **not** always faster.
Rows: `references/measure.md`.

## CCE SIMT — write (warp per output, staged through the buffer)

A hand-written `__simt_vf__` body, for when the generated TileLang body does not
give the wanted instruction stream. The measured body: `A` is fp16, `(4096, 32)`,
contiguous in `k`; `x` is fp16; `Out` is fp32; 256 threads, 8 warps. Each warp
owns 256 outputs. Lane `L` holds `x[L]` and loads `A[n, L]`, so one warp reads
one row as 32 adjacent halves. The sum is `asc_reduce_add`.

```text
__simt_vf__ body, one slab s:
    lane = tid & 31;  wid = tid >> 5
    xk = (float)X[lane]
    for i in 0 .. 255:
        n = wid * 256 + i
        prod = (float)A[n * 32 + lane] * xk
        sum = asc_reduce_add(prod)
        if lane == 0: Out[s * 2048 + n] = sum
```

The host-side `__vector__` kernel stages `A` and `x` through the unified buffer,
one slab of 2048 rows per VF launch, and calls the `__simt_vf__` body with
`asc_vf_call`. It copies with `asc_copy_gm2ub_align` / `asc_copy_ub2gm_align`
and orders the pipes with `asc_sync_notify` / `asc_sync_wait`. Two VF launches
cover `N = 4096`.

Compile with `skill:npu-cce-run`; language shape: `skill:npu-cce-run`
(`references/simt-vf.md`).

### Why the hand-written body is written this way

The generated TileLang buffer kernel uses `threadIdx.x * 64 + k`, so adjacent
threads are 128 bytes apart. The hand-written body makes lane `L` read element
`L` of the row, so one warp's loads are 32 adjacent halves and the reduce is one
`asc_reduce_add`. That is the whole difference between the two spellings.

### Refuse — a strided lane walk

A `__simt_vf__` body that spaces adjacent lanes across the row. That is the
generated kernel's stride. It is a slower spelling of the same formula, not a
correctness failure.

## Gotchas

- A wider load lane is not always faster — check the load-width grid before
  "widening" a load.
- Two elements per thread is two loads, not one wider load.
- The CCE body is fp16 in / fp32 out; a different dtype is not this measured
  body — measure it before citing it.
- Do not call a per-group or per-column reduce a "dot product"; they fail the
  signature.

## Output

- a TileLang `T.SimtVF` warp-per-output body (or the refused thread-per-output
  spelling, labeled why it loses)
- optionally a hand-written CCE `__simt_vf__` body staged through the buffer

## See also

- `references/measure.md` — measured grids (TileLang load width; CCE
  hand-written vs generated).
- `references/analyze.md` — run/read counters + pass check.
- `skill:npu-cce-run` — compile/launch the CCE body.
- `skill:tilelanggym-st-explore` — the ST study that would measure this formula.