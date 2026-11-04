---
id: PRC-SIMT-001
name: Dual-drain compiler-fence count versus el/cyc
category: SIMT
applies_to: SoftLib SIMT Case-3 G32 · era=case3-quant-bcast · R64×C128 E=8192 T=512 · axis=1xG · A5 camodel
status: ready
---

# PRC-SIMT-001：Dual-drain fence count versus the window

## 知识点

The published dual-drain kernel places three compiler memory clobbers in one body: after the loads, after the absolute values, and after the reciprocal. Those are `asm volatile("" ::: "memory")`. They are not `RV_SMEM_BAR`.

On one controlled matrix the fence count is the only change. The loads, the absolute values, the paired warp max, and the multiply stay the same. Zero fences is the long window. One fence, after the loads, matches two fences and three fences.

### 实测摘要

Shape: R64×C128, E=8192, T=512, G=32, float32, `era=case3-quant-bcast`. Pass, max abs error 1.192e-07.

| Fences | Where | VF | el/cyc |
|---:|---|---:|---:|
| 0 | none | 1322 | 6.20 |
| 1 | after the loads | 1203 | 6.81 |
| 2 | after the loads and the absolute values | 1198 | 6.84 |
| 3 | published walls, plus after the reciprocal | 1203 | 6.81 |

The published three-fence dig on this shape is VF 1210, el/cyc 6.7702. This matrix is the paired remeasure. It does not replace that dig.

## 错误写法

```c
// 反例：三道 compiler fence 被当成三次硬件等待，
// 然后删掉它们，指望窗口变短。
// 0 道在这张表上更长，不是更短。
```

```c
// 反例：S_sync=0% 被读成「fence 对调度没有作用」。
// 0 道和 1 道的 VF 差在这张表上是 119 个周期。
```

## 正确写法

```c
// 正例：load-all 之后留一道 compiler fence。
// ABS 之后和 reciprocal 之后的两道，在这个 shape 上不再缩短窗口。
for (int r = 0; r < rounds; ++r)
  a[r] = A0[r * T + tid];
asm volatile("" ::: "memory");  // wall LD
```

## 识别方法

1. In the SIMT source, count `asm volatile("" ::: "memory")` inside the VF. The four arms here are that count and nothing else.
2. In the instruction window, the zero-fence arm is the one whose VF is about 1320 on this shape. One or more fences sit near VF 1200.
3. Do not look for `RV_SMEM_BAR`. These walls do not emit one.

误报边界：this is T=512 on R64×C128. A different thread count or a different shape is a different row. A source comment that says "membar" is not this count. The count is the `asm` lines.

## 证据要求

A claim that cites this card must give:

- The fence count in the source, 0, 1, 2, or 3.
- VF and el/cyc from the same shape, or an explicit remeasure.
- The pass line.

It does not by itself support a SoftLib-versus-SIMD ranking. That ranking still needs PRC-IPC-001.

## 参考

- `work/ST-Analysis/skill-testing/PRC-SIMT-001/summary.txt`
- `work/ST-Analysis/skill-testing/PRC-SIMT-001/sources/walls{0,1,2,3}.asc`
- Sibling: PRC-SCH-001 (compiler clobber versus hardware `SMEM_BAR`)
- Published three-fence cell: tag `wc_c3e2e_back_loadall_absall_dual_drain_g32_t512_e8192`, VF 1210, el/cyc 6.7702
