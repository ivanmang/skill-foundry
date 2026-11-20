# group-scale-broadcast — SIMT

The mode is SIMT, the language is TileLang, the target is Ascend. G is 32 in the measured body. Other languages, modes, and G are not held in this library yet.

## Write — load-ahead

One warp owns one group of 32. Lane `t` reads element `t`, so the warp load is 32 adjacent columns. A pass loads `factor` groups into registers, then warp-maxes the absolute value of each, then multiplies by `1 / max(m, eps)` at the same address. The next group's load does not depend on the current group's max, so those loads go out before the maxes.

```text
addr = ((step * factor + k) * warps + warp) * 32 + lane
held[0..factor-1] = X[addr] for k = 0 .. factor-1
then warp-max each held value, with the eps floor, then the reciprocal
then store held[k] * inv[k] at the same addr
```

`warps = threads / 32`. `groups = rows * (cols / 32)`. `lane = tid % 32`. `warp = tid / 32`.

Load-4 is four groups before the max. Load-2 is the same schedule with two. Load-4 is legal only when `groups / warps` is divisible by 4; otherwise it is load-2. The first of the pass still waits on its load. The others were issued during that wait. The live set is `factor` floats per thread, then dropped. Compile with `tilelang/run/ascend.md` from the spelling above.

## Corner cases

- `cols` must be a multiple of 32, or a group crosses a row.
- `threads` is a multiple of 32, from 32 through 2048. `groups` is a positive multiple of `warps` and at least one group per warp. This kernel does not park extra threads.
- The number of group-loads stays equal to the number of groups. Doubling the threads does not halve that count.
- On 64×64 at 2048 threads, `groups / warps` is 2, so that cell is load-2, not load-4.

## Refuse — one-thread-one-group with lanes 32 apart

One thread owns a group of 32 consecutive columns, so neighboring lanes are 32 columns apart. Both `keep` and `reload` compile to that stride, and a wider load does not move the window. That is a slower spelling of the same formula, not a correctness failure. Compile with `tilelang/run/ascend.md` from the spelling above.

```text
refuse (one thread per group, lanes 32 apart):
    base = tid * 32
    for k in 0 .. 31:
        held[k] = X[base + k]        # lane t reads column base+k; lanes are 32 apart
    m = max over k of abs(held[k])
    for k in 0 .. 31:
        Out[base + k] = held[k] * (1 / max(m, eps))

write (load-ahead, one warp per group, lanes adjacent):
    addr = ((step * factor + k) * warps + warp) * 32 + lane
    held[0..factor-1] = X[addr]      # lane t reads element t of the group
    warp-max each held value, then multiply by the inverse at the same addr
```

The refuse block has lanes 32 columns apart, so the warp load is not coalesced; the write block has lane `t` on element `t`.

## Refuse — a wider load as a fix

Widening the load (LDS.64) on the within-group stride does not shorten the window, because the lanes are still 32 columns apart. A wider load is not a schedule.

## Refuse — dual-drain as load-ahead

Dual-drain keeps every group the warp owns until the max. That is a different live set and a different schedule, measured separately (`measure.md`). It is not load-ahead with a bigger pass.

## Refuse — G ≠ 32 called load-4

`G = 16` keeps the max inside 16 lanes; `G = 64` needs two warps per group. Those are different bodies and are not the measured load-4. Do not call a `G ≠ 32` kernel load-4.
