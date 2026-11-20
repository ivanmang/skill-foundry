# column-scale — SIMT

The mode is SIMT, the language is TileLang, the target is Ascend. Other languages and modes are not held in this library yet.

## Write — lane-local inverse

`C` is the thread count and a multiple of 32. One thread owns one column. The max of that column stays in the lane. There is no reducer and no barrier. The inverse is taken once, and pass 2 multiplies the values already held.

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

Unroll the row loop into one local per row so pass 2 multiplies that local. The UB form copies `X` into one shared tile first. The GM form has no shared tile: each local is loaded from `X`. Compile with `tilelang/run/ascend.md` from the spelling above.

## Refuse — a reducer across columns

Any `alloc_reducer`, `reducer_update`, or `finalize_reducer` across the columns. That computes the block scale, a different result. A dump of this schedule has `REDUX` 0 and `BAR` 0; a nonzero count is the check.

```text
refuse:
    reducer_update(m)            # folds the column maxes into one tile scale
    scale = finalize(reducer)
    Out[row, col] = held[row] / scale   # block-scale result, not column-scale

write:
    inv = 1 / max(m, eps)        # stays in the lane, no reducer
    Out[row, col] = held[row] * inv
```

The refuse block changes the math; the write block keeps the column scale in the lane.

## Refuse — the flat loop-versus-cross probe

The eps-past-warp-31 probe belongs to `block-scale`. This kernel has no cross-thread fold, so that probe is not a check here.

## Spill

Pass 2 multiplies the local from pass 1. When the held rows do not fit, tile the rows. The measured spill is the 256-row GM launch (`measure.md`).
