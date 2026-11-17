---
name: npu-stage-model
description: >
  Build a staged theoretical bound for a kernel and compare the schedules a body
  can actually run against that budget. Use when an ST study asks for the
  theoretical model (a separate <case>-theoretical.md), or when a kernel's
  measured VF should be checked against a serial sum of per-opcode lines. Pairs
  with the schedule write/refuse patterns in references/schedule-patterns.md.
license: CANN Open Software License Agreement Version 2.0
compatibility: >
  Requires python3 and the TileLang Ascend backend. Lines come from the
  single-opcode burst playbooks (skill:npu-op-burst); charts from
  skill:npu-single-opcode-rate.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# Stage model (theoretical model)

Build a staged bound for a kernel and compare the schedules a body can actually
run against that budget. Counterpart of the roof: the roof
(`skill:npu-perf-method`) takes the slowest overlapped pipe; this model **sums
stages back-to-back at their best pure lines**.

## Where the note lives

Write a **separate** case file next to `ANALYSIS.md`:

```text
<note-dir>/<case-name>-theoretical.md
```

Name the file from the case folder the user named for the note. Do **not** embed
this model as a subsection of `ANALYSIS.md` (`skill:tilelanggym-st-report`).
Point to the file from `ANALYSIS.md` in one line when it exists.

Use the **working best cell** from the ST study (shape / schedule / threads) as
the stock cell for the whole note, unless the user names another cell. The stock
cell is chosen one of two ways (decided in ask-first, `skill:tilelanggym-st-explore`):

1. **The user names the case** — shape and threads they want to study.
2. **The agent proposes** — compute the theoretical sum (§2) at each power-of-2
   thread count and propose the best as the case to study.

That stock cell is the kernel cell, not the single-op chart thread count.

**Note shape** (keep this heading order):

1. Kernel flow  
2. Theoretical estimation (from single-op lines)  
3. Case implementation — required Base / Op-matched / Serial; **Conclusion metrics last**  
4. Limitations  
5. Exploration Notes *(optional)*  

Lines from `skill:npu-op-burst`. How to write the TileLang schedules:
`references/schedule-patterns.md`. Charts: `skill:npu-single-opcode-rate`.
First-launch / 0-IPC: `skill:npu-i-cache-stall`.

## Accounting — warm VF

- **Single-launch** microbenches / Base with one VF: rates from that VF
  (post-`END` blank outside the target-op busy union does not pollute the rate).
- **Multi-launch** cases (multi-slab, redundant warm launch): **rates and charts
  use VF[1]** (`instr-ipc-plot.py --vf 1`). Full-case VF ≈ `2 × span(VF[1])`
  when two equal slabs each have one VF.

## 1. Kernel flow

Data path (GM → UB → VF ops → UB → GM) and a table of each operator's dtype and
bytes/elements per warp issue. Name the stock shape and thread count for the
whole note. The proposal uses the single-op lines at that thread count, so the
stock cell and the lines agree (convert-heavy kernels: usually **256t** — F2F's
microbench ceiling is 256t-only).

## 2. Theoretical estimation (from single-op)

For that stock thread count:

1. **Work counts** — unique algorithm traffic per operator.
2. **Lines** — best **pure** line per operator at that thread count
   (`skill:npu-op-burst`). Wrong thread / impure microbench is not a line.
3. **Terms** — `work / line`; **sum** = serial model cycles.

```text
term(operator) = unique work(operator) / best line(operator, threads)
model = sum of terms
```

Present: theoretical rates vs **Base** effective rates; serial-model cycles per
operator + **sum**, set against measured Base VF.

## 3. Case implementation

Same shape and thread count for every schedule. Effective rate = unique work ÷
opcode busy-union on the accounting VF. Each schedule subsection: short bullets,
**one** IPC + **one** warps figure, effective-rates table vs theoretical.
Optional: a small "VF against the model" table (measured / model sum, measured /
Base).

### Required (always, when the user asked for the theoretical model)

| Schedule | Meaning |
| --- | --- |
| **Base** | The **best SIMT version from `ANALYSIS.md`** — the working best cell's schedule, carried in as the reference body. |
| **Op-matched** | Try to implement the best instruction schedule from the uarch study at the TileLang level: the CCE techniques that won per opcode, re-spelled in the DSL where it can emit them. Record what was **emitted**. |
| **Serial** | One stage at a time — one instruction band, then the next. The purpose is to see how much of the theoretical performance this ordering reaches and where the bubbles are. |

Write/refuse for these: `references/schedule-patterns.md`. If serial spills at
the stock shape, shrink to the largest spill-free tile and name that ceiling in
Limitations.

### Optional (run only after the user reads the first three)

Do **not** invent these for every study. Offer them once the three required
schedules are written and read; only techniques that progressively improve get
promoted into §3 — the rest are tracked in §5 Exploration Notes.

| Class | Idea (examples) |
| --- | --- |
| **Warp-pipeline** | Same stages as serial, per strip of threads — shorten whole-slab drains. |
| **Double-buffer** | Prefetch strip `t+1` while multiplying strip `t`. |
| **Quad-buffer / deeper prefetch** | More strips in flight so loads issue as one band (hides return holes; may hit a bank-replay floor). |
| **ILP / multi-acc** | Split independent accumulate chains; straighten control flow (can collapse cold VF ≈ warm VF). |

### Same structure for every schedule (required)

Every schedule subsection of §3 — required or optional — carries, in this order:

1. **Illustration** — short text sketch of layout and stage order.
2. **Performance for the various instructions** — effective-rate table: each
   opcode's work, busy cycles, effective rate vs its theoretical line.
3. **Instr IPC chart** — opcode-row figure on the accounting VF.
4. **Warp IPC chart** — per-warp figure on the same window (`--warps`).

### Conclusion — performance metrics (required, end of §3)

Two tables:

1. **Methods vs theoretical serial sum** — one row per schedule run (theory sum,
   Base, Op-matched, Serial, plus optionals). Columns: VF (full-case estimate),
   el/cyc (`N / VF`), vs theoretical (measured VF / model sum). No "X wins"
   sentence.
2. **Per-operator effective rate by method** — rows = operators; columns =
   Theoretical + each schedule.

Short bullets: closest schedule to the model, which pipe is still far from its
line, what remains open. No crown sentence.

## 4. Limitations

Every line a schedule does not reach gets one entry, classed as:

- **Register ceiling** — live set spills; name largest spill-free shape.
- **No packed ISA** — packing did not drop issue count.
- **DSL cannot express** — a technique CCE/`.asc` can spell but TileLang cannot
  emit (missing barrier / access shape / layout inference); the CCE line stands,
  the DSL body cannot reach it.
- **Window pollution** — microbench line is a lower bound, or fused consumer
  sits in the band.
- **First-launch / I-stream** — cold VF[0]; rates from VF[1] on multi-launch
  cases (`skill:npu-i-cache-stall`).
- **Practical fused rate ≠ dedicated microbench** — e.g. F2F Schedule 4 @256
  does not transfer into a fused kernel (~47 el/cyc practical).
- **In-kernel bandwidth floor** — e.g. lane-stride bank replay capping fused LDS
  far below the pure pack line.
- **Theory reached only by case structure** — the CCE body hits its line because
  of the microbench's shape, small tile, or overlap freedom; a different case
  does not inherit that line.

A limitation is a fact from a trace or generated source. Not a conjecture.

## 5. Exploration Notes *(optional)*

When the path to the published schedules matters, keep a hierarchical journal
**after** Limitations — not mixed into §3. Purpose: prevent repeating the same
attempts. One subsection per step (goal → what ran → what the trace showed →
next lever); a small table of dead-end variants (idea / result / verdict) when
useful. Do **not** put exploration numbers into Conclusion unless that schedule
was promoted into §3.

## Consistency rule

Measured VF sits at or above the model sum; each schedule's effective rate sits
at or below its line. **A schedule below its line means the line is polluted —
re-run that operator's burst ladder**, then restate the model.

## Gotchas

- Do not write the model as a subsection of `ANALYSIS.md` — it is a separate
  file, named once from the note.
- Do not invent every optional class for every kernel; offer them only after the
  required three are written and read.

## Output

- `<case-name>-theoretical.md` in the note shape above
- runnable Base / Op-matched / Serial TileLang bodies (or Serial's spill-free
  ceiling named)

## See also

- `references/schedule-patterns.md` — TileLang write/refuse for the schedule
  classes.
- `skill:npu-op-burst` — the per-opcode lines the model sums.
- `skill:npu-single-opcode-rate` — busy-union + charts.
- `skill:npu-i-cache-stall` — warm VF[1] on multi-launch cases.
- `skill:tilelanggym-st-report` — the note the theoretical file sits beside.
