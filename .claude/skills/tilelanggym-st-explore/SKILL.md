---
name: tilelanggym-st-explore
description: >
  Use when the user gives SoftLib/ST (or sibling) problem definition / Aims /
  output expectation and wants the full exploration loop through a detailed
  ANALYSIS report — from semantic lock through case design, frontend pick,
  measure, theory match (~70–80%), close, and st-report; mandatory
  EXPLORATION_TRACE.md before MB DONE; SoftLib motif-seed ladder + coverage
  COMPARE (tag names) even when KPI COMPARE is N/A; FORCED PR9
  opcode_lanes_ipc overlays for both arms before MB/ANALYSIS DONE when
  claiming SoftLib≻SIMD or SIMD≻SoftLib (reject IPC-only PNGs).
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. Pack gate needs TILELANGGYM_PACK; full opencode hours are out of band.
---

# tilelangGym ST explore (skill-foundry)

**Role:** SoftLib/ST improve-loop conductor for the **tilelangGym** target.
Harness L0–L9 = knowledge; this skill owns order, Motif ladder, Done-bar, TRACE.

**Composes:** `tilelanggym-semantics-gate` · `tilelanggym-softlib-simt` ·
`tilelanggym-vmi-gmap` · `tilelanggym-st-report`

Machine-readable suites: `config/suites.json` → target `tilelangGym`.
Gate (no multi-hour opencode):

```bash
export TILELANGGYM_PACK=demo/fixtures/tilelanggym-pack-ok   # or a real pack
python3 -m skill_foundry.workflow.run --target tilelangGym --suite sv567-1xg-clean
python3 -m skill_foundry.workflow.run --target tilelangGym --suite sv567-nx1-outer
# or direct:
python3 -m skill_foundry.lib.tilelanggym_gate --suite sv567-1xg-clean --pack "$TILELANGGYM_PACK"
```

## Done-bar (no DONE without)

1. `EXPLORATION_TRACE.md` with required sections (Meta, Aims lock, Motif seed,
   Decision log, Tried/skipped, Best-sweep, SEMANTICS_GATE, Coverage COMPARE,
   What-if next).
2. SoftLib Motif ladder Coverage COMPARE (tag names; KPI COMPARE may be N/A).
3. When SoftLib≻SIMD / SIMD≻SoftLib / both-arm compare: PR9
   `*_running_ipc_pr9.png` (**both** arms; reject IPC-only).
4. PRC cites in ANALYSIS (`PRC-IPC-001` / `PRC-SCH-001` …); orphan gate via
   `scripts/check_prc_index.py`.
5. RESULT.tsv carries `era=` / `reduce_axis=` / motif tags.

## Motif seed (names only — never paste dig el/cyc)

Canonical: `hub/tilelanggym/MOTIF_SEED_SV567_absmax.md`.

- SoftLib 1×G: stock / wg / wc LDS · **loadall+absall (all G)** ·
  **dual_drain G16/32/64/128** · wc-multi · T∈{128,256,512}. SoT cell **axis=1xG only**.
- VMI inner: VC/VCG by reduce_axis; VMI outer Nx1: **pure VMAX**, dual-era +
  VAND alternate-builder.
- Appendix: `wr_*` / axis=Nx1 SoftLib never merges into SoftLib SIMT SoT.

## Loop (fixed order)

```
PROMPT_BIND → S1 semantic → S2 case seed → S3 HW compares → S4 frontend
  → S5 measure → S6 theory match → S7 close (~70–80%) → S8 st-report
```

## PRC

Index SoT: `hub/tilelanggym/perf-review-knowledge/perf-review-checklist.md`.
Only `status=ready` indexed cards count. Gate: `scripts/check_prc_index.py`.

## References

- `references/done-bar.md` — Done-bar checklist
- `hub/tilelanggym/MOTIF_SEED_SV567_absmax.md` — Motif ladder
