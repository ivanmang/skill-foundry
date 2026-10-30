---
id: PRC-SCH-001
name: Compiler asm memory clobber vs HW SMEM_BAR
category: SCH
applies_to: SoftLib SIMT (SV1 fence1 · Case-3 dual_drain G32) vs SIMD VMI VL-res; A5 camodel/opsim; naming trap SoftLib "membar" tag
status: ready
---

# PRC-SCH-001：Compiler `asm volatile("" ::: "memory")` vs HW `SMEM_BAR`

## 知识点

Two **different** barriers often both nicknamed “membar” in SoftLib digs:

| Mechanism | Token | Effect | Seen in SB8/SV8 digs? |
|-----------|-------|--------|------------------------|
| **Compiler memory clobber** | `asm volatile("" ::: "memory");` | Stops MI/-O2 from **cross-scheduling** loads across stage walls (LD↔ABS↔REDUX/recip↔mul). **No** HW sync instr. | SoftLib yes · SIMD VL-res no |
| **HW sync** | `RV_SMEM_BAR` / `SIMT_BAR` / SET·WAIT_FLAG | Pipeline mem barrier; shows in `S_sync` / instr_exe | G16 size-1 SIMD yes · G32 SoftLib/VL-res `S_sync=0%` |

Prior SB8 harvest `S_sync=0%` means **no HW bar** in that pair — it does **not** mean SoftLib lacks compiler walls.

### 实测摘要（t778u · REPORT_ASM_MEMORY_CLOBBER）

| arm | `# asm volatile("" ::: "memory")` | HW SMEM_BAR in VF |
|-----|----------------------------------:|------------------:|
| **SV1 SoftLib fence1** | **1×** (post-loadall, pre-FADD) | no (fence1 = compiler only) |
| **SoftLib G32 Case-3 dual_drain T512** (el/cyc **6.7702**, VF **1210**) | **3×** (walls: LD · ABS · REDUX/recip→KEEP-X mul) | `S_sync` **0%** |
| SoftLib stock `lds32_redux` G32 T512 | **0** | — |
| SoftLib `loadall_membar` / `loadall_absall_membar` | 1 / 2 | — |
| **SIMD VL-res G32** (el/cyc **4.1711**, VF **1964**) | **0** (pure PTO-DSL) | `S_sync` **0%** |

## 错误写法

```c
// 反例：把 SoftLib dual_drain 的 "membar" 理解成 RV_SMEM_BAR，
// 然後用 S_sync=0% 斷言「SoftLib 冇 barrier」——漏咗 compiler clobber。
if (S_sync_pct == 0) claim("no barriers on SoftLib");  // WRONG
```

```c
// 反例：SIMD VL-res 假設「同 SoftLib 一樣有 3 道 memory clobber」
// — VMI 排程已係 explicit；源碼 grep asm/volatile/memory → 0。
```

## 正确写法

```c
// 正例（SoftLib dual_drain ASC · 3 walls）— 機制同 SV1 fence1
// after loadall a[0..15]
asm volatile("" ::: "memory");  // wall LD
// ... abs into av[] ...
asm volatile("" ::: "memory");  // wall ABS
// ... dual_drain redux + recip into s[] ...
asm volatile("" ::: "memory");  // wall REDUX/recip → KEEP-X mul
C0[0*512 + tid] = a[0] * s[0];
```

```c
// 正例（SV1 SoftLib fence1）
b[31] = B0[31*256 + tid];
asm volatile("" ::: "memory");
c[0] = a[0] + b[0];
```

Naming in RESULT/ANALYSIS: write **「compiler memory clobber」** or **`asm volatile ::: memory`**; reserve **membar / SMEM_BAR** for HW (`PRC-MEM-002`).

## 识别方法

1. Grep ASC / generated C for `asm volatile` / `::: "memory"` — count walls; map to stage comments (`// STAGE LD` / ABS / …).
2. Grep instr_exe / dump for `RV_SMEM_BAR` / `SIMT_BAR` — that is **HW** (`S_sync`), separate card.
3. SoftLib pack tags containing `membar` still usually emit the **compiler** token (see REPORT table: `*_membar_g32*` counts 1–2 `asm volatile`).
4. SIMD PTO-DSL: grep kernel `.py` for `asm|volatile|__asm__|clobber` — VL-res = none.

误报边界：`S_sync=0%` ≠ 「無任何 barrier」；勿把 SET/WAIT_FLAG 少許 cycle tax 當 SMEM_BAR 主因；勿把 SoftLib 贏歸因成「有 SMEM_BAR」（G32 SoftLib 冇 HW bar）。

## 证据要求

- ASC path + line excerpts for each wall (or grep count table by tag).
- Pair with `S_sync` % from segment harvest when claiming HW vs compiler.
- Cite `/workspace/sv8_g32_sb8_t772u/asm_clobber_check/REPORT_ASM_MEMORY_CLOBBER.md`.

## 参考

- `/workspace/sv8_g32_sb8_t772u/asm_clobber_check/REPORT_ASM_MEMORY_CLOBBER.md` (t778u)
- SoftLib best ASC tag: `wc_c3e2e_back_loadall_absall_dual_drain_g32_t512_e8192`
- SV1: `/workspace/tilelangGym-pr11/benches/sv1/data/SOFTLIB_TILE_MION_FENCE1.md`
- Sibling: **PRC-MEM-002** (HW SMEM_BAR G16 size-1 vs G32 VL-res)
- Skill workflow: `tilelanggym-softlib-simt-schedule` fence/bar axis — load this card for meaning of “membar”
