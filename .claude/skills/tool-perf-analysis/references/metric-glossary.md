# metric-glossary：指标术语表

payload 各字段/列名的语义速查。三级结构：**前缀（哪个核）→ 单元（哪条流水）→ 度量（什么口径）**。

## 1. 核前缀

| 前缀 | 核 | 说明 |
|------|-----|------|
| `aic_` | AI Cube 核 | 矩阵乘主力；纯 Vector 算子整组 NA |
| `aiv_` | AI Vector 核 | 向量/逐元素主力 |

`sub_block_id` = `vector0` 表示 Vector 核上的 vector 子块。

## 2. 计算单元（Unit）

| 片段 | 单元 | 功能 |
|------|------|------|
| `vec` | 向量计算单元 | 逐元素算术、逻辑 |
| `cube` | Cube 矩阵单元 | 矩阵乘累加（仅 aic_） |
| `scalar` | 标量单元 | 循环控制、地址计算、条件分支 |
| `fixpipe` | Cube 结果回写通路（仅 aic_） | 量化/格式转换后写回 |
| `vf` | 向量浮点 | FP 运算按位宽折算 |
| `sfu` | 特殊函数单元 | exp / log / sin / rsqrt 等超越函数 |
| `simt_vf` | SIMT 向量浮点 | SIMT 模式向量核（如 C2 类核）；与 vf 互斥使用 |

> 注：部分采集版本的 ArithmeticUtilization 使用按 dtype 细分的列名（`aiv_vec_fp32_ratio` / `fp16` / `int32` / `int16` / `misc`），与 vf/sfu/simt_vf 是两套命名，见到时任选存在的解析，语义按 dtype 占比理解。

## 3. 搬运引擎（MTE, Memory Transfer Engine）

| 片段 | 通路 | 方向 |
|------|------|------|
| `mte1` | L0A/L0B ← 外部 | Cube 专用搬入（仅 aic_） |
| `mte2` | UB ← GM/L2 | 搬入（Load） |
| `mte3` | GM/L2 ← UB | 搬出（Store） |

**口径警示**：`*_active_bw` 是"搬运正在进行期间"的带宽；全程平均 = active_bw × 该 pipe 的 ratio。判带宽瓶颈必须用全程平均。

## 4. 度量后缀

| 后缀 | 含义 | 判读基线 |
|------|------|---------|
| `_time(us)` | 时长 | — |
| `_ratio` | 时间占比（同核各 pipe 分片） | 排序找主瓶颈 |
| `_active_bw(GB/s)` | 活动期带宽 | × ratio 换算全程 |
| `_total_cycles` | 周期数 | cycles/μs ≈ 主频，可交叉验证 |
| `_cflt_ratio` | conflict 冲突率 | > 0.05 显著 |
| `_wait_ratio` | 等待占比 | > 0.05 且 cflt=0 → 上游供给不足 |
| `_miss_rate`（icache） | 指令缓存缺失 | > 0.01 关注 |
| 命中率（L2） | hit rate | < 0.5 局部性差 |

## 5. 特殊值

| 值 | 语义 | 处理 |
|----|------|------|
| `"NA"` | 该指标对此算子不适用 | 剔除统计；整列 NA → 输出"未使用该单元" |
| `0.000000`（ratio） | 真实为零（如 icache_miss、cflt） | 有效结论："无该问题证据" |
| headers 末尾 `""` 列 | CSV 拖尾逗号 | 忽略 |

## 6. ratio 的两种口径（易混）

| 口径 | 例 | 和为 |
|------|-----|------|
| pipe 分片占比（互斥时间段） | aiv_vec_ratio + aiv_scalar_ratio + aiv_mte2_ratio + … | ≈ 1 |
| 单元内部构成 | aiv_vec_vf_ratio / sfu_ratio / simt_vf_ratio（占 vec 时间的比例） | ≤ vec_ratio |

ArithmeticUtilization 的三个子 ratio 是第二种口径——`simt_vf_ratio == vec_ratio` 时说明全部向量时间都在 SIMT 浮点上。

## 7. L2 Cache 与存储层级补充（npu-rep 明细口径）

| 字段片段 | 含义 |
|---------|------|
| `read/write_close_*` | 本 Die（near）读/写 |
| `read/write_far_*` | 跨 Die（far/remote）读/写 |
| `*_hit` / `*_miss` / `*_victim` | 命中 / 缺失 / 被逐出行数（次数，非字节） |
| `*_hit_rate(%)` | 命中率；面板箭头用 total（读+写合并）口径 |
| `main_mem_read/write_bw` | 主存（HBM）读/写速率，**单 block 口径** |
| `gm_to_ub_bw` / `ub_to_gm_bw` | GM↔UB 直通（MTE2/3）速率；与 MemoryUB 的 `ub_read/write_bw_gm` 同物异名，优先 Memory.csv 口径 |
| `*_datas(KB)` | 通路数据量（单 block） |
| `l1_read/write_bw` | L1（仅 aic） |
| `l0a/l0b/l0c_*` | L0A/L0B/L0C（Cube 专用，纯 Vector 算子 NA） |
| `Task Duration(us)` | Task 级总耗时 > 块级 aiv_time 之和的口径（含调度） |
| `Block Dim` | Task 切分数 = 并行 block 数 |
| `aicore_parallel_utilization` | 并行使用率 Σ busy/(N×T_kernel) |
| `aicore_parallel_balance` | 均衡度（1 − σ/μ） |
| `Current/Rated Freq` | 实际/额定主频，Current < 90% Rated → 降频，性能数据失真 |
