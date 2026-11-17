---
name: npu-single-opcode-rate
description: >
  Measure one instruction (opcode) in isolation on the Ascend NPU simulator to
  learn its rate, then use that rate to reason about a whole kernel. Use when
  building a roof or stage model, attributing kernel cost to opcodes, or
  microbenchmarking SIMT_LDS / F2F / FFMA / STS / RV_* before an ST or SoftLib
  study. Implements the two-dump trace pairing, busy-union (not span)
  accounting, and the instruction/IPC figures.
license: CANN Open Software License Agreement Version 2.0
compatibility: >
  Requires python3, the Ascend simulator decoder (cannsim.core.public.instr_decoder),
  and a recorded instr.bin plus the two per-core dumps (instr_popped_log.dump /
  instr_log.dump). The figure script also needs matplotlib.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# Single-opcode rate (uarch measurement)

Measure one **instruction** (opcode) alone, get its rate, then use that rate to
reason about a whole kernel. This is the measurement half of the perf method;
`skill:npu-perf-method` is the estimate-first roofline half. The CCE ladder that
*pushes* an opcode to its best line is a separate skill (`skill:npu-op-burst`).

## Two terms that are not the same

- **instruction (opcode)** — a mnemonic in the recorded `instr.bin` on veccore0
  (`core == 0`, `sub == 1`), paired by PC and ID, **inside the VF window**.
  Examples: `SIMT_LDS`, `SIMT_FDIV_I`, `SIMT_REDUX`, `RV_VMUL`.
- **schedule** (load-4, dual-drain, keep, paint, …) — how the program owns work
  and orders stages. A schedule is **not** an instruction; never put a schedule
  name in a single-opcode / uarch section.

## Portable procedure

### 1. Record one launch

Run under the simulator recorder, one launch at a time, preloading the camodel
runtime before loading `libascendcl.so`:

```bash
npusim record -s <soc> -g -n 0 "<the launch command>"
```

The recorder writes, per core, two dumps plus the decoded `instr.bin`:
`*.instr_popped_log.dump` (issue/start, `is_popped == 1`) and `*.instr_log.dump`
(completion, `is_popped == 0`). The full TileLang / CCE compile+launch recipes
are separate run skills; the measurement rules below are language-agnostic.

### 2. Pair the two dumps (the general rule)

Pair every instruction by **PC and ID** across the two dumps. One instruction
runs from its start tick to its completion tick, **both ticks included**:
`active = completion − issue + 1`. This pairing is the general rule behind every
number in this skill family — busy cycles, VF windows, and the IPC line.

### 3. Busy union, not span

When several warps issue the same opcode the windows may overlap. The opcode's
time is the **union** of the per-warp `[issue, completion]` windows — an
overlapped tick is counted once. Warp 0 running 45–60 and warp 1 running 56–74
is `74−45+1`, **not** `(60−45+1)+(74−56+1)`. Compute it with the bundled tool
(it refuses to run on a single log):

```bash
python3 scripts/op-busy-cycles.py SIMT_LDS instr_popped_log.dump instr_log.dump
# pass the same instr.bin twice when the recorder wrote both halves into one file
```

### 4. Rate

`rate = useful work / busy`. For a copy the useful work is bytes moved; for
arithmetic it is the issue count (elements = issues × lanes). Keep the span as a
secondary number only.

### 5. Draw the figure

```bash
python3 scripts/instr-ipc-plot.py instr.bin simd|simt out.png [--bin W] [--warps] [--vf N]
```

Opcode rows by default; `--warps` for per-warp rows (SIMT only); `--vf N` picks
the N-th VF launch (0-based). Windowing, row rules, and the IPC line:
`references/instr-ipc.md`. Draw to the **last body issue**, not VF completion.

### 6. Chart thread count vs working cell

The single-op **chart thread count** (usually **256**) is where you draw the
IPC + warps figures — it is independent of the kernel's **working best cell**.
Do not skip single-op charts because the kernel cell is not 256. Note layout:
`skill:tilelanggym-st-report`.

## Accelerator

None beyond the two bundled scripts — they *are* the tooling. There is no
harness verb for this; run the scripts directly.

## Gotchas

- Computing a rate from a **single** log silently degrades to a span and
  double-counts overlap. The tool refuses one argument for this reason.
- A fixed-`N` launch that shrinks work/thread as threads grow can make the rate
  fall for that reason alone — prefer fixed work/thread when sweeping thread
  counts.
- A long all-warp 0-issue hole is an I-cache/I-stream stall, not a rate fact —
  diagnose separately (`skill:npu-i-cache-stall`).
- The figure x-axis ends at the last issue; empty VF drain is not drawn, or the
  busy part hides behind a long blank right edge.
- The decoder import needs the camodel runtime loaded first (see step 1) — a
  bare `import cannsim…` fails without it.

## Output

- busy / span / active-time percentiles per opcode (from `op-busy-cycles.py`)
- rate table (B/cyc or el/cyc) per opcode at the chart thread count
- one IPC figure + one warps figure per Schedule at the chart thread count

## See also

- `references/reading-trace.md` — full method: procedure, note layout, reading a
  load vs an arithmetic op, thread sweep, dtype matching.
- `references/instr-ipc.md` — the figure method (windowing, rows, IPC line, `--vf`).
- `skill:npu-perf-method` — estimate-first roofline / resource budget.
- `skill:tilelanggym-st-report` — where the uarch study is written in an ST note.
