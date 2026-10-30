---
id: PRC-MEM-001
name: KEEP-X / VL-resident vs UB-reload for Case-3 G32
category: MEM
applies_to: SV8/SB8 Case-3 G32 SoftLib dual_drain + SIMD VL-res · era=case3-quant-bcast · R64×C128 E=8192; contrast G16 size-1 SIMD (UB reload)
status: ready
---

# PRC-MEM-001：KEEP-X / VL-resident vs UB 再載 X

## 知识点

**KEEP-X** = after first load of input X, the mul/scale epilogue reuses X from **RF (SoftLib)** or **VL registers (SIMD VL-res)** — **no second full `VLDS`/`LDS` of X (=E)** for the eltwise.

On the **G32 SoftLib≻SIMD headline pair**, **both** arms are KEEP-X:

| arm | X residency for mul | VLDS of X in body | el/cyc |
|-----|---------------------|------------------:|-------:|
| SoftLib dual_drain T512 | RF `a[]` after loadall | no second X LDS for mul | **6.7702** |
| SIMD VL-res | VL keeps X · `VLDS=0` extra | **0** extra VLDS | **4.1711** |

Therefore SoftLib’s 1.62× lead is **not** explained by “SIMD paid a second X load.” Gap drivers are schedule density (**PRC-IPC-001**) + scale path (**PRC-SCH-002**).

### Contrast — G16 size-1 SIMD (wrong SoftLib target)

G16 handwritten size-1 SIMD **does** reload X: `RV_VLDS=E` for mul + scratch expand — see G16 segment ANALYSIS. Do **not** merge that MEM tax into the G32 VL-res SoT story.

## 错误写法

```text
// 反例：G32 SoftLib≻SIMD 結論寫「SIMD 輸喺第二次 VLDS X」
// — VL-res SoT 已 VLDS=0；呢句只適用 G16 size-1 類臂。
```

## 正确写法

- Tag kernels **KEEP-X** vs **UB-reload** in RESULT rows.
- For G32 compare: state both KEEP-X explicitly; attribute win via PR9 + S_scale / IPC.
- When exploring SIMD: VL-resident / keep-X is a **first-class** axis vs size-1 scratch expand.

## 识别方法

1. instr_exe: count `RV_VLDS` / `SIMT_LDS` vs E and vs trip count; VL-res body → no second X load family matching E.
2. SoftLib ASC: mul uses `a[i] * s[i]` after loadall — no intervening reload of A from UB for that mul.
3. Kernel name / tag: `vl_resident` / `KEEP-X` / `vlres`.

误报边界：G16 size-1 嘅第二 VLDS 唔好算入 G32 VL-res；MTE2 一次搬入 UB ≠ body 內第二 VLDS。

## 证据要求

- Cite VLDS/LDS call counts from instr_exe for both arms.
- ANALYSIS_SB8_SEGMENT_IPC_G32.md headline: SoftLib KEEP-X RF · SIMD VLDS=0.
- If claiming “second X load” as gap driver → must show non-zero second-load opcodes on the **losing** arm of **that** pair.

## 参考

- `/workspace/sv8_g32_sb8_t772u/ANALYSIS_SB8_SEGMENT_IPC_G32.md`
- G16 contrast (UB reload): `/workspace/sv8_g16_e2e_t726u/ANALYSIS_SB8_SEGMENT_IPC.md`
- Sibling: **PRC-MEM-002**, **PRC-SCH-002**, **PRC-IPC-001**
