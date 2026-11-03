---
id: PRC-SCH-007
name: Column scale — one scale per column, inverse in the lane
category: SCH
applies_to: SV2.A column scale · one scale per column · float32 · no cross-thread redux · A5 camodel Ascend950
status: ready
---

# PRC-SCH-007：Column scale

## 知识点

One scale per column. eps is 1e-6. Storage is float32. The column stays in its lane. `REDUX` and `BAR` are 0 on every measured row.

```text
scale[col] = max(eps, max over rows |X[row, col]|)
Out[row, col] = X[row, col] * (1 / scale[col])
```

Pass 2 multiplies the values already held. There is no reducer and no broadcast. Inserting a tile-wide reducer produces the block scale (PRC-SCH-006), which is a different result.

VF is `VF` or `VF_SIMT` completion minus issue, veccore0 (`core == 0`, `sub == 1`). el/cyc is N/VF. The procedure is `skill:tilelanggym-column-scale`. PRC-SCH-002 is the Case-3 per-group divide path.

### 实测摘要

Keep, threads = 128. Source: `work/ST-Analysis/SV2/ANALYSIS.md` §5.2.1.

| Rows | N | Method | LDK | MRF | VF | el/cyc |
|---:|---:|---|---:|---|---:|---:|
| 32 | 4096 | unroll | 0 | 20.5KB / 16% | 1053 | 3.89 |
| 64 | 8192 | unroll | 0 | 37.0KB / 29% | 2153 | 3.80 |
| 128 | 16384 | unroll | 36 | 63.5KB / 50% | 4350 | 3.77 |
| 256 | 32768 | GM | 832 | 63.5KB / 50% | 144635 | 0.23 |

Thread sweep. Same N, so rows × threads stays fixed. `REDUX` and `BAR` are 0. `LDK` is 0 except 36 at 128 threads and 128 rows. Bold is the lowest VF inside that N. Source: `work/ST-Analysis/SV2/ANALYSIS.md` §5.2.2.

| N | Threads | Rows | VF | el/cyc | IPC |
|---:|---:|---:|---:|---:|---:|
| 4096 | 128 | 32 | 1053 | 3.89 | 0.76 |
| 4096 | 256 | 16 | **479** | 8.55 | 1.72 |
| 4096 | 512 | 8 | 591 | 6.93 | 1.49 |
| 4096 | 1024 | 4 | 626 | 6.54 | 1.58 |
| 8192 | 128 | 64 | 2153 | 3.80 | 0.73 |
| 8192 | 256 | 32 | 1426 | 5.74 | 1.12 |
| 8192 | 512 | 16 | **910** | 9.00 | 1.81 |
| 8192 | 1024 | 8 | 980 | 8.36 | 1.80 |
| 16384 | 128 | 128 | 4350 | 3.77 | 0.73 |
| 16384 | 256 | 64 | 2352 | 6.97 | 1.33 |
| 16384 | 512 | 32 | **1665** | 9.84 | 1.91 |
| 16384 | 1024 | 16 | 1690 | 9.69 | 1.95 |

SIMD, VL = 64. One `VDIV` per 64 columns. For R>1 the steady counts are `VMUL = VMAX = 2×N/64` and `VST = N/64`. `C` must be a multiple of 64, so 512×32 is outside this body.

| N | Shape | VF | el/cyc | IPC |
|---:|---|---:|---:|---:|
| 64 | 1×64 | 77 | 0.83 | 0.16 |
| 512 | 8×64 | 103 | 4.97 | 0.62 |
| 4096 | 32×128 | 279 | 14.68 | 1.65 |

N=16384. Bold is the lowest VF.

| Shape | VF | el/cyc | IPC |
|---|---:|---:|---:|
| 256×64 | **849** | 19.30 | 2.12 |
| 64×256 | 1064 | 15.40 | 1.70 |
| 32×512 | 1255 | 13.05 | 1.45 |
| 16×1024 | 902 | 18.16 | 2.08 |

Head-to-head at N=16384: SIMD 256×64 is VF **849**, el/cyc 19.30, IPC 2.12. SIMT 512 threads, 32 rows is VF 1665, el/cyc 9.84, IPC 1.91. SIMD is 1.96× that SIMT row on el/cyc.

Stage flush uses the other SIMT row: N=16384, 1024 threads, 16 rows, VF 1690, el/cyc 9.69. An empty compiler fence is deleted. Fused is VF **1690**. Split is a different binary, VF 1725. Flushing the 16 loads is VF 7694. Flushing the 16 products is VF 6403. Flushing the max is VF 1991. Flushing the inverse is VF 1971.

The full kernel at 9.69 el/cyc sits next to the copy (10.95) and the multiply (10.56). There is no redux kernel between them. The inverse kernel issues 32 `FDIV` (one per warp) and those inverses run at 2.43 el/cyc inside a whole-kernel 26.05.

## 错误写法

```text
reducer_update(column max)
scale = max(eps, finalize(reducer))
Out[row, col] = held[row] / scale
```

That reducer is the block scale. The column scale never leaves the lane.

```text
threads = N
redux warp partials past warp 31
```

That probe belongs to the flat block-scale reduce (PRC-SCH-006). This kernel has no cross-thread fold.

## 正确写法

```text
thread col owns column col
held[row] = X[row, col]
m = max over those rows of abs(held[row])
inv = 1 / max(m, eps)
Out[row, col] = held[row] * inv
```

`C` is a multiple of 32. No `alloc_reducer`. Pass 2 multiplies the local. A tile whose rows spill is split by rows. The 256-row GM launch is the measured spill (VF 144635, el/cyc 0.23, LDK 832).

On SIMD, `C` is a multiple of 64. Sixty-four columns are one `VDIV`. A wider tile repeats that walk.

Compiled bodies: `work/ST-Analysis/SV2.A/simt.py`, `work/ST-Analysis/SV2.A/keep.py`, `work/ST-Analysis/SV2.A/simd.py`.

## 识别方法

1. The formula is one scale per column, and the store is a multiply by `1 / scale[col]`.
2. The dump has `REDUX` 0 and `BAR` 0.
3. Issued `FDIV` counts one inverse per warp, not one divide per element.
4. SIMD `C` is a multiple of 64. A change of shape at fixed N changes the VF. On the block scale, the measured shapes at N=16384 share one VF. That is the only N where the note records it.

误报边界：do not rank a block-scale row against this table. Do not quote the fence VF 1690 as the head-to-head SIMT row. The head-to-head SIMT row is 512 threads, VF 1665. Do not treat an empty compiler fence as a measured cut. Fused and split are different binaries on this formula.

## 证据要求

- Cite `work/ST-Analysis/SV2/ANALYSIS.md` §5.2, §7.2, §9.2.
- A claim names rows, threads, and whether the locals spilled (`LDK`).
- A SIMD claim names the shape. At N=16384 the shape is part of the result.
- A SIMD≻SIMT or SIMT≻SIMD sentence also cites PRC-IPC-001.

## 参考

- `work/ST-Analysis/SV2/ANALYSIS.md` sections 1.2, 3.2, 4.2, 5.2, 7.2, 8.2, 9.2
- `work/ST-Analysis/SV2.A/simt.py`
- `work/ST-Analysis/SV2.A/keep.py`
- `work/ST-Analysis/SV2.A/simd.py`
- Skill: `tilelanggym-column-scale`
- Sibling: PRC-SCH-006 (block scale). PRC-SCH-002 is the Case-3 per-group divide path.
