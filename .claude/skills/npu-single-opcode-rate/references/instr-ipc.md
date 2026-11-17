# Instruction rows and the IPC line

One figure for a recorded launch. The method does not depend on which compiler
emitted the kernel. Drawn with `../scripts/instr-ipc-plot.py`.

## Trace

Use veccore0 (`core == 0`, `sub == 1`). The recorder writes two dumps:
**`*.instr_popped_log.dump`** holds each instruction's **start** (issue) tick,
**`*.instr_log.dump`** holds its **completion** tick. Pair each instruction by
PC and ID across the two. `is_popped == 1` is the start tick; `is_popped == 0`
is the completion tick.

The window is the completion of the mode's VF opcode minus its start, both ticks
included. SIMD uses `VF`; SIMT uses `VF_SIMT`. The same pairing — start from the
popped log, end from the instruction log, inclusive, overlap merged once —
governs **all** calculations: VF windows, busy cycles, active times, and the IPC
line.

## Which VF (warm launch)

By default the trace must hold **exactly one** VF launch. When a record has
several (multi-slab, or a redundant warm launch), pick one with `--vf N`
(0-based). For rates and charts after a cold first-launch / 0-IPC gap, use
**`--vf 1`** — see `skill:npu-i-cache-stall`.
Do not publish VF[0] as the result when VF[1] is the warm window.

## Drawn span (to last issue)

The figure's **x-axis ends at the last body issue** (`span = last_issue + 1`),
not at VF completion. After the last instruction the VF may still be draining
with no further issues; padding that empty drain makes a long blank right edge
and hides the busy part. Draw to the last issue. Keep the full VF length in the
title or print line as context — `span N (VF M)` — so a short span next to a
long VF is visible. The same clip applies to opcode-row and warp-row charts.

## Instruction rows

One row per opcode that is drawn. Address math may be left off the rows. The IPC
line still counts it.

Two row variants:

- **Opcode rows** — one row per opcode found in the window.
  `../scripts/instr-ipc-plot.py` draws this variant by default.
- **Warp rows** — one row per warp, marks colored by opcode (address math gray),
  `--warps`. `instr.bin` has no warp id. The tool infers the warp index only
  when the body is fully unrolled with one pass: every body PC then issues
  exactly `n_warps` times in the window, and the k-th issue of a PC in tick
  order belongs to warp k. Once-per-kernel setup and teardown PCs (one issue for
  the whole VF) stay off the warp rows but count in the IPC line. Any other
  per-PC count refuses the chart — a loop body that runs several iterations per
  warp cannot be assigned, and no guess is drawn. Burst-shaped bodies qualify;
  interleaved case kernels usually do not.

## IPC line

The scalar IPC for comparison is the issues inside the VF window, excluding the
VF opcode, divided by **VF**. The drawn IPC line bins those same issues over the
**drawn span** (to last issue). A point is the count in the bin divided by the
bin width. The last bin is only the ticks that remain inside the span.

```text
python3 ../scripts/instr-ipc-plot.py instr.bin simd|simt out.png [--bin W] [--warps] [--vf N]
```

It prints VF ticks, drawn span, the issue count, and the scalar IPC
(issues / VF). Without `--vf`, several VF launches in one trace are refused.
`--warps` is SIMT only. The bin width `W` used for a note's figure is named in
the appendix.

A detail figure — the first ticks of the window, magnified — is a crop of the
same figure, drawn from the same window and IPC rules with the x-axis clipped
further; the appendix names the tick range when a note uses one.

## What the figure is not

The figure is evidence of issue order and overlap. The comparison number is
el/cyc from the VF window, and that number stays in the measure file.