# block-scale — SIMT

The mode is SIMT, the language is TileLang, the target is Ascend. Other languages and modes are not held in this library yet.

## Write — 2D tile, keep the rows

`C` is the thread count and a multiple of 32, so a warp covers 32 adjacent columns of one row. One thread owns one column. The column max stays in the thread. One reducer across those threads finishes the block scale, and the scale stays in a register for the divide.

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

Unroll the row loop into one local per row, so pass 2 divides the local. The UB form copies `X` into one shared tile first. The GM form has no shared tile: each local is loaded from `X`. Compile with `tilelang/run/ascend.md` from the spelling above.

## Write — flat vector, the loop

When the input is one vector and the only result is the scale, fix the threads at 128 (four warps). `N` must be divisible by 128. Thread `t` walks a stride of 128, then one redux runs across those four warps.

```text
threads = 128
thread t reads x[t + k * 128] for k in 0 .. reps-1
then one redux across these 128 threads
scale = max(eps, that redux)
```

Compile with `tilelang/run/ascend.md` from the spelling above.

## Refuse — the cross schedule

Setting `threads = N`, one element per thread, then a redux of the warp partials. The fold stops after warp 31, so a max that lives in the last element comes back as eps. The probe sets `X[N-1] = 4` and the rest to 0: at 2048 threads the cross scale is eps and the 128-thread loop scale is 4. This is a wrong-result spelling, not a slower one. The probe is the check.

The 2D keep kernel at 1024 threads is a different body and was not given that probe. Do not call the 2D 32-warp row the eps probe.

## Spill

Pass 2 divides the local from pass 1. When the held rows do not fit, tile the rows. The measured spill is the 256-row GM launch (`measure.md`).
