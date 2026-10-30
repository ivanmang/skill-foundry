---
id: PRC-SCH-003
name: Case-3 pack-UB / keeplive_vbrc vs VSEL range-paint scale expand
category: SCH
applies_to: SV8/SB8 Case-3 G32 · era=case3-quant-bcast · SIMD VMI pack_ub / keeplive_vbrc vs VL-res VSEL paint; reduce_axis=inner; A5 camodel
status: ready
---

# PRC-SCH-003：Case-3 pack-UB／keeplive_vbrc vs VSEL paint

## 知识点

Case-3 e2e scale expand after group absmax. **VL-res recip_vmul SoT** historically paints size-1 inv across the VL with **`RV_VSEL` range-paint** (plus size-1×NG `VDIV` + `VDUP`) — S_scale tax vs SoftLib `FDIV_I`+`FMUL` (see **PRC-SCH-002** forms A/B/C).

**Pack-UB / keeplive_vbrc** Legal set cuts that size-1×NG paint:

```text
vcmax(group=NG) → compact store → packed / size-NG VDIV → vbrc(size=VL, group=NG) → VMUL
```

- `pack_ub_vl*`: batch recip over packed absmax in UB (reload X; fewer VDIV).
- `keeplive_vbrc_vl*`: KEEP-X; compact DIV size=NG then vbrc expand.

**Expand not fully paint-free until `RV_VSELR` explained** — TSV `VSEL` counts `RV_VSEL` only; pack success can still show high `RV_VSELR` in opcode mix.

### 实测摘要（t548u RESULT — cite only）

era=`case3-quant-bcast` · G32 · E=8192 · R64×C128 · reduce_axis=inner

| arm | VF | el/cyc | note |
|-----|---:|-------:|------|
| pack_ub_vl256 | 969 | **8.4541** | VDIV=4 · TSV-VSEL=0 · VCGMAX=32 · mix **RV_VSELR=128** |
| keeplive_vbrc_vl256 | 1065 | **7.6920** | VDIV=32 · TSV-VSEL=0 · VSELR=32 |
| pack_ub_vl64 | — | — | **COMPILE_CLIFF** VMI-RESIDUAL-OP |
| Prior SIMD SoT VL-res recip_vmul | 1964 | **4.1711** | VSEL=1024 · VDIV=256 · VDUP=256 |
| SoftLib dual_drain | — | **6.7702** | leave SoftLib SoT alone |

Pack / keeplive **beat** VL-res paint on measured el/cyc → **candidate SIMD SoT pending Lok yes** (do not auto-crown). SoftLib SoT unchanged.

Frontend unlock (compile): drop `from __future__ import annotations` — it stringifies `pto.ptr(...)` formals for `@pto.jit`. Attested API: GM `pto.ptr(...,"gm")` + UB `castptr` offsets (same as recip_vmul); not pypto.Tensor.

## 错误写法

```text
// 反例：Case-3 G32 默認用 vcmp+vsel range-paint 做 size-1 inv expand
// — 當 VL%G==0 有 compact NG 時，應先試 pack_ub / keeplive_vbrc
```

```text
// 反例：SIMD Case-3 DONE / SoT 只報 VL-res VSEL paint，未 cover pack_ub_vl256 + keeplive_vbrc_vl256
// （亦未記 COMPILE_CLIFF / wrong-arm）— 交付 FAIL；缺 stage×VL-util（size=VL|NG|1）同 FAIL
```

```text
// 反例：@pto.jit VMI explicit kernel 頂部 from __future__ import annotations
// — pto.ptr formals 變字串 → decorator TypeError（看起來像 GM type 錯）
```

```text
// 反例：TSV VSEL=0 就宣稱 paint-free
// — 必須同時報 RV_VSELR；pack 仍可有 VSELR=128
```

```text
// 反例：未獲 Lok yes 就 crown pack 為新 SIMD SoT；或改 SoftLib SoT
```

```text
// 反例：把「修 compile」做成改寫成 pypto.Tensor tile API
// — 本棧 attested 係 pto.ptr + castptr；future-annotations 先拿掉
```

## 正确写法

- **Must** cover tags **`pack_ub_vl256`** + **`keeplive_vbrc_vl256`** (or record COMPILE_CLIFF / wrong-arm) before closing on VL-res VSEL paint when Case-3 / quant-bcast / compact NG (`VL%G==0`) available; fill stage×VL-util (harness §2b).
- **NG=8 preference (t593u):** for any gold G, first VL×G guess = **VL=8×G** (NG=8) when Legal — enables VCG*/`vcmax(group=NG=8)`. Ex: G32→VL256 · G16→VL128 · G8→VL64 (may cliff). Prefer **VL=256 NG=8** (G32) over **VL=64 NG=2**. **G8×VL=256** = optional extra sens candidate only.
- **VL × gold-G candidates (harness §2 · t591u — status only, no invent KPI):** G32×VL256 NG=8 measured Legal; G32×VL64 NG=2 COMPILE_CLIFF; G32×VL128 NG=4 **UNMEASURED**; **G8×VL256 NG=32 Legal candidate** (gold-G sensitivity). Skills Top-3: `pack_ub_vl256` → `keeplive_vbrc_vl256` → next harness candidate.
- Legal expand: `vbrc(group=NG)` / VDUP / e2b — forbid vcmp+vsel range paint as default when compact NG available.
- Formals: live `pto.ptr(...,"gm")`; UB = `castptr` byte offsets; **no** `from __future__ import annotations` on these kernels.
- Measure both pack and keeplive; report **RV_VSEL and RV_VSELR**; VDIV; VCGMAX vs VCMAX from dump.
- SoftLib≻SIMD ratio update → still **PRC-IPC-001** PR9 both arms + ISA-mix bridge.

## 识别方法

### stage×VL-util (harness §2b)

When attributing pack/keeplive vs paint, also name **working size** per stage (from dump, not wish):

| Stage | Paint anti-pattern | Legal pack_ub | Legal keeplive_vbrc |
|-------|--------------------|---------------|---------------------|
| S_reduce | size-1 × NG / trip | VL → NG compact (`vcmax(group=NG)`) | VL → NG compact |
| S_scale recip | size-1 × NG | **VL** batched VDIV (N_SCALE==VL) | **NG**-wide VDIV / trip |
| S_scale expand | full-VL **RV_VSEL** paint | `vbrc(size=VL, group=NG)` — forbid vsel | same vbrc |
| S_eltwise | full VL VMUL | full VL; X reloaded | full VL; KEEP-X |

Geometry: `NG=VL//G` (`VL%G==0`); `N_SCALE=N_TRIPS*NG`. Full map: harness `HARNESS_CASE3_PACK_UB_SCALE_t548u.md` §2b.

1. `instr_exe.csv` / opcode_focus: `RV_VDIV`, `RV_VSEL`, `RV_VSELR`, `RV_VCGMAX`/`RV_VCMAX`, `RV_VDUP`/`RV_VDUPS`.
2. Pack signature: VDIV ≪ 256 (G32 VL-res recip class); TSV-VSEL≈0; may still have VSELR.
3. Keeplive signature: VDIV ≈ N_TRIPS (G32 E=8192 VL256 → 32); KEEP-X; TSV-VSEL≈0.
4. Paint SoT signature: VSEL≈1024 · VDIV≈256 · VDUP≈256 (same shape).
5. SUMMARY / RESULT el/cyc + gold maxabs; SEMANTICS_GATE before compare.
6. Compile fail with stringified ptr / TypeError on decorate → check future-annotations.

误报边界：勿把 pack COMPILE_CLIFF 當 KPI；勿無 `era=case3-quant-bcast` 合併 absmax-only；勿用 VSEL=0 掩蓋 VSELR；勿把 SoftLib FDIV_I 路徑當 SIMD pack。

## 证据要求

- Cite `/workspace/sv8_simd_pack_scale_t548u/RESULT.md` numbers or remeasure same shape.
- Peanut SUMMARY: `/mnt/fluxdata/happybot/sv8_simd_pack_scale_t548u/out/dsl_pack_scale_t548u/SUMMARY_pack_scale_t548u.tsv`
- Kernel: `/workspace/sv8_simd_pack_scale_t548u/kernels/sv8d_pack_ub_scale_case3.py`
- SoftLib≻SIMD publish → also **PRC-IPC-001**.
- Crown / SoT replace → explicit Lok yes (not implied by this card).

## 参考

- Harness: `/workspace/REGRESSION_salvage_2026-09-17/HARNESS_CASE3_PACK_UB_SCALE_t548u.md`
- Sibling: **PRC-SCH-002** (scale VDIV/paint/VMUL vs SoftLib FDIV_I)
- Sibling: **PRC-MEM-001** (KEEP-X / VL-resident)
- SoftLib≻SIMD: **PRC-IPC-001**
- Prior paint SoT RESULT: `/workspace/sv8_g32_sb8_t772u/RESULT_simd_recip_vmul_g32.md`
