---
name: npu-op-burst
description: >
  Drive a hand-written CCE single opcode (SIMT_LDS / SIMT_F2F / SIMT_FFMA /
  SIMT_STS) to its best measured rate. Use when a roof or stage model needs a
  real per-opcode line, when a kernel beats a recorded line and that line must
  be re-pushed, or when preparing single-op Schedule bodies for an ST study.
  Bundles the burst ladder (purity, coalescing, packing, barrier, window purity)
  plus per-op playbooks with measured constants and runnable .asc bodies.
license: CANN Open Software License Agreement Version 2.0
compatibility: >
  Requires the CANN bisheng compiler (npu-arch dav-3510), the tl_templates
  headers, npusim + the camodel runtime, and a launch/decode harness
  (see skill:npu-cce-run). .asc bodies compile with -DSIMT_THREADS and friends.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# Single-opcode burst (CCE)

Push one CCE opcode to its maximum rate. This is the CCE counterpart of
`skill:npu-single-opcode-rate`: that skill measures an opcode as it naturally
falls; this one drives it to its best measured line, so a roof or stage model
built from these numbers is a real upper bound for hand-written bodies.

## Naming

- Each spelling of one opcode is a **Schedule** numbered from 1: Schedule 1,
  Schedule 2, …
- Do not use "Attempt A/B" or "v3/v4" as the public name. Version tags may stay
  in file names; the note and the tables say Schedule N.
- A short label names what changed: "Schedule 2 — packed, register sink".

## Purity (required)

A single-op case measures **one** target opcode. The body may use only:

- the target opcode in the measured band
- forced helpers the band cannot avoid (`IADD_I` / `LEA` for addresses; `LDS`
  preload before an F2F/FFMA band; a checksum or store sink **after** the band)

Refuse anything else in that case: no cross-op contamination (no `F2F` in an LDS
sink — use a checksum word), no spills (`STK`) to "help" the band, no store-all
of the tile when a 1-word/thread checksum proves the loads happened.

Busy-union is always of the **target** opcode only. Preload helpers for F2F/FFMA
are allowed outside that union; they must not sit inside the convert/multiply
busy window when a barrier can keep them out.

## The ladder, in order

Each step is a separate launch and a separate Schedule when the spelling
changes. Measure, then move to the next only if the step moved the rate.

1. **Coalesced layout.** Element index is `tid + i * threads`: a warp touches 32
   consecutive elements per iteration. Index `tid * kPerThread + i` puts one
   thread's elements consecutively and scatters the warp's lanes; refuse it.
2. **Fixed work/thread, then thread sweep.** Hold elements (or products) per
   thread fixed when the thread count changes — e.g. 32 el/thread so
   `N = 32 × threads`. Then sweep 128, 256, 512. A fixed-`N` sweep shrinks
   work/thread as threads grow and can make the rate fall for that reason alone;
   that fall is not a hardware fact. Some operators (LDS/FFMA) use fixed `N` at
   the stock thread count for the line; say which.
3. **Burst isolation.** Preload every operand into registers first, then issue
   only the target opcode, then drain (checksum or store). The measured window
   holds only that opcode.
4. **Width packing.** Two fp16 per lane, one 32-bit load per lane: 128 bytes per
   warp issue instead of 64. Unpack in registers after the window. Verify from
   the trace that the issue count dropped and the bytes per issue rose; a narrow
   re-emit means the compiler saw a second load path.
5. **Window purity check.** Count the non-target opcodes between the first and
   last issue of the target opcode. Address adds, spills, or stray
   loads/converts in the window hold the issue rate down. This check separates a
   real burst from a mixed stream. Barriers that align warp entry belong here
   when stagger is the limiter. A long blank where **every** warp issues nothing
   is an I-stream stall — not stagger; prefer rates/charts from a **warm 2nd
   VF** before publishing the line (separate skill, drafted next).
6. **Size scale (loads/stores).** When hunting an absolute bandwidth peak, push
   `N` / work-per-thread at fixed threads until the rate plateaus without
   spills. Past the plateau, denser WPT can drop; more warps may be required.
   Record the peak cell separately from a small fixed-`N` pack cell.

The step-1 spelling, both ways, on a load:

```cpp
// refuse — one thread's elements consecutive, the warp's lanes scattered
for (int i = 0; i < kPerThread; ++i)
  v[i] = src[tid * kPerThread + i];

// write — a warp touches 32 consecutive elements per iteration
for (int i = 0; i < kPerThread; ++i)
  v[i] = src[tid + i * kThreads];
```

## Use a known operator: start from the playbook

For LDS, F2F, FFMA, or STS, do **not** re-run the whole ladder — start from
`references/op-bursts.md`, which is the ladder already climbed: per operator,
the Schedule that won, the spelling to refuse, the measured constants, and the
compile params. Pick the runnable body under `scripts/{lds,f2f,ffma,sts}/` and
compile/launch per `skill:npu-cce-run`. Re-run the ladder only when a kernel's
effective rate lands **above** the recorded line (the line is then stale or
polluted).

## Note layout per operator (required)

For each **opcode** section (not a case schedule name):

1. **Case line** — dtype, fixed `N` or fixed work/thread, sink rule, purity note.
2. **Per Schedule** (Schedule 1, 2, …):
   - short ` ```text ` diagram of one warp issue (and stagger vs barrier when it matters)
   - rate table (chart-thread / stock cell always; full 128/256/512 sensitivity when fixed-WPT was swept)
   - **one** chart set at the **chart thread count** (usually 256; also called stock): IPC figure + warps figure — not one pair per thread cell
   - one bullet naming a drop cause when the sensitivity table falls
3. **Comparison** table across Schedules at the chart thread count, then the winner line.

Do not draw charts for 128 and 256 of the same Schedule. Multi-thread evidence
belongs in the table; the figure is the chart-thread picture. In an ST study
this chart thread is independent of the kernel **working best cell**
(`skill:tilelanggym-st-report`).

## Thread-sensitivity table

When the harness is fixed work/thread, every Schedule that was swept gets its
rate table across 128 / 256 / 512 (/1024 when useful). When the harness is fixed
`N` at stock threads only, the Schedule table may be one row — say so.

**Expectation under fixed work/thread:** as threads grow, the rate (B/cyc or
el/cyc) often **raises or holds** (LDS / STS / FFMA). If it **drops**, name the
cause in one bullet — typical causes: warp **stagger** into the band (no
barrier); pollution inside the window (`PRMT`, address adds, spills); **issue-
window over-fill** (F2F Schedule 4: 107.79 @256t → 39.57 @512 → 30.65 @1024);
or fixed-`N` by mistake (work/thread fell) — fix the harness, do not record the
drop as a limit.

## What limits the rate

Each constant is a measured opcode fact, read with the pairing in
`skill:npu-single-opcode-rate`; the worked numbers are in
`references/op-bursts.md`.

- **Issue spacing.** Active time is latency; busy time ÷ issue count is spacing.
  A packed burst reaches near one issue per cycle when enough independent issues
  are in flight: ~64 per thread hides the 8–11 cycle `F2F`/`FFMA` latency at 128
  threads.
- **Address math.** One address add per load in the window caps the issue rate
  near 0.5–0.65 per cycle; folding them out reaches ~0.90. A `noinline` callee
  does not fold — the call boundary adds stack spills, worse than the adds.
- **`-enable-misched=false -enable-post-misched=false`** only helps when the
  window is already separated; on a spilling callee it changes nothing.
- **Warp stagger.** Without a barrier, warps enter the band at different ticks;
  busy-union stretches and the rate can fall as threads grow even under fixed
  work/thread.

## Measure

Same trace method as `skill:npu-single-opcode-rate`: veccore0, pair by PC and
ID — start tick from the popped log, completion tick from the instruction log —
busy union of the target opcode's windows, both ticks included. B/cycle for
loads and stores; output elements per cycle for arithmetic. A wrong-result
signature here is usually the checker, not the kernel: a checksum sink writes
`threads` floats, not the tile.

## Accelerator

None — compile the `.asc` with `bisheng` and record with `npusim` per
`skill:npu-cce-run`; the `.asc` bodies under `scripts/` are the tooling.

## Gotchas

- Do not call a `G ≠ 32` or different-body kernel by a playbook Schedule name
  (e.g. "load-4") — the Schedule names belong to specific measured bodies.
- Microbench vs case VF: single-launch pure Schedules chart **VF[0]** (a
  first-launch post-`END` blank sits outside the target-op busy union); multi-
  slab **case** kernels use warm **VF[1]**.
- F2F's 107.79 ceiling is **256t-only**; do not treat it as valid at 512/1024.

## Output

- per-op Schedule bodies (compilable `.asc`) + their compile params
- rate table per Schedule, one IPC + one warps figure at the chart thread count
- a winner line per opcode feeding the roof / stage model

## See also

- `references/op-bursts.md` — the per-op playbooks (LDS / F2F / FFMA / STS) with
  measured constants, write/refuse, and compile params.
- `skill:npu-single-opcode-rate` — the trace-pairing + busy-union method.
- `skill:npu-cce-run` — compile / launch / decode a `.asc` body.
- `skill:tilelanggym-st-report` — where single-op Schedules live in an ST note.
