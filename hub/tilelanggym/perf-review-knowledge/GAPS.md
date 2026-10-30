# PRC gaps (unmeasured / not yet carded) — do not invent

| Candidate ID | Topic | Why blocked |
|--------------|-------|-------------|
| PRC-SIMT-001 | SoftLib dual_drain vs fused/no-clobber **A/B el/cyc delta** on same G32 Case-3 | Have clobber **counts** (0/1/2/3) by tag; **no** paired el/cyc table proving wall count → KPI in one controlled matrix on Case-3 e2e |
| PRC-SIMT-002 | `vec-misched=on` vs `=0` effect on dual_drain G32 | Schedule axis required by skill; no seed card numbers yet |
| PRC-SIMT-003 | LDS.32 vs LDS.64 bandwidth on SoftLib Case-3 G32 best motif | Digs exist elsewhere; not harvested into PRC with SB8 G32 SoT tags |
| PRC-ALU-001 | SoftLib `FDIV_I` latency vs SIMD `VDIV` pipe on A5 | Mechanism known; need microbench table before ready card |
| PRC-MEM-003 | UB bank conflict on SoftLib LDS patterns (CANNBot PRC-MEM-009 style for our packs) | Need SoftLib-specific probe; do not copy CANNBot A5 % blindly |
| PRC-IPC-002 | Body4 firstLDS→lastSTS vs defining-opcode stage mid when they disagree | Noted MISSING in G32 ANALYSIS; no closed rule |
| PRC-SCH-004 | When VL `VDIV(X/absmax)` should replace recip+VMUL as SIMD SoT | t779u shows B≻A on G32 Case-3; SoT promotion policy not harness-frozen (PRC-SCH-003 now = pack-UB vs VSEL paint · t591u) |
| PRC-MEM-004 | G16 scratch expand VSTI↔VLDI address pattern | Described in G16 ANALYSIS; not yet its own PRC with snippets |

Update this list when a dig lands numbers; then promote `needs-measure` → `ready`.

---

**Index discipline (t784u):** Rows here are **not** checkpoints. Promote only after measure → write card (six sections + front matter) → **register in `perf-review-checklist.md`** → pass `scripts/check_prc_index.py`. Do not create empty category dirs for gaps.
