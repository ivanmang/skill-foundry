# Dot product — measured grids

`A[n, k]` is contiguous in `k`. el/cyc is `N / VF`. mac/cyc is `N × K / VF`. VF
is `VF` (SIMD) or `VF_SIMT` (SIMT) completion minus start, both ticks included,
veccore0 (`core == 0`, `sub == 1`).

## TileLang — load width, one warp

The TileLang load is 32 threads and one float per lane. One `LDS` is 128 bytes
and stays active about 27 cycles, which is 4.74 bytes per cycle. The value is
kept with an `FADD`. Two elements per thread issue two 128-byte `LDS`, each
active about 28 cycles.

## TileLang — load width, bytes per cycle

One block, `threads` by 1, on a 64×128 float tile (32768 bytes). Every launch
passed. Bold is the highest bytes-per-cycle in the row.

| Threads | 32-bit | 64-bit | 128-bit |
| ---: | ---: | ---: | ---: |
| 32 | 4.74 | 8.53 | **12.34** |
| 128 | 27.07 | **47.03** | 31.64 |
| 256 | 35.61 | **51.82** | 32.02 |
| 512 | **105.07** | 55.36 | — |

The 128-bit lane is not always the fastest. Above 128 threads the 64-bit lane
moves more bytes per cycle than the 128-bit lane.

## TileLang — stock launch

The stock SIMT launch is 256 threads. On `N = 4096` that is 16 outputs per
thread in the thread-per-output spelling. The head-to-head thread search is 128,
256, 512, 1024, and 2048, and stops when the launch would pass `N`.

## CCE — hand-written against generated

One measured cell: `N = 4096`, `K = 32`, 256 threads. The body passed, max abs
error 9.537e-07 against the fp32 gold. Bold is the lower VF.

| Kernel | VF | el/cyc | mac/cyc | IPC |
| --- | ---: | ---: | ---: | ---: |
| Buffer (TileLang) | 132303 | 0.03 | 0.99 | 0.16 |
| CCE (hand-written) | **55100** | 0.07 | 2.38 | 1.12 |

The hand-written window is shorter. Buffer `LDS` issues every 32 cycles, median
active time 652. CCE `LDS` issues every 13 cycles and finishes in 27. CCE uses
`FMUL` and `REDUX` in place of `FFMA`.

## What is not yet here

The full TileLang thread-sweep grid and head-to-head rows are not measured yet;
the CCE shelf has one measured cell (no thread sweep, no single-opcode rate
sweep in CCE). Add them here when measured — do not invent them.