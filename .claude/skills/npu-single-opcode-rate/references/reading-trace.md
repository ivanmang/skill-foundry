# Reading a trace — the single-opcode rate method

Full method behind `SKILL.md`. The idea: a whole kernel's VF window is the
overlap of many opcodes. To attribute cost, first measure each opcode alone in a
tiny launch that issues it many times, then read the rate from the trace.

## Instruction (not schedule)

An **instruction** is an opcode mnemonic in the recorded `instr.bin` on veccore0
(`core == 0`, `sub == 1`), paired by PC and ID, **inside the VF window**.
Examples: `SIMT_LDS`, `SIMT_FDIV_I`, `SIMT_REDUX`, `RV_VMUL`.

A **schedule** (load-4, dual-drain, keep, paint, …) is not an instruction. Do
not create a single-op / uarch section named after a schedule. Schedules belong
in the case layout and sweep tables (`skill:tilelanggym-st-report`).

The kernel **working best cell** (breakdown / running IPC) is not the same as
the single-op **chart thread count** (usually 256). Charts still go at the chart
thread count even when the working best cell differs.

## Reading the trace (two dumps — the general rule)

The recorder writes two logs per core. The pairing and the arithmetic below are
**the general rule for every calculation in this skill family** — busy cycles,
active time, VF windows, IPC charts.

- **`*.instr_popped_log.dump`** holds the **start** of each instruction: the
  tick it is issued (`is_popped == 1`).
- **`*.instr_log.dump`** holds the **completion** of each instruction: the tick
  it finishes (`is_popped == 0`).

Pair one instruction by its **PC and ID** across the two dumps. One instruction
runs from its start tick to its completion tick, **both ticks included**: active
cycles are `end − start + 1`.

With several warps, the same opcode issues once per warp and the windows may
overlap. The opcode's time is the **union** of the per-warp windows — an
overlapped tick is counted once, never double-counted. An instruction that runs
45–60 in warp 0 and 56–74 in warp 1 is **not** `(60−45+1) + (74−56+1)`; it is
`74−45+1`. Same instruction, different warps, different active times — take the
union.

## Procedure

1. Write a launch whose body is a single opcode repeated. Prefer **fixed
   work/thread** when comparing thread counts (for example 32 el/thread so
   `N = 32 × threads`). A fixed-`N` launch that shrinks work/thread as threads
   grow can make the rate fall for that reason alone — that fall is not the
   hardware limit. (To push an opcode to its best line, use the CCE burst ladder
   — separate skill `npu-op-burst`.)
2. Record it once. From veccore0, pair each instruction by PC and ID: start tick
   from the popped log, completion tick from the instruction log.
3. **Active cycles** for one instruction are `completion − issue + 1` (both
   ticks included).
4. **Issue span** is from the first issue of that opcode to its last completion,
   inclusive.
5. The **rate** is the useful work divided by the **busy time**, the union of
   the per-warp `[issue, completion]` windows — overlapping warps are counted
   once. For a copy, useful work is the tile bytes moved. For arithmetic, it is
   the issue count. Keep the span as a secondary number only.

The pairing, the busy union, and the span are computed by
`../scripts/op-busy-cycles.py`. It takes both logs and refuses one; do not
compute active cycles from a single log.

**Refuse as the uarch study:** fused "piece" kernels that still run several
opcodes (piece-load / piece-max / …). Those may appear as a short check next to
the kernel breakdown; they do **not** replace per-opcode Schedules with diagrams
and charts. Inside an ST study the single-opcode bodies are CCE (`.asc`) — not
TileLang — see the op-burst skill's runnable Schedules.

## Note layout and diagrams (required)

Everything below is defined in this skill. Do not open an external case note for
the layout.

### Where to write it (hard rule)

| Situation | Where |
| --- | --- |
| Inside an ST study (any number of opcodes) | **Required:** `<note-dir>/simt-uarch/simt-uarch.md` + plots under `simt-uarch/plots/` (or `<note-dir>/plots/`), cases run as **CCE (`.asc`) bodies**. `ANALYSIS.md` names the file once (intro or appendix) — do not paste the rate tables into ANALYSIS. |
| Outside an ST study, one opcode only | The same skeleton may live in the measuring note itself. |

A note that only has rate tables and no IPC/warps figures is **incomplete**.
Citing playbook numbers without a case launch and charts is incomplete.

### File skeleton (copy this shape)

```text
# uarch

- one-block target, busy = union of [issue, completion] windows (inclusive), purity rule
- chart thread count (usually 256); index rule; VF window rule

## 1. Case config
- working-best or reference shape (bullets)
- table: Op | Dtype | B or els / warp-issue | Active cyc

## 2. <OPCODE>          # e.g. LDS — instruction name only
### 2.1 Schedule 1 — <label>
### 2.2 Schedule 2 — <label>   # only if climbed
### 2.3 Comparison

## 3. <next OPCODE>
…

## N. Conclusion
- winners per opcode at the chart thread count
- which lines feed the roof / stage model

## Appendix — provenance
- which .asc body, which run dirs, plot commands
```

### Per Schedule (required — every Schedule that is reported)

1. Short bullets: dtype, bytes or elements per warp issue, active latency, index
   rule, purity (target + forced helpers only).
2. A short **text diagram** of one warp issue.
3. A **rate table** (full thread sensitivity when fixed work/thread was swept).
4. **One IPC figure and one warps figure** at the **chart thread count**
   (usually 256) — `instr-ipc.md` in this folder + `../scripts/instr-ipc-plot.py`.
   Embed both images next to that Schedule. Charts are **required** — do not
   attach a chart set per thread cell.
5. A **Comparison** subsection when more than one Schedule was climbed for that
   opcode.

## Reading a load

One `LDS` issue is one warp of 32 lanes. The lane width sets the bytes in one
issue: 32-bit is 128 bytes, 64-bit is 256, 128-bit is 512. A wider lane cuts the
issue count, and the bytes per cycle rise only when the wider issue does not
stall longer than the extra bytes are worth.

Two loads of two elements each are not a wider load: the lane width is set by
the load's operand size, not by the per-thread count. The way to one wide issue
per lane is packing — two fp16 bit-packed into one 32-bit word.

## Reading an arithmetic op

The rate is the issue count divided by the active cycles of that opcode. An
`FFMA` result count is the element count of the multiply. The per-cycle result
rate is the `FFMA` issue rate times the number of lanes.

## Sweep the thread count

Run the same single-opcode launch at several thread counts under fixed
work/thread. Expectation: the rate should **raise or hold** as threads grow. If
it drops, name the cause (warp stagger, window pollution, or a fixed-`N` harness
mistake). Record each cell; do not extrapolate.

## Busy cycles, not span

When warps overlap, the span double counts. Report the union of the per-warp
issue-to-completion windows, inclusive of both ticks. Keep the span as a
secondary number.

## Match the dtype

The launch must issue the same dtype the studied body issues for that opcode.
Read the opcode encoding in the trace when the source is not clear.

## Source

Busy-union pairing: `../scripts/op-busy-cycles.py`. Runnable single-opcode CCE
Schedules and the ladder that pushes them to their best line: the op-burst skill
(`npu-op-burst`, drafted next). Inside an ST study, write the study to
`<note-dir>/simt-uarch/simt-uarch.md` (`skill:tilelanggym-st-explore`).
