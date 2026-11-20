# dot-product — analyze

How to run and read this formula. Numbers for comparison are in `measure.md`.

## Run

Build the body from this formula's `simt.md`. Compile and launch with `tilelang/run/ascend.md`. Record with `npusim record -s Ascend950 -g -n 0`, one launch at a time.

## Counters

From veccore0 (`core == 0`, `sub == 1`), paired by PC and ID.

- **VF** — completion of `VF` or `VF_SIMT` minus its start, both ticks included.
- **el/cyc** — `N / VF`.
- **mac/cyc** — `N × K / VF`.
- **LDS bytes per issue** — 128 bytes at 32-bit lane width, 256 at 64-bit, 512 at 128-bit. One issue is one warp of 32 lanes.
- **bytes per cycle** — tile bytes divided by the overlap-adjusted active cycles of the load opcode.

## Pass check

Each output equals the dot product of its row of `A` with `x`.

## Reading a load-width run

Count issued `LDS` and the active cycles of that opcode. A wider lane that raises the issue latency without a matching byte gain lowers bytes per cycle. Two elements per thread issue two loads, not one wider load.
