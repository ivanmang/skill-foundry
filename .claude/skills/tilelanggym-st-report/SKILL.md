---
name: tilelanggym-st-report
description: >
  Use when writing or rewriting a tilelangGym ST ANALYSIS report
  (SV*/CF*/SP*/SB*) to the standard spine from Aims + design only — no dig
  numbers, no agent memory; after RESULT fill COMPARE harvest (or N/A) plus
  motif-seed Coverage COMPARE; FORCED PR9 running-IPC + opcode-lane mix
  overlay (plot_style=opcode_lanes_ipc) — reject IPC-only *_running_ipc.png;
  require EXPLORATION_TRACE.md link when explore-from-prompt / clean regress;
  when SIMT-over-SIMD (or reverse) or both-arm perf compare closes, require
  PR9 overlays + per-segment opcode mix + stage mid-IPC for BOTH arms;
  §8.1/§8.2/*_pr9_staged.png share harness STAGE_TAXONOMY defining-opcode map
  (ISA-mix stays ops/N orthogonal).
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. PR9 helper scripts/make_pr9_running_ipc_overlay.py.
category: perf-analysis
origin: native
maturity: ready
owner: skill-foundry
---

# tilelangGym ST report

**Contract only.** No dig el/cyc. Inputs: ST id, Aims (`A1…`), optional design.

## Spine

1. Aims · 2. Test-case design · 3. Layout/schedule · 4. SIMD PTO-DSL ·
5. SIMT Ascend · 6. SoftLib SIMT · 7. **PR9 overlays** · 8. Opcode mix / stage mid-IPC ·
9. Conclusion · 10. TRACE pointer

## Enforce

- Reject IPC-only `*_running_ipc.png` — require `*_running_ipc_pr9.png`
  (`plot_style=opcode_lanes_ipc`). Helper: `scripts/make_pr9_running_ipc_overlay.py`.
- SoftLib≻SIMD / both-arm compare → PR9 **both** arms + stage mid-IPC table.
- Cite ready PRC-ids (`PRC-IPC-001` …); KPI COMPARE may be N/A on clean; Coverage COMPARE required.
- SoftLib SoT = axis=1xG; Nx1 SoftLib = appendix.

## Stage taxonomy (shared · t589u)

Seg ids `S_load` · `S_reduce` · `S_scale` · `S_eltwise` · `S_store` (+ optional `S_sync`) must use the **same defining-opcode map** for §8.1 per-segment mix, §8.2 stage mid-IPC, and `*_pr9_staged.png`. Prefer harness export when present:

- Module: `scripts.st_report.stage_taxonomy.STAGE_TAXONOMY`
- JSON: `benches/<st>/plots/stage_taxonomy.json` (or repo `scripts/st_report/stage_taxonomy.json`)

Do **not** invent a second stage split. Window = first..last issue of defining opcodes (overlap OK).

| frontend | S_load | S_reduce | S_scale | S_eltwise | S_store |
|----------|--------|----------|---------|-----------|---------|
| SoftLib | LDS | REDUX+FADD+SEL+FSETP_I | FDIV_I | FMUL | STS |
| SIMD | VLDI | VCMAX+VMAX+VAND | VSEL+VDIV+VDUP | VMUL | VSTI |

ISA-mix (§9 / ops/N families) stays **orthogonal** — optionally label families with the same `S_*` names; do not fold ops/N into tick-window mid-IPC.

## Gate

```bash
python3 -m skill_foundry.lib.tilelanggym_gate --suite sv567-1xg-clean --pack "$TILELANGGYM_PACK"
```
