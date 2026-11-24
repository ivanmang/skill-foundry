---
name: formula-block-scale
description: >
  Write and check the block-scale formula (one scale for the whole input, then divide): the signature, the SIMT spelling to write vs refuse, measured rows, and the run/read recipe. Use when the code reduces a whole tensor to a single scale factor.
license: Apache-2.0
category: formula
origin: library
owner: skills-library
maturity: ready
metadata:
  source: skills-library
  location: ~/skills-library
  fingerprint: 2974dec11c8959147428235a1acc5036ac133d1789394f2b1888a1285b40ad83
---

# block-scale

Write and check the block-scale formula (one scale for the whole input, then divide): the signature, the SIMT spelling to write vs refuse, measured rows, and the run/read recipe. Use when the code reduces a whole tensor to a single scale factor.

Imported from `skills-library` (`~/skills-library`) — reference snapshot. Run `./harness import skills-library --sync` to refresh from source.

## Files

Match your job, then open the one file it names.

| File | Purpose |
|---|---|
| `references/tilelang/formulas/block-scale/analyze.md` | block-scale — analyze |
| `references/tilelang/formulas/block-scale/formula.md` | block-scale |
| `references/tilelang/formulas/block-scale/measure.md` | block-scale — measured grid |
| `references/tilelang/formulas/block-scale/simt.md` | block-scale — SIMT |

## Start here

Open `references/tilelang/formulas/block-scale/formula.md` first.

## Gotchas

- The reference files are snapshots; the source library is the single source of truth. Refresh with `./harness import <source> --sync`.
- Open one file per job (the library's `job → one open` rule).
