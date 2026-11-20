# dot-product — CCE analyze

How to run and read the CCE body. Numbers for comparison are in `measure.md`. The compile and launch recipe is `cce/run/ascend.md`.

## Run

Compile the `.asc` with the CCE toolchain into a shared object (`cce/run/ascend.md`). Launch it for `N = 4096`, `K = 32`. The launcher compares against the fp32 gold and prints `PASS maxabs=<value>`. Record with `npusim record -s Ascend950 -g -n 0`, one launch at a time.

## Counters

From veccore0 (`core == 0`, `sub == 1`), paired by PC and ID.

- **VF** — completion of `VF_SIMT` minus its start, both ticks included.
- **el/cyc** — `N / VF`.
- **mac/cyc** — `N × K / VF`.
- **LDS** — issue period and active time. The measured body issues `LDS` every 13 cycles, active 27. The generated buffer kernel issues every 32 cycles, median active 652.
- **Opcode mix** — `FMUL` and `REDUX` on this body, where the generated kernel uses `FFMA`.

## Pass check

Max abs error against the fp32 gold is at the e-07 scale. The measured body is 9.537e-07.

## Wrong schedule signature

A `__simt_vf__` body whose `LDS` is spaced like the generated kernel (adjacent lanes far apart) shows the strided walk. The lane-`L`-on-element-`L` body shows the coalesced walk.
