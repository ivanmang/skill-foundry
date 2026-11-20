# column-scale — analyze

How to run and read this formula. Numbers for comparison are in `measure.md`.

## Run

Build the body from this formula's `simt.md`. Compile and launch with `tilelang/run/ascend.md`. Record with `npusim record -s Ascend950 -g -n 0`, one launch at a time.

## Counters

From veccore0 (`core == 0`, `sub == 1`), paired by PC and ID.

- **VF** — completion of `VF` or `VF_SIMT` minus its start, both ticks included.
- **el/cyc** — N/VF.
- **REDUX, BAR** — both 0 on this schedule. A nonzero count means a reducer was inserted and the result is the block scale.
- **FDIV** — one inverse per warp, not one divide per element.
- **LDK** — local spill. Above zero on a keep body means the held rows spilled.

## Pass check

For each column, `max over rows |Out[row, col]|` equals `max over rows |X[row, col]| / max(eps, that max)`.

## Wrong result signature

A nonzero `REDUX` or `BAR`. This formula has no cross-thread fold.
