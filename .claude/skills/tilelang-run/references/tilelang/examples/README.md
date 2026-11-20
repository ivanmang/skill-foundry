# TileLang examples

Reference bodies. They are not formulas and they are not measured rows. Open one only when a draft needs a shape the formula shelf does not already give.

## When to open

- The user's math matches a formula: use that formula's `simt.md`. Do not open an example instead.
- The user's math matches none, and you are drafting the missing SIMT or SIMD arm: open the example whose shape fits the ownership, then adapt it to their math.
- You are writing a single-opcode launch: open `contiguous-load.md`.

## When not to open

- Do not treat an example as the schedule for a named formula.
- Do not copy an example whose ownership does not fit. A contiguous load is not a group-of-32 schedule.

## Files

| File | What it shows |
| --- | --- |
| `contiguous-load.md` | One warp, lane `t` on element `t`, and the stride that puts lanes far apart |

For **stage schedules** (serial, strip pipeline, prefetch, multi-acc) — not address shape alone — use `tilelang/techniques/schedule-patterns.md` (pairs with `stage-model.md`).

Compile and launch with `tilelang/run/ascend.md`.
