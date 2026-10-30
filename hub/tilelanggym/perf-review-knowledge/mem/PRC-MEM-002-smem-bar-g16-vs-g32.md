---
id: PRC-MEM-002
name: HW SMEM_BAR — G16 size-1 scratch vs G32 VL-res / SoftLib (no bar)
category: MEM
applies_to: SV8/SB8 Case-3 · G16 size-1 SIMD scratch expand vs G32 SoftLib dual_drain + SIMD VL-res; S_sync segment
status: ready
---

# PRC-MEM-002：HW `SMEM_BAR` — G16 size-1 scratch vs G32 無 bar

## 知识点

**HW** pipeline barrier (`RV_SMEM_BAR` / related) appears in **S_sync**. Distinct from compiler `asm volatile("" ::: "memory")` (**PRC-SCH-001**).

| pair | SIMD S_sync | SoftLib/SIMT S_sync | Role in gap |
|------|------------:|--------------------:|-------------|
| **G16** size-1 SIMD vs simt-asc | `RV_SMEM_BAR:1160` ≈ **14.6%** VF | BAR **0%** (flags only) | **Secondary** (~14.6%); primary still size-1 VMAX + VLDS=E |
| **G32** SoftLib dual_drain vs SIMD VL-res | **0%** | **0%** | **Not** a gap driver |

G16 SIMD membar comes from **scratch expand** path (VSTI/VLDI + SMEM_BAR around scale paint). G32 VL-res / SoftLib dual_drain avoid that scratch → no HW bar in VF.

## 错误写法

```text
// 反例：用 G16 嘅「SIMD 有 membar」解釋 G32 SoftLib 6.77 vs VL-res 4.17
// — G32 兩邊 S_sync 都係 0%。
```

```text
// 反例：把 SoftLib dual_drain 3× compiler clobber 叫做 SMEM_BAR
// — 見 PRC-SCH-001。
```

## 正确写法

- G16 ANALYSIS: report S_sync as secondary (cite 14.6% / RESULT H3); primary = S_reduce size-1 + second VLDS.
- G32 ANALYSIS: state S_sync N/A / 0% both arms; do not invent membar narrative.
- SoftLib schedule tags `membar` → verify token (**PRC-SCH-001**) before writing S_sync claims.

## 识别方法

1. Segment harvest: `S_sync` cyc% and opcode list (`RV_SMEM_BAR` count).
2. G16 size-1: expect SMEM_BAR with scratch VSTI/VLDI in S_scale.
3. G32 VL-res / SoftLib dual_drain: expect S_sync empty; SET/WAIT_FLAG may exist but excluded from share / not SMEM_BAR.

误报边界：SET_FLAG/WAIT_FLAG ≠ SMEM_BAR 主因；compiler clobber 唔入 S_sync%；唔好把 G16 14.6% 外推到 G32 VL-res。

## 证据要求

- instr_exe `RV_SMEM_BAR` call/cyc counts per arm.
- G16: `/workspace/sv8_g16_e2e_t726u/ANALYSIS_SB8_SEGMENT_IPC.md` S_sync row.
- G32: `/workspace/sv8_g32_sb8_t772u/ANALYSIS_SB8_SEGMENT_IPC_G32.md` S_sync **0.0%** both.

## 参考

- Sibling: **PRC-SCH-001** (compiler clobber), **PRC-MEM-001** (KEEP-X)
- SoftLib schedule fence axis: skill `tilelanggym-softlib-simt-schedule` — load this card for HW vs compiler
