---
id: PRC-SIMT-003
name: LDS.32 versus LDS.64 on Case-3 G32
category: SIMT
applies_to: SoftLib SIMT Case-3 G32 · era=case3-quant-bcast · R64×C128 E=8192 · within-group · T=128 and T=256 · A5 camodel
status: ready
---

# PRC-SIMT-003：LDS.32 versus LDS.64

## 知识点

LDS.32 is one `float` per load. LDS.64 is one `float2` per load. On the within-group Case-3 body a thread owns 32 adjacent columns, and the next thread owns the next 32. The two arms share the max, the reciprocal, the multiply, and one compiler fence after the loads.

Each group is 32 `float` loads or 16 `float2` loads in the source. T=128 walks two groups, so that is 64 against 32 source loads per thread. The issued `SIMT_LDS` count is a different number: 256 against 128 at both thread counts. The window does not move. Neighboring threads are still 32 columns apart, so the wider load does not close that gap.

This is not the warp-coop dual-drain kernel. That kernel gives each lane one column. Those addresses are not `float2` pairs, so a 64-bit load is not a drop-in change there.

### 实测摘要

R64×C128, E=8192, G=32, float32. Pass, max abs error 1.192e-07.

| Arm | T | SIMT_LDS | VF | el/cyc |
|---|---:|---:|---:|---:|
| lds32 | 128 | 256 | 16536 | 0.50 |
| lds64 | 128 | 128 | 16544 | 0.50 |
| lds32 | 256 | 256 | 16480 | 0.50 |
| lds64 | 256 | 128 | 16536 | 0.50 |

`SIMT_LDS` is the issue count of that mnemonic on veccore0, `is_popped==1`. It is recorded in `summary.txt` next to the VF lines.

## 错误写法

```c
// 反例：把 LDS.64 当成带宽翻倍，用来缩短 within-group 的窗口。
// 线程之间仍隔 32 个 float。SIMT_LDS 减半，VF 不动。
__ubuf__ float2* P = (__ubuf__ float2*)(A0 + tid * 32);
```

## 正确写法

```c
// 正例：要相邻列，把一个 warp 放在一个 group 上，每条 lane 一个 float。
// 那是 dual-drain / load-4 的地址，不是把 within-group 的 load 改成 float2。
a[r] = A0[r * T + tid];
```

## 识别方法

1. A within-group arm has base `tid * G`. LDS.32 loads `float`. LDS.64 loads `float2` from that base.
2. On this shape the issued `SIMT_LDS` count is 256 for lds32 and 128 for lds64, at both thread counts, and the VF matches. That is not the per-thread source count.
3. A warp-coop arm has base `r * T + tid` and one float per lane. Do not label that arm LDS.64.

误报边界：T=128 and T=256 on R64×C128. A different group size changes the stride. Dual-drain staying on scalar loads is not a failure to try LDS.64.

## 证据要求

A claim that cites this card must give:

- Which arm, lds32 or lds64, and the thread count.
- VF, and the `SIMT_LDS` issue count when the claim is about the load width.
- The pass line.

## 参考

- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/summary.txt`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/sources/lds32_t256.asc`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/sources/lds64_t256.asc`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/runs/lds32_t128/`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/runs/lds64_t128/`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/runs/lds32_t256/`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-003/runs/lds64_t256/`
- Sibling: PRC-SIMT-001 (fence count on the warp-coop body)
