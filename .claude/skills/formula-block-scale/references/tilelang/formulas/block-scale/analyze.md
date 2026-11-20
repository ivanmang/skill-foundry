# block-scale — analyze

How to run and read this formula. Numbers for comparison are in `measure.md`.

## Run

Build the body from this formula's `simt.md`. Compile and launch with `tilelang/run/ascend.md`. Record with `npusim record -s Ascend950 -g -n 0`, one launch at a time.

## Counters

From veccore0 (`core == 0`, `sub == 1`), paired by PC and ID. `is_popped == 1` is issue, `0` is completion.

- **VF** — completion of `VF` or `VF_SIMT` minus its start, both ticks included.
- **el/cyc** — N/VF.
- **REDUX, BAR** — issued counts. On the 2D keep: `REDUX = W+1` up to 16 warps, `REDUX = 2W` at 32 warps, `BAR = 4×W`, `W = threads / 32`. On the flat loop: `REDUX` 5, `BAR` 16.
- **LDK** — local spill. Above zero on a keep body means the held rows spilled.

## Pass check

`max |Out|` equals `max |X| / max(eps, max |X|)`. An all-zero input gives an eps scale and zero output.

## Wrong result signature

A last-element probe, `X[N-1] = 4` with the rest 0, distinguishes a fold that dropped warp 32 and above. The flat cross schedule at 2048 threads returns eps. The 128-thread loop returns 4. Use this probe on a flat reduce whose thread count grows with N.
