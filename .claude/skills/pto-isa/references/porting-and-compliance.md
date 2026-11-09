# PTO-ISA contributing: porting, build & compliance

Conventions for adding/porting testcases and passing CI in the pto-isa repo.
Aggregated from the 2026-11 A6-porting and OAT-compliance work.

## OAT / license compliance

- Use the canonical header wording: `You may not use this file except in
  compliance with the License.` and `MERCHANTABILITY, OR FITNESS FOR A
  PARTICULAR PURPOSE` on one line.
- New files carry the **current year** (2026) in the copyright header.
- Every source file ends with **exactly one newline** (pre-commit
  `end-of-file-fixer`).
- Run `oat-check` manually and fix license wording even in files OAT didn't
  flag in its log.

## Build / layout

- A testcase dir must be named `CMakeLists.txt` (plural) — `add_subdirectory`
  will not resolve `CMakeList.txt`.
- The header filename must match what sources `#include` (e.g. `cases.h`);
  mirror the naming used by sibling testcases.
- Squash (or cherry-pick) all PR changes into **one commit** and force-push.

## A6 porting

- `TLOAD`/`TSTORE` do not lower correctly on A6 — use the raw
  `pto_copy_gm_to_ubuf_align_v2` / `pto_copy_ubuf_to_gm_align_v2` intrinsics
  directly (lengths in **bytes**).
- Mirror `a5/TCvt.hpp` as a thin wrapper (the `tcvt_common.hpp` is shared);
  update the `header.hpp` includes to point at the a5 copy.

## Regression hygiene

- `cpu-st` failing because the root filesystem is full is an **environment**
  failure, not a test regression.
- The pinned baseline can drift (thousands of removed cases over days) — refresh
  it before trusting the review diff; a single `PASS→FAIL` may be baseline drift.
- Before a regression, clean deleted-but-open files and free `/tmp` (a full root
  fs breaks cmake/gtest temp files).
- Extract failing filters from the per-suite **log**, not the `run.json` case
  list — `run.json` can miss failures.

## Harness capture

- Auto-capture does **not** dedupe against already-promoted knowledge (dedupe
  only happens at promote). Prefer explicit promote steps, and check
  `promoted.md`/the target doc before capturing to avoid duplicate pending entries.