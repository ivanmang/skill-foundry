# dot-product — CCE SIMT

A hand-written `__simt_vf__` body. This is the pattern an agent writes when the generated TileLang body does not give the wanted instruction stream, or when a comparison needs a hand-controlled body.

## Write — warp per output, staged through the buffer

The measured body: `A` is fp16, `(4096, 32)`, contiguous in `k`. `x` is fp16. `Out` is fp32. 256 threads, 8 warps. Each warp owns 256 outputs. Lane `L` holds `x[L]` and loads `A[n, L]`, so one warp reads one row as 32 adjacent halves. The sum is `asc_reduce_add`.

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

The host-side `__vector__` kernel stages `A` and `x` through the unified buffer, one slab of 2048 rows per VF launch, and calls the `__simt_vf__` body with `asc_vf_call`. It copies with `asc_copy_gm2ub_align` / `asc_copy_ub2gm_align` and orders the pipes with `asc_sync_notify` / `asc_sync_wait`. Two VF launches cover `N = 4096`.

Compile with `cce/run/ascend.md` from the spelling above. Language shape: `cce/examples/simt-vf.md`.

## Why the hand-written body is written this way

The generated TileLang buffer kernel uses `threadIdx.x * 64 + k`, so adjacent threads are 128 bytes apart. The hand-written body makes lane `L` read element `L` of the row, so one warp's loads are 32 adjacent halves and the reduce is one `asc_reduce_add`. That is the whole difference between the two spellings, and it is why the hand-written window is shorter.

## Refuse — a strided lane walk

A `__simt_vf__` body that spaces adjacent lanes across the row. That is the generated kernel's stride. It is a slower spelling of the same formula, not a correctness failure.

## Refuse — a TileLang source in this shelf

This shelf is for the `__simt_vf__` and `__vector__` body. A `T.SimtVF` or `T.SimdVF` source belongs in `tilelang/`.
