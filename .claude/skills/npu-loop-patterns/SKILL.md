---
name: npu-loop-patterns
description: >
  Use when structuring hot vector loops on A5/A6 — unroll width, loop-carried
  dependencies, tail handling, predicates (plt/POST_UPDATE), pointer addressing,
  scalar/ASU pressure — AND when reviewing kernels for known anti-patterns
  (chained POST_UPDATE, vcmax-per-VL, PK4-store floods, mid-loop predicate
  construction, plt-counter duplication, VSQZ store-hint deadlocks). Rules
  R1/R4/R7/R11-13 plus the case-writing anti-pattern catalog with measured costs.
category: ascendc-dev
license: CANN Open Software License Agreement Version 2.0
origin: local
maturity: draft
owner: skill-foundry
---

# Loop steady-state rules (A5-sim-validated; A6 carries except where noted)

1. **Eliminate loop-carried dependencies (R1)**: `acc = f(acc, x)` serializes at
   latency (5–15 cyc), not throughput. Per-iteration partials + a separate pass.
2. **Unroll for dual-issue, 2× usually saturates (R11)**: measured IPC 1.98 at 2×
   on EXUs; go 4× only for chain-depth ≥ execution queue (64) or confirmed
   load-bound. Stop when `c_cycle_phy_vreg_stall` >30% or icache_miss >0.
3. **Branch-free tails (R7)**: tail-counter loop (≤1 iter) + dynamic predicate;
   never `if` on tail size.
4. **Static predicates for the body (R13)**: `pset(PAT_ALL)` once; reserve `plt`
   for the tail. `plt_bX(scalar, POST_UPDATE)` decrements the counter itself —
   NEVER keep a parallel scalar countdown (pure ASU waste; measured 165→8
   scalar/VF, −97% asu stall).
5. **POST_UPDATE pointers (R12)**: one per stream; chaining one pointer across
   unrolled lanes creates AGS RAW (measured 67-cyc inter-iteration gaps).
   4 pre-offset independent pointers, advanced 256 B/iter, let AGS run ahead.
6. **Write port is 1/cyc (A6-verified)**: unroll ×4 hits `DST_PORT_LIMIT`
   (measured 488→615). Useful in-flight results ≈ 3/cyc.
7. **`__VEC_SCOPE__` control flow**: no early `return` inside a scope (bisheng
   9.3 backend fatal "cannot split the result"); use `#if` around whole scopes.

---

# Anti-pattern catalog — reject on sight

> **ARCH SCOPE**: consequences below were **measured on A5** (Ascend950PR_9599 sim).
> The **A6** column re-scopes each entry for the 3-EXU model (SLIDE→LNQ/EXU2, reduce
> v2 group-stage→ADD_CONV): ✔ = carries unchanged, ◐ = carries with a different
> mechanism/severity, ✘ = largely dissolved on A6 (watch the replacement trap).

## Scheduling & dependencies
| # | Anti-pattern | A5: why it loses (measured) | A6 | Fix |
|---|---|---|---|---|
| A1 | Loop-carried accumulator (`acc = f(acc, x)`) | Iteration waits producer **latency** (5–15 cyc), not throughput | ✔ chains are physics on both archs | Per-iter partials + separate reduce pass |
| A2 | `vcmax`-per-VL / running BRC+vmax scalar max | All-SLIDE serialization on EXQ0 — proven dominated | **✘ dissolves**: group-stage is fast ADD_CONV; cascade sits on its own LNQ. **A6 replacement trap → A19** | A5: vmax-tree (ADD) + ONE vcmax at the end |
| A3 | Seed-with-`vbr(-Inf)` then max from iter 0 | Dead first-iteration work + 1 MOV instr | ✔ | Peel iteration 0: load `src[0]` into the accumulator |
| A4 | Unroll ×4+ on already-parallel bodies | VREG write port 1/cyc → `DST_PORT_LIMIT` (488→615, +26%) | ✔ write port 1/cyc on A6 too (merge-cliff dumps); **plus** A6 arch-VREG(32) spill → SMEM_BAR cliff at u8 | ×2 once; ≥2 chains → chain-shorten |
| A5 | Optimizing without the roofline | EXU tuning on an LSU-bound kernel (V ≥ ~48 VLs) | ✔ method arch-neutral; EXU formula differs (see npu-perf-method) | Roofline first |

## Addressing & predicates
| # | Anti-pattern | A5: why it loses (measured) | A6 | Fix |
|---|---|---|---|---|
| A6 | **POST_UPDATE chained on ONE pointer across unrolled lanes** — "the most damaging anti-pattern in fused vec code" | AGS RAW: every update reads+writes the same scalar; measured 67-cyc inter-iteration gaps | ✔ ASU/AGS essentially unchanged (a6-notes §1) | One independent pre-offset pointer per lane (k·64 start, +256/iter) |
| A7 | Parallel scalar counter beside `plt`+POST_UPDATE | Duplicates the built-in countdown; ASU slots don't dual-issue (165→8 scalar/VF, −97% ASU stalls when removed) | ✔ | Let `plt_bX(scalar, POST_UPDATE)` own the decrement |
| A8 | `pset`/predicate construction inside the loop | Loop-invariant rebuilt every iter — wasted SLIDE/scalar cycles | ✔ | Hoist static predicates; dynamic `plt` only for the ≤1 tail iter |
| A9 | Runtime `if` on tail size | Disrupts the pipeline | ✔ | Tail-counter loop + dynamic predicate |
| A10 | Per-iteration `plt` on full-VL bodies | Full iterations need no dynamic mask | ✔ | Static `pset(PAT_ALL)` body; `plt` only in the tail |

## Data movement & stores
| # | Anti-pattern | A5: why it loses (measured) | A6 | Fix |
|---|---|---|---|---|
| A11 | ≥3 packed (PK4/PK) stores per iteration | STU queue (depth 6) backpressure: 2.36–5.2× (D6 3649 vs D1 699); max(EXU,LSU) model misses it | ◐ **not re-derived** — A6 STU depth/queueing unmeasured; assume similar, verify before tuning | vor-merge PART channels in registers, ONE store out |
| A12 | `vintlv`/`vdintlv`/`vpack` instructions where a dist-mode suffices | Burns the one slide FU on EXQ0; steals arithmetic slots | ◐ cost moves, not vanishes: v2 interleave/pack occupy **LNQ** slots and contend with SLIDE+LNEXP — budget them against the 2:1 mix | DINTLV loads / INTLV·PK stores — LSU, zero EXU cost, both archs |
| A13 | DINTLV load → vintlv round-trip | Paying LSU + SLIDE for one movement | ◐ same as A12 (the wasted op is LNQ-side on A6) | Choose the orientation that lands ordered |
| A14 | PK4 sequence relying on a compiler peephole | Silent ND byte-order break across compiler versions | ✔ toolchain issue, arch-neutral | Spell the fused single store explicitly |
| A15 | Per-element scale expansion via BRC + masked-store loops | 512 iters = 1024 serialized LSU round-trips (813 cyc) | ✔ LSU-side; the INTLV-dup+E2B fix ports (a6 twin compile-verified, runtime pending) | Self-INTLV dup buffer + E2B consume (194 cyc) |

## Control flow & scope
| # | Anti-pattern | A5: why it loses (measured) | A6 | Fix |
|---|---|---|---|---|
| A16 | Early `return` inside `__VEC_SCOPE__` | bisheng 9.3 backend fatal | ✔ toolchain issue | `#if` / `if constexpr` around whole scopes |
| A17 | Two `vsqz(..., STORE_REG)` without an intervening consuming store | **Hardware deadlock** (SQZN queue) | ✔ explicitly carries (a6-notes §8) | Alternate strictly: vsqz→vstus→vsqz→vstus |
| A18 | VF-local optimization judged without E2E measurement | Local wins lose overall (measured +5.9% net) | ✔ discipline | Always measure E2E ticks; dumps before/after |

## A6-specific traps (replace the dissolved A5 patterns)
| # | Anti-pattern | Why it loses on A6 (measured) | Fix |
|---|---|---|---|
| A19 | Calling A5 `vcgmax()`/`vcmax()` blindly (pack-per-iteration) | Compiler force-emits `vpackv2` **every iteration** — the A6 form of the vcmax-per-VL waste | Deferred pack: `vcgmaxv2` in-loop + ONE `vpackv2` after the loop |
| A20 | Pouring work into LNQ to "keep the third unit busy" below ~2 IPC demand | EXQs alone suffice; forced balance cost **+19.2%** (case8) and **1.52×** (DequantHiF4 baseline) | LNQ idle is optimal under 2 IPC — delete slide work instead |
| A21 | Porting unrolled bodies without re-checking the 8 KB / 2-way i-cache | Body growth cliff measured **456→926 (+103%)** = 441 `c_cycle_icache_miss` | Count hot-loop instrs (~60 ≈ 2 KB budget); auto-advancing pointers |
| A22 | A5 cross-core sync (`TSync_Custom` flag+16) left in a port | **Deadlocks on A6** | `set_intra_block` / `wait_intra_block` |

## Gotchas

- Drafted hub/inbox/npu-loop-patterns/SKILL.md: 7 rules with measured anchors. Source: npu_skills vloop-steady-state-patterns, predicate-patterns, post-update-and-fusion-tradeoffs. (was: Hot loops written with loop-carried accumulators, runtime-if tails, parallel scalar counters beside plt predicates, chained POST_UPDATE pointers, and unroll x4+ — each a measured stall source with no scoped skill warning about them or the __VEC_SCOPE__ early-return backend fatal.) — `dissection of npu_skills case-writing (2026-11-04)`
- Extended hub/inbox/npu-loop-patterns/SKILL.md with an 18-entry anti-pattern catalog (scheduling/addressing/stores/control-flow), each row: shape, measured/root cause, fix. Sources: npu_skills kernel-writing-rules R9/R12/R13, post-update-and-fusion-tradeoffs §5/§8, reduce-patterns A1-5, convert-patterns D/G matrix, store-dist-modes, squeeze-patterns deadlock rule, vloop §3/§6. (was: Loop-structure skills teach only positive rules; nothing tells a reviewer which concrete code shapes are known-bad, so kernels ship with chained POST_UPDATE pointers, vcmax-per-VL reductions, PK4-store floods, mid-loop predicate construction, plt-counter duplication, peephole-dependent PK4 byte order, and VSQZ store-hint deadlocks.) — `dissection of npu_skills case-writing (2026-11-04), extension`
- Rewrote the anti-pattern tables in hub/inbox/npu-loop-patterns/SKILL.md: per-entry A6 column + 'A6-specific traps' section (A19-A22). Positive rules unchanged. Source: a6-case-writing-notes §1/§4/§8/§10 + pto-vmi A6-box dumps. (was: Anti-pattern catalog presented A5-measured consequences as if arch-neutral — e.g. A2 (vcmax-per-VL = EXQ0 slide serialization) is explicitly 'largely gone' on A6 where the group-stage is fast ADD_CONV and the cascade has its own LNQ; several other entries change mechanism or severity on the 3-EXU model.) — `review of the dissected anti-pattern catalog (2026-11-04)`
