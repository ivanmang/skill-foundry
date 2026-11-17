# Dot product — run and read

How to run and read this formula. Numbers for comparison are in
`measure.md` (this folder).

## TileLang body

Build the body from the write spelling in `../SKILL.md`. Compile and launch with
the TileLang Ascend backend. Record with `npusim record -s Ascend950 -g -n 0`,
one launch at a time.

## CCE body

Compile the `.asc` with the CCE toolchain into a shared object
(`skill:npu-cce-run`). Launch it for `N = 4096`, `K = 32`. The launcher compares
against the fp32 gold and prints `PASS maxabs=<value>`. Record with
`npusim record -s Ascend950 -g -n 0`, one launch at a time.

## Counters

From veccore0 (`core == 0`, `sub == 1`), paired by PC and ID.

- **VF** — completion of `VF` or `VF_SIMT` minus its start, both ticks included.
- **el/cyc** — `N / VF`.
- **mac/cyc** — `N × K / VF`.
- **LDS bytes per issue** — 128 bytes at 32-bit lane width, 256 at 64-bit, 512
  at 128-bit. One issue is one warp of 32 lanes.
- **bytes per cycle** — tile bytes divided by the overlap-adjusted active cycles
  of the load opcode.
- **Opcode mix (CCE)** — `FMUL` and `REDUX` on the hand-written body, where the
  generated kernel uses `FFMA`. The measured body issues `LDS` every 13 cycles,
  active 27; the generated buffer kernel issues every 32 cycles, median active
  652.

## Pass check

Each output equals the dot product of its row of `A` with `x`. The CCE body
passed at max abs error 9.537e-07 against the fp32 gold.

## Reading a load-width run

Count issued `LDS` and the active cycles of that opcode. A wider lane that
raises the issue latency without a matching byte gain lowers bytes per cycle.
Two elements per thread issue two loads, not one wider load.

## Wrong schedule signature

A `__simt_vf__` body whose `LDS` is spaced like the generated kernel (adjacent
lanes far apart) shows the strided walk. The lane-`L`-on-element-`L` body shows
the coalesced walk.