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
  PR9 overlays + per-segment opcode mix + stage mid-IPC for BOTH arms.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. PR9 helper scripts/make_pr9_running_ipc_overlay.py.
category: perf-analysis
origin: native
maturity: ready
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

## Gate

```bash
python3 -m skill_foundry.lib.tilelanggym_gate --suite sv567-1xg-clean --pack "$TILELANGGYM_PACK"
```
