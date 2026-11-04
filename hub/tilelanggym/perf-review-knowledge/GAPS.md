# PRC gaps (unmeasured / not yet carded) — do not invent

| Candidate ID | Topic | Why blocked |
|--------------|-------|-------------|
| PRC-SIMT-002 | `vec-misched=on` vs `=0` effect on dual_drain G32 | Schedule axis required by skill; no seed card numbers yet |
| PRC-ALU-001 | SoftLib `FDIV_I` latency vs SIMD `VDIV` pipe on A5 | Mechanism known; need microbench table before ready card |
| PRC-MEM-003 | UB bank conflict on SoftLib LDS patterns (CANNBot PRC-MEM-009 style for our packs) | Need SoftLib-specific probe; do not copy CANNBot A5 % blindly |
| PRC-IPC-002 | Body4 firstLDS→lastSTS vs defining-opcode stage mid when they disagree | Noted MISSING in G32 ANALYSIS; no closed rule |
| PRC-SCH-004 | When VL `VDIV(X/absmax)` should replace recip+VMUL as SIMD SoT | t779u shows B≻A on G32 Case-3; SoT promotion policy not harness-frozen (PRC-SCH-003 now = pack-UB vs VSEL paint · t591u) |
| PRC-MEM-004 | G16 scratch expand VSTI↔VLDI address pattern | Described in G16 ANALYSIS; not yet its own PRC with snippets |

Update this list when a dig lands numbers; then promote `needs-measure` → `ready`.

---

**Index discipline (t784u):** Rows here are **not** checkpoints. Promote only after measure → write card (six sections + front matter) → **register in `perf-review-checklist.md`** → pass `scripts/check_prc_index.py`. Do not create empty category dirs for gaps.
