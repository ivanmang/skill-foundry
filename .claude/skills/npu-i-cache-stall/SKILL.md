---
name: npu-i-cache-stall
description: >
  Diagnose a long empty strip in a SIMT VF window where every warp issues nothing
  — an I-cache / I-stream (or cold first-launch) stall, not warp stagger. Use
  when a single-op Schedule or case kernel chart shows a long all-warp 0-IPC
  blank, or when a multi-launch case needs a warm VF[1] for rates and charts.
  Prefer the "same body twice, use VF[1]" fix before publishing a line.
license: CANN Open Software License Agreement Version 2.0
compatibility: >
  Requires the recorded trace and the plot tool from
  skill:npu-single-opcode-rate (instr-ipc-plot.py --warps / --vf N).
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# I-cache / I-stream stall (0-IPC hole)

Diagnose a long empty strip in a SIMT VF window where **every warp issues
nothing**. **Language-agnostic:** hits hand-written CCE and TileLang-generated
bodies. Not warp stagger; not a per-warp data stall.

## Symptom

```text
VF-rel time →
w0..w7  [… useful work …] ████████████ [tail ops … END]
                          ↑ long blank ↑
                          0 issues on EVERY warp
```

- Longest **0-issue** run is huge (hundreds of ticks); can sit mid store-tail or
  **post-`END`** on a cold first launch.
- **All** warps silent together (shared fetch / first-launch tax).
- Barriers do **not** fix it.

Contrast: warp **stagger** still shows some warps issuing. This stall is global
silence.

## Cause

Large fully-unrolled VF I-stream and/or **cold first launch**. Evidence that
fits: all warps stop together; resume continues nearby PCs; large
`.aicore_binary` / many distinct store PCs from full `#pragma unroll`; an
**identical second launch of the same body is clean**; shrinking per-VF unroll
can also shrink the hole (secondary).

## Confirm

1. Pair the trace; find the longest 0-issue run; check every warp empty
   (`--warps`).
2. Name opcodes at the hole edges (often `STS` → more `STS`, or post-`END` drain).
3. If other ops keep issuing across a "gap," it is stagger/pollution — not this.
4. If a second identical VF in the same record (or a redundant warm launch) is
   clean, treat the hole as first-launch / I-stream tax.

## Preferred fix for analysis — Fix G (2nd VF)

**For multi-launch case kernels (rate tables and charts):**

1. Launch the **same** VF body at least twice (redundant work is fine for
   measurement), or use a multi-slab case where slab 1 is already warm.
2. Discard VF[0] (cold / first-launch gap).
3. Take busy-union, IPC, and charts from **VF[1]** (and later identical launches).
4. Multi-slab cases (one VF per slab): estimate full-case VF as
   `2 × span(VF[1])` when the two slabs are equal work.

Draw with `instr-ipc-plot.py … --vf 1` (`skill:npu-single-opcode-rate`). Do not
publish VF[0]-only figures as the case Schedule result when a warm launch exists.

**Single-launch pure microbenches** (one VF): chart and rate that VF. A
first-launch post-`END` blank usually sits **outside** the target-op busy union,
so the opcode rate is unaffected — Fix G is not required for those Schedule
lines.

This is the **headline methodology for case kernels**. It preserves one-body /
comparable accounting without rewriting the kernel.

## Other options

| Option | Idea | Hole? | OK as reported rate? |
| --- | --- | --- | --- |
| **G. Same body twice; use VF[1]** | Warm launch; rates/charts from 2nd | Proven clean on 2nd | **Yes — preferred** |
| **A. Bounded unroll / chunk, one VF** | Shrink I-working set | May help | Secondary / optional |
| **B. Dual VF (split work)** | Half work per launch | Proven gone | **No as headline** — diagnosis only |
| **C. More threads @ fixed N** | Smaller unroll | Likely helps | Yes as its **own** thread-count row |
| **D. Fewer warps @ fixed N** | Larger unroll | Likely worse | Refuse |
| **E. Barriers only** | Align warps | Does not fix | Irrelevant |

### Refuse — Fix B as the official cell

Splitting work across two VFs changes the launch model, breaks stock "first VF"
charts, and inflates span with inter-VF quiet. Lab proof only — not the reported
Schedule cell.

### Secondary — Fix A

```cpp
#pragma unroll 4
for (int i = 0; i < kPerThread; ++i) /* … */;
// or explicit chunk loop under one asc_vf_call
```

Useful if the body must stay single-launch; verify codegen actually looped. Still
apply Fix G when multiple launches are recorded.

## Definition of done

- **Case / multi-launch:** rates/charts from a **warm** VF (VF[1] when two
  identical launches exist).
- **Single-launch microbench:** rates from that VF's target-op busy union
  (post-`END` blank outside the union is fine).
- Stock IPC / warp charts show the full op count for that chosen window
  (`--vf` when needed).
- Note names cold vs structural blanks in one bullet when both appear.

## Where this shows up

- **CCE:** fully unrolled Schedules (e.g. FFMA Schedule 3 store tail —
  `skill:npu-op-burst`).
- **TileLang:** long unrolled VFs; fused multi-slab cases with a cold first launch.

When climbing the burst ladder or writing a theoretical note, if the window shows
a long all-warp blank, open this file and prefer Fix G before publishing the
line.

## Gotchas

- Do not publish VF[0]-only figures when a warm launch exists.
- Splitting work across VFs (Fix B) is diagnosis-only, never the reported cell.

## Output

- a named cause (cold first-launch vs structural I-stream tax)
- rates + charts from the warm VF[1] window