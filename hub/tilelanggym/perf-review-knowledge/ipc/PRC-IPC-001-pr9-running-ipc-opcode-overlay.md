---
id: PRC-IPC-001
name: PR9 running-IPC + opcode-lane overlay (FORCED for SoftLib≻SIMD)
category: IPC
applies_to: Any SB*/SV* ANALYSIS claiming SoftLib≻SIMD / SIMD≻SoftLib / SIMT≻SIMD / both-arm perf compare / mix-split stage mid-IPC; A5 opsim dumps
status: ready
---

# PRC-IPC-001：PR9 running-IPC + opcode-lane mix overlay（強制）

## 知识点

**PR9 figure** = dual-pane plot with `plot_style=opcode_lanes_ipc`:

- **Top:** one lane per opcode family with **issue marks** (instr mix in time).
- **Bottom:** rolling IPC W=20 on the **same** tick axis; mid-med dashed = steady body.

Filename convention: `*_running_ipc_pr9.png` (+ optional `*_pr9_staged.png` with stage bounds). Sidecar JSON must show `plot_style == "opcode_lanes_ipc"` and non-empty `lane_opcodes`.

**IPC-only** `*_running_ipc.png` (single axes, no lanes / no `_pr9`) is **rejected** under this card — not “almost PR9”.

### Stage taxonomy (shared with §8 · t589u)

Seg ids `S_load` · `S_reduce` · `S_scale` · `S_eltwise` · `S_store` (+ optional `S_sync`) for stage mid-IPC / `*_pr9_staged.png` / per-segment mix must share one defining-opcode map. Prefer harness `scripts.st_report.stage_taxonomy.STAGE_TAXONOMY` (SoftLib: LDS · REDUX+FADD+SEL+FSETP_I · FDIV_I · FMUL · STS; SIMD: VLDI · VCMAX+VMAX+VAND · VSEL+VDIV+VDUP · VMUL · VSTI). ISA-mix stays ops/N families (orthogonal). Do not invent a second stage split in ANALYSIS prose.

### 实测摘要（SB8=SV8 Case-3 G32 · t773u）

| arm | PR9 mid-med | official mid IPC | official el/cyc |
|-----|------------:|-----------------:|----------------:|
| SoftLib dual_drain T512 | **3.40** | **3.30** | **6.7702** |
| SIMD VL-res | **1.35** | **1.45** | **4.1711** |

SoftLib stages (defining-opcode windows): S_load 3.25 / S_reduce·S_scale 3.50 / S_eltwise 3.45 / S_store 3.40. SIMD fused loop: every stage mid ≈ **1.35**.

## 错误写法

```text
# 反例：只交 IPC 曲線就宣稱「有 PR9 / 睇到 mix 差異」
plots/softlib_…_running_ipc.png   # no lanes → FAIL
```

```text
# 反例：SoftLib≻SIMD 只貼 winner 臂圖
# — 兩邊臂都要 *_running_ipc_pr9.png + stage mid 表
```

## 正确写法

```bash
PYTHONPATH=/workspace/tilelangGym-pr8-tip \
  python /workspace/REGRESSION_salvage_2026-09-17/scripts/make_pr9_running_ipc_overlay.py \
    --dump …/softlib_dual_drain_g32.instr_log.dump \
    --out-png …/plots/softlib_…_running_ipc_pr9.png \
    --title "… running IPC (W=20)" --E 8192
# repeat for SIMD dump → simd_…_running_ipc_pr9.png
# verify JSON plot_style=opcode_lanes_ipc
```

ANALYSIS embeds both arms + stage mid-IPC table (or writes fused ≈ body mid explicitly).

## 识别方法

1. Trigger if **any**: SoftLib≻SIMD / reverse / both-arm el/cyc|VF ratio / mix-split stage narrative.
2. Check filename `*_pr9*` **or** JSON `plot_style`.
3. Top pane must show multiple opcode lanes with marks; bottom IPC aligned.

误报边界：dump 缺失 → **MISSING + next-cmd**（唔係默認跳過）；plot VF 可以短過 official VF — KPI 仍用 official VF row；fused SIMD 唔好發明假 sequential walls。

## 证据要求

Finding / ANALYSIS DONE / MB DONE / SoftLib SIMT DONE（when compare claimed）必须：

- Both arms `*_running_ipc_pr9.png` (or MISSING+next-cmd)
- Stage mid-IPC table when mix splits (or explicit fused note)
- Pointer to harness L6 § PR9

## 参考

- Harness: `REGRESSION_salvage_2026-09-17/L6_ANALYSIS_INVENTORY.md` § PR9
- Script: `REGRESSION_salvage_2026-09-17/scripts/make_pr9_running_ipc_overlay.py`
- Worked plots: `/workspace/sv8_g32_sb8_t772u/plots/*_running_ipc_pr9*.png`
- Skills (workflow): `tilelanggym-st-report` · `tilelanggym-st-explore-from-prompt` · `tilelanggym-softlib-simt-schedule` Done-when §7
