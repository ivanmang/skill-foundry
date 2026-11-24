---
name: tilelang-run
description: >
  Compile, launch, and read the counters of a TileLang body on Ascend, plus the contiguous-load SIMT reference body. Use when you have a TileLang kernel to run and read its dump, or need the load-pattern reference.
license: Apache-2.0
category: run
origin: library
owner: skills-library
maturity: ready
metadata:
  source: skills-library
  location: ~/skills-library
  fingerprint: 5df4f5b5c994e1e0073a80e4434292d610b6753c84d98143e6b351e67b527f66
---

# Run a TileLang case on Ascend

Compile, launch, and read the counters of a TileLang body on Ascend, plus the contiguous-load SIMT reference body. Use when you have a TileLang kernel to run and read its dump, or need the load-pattern reference.

Imported from `skills-library` (`~/skills-library`) — reference snapshot. Run `./harness import skills-library --sync` to refresh from source.

## Files

Match your job, then open the one file it names.

| File | Purpose |
|---|---|
| `references/tilelang/run/ascend.md` | Run a TileLang case on Ascend |
| `references/tilelang/examples/README.md` | TileLang examples |
| `references/tilelang/examples/contiguous-load.md` | Contiguous load |

## Start here

Open `references/tilelang/run/ascend.md` first.

## Gotchas

- The reference files are snapshots; the source library is the single source of truth. Refresh with `./harness import <source> --sync`.
- Open one file per job (the library's `job → one open` rule).
