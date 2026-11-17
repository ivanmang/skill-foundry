# Schedule patterns (TileLang SIMT)

How to **write** the schedule classes that `../SKILL.md` names. That file is the
note shape and accounting; this file is the TileLang spelling. Cross-formula: any
body that stages load → convert → compute → store through UB can use these
patterns. Compile with the TileLang Ascend backend (the pto-vmi/pto-isa target
adapters document the repo commands; the `tilelang.compile(..., target="ascend")`
mechanism is shared).

Use only when the study asked for the theoretical model, or when a clear next
lever exists after Base / Op-matched / Serial. Do not invent every optional class
for every kernel.

Notation: `slab` = rows in one VF launch; `threads` = launch size; a **strip** =
`threads` consecutive rows (one row per thread). Fragments are thread-private
registers.

## Ladder (order to climb)

```text
Base (best SIMT from ANALYSIS)  →  Op-matched  →  Serial  →  Warp-pipeline  →  Prefetch (dbl / deeper)  →  Multi-acc
                      ↑ required for the theoretical model ↑         ↑ optional ↑
```

Stop when the next lever does not apply (no strip structure, live set spills,
bank floor unchanged).

---

## 1. Base — the best SIMT version from ANALYSIS

The working best cell's schedule from `ANALYSIS.md` (§4 stages), carried into
the theoretical note as the reference body — no rewrite. Measure it; use it as
the reference VF in `../SKILL.md` §2–§3.

## 2. Op-matched — the uarch winners at TileLang level

Try to implement, in the DSL, the per-opcode techniques that won in the uarch
study, where TileLang can emit them. Record what was **emitted**, not what was
asked for.

```text
write:
    convert x once into xf[K]          # packed convert if dtype allows
    keep accumulators in fragments
    pack stores when pairs are ready   # float2 STS when producer holds pairs

refuse:
    convert x again on every product
    force packed A loads the DSL cannot emit  # then claim "op-matched LDS"
```

If live state grows (`acc` + `xf` + …) and spills appear (`LDK`/`STK`), that is
a **register ceiling** — go to Serial (or shrink the tile), not more packing.

## 3. Serial — one stage at a time

Run one instruction band, then the next: load+convert, then multiply, then store
— each stage a dense band. The purpose is to see how much of the theoretical
performance this ordering reaches and where the bubbles are.

```text
write:
    xf[K]  = Cast(x_ub[…])                 # once
    af[slab, K] = Cast(a_ub[…])            # all load+convert first
    acc[…] = 0
    for k:  acc += af[:, k] * xf[k]        # pure multiply band
    out_ub[…] = acc                        # store band

refuse:
    LDS → F2F → FFMA → STS per element     # Base interleave; holes between groups
```

Live set ≈ `slab×K + K + slab` fp32/thread-scale fragments. If it spills, shrink
to the largest spill-free tile and name that ceiling in Limitations
(`../SKILL.md`).

## 4. Warp-pipeline — stages per strip

Same stage order as Serial, but one strip of `threads` rows at a time. Later
strips are not gated on a whole-slab LDS→F2F drain.

```text
write:
    xf[K] = Cast(x_ub[…])                  # once per VF
    for t in strips:                       # strip = threads rows
        af[threads, K] = Cast(a_ub[t*threads + …])
        mac strip t into acc
        store strip t

refuse:
    wait for entire slab af before any multiply   # Serial whole-slab drain
```

Scratch is strip-sized (`af[threads, K]`), so register pressure drops vs Serial
at the same `N`.

## 5. Double-buffer — prefetch strip `t+1`

Keep the next strip's loads in flight while multiplying the current strip.

```text
write:
    prolog:   load strip 0 → af0
    steady:   prefetch strip t+1 → idle half
              mac+store strip t from ready half
    epilog:   mac+store last strip

refuse:
    load strip t, wait, convert, mac, store, then start t+1   # no overlap
```

Needs ≥ 2 strips. Prefetch depth of one strip may still leave **LDS holes**
between bursts — deepen prefetch next.

## 6. Deeper prefetch (quad-buffer class)

Put several strips in flight so the slab's `A` loads issue as **one** band
instead of short bursts separated by drain holes.

```text
write:
    prolog:   load strips 0 .. D-2 into af0 .. af(D-2)
    steady:   prefetch strip t+(D-1); mac+store strip t
    epilog:   mac+store remaining strips
    # D = prefetch depth (e.g. 4 strips → 4 af halves)

refuse:
    deepen prefetch when the mid-band issue rate is already bank-replay bound
    # more in-flight loads do not fix a bad lane stride
```

Needs `n_strips ≥ D`. If the merged band still sits far below the pure LDS line,
name an **in-kernel bandwidth floor** (lane stride / bank replay) in Limitations
— do not keep deepening.

## 7. Multi-acc / ILP

When independent strips (or half-fragments) wait on a long serial `acc += …`
chain, split into several accumulators advanced in the **same** `k` loop.
Straight-line control (no modular `t`-loop) can also collapse cold VF ≈ warm VF
(`skill:npu-i-cache-stall`).

```text
write:
    split independent work into acc0, acc1, … (or half-fragments af*a / af*b)
    for k:
        acc0 += …; acc1 += …; …            # several chains per iteration
    store combined results

refuse:
    even/odd indexing inside one Parallel body when the Ascend
    structural-equal check rejects it — split fragments instead
    claim LDS improved when only the FFMA tail shortened
```

Fragment-half split: each buffer sees **one** index expression per `Parallel`
body (e.g. cols `0..3` and `4..7` in separate fragments). That is a compile
workaround, not a math change.

## 8. Drop auto thread-storage sync (optional lever)

Codegen may insert `asc_syncthreads` via the thread-storage-sync pass. When
every `out_ub` write is **thread-private**, UB inputs are ordered by MTE2 pipe
syncs, and VF→MTE3 uses notify/wait in the host wrapper, those barriers can gate
the store on the slowest warp's FFMA for no correctness reason.

```python
# tilelang.compile(..., pass_configs={
#     "tl.disable_data_race_check": True,
#     "tl.disable_thread_storage_sync": True,  # opt-in
# })
```

```text
write (opt-in):  disable_thread_storage_sync when the family has no cross-thread UB writes
refuse:          disable it on bodies that share UB cells across threads
```

Re-check correctness (`PASS`) after enabling.

---

## Refuse as a class

| Idea | Why refuse as headline |
| --- | --- |
| Dual VF that **splits** work to shrink I-stream | Changes the launch model; diagnosis only (`skill:npu-i-cache-stall` Fix B) |
| Relayout that does not compile | Record as Limitations / Exploration; do not ship a broken builder |
| Reorder that sinks stores / leaves LDS trickle unchanged | Overlap without shortening the busy band is not a win |
| Copying a microbench barrier convert into a fused kernel | F2F Schedule 4 does not transfer (`skill:npu-op-burst`) |

## Definition of done

- Required Base / Op-matched / Serial exist as runnable TileLang bodies for the
  studied shape (or Serial's spill-free ceiling is named).
- Each optional pattern that was run has a short write spelling in the note
  (cite this file) plus charts/rates per `../SKILL.md`.
- Nosync, if used, is called out and correctness still passes.

## Reference — contiguous load (address shape only)

Not a stage schedule. Lane `t` reads element `t + step * threads`, so one warp
reads 32 adjacent elements. The other address, `t * stride + step`, puts
neighboring lanes far apart. Use the first when the data is contiguous.

```text
with T.SimtVF(threads):
    for step in steps:
        for t in Parallel(threads):
            acc[t] = acc[t] + buf[step * threads + t]

refuse, lanes far apart:
    acc[t] = acc[t] + buf[t * stride + step]
```
