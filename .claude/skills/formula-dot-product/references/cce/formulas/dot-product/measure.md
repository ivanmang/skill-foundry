# dot-product — CCE measured

One measured cell: `N = 4096`, `K = 32`, 256 threads. VF is `VF_SIMT` completion minus start, both ticks included, veccore0 (`core == 0`, `sub == 1`). el/cyc is `N / VF`. mac/cyc is `N × K / VF`. The body passed, max abs error 9.537e-07.

## Hand-written against generated

The same shape and thread count. The generated body is the TileLang buffer kernel. Bold is the lower VF.

| Kernel | VF | el/cyc | mac/cyc | IPC |
| --- | ---: | ---: | ---: | ---: |
| Buffer (TileLang) | 132303 | 0.03 | 0.99 | 0.16 |
| CCE (hand-written) | **55100** | 0.07 | 2.38 | 1.12 |

The hand-written window is shorter. Buffer `LDS` issues every 32 cycles, median active time 652. CCE `LDS` issues every 13 cycles and finishes in 27. CCE uses `FMUL` and `REDUX` in place of `FFMA`.

## What is not yet here

This shelf has one measured cell. A thread sweep, other shapes, and a single-opcode rate sweep in CCE are not measured yet. Those cells stay out until they are run.
