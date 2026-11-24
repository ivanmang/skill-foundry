---
name: formula-group-scale-broadcast
description: >
  Write and check the group-scale-broadcast formula (one scale per group, then broadcast-multiply): signature, SIMT spelling to write vs refuse, measured rows, and the run/read recipe. Use when a per-group scale is broadcast back to the group.
license: Apache-2.0
category: formula
origin: library
owner: skills-library
maturity: ready
metadata:
  source: skills-library
  location: ~/skills-library
  fingerprint: 2f964f6a2121efec13647dd464f1abf9863f8429d042d7b0c8002cd969c0d4c6
---

# group-scale-broadcast

Write and check the group-scale-broadcast formula (one scale per group, then broadcast-multiply): signature, SIMT spelling to write vs refuse, measured rows, and the run/read recipe. Use when a per-group scale is broadcast back to the group.

Imported from `skills-library` (`~/skills-library`) — reference snapshot. Run `./harness import skills-library --sync` to refresh from source.

## Files

Match your job, then open the one file it names.

| File | Purpose |
|---|---|
| `references/tilelang/formulas/group-scale-broadcast/analyze.md` | group-scale-broadcast — analyze |
| `references/tilelang/formulas/group-scale-broadcast/formula.md` | group-scale-broadcast |
| `references/tilelang/formulas/group-scale-broadcast/measure.md` | group-scale-broadcast — measured grid |
| `references/tilelang/formulas/group-scale-broadcast/simt.md` | group-scale-broadcast — SIMT |

## Start here

Open `references/tilelang/formulas/group-scale-broadcast/formula.md` first.

## Gotchas

- The reference files are snapshots; the source library is the single source of truth. Refresh with `./harness import <source> --sync`.
- Open one file per job (the library's `job → one open` rule).
