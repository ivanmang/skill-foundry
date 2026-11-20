# group-scale-broadcast — analyze

How to run and read this formula. Numbers for comparison are in `measure.md`.

## Run

Build the body from this formula's `simt.md` (kinds: warp unroll 1/2/4, reload, keep). Compile and launch with `tilelang/run/ascend.md` (G is 32, float32). Record with `npusim record -s Ascend950 -g -n 0`, one launch at a time.

## Counters

From veccore0 (`core == 0`, `sub == 1`), paired by PC and ID.

- **VF** — completion of `VF_SIMT` minus its start, both ticks included.
- **el/cyc** — N/VF.
- **SIMT_LDS** — issued group loads. Equals the number of groups on a load-ahead body.
- **LDK, STK** — local spill. Above zero on a keep body means the held rows spilled.

## Pass check

For each group, `max |Out|` over the group equals `max |X|` over the group divided by `max(eps, that max)`. Max abs error about 1e-7 against the per-group absmax-reciprocal gold.

## Wrong schedule signature

- A `SIMT_LDS` count well above the number of groups means a reload body, not load-ahead.
- A launch whose `groups / warps` is not divisible by 4 is load-2. Calling it load-4 is the mis-name.
- On the within-group stride, a wider load that does not shorten the window is the width result, not a schedule fix.
