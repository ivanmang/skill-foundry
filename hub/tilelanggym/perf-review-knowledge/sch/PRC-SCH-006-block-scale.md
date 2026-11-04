---
id: PRC-SCH-006
name: Block scale — one tile scale, loop versus cross
category: SCH
applies_to: SV2 block scale · one scale for the whole tile · float32 · flat reduce and 2D column-then-redux · A5 camodel Ascend950
status: ready
---

# PRC-SCH-006：Block scale

## 知识点

One scale for every element. eps is 1e-6. Storage is float32.

```text
scale = max(eps, max |X|)
Out = X / scale
```

On a 2D tile the same formula is a per-column max, then one reducer across columns, then a divide of the values already held. On a flat vector the measured schedule fixes 128 threads and strides. Setting threads equal to N is a different schedule, and at 2048 threads it returns the wrong scale.

VF is `VF` or `VF_SIMT` completion minus issue, veccore0 (`core == 0`, `sub == 1`). el/cyc is N/VF. The procedure is `skill:tilelanggym-block-scale`. This card is not the column-scale table (PRC-SCH-007) and not the Case-3 per-group path (PRC-SCH-002).

### 实测摘要

Flat reduce. Bold is the lower VF. Source: `work/ST-Analysis/SV2/reduce-options/sweep.txt`.

| N | Cross VF | Loop VF | Cross REDUX | Loop REDUX | Cross BAR | Loop BAR |
|---:|---:|---:|---:|---:|---:|---:|
| 128 | 633 | **632** | 5 | 5 | 16 | 16 |
| 256 | 701 | **576** | 9 | 5 | 32 | 16 |
| 512 | 835 | **663** | 17 | 5 | 64 | 16 |
| 1024 | 988 | **535** | 64 | 5 | 128 | 16 |
| 2048 | 1549 | **503** | 128 | 5 | 256 | 16 |

Last-element probe, `X[N-1] = 4`, rest 0. Cross at N=2048 (64 warps) returns eps. The 128-thread loop returns 4.

2D keep, threads = 128. Source: `work/ST-Analysis/SV2/ANALYSIS.md` §5.1.2.

| Rows | N | Method | LDK | MRF | VF | el/cyc |
|---:|---:|---|---:|---|---:|---:|
| 32 | 4096 | unroll | 0 | 21.5KB / 17% | 1806 | 2.27 |
| 64 | 8192 | unroll | 0 | 47.5KB / 37% | 2474 | 3.31 |
| 128 | 16384 | unroll | 88 | 63.5KB / 50% | 4963 | 3.30 |
| 256 | 32768 | GM | 996 | 63.5KB / 50% | 113398 | 0.29 |

2D thread sweep. Same N, so rows × threads stays fixed. Bold is the lowest VF inside that N. Source: `work/ST-Analysis/SV2/ANALYSIS.md` §5.1.3.

| N | Threads | Rows | VF | el/cyc | IPC | REDUX | BAR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4096 | 128 | 32 | 1806 | 2.27 | 0.49 | 5 | 16 |
| 4096 | 256 | 16 | **856** | 4.79 | 1.16 | 9 | 32 |
| 4096 | 512 | 8 | 904 | 4.53 | 1.35 | 17 | 64 |
| 4096 | 1024 | 4 | 1190 | 3.44 | 1.40 | 64 | 128 |
| 8192 | 128 | 64 | 2474 | 3.31 | 0.67 | 5 | 16 |
| 8192 | 256 | 32 | 1960 | 4.18 | 0.90 | 9 | 32 |
| 8192 | 512 | 16 | **1332** | 6.15 | 1.49 | 17 | 64 |
| 8192 | 1024 | 8 | 1402 | 5.84 | 1.73 | 64 | 128 |
| 16384 | 128 | 128 | 4963 | 3.30 | 0.68 | 5 | 16 |
| 16384 | 256 | 64 | 3042 | 5.39 | 1.09 | 9 | 32 |
| 16384 | 512 | 32 | 2513 | 6.52 | 1.40 | 17 | 64 |
| 16384 | 1024 | 16 | **2363** | 6.93 | 1.68 | 64 | 128 |

SIMD, VL = 64. At N=16384 the shapes 32×512, 64×256, 256×64, and 512×32 share VF 1119, el/cyc 14.64, IPC 1.61. Head-to-head against the 1024-thread, 16-row SIMT row: SIMD VF **1119** el/cyc 14.64; SIMT VF 2363 el/cyc 6.93. SIMD is 2.11× that SIMT row on el/cyc. IPC is 1.61 and 1.68.

Stage flush, N=16384, 1024 threads, 16 rows. An empty compiler fence is deleted. Fused and split are one binary, VF **2360**. Flushing the 16 loads is VF 8355. Flushing the 16 quotients is VF 7158. Flushing the block scale is VF 2368. The stock head-to-head kernel is VF 2363 and is a different binary from the handwritten uncut kernel.

The full kernel at 6.93 el/cyc sits below the copy (10.95) and the 16 divides (10.42) because the redux of 1024 values issues at 1.95 el/cyc between them.

## 错误写法

```text
threads = N
thread t owns x[t]
redux the warp partials
```

At 2048 threads that fold drops partials past warp 31. The probe scale is eps. The loop scale is 4.

```text
scale[col] = max over rows |X[row, col]|
Out[row, col] = X[row, col] * (1 / scale[col])
```

That is the column-scale program (PRC-SCH-007). It is a different result.

## 正确写法

```text
threads = 128
thread t reads x[t + k * 128]
redux across those four warps
scale = max(eps, that redux)
```

2D:

```text
thread col owns column col
held[row] = X[row, col]
m = max over those rows of abs(held[row])
scale = max(eps, reducer(m))
Out[row, col] = held[row] / scale
```

`C` is a multiple of 32. Pass 2 divides the local. A tile whose rows spill is split by rows. The 256-row GM launch is the measured spill (VF 113398, el/cyc 0.29, LDK 996).

Compiled bodies: `work/ST-Analysis/SV2/block-quant/simt.py`, `work/ST-Analysis/SV2/simt-rows/keep.py`, `work/ST-Analysis/SV2/reduce-options/reduce.py`.

## 识别方法

1. The formula is one scale, and the store is a divide by that scale.
2. On a flat dump, threads are 128, `REDUX` is 5, and `BAR` is 16 as N grows. Threads equal to N with `REDUX` and `BAR` growing in the warp count is the cross schedule.
3. On a 2D dump, `REDUX = W+1` up to 16 warps and `REDUX = 2W` at 32 warps, with `W = threads / 32`. `BAR = 4×W`.
4. A last-element probe (`X[N-1] = 4`, rest 0) distinguishes a fold that dropped warp 32 and above. The loop result is 4.

误报边界：do not call the 2D 1024-thread row the eps probe. That probe is the flat cross kernel at 2048 threads. Do not rank a column-scale row against this table. Do not treat an empty compiler fence as a measured cut. Fused and split are one binary on this formula only.

## 证据要求

- Cite `work/ST-Analysis/SV2/ANALYSIS.md` §5.1, §7.1, §9.1, or `work/ST-Analysis/SV2/reduce-options/sweep.txt`.
- A flat-scale claim names loop or cross, N, and the thread count.
- A 2D claim names rows, threads, and whether the locals spilled (`LDK`).
- A SIMD≻SIMT or SIMT≻SIMD sentence also cites PRC-IPC-001.

## 参考

- `work/ST-Analysis/SV2/ANALYSIS.md` sections 1.1, 3.1, 4.1, 5.1, 7.1, 8.1, 9.1
- `work/ST-Analysis/SV2/reduce-options/sweep.txt`
- `work/ST-Analysis/SV2/reduce-options/reduce.py`
- `work/ST-Analysis/SV2/block-quant/simt.py`
- `work/ST-Analysis/SV2/simt-rows/keep.py`
- Skill: `tilelanggym-block-scale`
- Sibling: PRC-SCH-007 (column scale). PRC-SCH-002 is the Case-3 per-group divide path.
