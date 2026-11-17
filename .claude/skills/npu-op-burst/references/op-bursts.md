# Per-operator burst playbooks

How to drive each common SIMT opcode to its best line. `../SKILL.md` is the
general ladder — coalescing, fixed work/thread sweep, burst isolation, packing,
purity — in the order to climb it. This file is the ladder already climbed: per
operator, the Schedule that won, the spelling to refuse, what limits it, and the
measured constants on this target. When a case needs one of these operators,
start here instead of re-running the search; re-run the ladder only when a
kernel's effective rate lands above the line here (the line is stale or
polluted).

Naming: **Schedule 1, Schedule 2, …** — not "Attempt" or "v3/v4". File tags may
keep a version suffix; the note does not.

The constants are measured hardware facts on dav-3510, unified buffer, read per
`skill:npu-single-opcode-rate`. Runnable Schedule bodies live under
`../scripts/{lds,f2f,ffma,sts}/`. Pack LDS / FFMA use fixed `N=8192` unless
noted. F2F uses fixed 32 el/thread (`N = 32 × threads`). Charts: **one** IPC +
warps figure per Schedule at that Schedule's **stock cell** (usually 256t).
Multi-thread numbers live in the sensitivity table — do not attach a chart set
per thread cell.

**Microbench vs case VF.** Single-launch pure Schedules chart **VF[0]**; a
first-launch post-`END` blank sits outside the target-op busy union, so the rate
is unaffected. Multi-slab / multi-VF **case** kernels use warm **VF[1]** for
rates and charts (`skill:npu-i-cache-stall`).

## LDS — load from unified buffer

Two lines, do not confuse them:

| Line | Cell | Rate | Use |
| --- | --- | --- | --- |
| Pack (fp16 GEMV-style) | 256t, `N=8192` pairs, 128 B/issue | **81.11 B/cyc** | stock GEMV / half-tile roof at 256t |
| Size-scaled LDS.b32 (fp32) | 256t WPT=96 → **76.38**; 512t WPT=96 → **95.95**; 1024t → **97.72** | absolute pure LDS.b32 peak | roof when LDS.b32-bound and can size-scale |

| Fact | Value |
| --- | --- |
| Active latency | 27–29 cycles per issue |
| Scalar fp16 width | 64 B (32 lanes × 2 B) |
| LDS.b32 / pack width | 128 B (32 lanes × 4 B) — fp32, uint32 pack, `half2`, `bfloat16x2_t` |
| Issue-rate with ~1 `IADD_I` / `LDS` | ~0.60–0.76/cyc at the peaks; SoftLib ~114 needs ~0.9 |

```text
Schedule 2 warp issue:  lane0→(e0,e1) … lane31→(e62,e63)   ← 32 × 4 B = 128 B
index: tid + i * threads   (strided). contiguous tid*WPT+i → ~4 B/cyc — refuse
```

- **Write (pack @256)** — Schedule 2 uint32 / Schedule 3 `half2` / Schedule 4
  `bfloat16x2_t` — ISA-identical **81.11**. Checksum sink only. Bodies:
  `../scripts/lds/schedule-{2,3,4}.asc`. Compile `-DSIMT_THREADS=256`.
- **Write (LDS.b32 peak)** — size-scaled fp32, strided, WPT≈96: **76.38 @256**,
  **95.95 @512**, **97.72 @1024** (best measured; @2048 collapses). Body:
  `../scripts/lds/schedule-fp32-size.asc`. Compile
  `-DSIMT_THREADS=256|512|1024 -DLDS_N=…` (WPT ≈ 96 at 256/512 peaks).
- **Refuse** — Schedule 1 scalar fp16; contiguous `tid * WPT + i`; per-lane
  float4 (also bank-conflicts); convert/`F2F` in the LDS sink; treating
  `bfloat16x2` as SoftLib ~114. At matched issues/bytes, bf16x2 ≡ fp32 at small
  tile and at @1024 peak; at @512 peak bf16x2 is slightly behind (~94.43 vs
  95.95). Body: `../scripts/lds/schedule-1.asc`.
- **Limit** — `IADD_I` 1:1 with `LDS` (pointer CSE / pre-addr / unroll do not
  clear it); SoftLib ~114 open. @256t past WPT=96 denser WPT drops — 8 warps
  cannot hide latency (76.38 is the 256t size ceiling).

Charts: one IPC + one warps figure per Schedule at the stock cell (256t for
pack; peak cell for size-scaled).

## F2F — fp16 to fp32 convert

| Fact | Value |
| --- | --- |
| Active latency | 8 cycles per issue |
| Schedule 1 width | 32 values / warp-issue |
| Schedule 2+ width | 64 values (`__half22float2`) |
| Best line | **107.79 el/cyc @256t** — Schedule 4, barrier-aligned (**256t-only ceiling**) |
| Same S4 @512 / @1024 | **39.57** / **30.65** — busy inflates; warps over-fill the issue window |
| Co-issue in the pure band @256 | 4 warps per tick |

```text
preload (per warp)     BARRIER      pure F2F band
w0  ▓▓▓▓▓▓▓▓▓▓           |||          ████████████
…                        |||          ████████████     ← 4 warps / tick @256
w7           ▓▓▓▓▓▓▓▓▓▓  |||          ████████████
```

- **Write** — Schedule 4: preload `uint32`, reinterpret as `half2`,
  `asc_syncthreads` before and after the convert band. Body:
  `../scripts/f2f/schedule-4.asc`. Compile `-DSIMT_THREADS=128|256|512|1024
  -DSIMT_WPT=32` (fixed work/thread; `N = WPT × threads`).
- **Refuse** — Schedule 1 scalar; Schedule 2 `__half22float2` from two `half`
  regs (`PRMT` in the window); Schedule 3 word-preload without barrier; treating
  107.79 as valid at 512/1024. Bodies: `../scripts/f2f/schedule-{1,2,3}.asc`.
- **Limit** — 107.79 is a **dedicated-microbench ceiling at 256t**. Past 256t
  the barrier band collapses. In a fused kernel the consumer issues inside the
  convert band; practical fused rate ~47 el/cyc.

## FFMA — fp32 multiply-add on registers

| Fact | Value |
| --- | --- |
| Active latency | 11 cycles per issue |
| Issue width | 32 products — no wider ISA observed |
| Best microbench line | Schedule 3 barrier: **20.90 @256** → **24.67 @512** → **26.01 @1024** (improves with warps; still lower bound) |
| Practical staged ceiling | **32.38 el/cyc** (serial fused case) |

```text
source as float2  →  still 2 × scalar FFMA emitted  (no vector FFMA ISA)
```

- **Write** — Schedule 3: preload+convert, barrier around the multiply band,
  scalar `FFMA`. Body: `../scripts/ffma/schedule-3.asc`. Compile
  `-DSIMT_THREADS=256|512|1024` (stock charts @256); fixed `N=8192`; host copies
  two fp16 tiles (operands A and B).
- **Refuse** — expecting `float2` sources to widen the issue (Schedule 2 buys
  schedule density only). Bodies: `../scripts/ffma/schedule-{1,2}.asc`.
- **Limit** — issue-bound; window may leak preload → microbench lines are lower
  bounds below serial 32.38. Cold first-launch / all-warp 0-IPC holes: the
  `skill:npu-i-cache-stall`.

## STS — fp32 store to unified buffer

| Fact | Value |
| --- | --- |
| Active latency | 20 cycles per issue |
| Issue width | 128 B (32 lanes × 4 B) |
| Line | **92.30 @256** → **95.34 @512** → **99.60 @1024** (best measured; mild warp scaling) |

```text
warp issue: lane0→out[tid] … lane31→out[tid+31]   ← 32 × 4 B = 128 B
```

- **Write** — Schedule 1 coalesced; pack `float2` stores when the producer holds
  pairs. Body: `../scripts/sts/schedule-1.asc`. Compile
  `-DSIMT_THREADS=256|512|1024 -DSIMT_WPT=32` (floats per thread;
  `N = WPT × threads`).
- **Refuse** — nothing observed that beats coalesced.
- **Limit** — none observed among the four pipes for store; strongest streaming
  store line ~100 B/cyc @1024t.

## Reading the playbooks

- Pick the line that matches the studied launch (threads, dtype, width). Pack
  **81.11** is the 256t fp16 pack cell; LDS.b32 peak **97.72** is @1024
  size-scaled; F2F **107.79** is **256t-only**.
- **Thread-count tradeoff for convert-heavy kernels:** LDS / STS / FFMA improve
  with warps; **F2F collapses** past 256t. A F2F-heavy GEMV serial model is
  strongest at **256t**; 1024t pays only for pure streaming (LDS/STS-dominated,
  no converts).
- Off-cell launches run their own ladder (`../SKILL.md`).
- One chart set per Schedule at that Schedule's stock cell.
- A fused kernel is expected below LDS and F2F microbench lines (window
  pollution) and near the FFMA staged cap.
