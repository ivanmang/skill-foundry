# MOTIF_SEED — SoftLib/ST SV5–7 absmax clean regress (t788u_r2)

**Rule:** tag / recipe **names only**. Do **not** paste dig or prior el/cyc into the runner.  
**Coverage COMPARE** in `EXPLORATION_TRACE.md` must mark each seed ✓ measured / ✗ absent / stop\<reason\>.  
**Source classes:** audit M1–M5 (`ref/AUDIT_MISS_LIST_t759u.md`) + tip softlib-simt-schedule / vmi-gmap-close.

---

## SoftLib SIMT — axis=1xG (forced SoT ladder; Harness §20)

| Seed tag (name) | G focus | Class (audit) | Notes |
|-----------------|--------:|---------------|-------|
| `softlib_simt_stock_stream` | 16/32/64/128 | baseline | Not SoT alone |
| `softlib_simt_wg_lds_matrix` | mid-G | §20 matrix | within-group contig; LDS.32/64 · membar · misched |
| `softlib_simt_wc_lds_matrix` | all | §20 matrix | warp-coop; **necessary, not sufficient** |
| `softlib_simt_loadall_absall` | **all** (16/32/64/128) | **M1** | load-all + abs-all then redux |
| `softlib_simt_dual_drain` | **16, 32, 64, 128** | **M1/M2** | dual-drain / high back-pressure — **required all G** (t760u: G64/128 dual_drain beat wc-multi) |
| `softlib_simt_wc_multi` | **64, 128** | **M1/M2** | warp-coop multi — necessary **not** sufficient alone |
| `softlib_simt_T128` | winning motif | **M1** | T ladder rung |
| `softlib_simt_T256` | winning motif | **M1** | T ladder rung |
| `softlib_simt_T512` | winning motif | **M1** | T ladder rung (G128: legal high-T ≤64 — still try legal set) |

**Forbidden early SoftLib SIMT DONE:**
- freeze to prior **t676-class** `.so` universe (LDS/membar/misched T128/T64 only) without the ladder above;
- mark SoftLib DONE at **G64/G128 on wc-multi alone** while `softlib_simt_dual_drain` / loadall+absall dual-drain is untried and buildable (t760u / t788u).

**SoftLib SIMT SoT cell = `axis=1xG` only.** Never promote `wr_*` / `axis=Nx1` into SoftLib SIMT SoT even if el/cyc is higher.

**Appendix (not main 1×G SoT):** `softlib_simt_axis_Nx1_wr_*` — label `axis=Nx1`; never merge into main SoftLib SIMT SoT.

---

## VMI inner — reduce_axis=inner (1×G)

| Seed tag (name) | G focus | Class | Notes |
|-----------------|--------:|-------|-------|
| `vmi_inner_vcgmax_small` | 16 | recipes | VCGMAX-oriented |
| `vmi_inner_vl256_ng8_vcgmax` | **32** (also try 16) | **M5** | VL=256 + group=8 |
| `vmi_inner_vcmax_half_or_whole` | mid | recipes | Opcode from **lowering** |
| `vmi_inner_vand_i32_bitcast` | 16/32 | **M4** | abs path i32-VAND |
| `vmi_inner_vabs_fp` | peer | era | Label `era=` / abs-path |
| `vmi_inner_vmax_to_vcg` | 64/128 | recipes | Large-G fold→VC(G) |
| `vmi_inner_shape_2d` | peers | §19 | R×C |
| `vmi_inner_shape_1d_group` | peers | §19 | 1D+group / retile |

---

## VMI outer — reduce_axis=outer (N×1 / column)

| Seed tag (name) | Class | Notes |
|-----------------|-------|-------|
| `vmi_outer_vmax_fold` | required | Elementwise VMAX only — no VC/VCG as reduce |
| `vmi_outer_era_absmax_only` | **M3** | Dual-era track A |
| `vmi_outer_era_case3_recip` | **M3** | Dual-era track B — non-comparable without `era=` |
| `vmi_outer_vand_i32` | **M3** | Prefer when stack allows (t720-class) |
| `vmi_outer_vand_alternate_builder` | **M3** | **Required attempt** if VAND no-path on first builder |
| `vmi_outer_vabs_fp` | peer | Only after alternate-builder attempt if claiming VAND no-path DONE |
| `vmi_outer_ilp_unroll_dual_split` | schedule | Unroll / dual-chain / split-stage |

**Forbidden:** mark outer DONE solely on Case-3+VABS and treat as absmax-only SoT.

---

## SoftLib CCE SIMD (optional when VMI best; A2)

| Seed tag (name) | Notes |
|-----------------|-------|
| `softlib_cce_whatif_or_skip` | Measure **or** explicit `skipped — VMI sufficient` / what-if MB |
| `softlib_cce_era_label` | Absmax-only vs Case-3 recip — do not merge eras |

---

## SIMT-ASC stock (A6)

| Seed tag (name) | Notes |
|-----------------|-------|
| `simt_asc_stock_per_ST` | Honest measured **or** TODO + MICROBENCH row per ST |

---

## Coverage gate

SoftLib SIMT / VMI best-sweep / MB_* **DONE forbidden** until:

1. This Motif seed is copied into `EXPLORATION_TRACE.md` § Motif seed.
2. Coverage COMPARE fills every SoftLib ladder rung + outer dual-era / VAND alternate-builder.
3. `EXPLORATION_TRACE.md` exists (DB thinking alone ≠ TRACE).
