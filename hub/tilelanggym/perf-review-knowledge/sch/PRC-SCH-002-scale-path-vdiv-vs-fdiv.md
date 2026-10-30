---
id: PRC-SCH-002
name: Scale path — size-1 VDIV+paint+VMUL vs VL VDIV(X/absmax) vs SoftLib FDIV_I+FMUL
category: SCH
applies_to: SV8/SB8 Case-3 G32 · era=case3-quant-bcast · KEEP-X · SoftLib SIMT dual_drain vs SIMD VL-res; A5 camodel Ascend950PR_9599
status: ready
---

# PRC-SCH-002：Scale 路徑 VDIV / recip+VMUL / SoftLib FDIV_I

## 知识点

Case-3 e2e scale = produce per-group `sf` then `Out = X * sf` (equiv. `X / absmax` with eps). **Three measured forms** on G32 R64×C128 E=8192 KEEP-X:

| Form | What issues | Who uses it | G32 el/cyc (PASS) |
|------|-------------|-------------|------------------:|
| **A. recip+VMUL** | size-1 `VDIV(1,absmax)×NG` + VSEL/VDUP paint inv + **VMUL(x,inv)** | SIMD VL-res **SoT** (t737u / t779u) | **4.1711** (VF **1964**) |
| **B. VL VDIV(X/absmax)** | paint absmax + **one VL `VDIV(x,absmax)` / trip** · no VMUL | SIMD contrast `vdiv_x` (t779u) | **4.9799** (VF **1645**) |
| **C. SoftLib FDIV_I + FMUL** | sparse **`FDIV_I:256`** (group-scale / recip) + **`FMUL:256`** | SoftLib dual_drain T512 | **6.7702** (VF **1210**) |

SoftLib **already** uses form C — the “drop VDIV, do 1/absmax + VMUL” what-if **does not change SoftLib**; it **is** form A on SIMD.

### 实测摘要（t779u RESULT_simd_recip_vmul_g32）

| compare | SoftLib÷SIMD | note |
|---------|-------------:|------|
| SoftLib ÷ recip_vmul (A) | **1.623×** | = VL-res SoT |
| SoftLib ÷ vdiv_x (B) | **1.360×** | gap closes; still SoftLib |
| vdiv_x ÷ recip_vmul | **1.194×** | VL-VDIV wins **inside** SIMD |

S_scale FOCUS (instr_exe aggregates):

| opcode | recip_vmul calls / cyc | vdiv_x calls / cyc |
|--------|------------------------:|-------------------:|
| RV_VDIV | **256 / 4352** | **128 / 2176** |
| RV_VMUL | 128 / 1024 | **0 / 0** |
| RV_VSEL | 1024 / 6144 | 1024 / 6144 |
| RV_VCMAX | 256 / 4096 | 256 / 4096 |

VSEL paint cost **identical** on A vs B — gap is size-1 VDIV×NG + VMUL vs one VL VDIV.

SoftLib S_scale (SB8 G32 harvest): `SIMT_FDIV_I:256` — **not** per-element VDIV.

## 错误写法

```text
// 反例：以為 SoftLib dual_drain「冇 DIV」，所以改 SIMD recip 就會同 SoftLib 一樣
// — SoftLib 有 FDIV_I:256；贏主要係 issue density (PR9 mid ~3.4 vs ~1.35) + 平價 S_scale。
```

```text
// 反例：宣稱「SIMD 改 1/absmax+VMUL 會翻盤 SoftLib」
// — form A 量到 4.1711，SoftLib 仍 1.62×；form B 最快 SIMD 仍 1.36× SoftLib lead。
```

## 正确写法

- SoftLib: keep **FDIV_I + FMUL** (dual_drain); do not “port” size-1 VDIV into SoftLib expecting a new KPI.
- SIMD explore: treat **A vs B** as schedule variants; quote t779u table; still require **PRC-IPC-001** overlays when publishing SoftLib≻SIMD.
- When attributing SoftLib win: cite **S_scale Δcyc** (SIMD VSEL/VDIV tax vs SoftLib FDIV_I) **and** PR9 mid-IPC density — not “SIMD forgot recip”.

## 识别方法

1. instr_exe: count `RV_VDIV` vs `SIMT_FDIV_I` vs `RV_VMUL` / `SIMT_FMUL`.
2. Size-1 recip signature: `RV_VDIV` call count ≈ **NG × trips** (G32: 256) + VMUL present.
3. VL `vdiv_x` signature: `RV_VDIV` ≈ trips (128) · VMUL=0.
4. SoftLib: `FDIV_I` in S_scale · no `RV_VDIV` in SoftLib ASC path.

误报边界：勿把 G16 size-1 SIMD (0.06 el/cyc) 當 G32 VL-res SoT；勿無 `era=case3-quant-bcast` 就合併 absmax-only；VSEL 同量唔等於 scale 路徑相同（仲要睇 VDIV 形態）。

## 证据要求

- Cite `/workspace/sv8_g32_sb8_t772u/RESULT_simd_recip_vmul_g32.md` numbers or remeasure same shape.
- SoftLib reference row: dual_drain T512 KEEP-X **6.7702** / VF **1210**.
- SoftLib≻SIMD publish → also **PRC-IPC-001**.

## 参考

- `/workspace/sv8_g32_sb8_t772u/RESULT_simd_recip_vmul_g32.md` (t779u)
- `/workspace/sv8_g32_sb8_t772u/ANALYSIS_SB8_SEGMENT_IPC_G32.md` (S_scale row)
- Sibling: **PRC-IPC-001**, **PRC-MEM-001** (KEEP-X)
