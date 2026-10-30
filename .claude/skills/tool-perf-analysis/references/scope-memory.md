# scope-memory：内存负载快照解析规则

输入：`data.memoryTables`（Memory.csv / MemoryL0.csv / MemoryUB.csv / L2Cache.csv）+ `data.memoryTopology` + `data.bandwidthCards` + `data.csvTexts`

> 字段语义已用 npu-rep 明细数据（vector_muladd_plain）校准。口径来源：npu-tools `NPU-Compute.md`。

## 0. 每块 vs 全核口径（本 scope 最易错点）

memoryTables 是**逐 block** 的。带宽字段（如 `aiv_main_mem_read_bw`）是**该 block 的速率**：
- 多 block 并行执行 → 设备级总带宽 ≈ Σ(各 block 带宽)，64 block × 27 GB/s ≈ 1.7 TB/s 量级即可触及 SOL
- `*_bw_usage_rate(%)` 与 `datas(KB)` 为该 block 口径；总搬运量 = Σ 各 block
- 对照理论峰值时先确认分子分母口径一致（全核 vs 单块），否则结论作废

## 1. bandwidthCards / OpInfoSummary 带宽卡片

| 字段 | 来源 | 解读 |
|------|------|------|
| `aicore_gm_bw_theoretical(GB/s)` | OpInfoSummary（SOL 固定参数，样例 1600） | 理论峰值分母 |
| `aicore_gm_read_bw` / `write_bw` | OpInfoSummary（= Memory 表 aic+aiv 求和） | 实测读写 |
| `aicore_gm_bw_usage_rate(%)` | OpInfoSummary | 利用率 |

**解读**：
- 利用率 < 30% 且 compute scope 显示 vector 高占用 → 不是带宽瓶颈（带宽大量富余）
- 利用率 > 80% → memory-bound 强证据，优化方向是减少搬运量而非提高并行
- 读/写 > 3:1 → 读主导，提示 L2 驻留/预取；写主导 → 合并写回

## 2. Memory.csv（GM 级访存）

关键列：

| 列 | 解读 |
|----|------|
| `aiv_main_mem_read_bw` / `write_bw` | 该 block 主存读/写速率 |
| `aiv_gm_to_ub_bw` / `aiv_ub_to_gm_bw` | GM↔UB 直通搬运速率（MTE2/3 通路） |
| `aiv_mte2/mte3_instructions` / `_ratio` | 搬运指令条数与占比（与 PipeUtilization 交叉验证） |
| `read/write_main_memory_datas(KB)` | 该 block 主存读/写**数据量** |
| `GM_to_UB_datas(KB)` + `GM_to_UB_bw_usage_rate(%)` | GM→UB 通路数据量与通路带宽使用率 |
| `GM_to_L1_*` / `L0C_to_L1_*` / `L0C_to_GM_*` | Cube 相关通路（纯 Vector 算子 NA） |

**核心解读——冗余搬运判定**（本 scope 独有答案）：
- 总读量 = Σ read_main_memory_datas；理论必要读量 = shape × dtype（需用户给 shape）
- 实测/理论 > 1.5 → 冗余搬运（tiling 重读、未复用），提示排查 tiling 复用
- `GM_to_UB_datas` 远小于 `read_main_memory_datas` → 大部分读走了 L1/缓存通路而非直通 UB，属正常（直通通路只是众多通路之一）

## 3. MemoryUB.csv（UB 级）

| 列 | 解读 |
|----|------|
| `aiv_ub_read_bw_vector` / `write_bw_vector` | 计算单元对 UB 的读/写速率（本例 ~54 GB/s 每块） |
| `aiv_ub_read_bw_gm` / `write_bw_gm` | MTE 从 GM 搬入/向 GM 搬出的速率（与 Memory.csv 的 gm_to_ub/ub_to_gm 同物异名，**优先用 Memory.csv 口径**） |

**解读**：UB 带宽 ≫ GM 带宽时说明 UB 不是瓶颈；UB 读 ≈ UB 写且都高 → 计算确实在吃 UB 数据（与 vector 高占用互证）。

## 4. L2Cache.csv（L2 缓存）

字段结构：`{aic|aiv}_{read|write}_{close|far}_{hit|miss|victim}`（次数）+ `{aic|aiv}_{read|write}_hit_rate(%)`。

- **close/far**：本 Die / 跨 Die（远端）访问
- **victim**：因该访问被逐出的行数
- 汇总口径用 **total**（读+写合并命中率），面板 GM↔L2 箭头也是 total 口径

**解读模板**（用真实样例）：

| 现象 | 含义 |
|------|------|
| 读命中率 ~0.03% + 写命中率 100%（本算子实测） | 典型**流式访问**：输入只读一次无复用（读 miss 正常），写全命中（写分配生效）。对 elementwise 算子这是**预期行为**，不是优化点 |
| 读命中率 < 50% 且同一数据被多次读 | 局部性差 → 分块不连续 / stride 访问 → 改 tiling 提升空间局部性 |
| `far_miss` 占 miss 主要部分 | 跨 Die 访问代价高 → 数据布局应靠近计算核（numa 级问题） |
| miss 计数 × 64B 行 × block 数 ≈ 主存读量 | 交叉验证：L2 miss 是 GM 读量的下界解释 |

## 5. memoryTopology（访存拓扑图）

面板渲染 GM↔L2↔UB↔L0 拓扑，边上数值：GB/s 用带宽字段（GB/s 统一单位，KB 数据量仅 L0C 通路用）；L2 节点上标 total 命中率；L0C→UB 边不显示（无字段）；Dual-Die/Remote 边暂无数据不显示。

## 6. 必输出清单（填入 SKILL.md §4 固定框架的"4. 关键指标"节，scope=memory 时）

1. GM 读写带宽与利用率（对 1600 GB/s 级 SOL），注明口径（单块/Σ块）
2. L2 total 命中率 + 读/写分项 + 流式/复用判定
3. 总搬运量（Σ per block），有 shape 时给冗余度
4. UB 带宽是否为瓶颈（通常否）
5. memory bound 证据链结论或"无 memory bound 证据（带宽富余 + vector 主导）"

**memory-bound 证据三件套**（详见 [bound-heuristics.md](bound-heuristics.md) §3——带宽利用率高单独不足以判定）：
1. MTE2/搬运单元利用率高（带宽接近理论峰值，注意口径）
2. 计算单元存在等待气泡（vec/cube ratio 偏低 + wait_ratio > 0，需 compute scope 佐证）
3. 计算密度低（算术强度 Ops/Byte 低于 roofline 转折点，需 summary scope 佐证）
缺项时结论降级为"疑似 memory-bound（缺 <某项> 证据）"，缺项列入数据缺口；MC² 算子另按 bound-heuristics.md §5 排查 MTE2 污染。

**本 scope 常触发的优化建议**（先读 [optimization-advice.md](optimization-advice.md) 索引：按本表现象命中条目号后，**只读对应正文文件** [advice/general.md](advice/general.md) / [advice/matmul.md](advice/matmul.md) / [advice/conversion.md](advice/conversion.md)；未命中条目不读正文也不输出）：

| 本表提取到的现象 | 触发条目 |
|----------------|---------|
| mte2_ratio 高但带宽利用率不高（次数多而非量大） | §1.4 UB/TBuf 常驻复用（附 bank 冲突规避） |
| 带宽利用率低但 mte_ratio 不低 / mte2_wait_ratio > 0 而冲突为 0 | §1.5 DataCopy 优化（对齐、粒度、离散） |
| L2 命中率低 + 同一数据被反复读入 | §1.4（常驻复用消除重复 GM 读） |
| 真 MTE2 bound：MTE2 busy 高 **且** 带宽利用率高（matmul 族） | §2.4 A/B-Full-Load |
| 假 MTE2 bound：MTE2 busy 高 **但** 带宽利用率 < 70% + 存在 < 20 KB 小块（matmul 族） | §2.5 小数据块合并载入 |
| mte3 段大量小 strided 搬运（conversion 族 N_LAST） | §4.3 写出维度合并 |
| 带宽利用率极低（逐元素路径，conversion 族 SMALL_SHAPE） | §4.2 向量化读写 |
| 反向排除成立（带宽 < 30% + 计算高占用 / UB 带宽 ≫ GM 带宽） | §5 已排除的方向 |

> 真/假 MTE2 bound 的分界是**带宽利用率**（高→§2.4，< 70%→§2.5），这是 matmul 族最易混淆的一对，判定前先把口径（单块 vs Σ 块）核对一致。MC² 算子在 MTE2 污染排除前**不得**据 `mte2_ratio` 推这两条。

## 7. 本 scope 能回答 / 不能回答

**能回答**：
- 带宽跑满没有？离峰值多远？
- L2 命中率？流式还是复用型访问？有没有跨 Die 代价？
- 实际搬运量多少（可与理论必要量比冗余）？
- UB/L0 各级是否瓶颈？

**不能回答**：
- 计算单元利用率与冲突？（compute scope）
- 怎么改 tiling？（本技能只出证据，不出改造方案）
- 稳态带宽？（单次采集，无 repeat）
