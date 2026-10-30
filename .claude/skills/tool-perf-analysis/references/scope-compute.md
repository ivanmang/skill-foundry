# scope-compute：计算负载快照解析规则

输入：`data.pipeOccupancy` + `data.computeTables`（PipeUtilization.csv / ArithmeticUtilization.csv / ResourceConflictRatio.csv）+ `data.csvTexts`

> 字段语义已用真实 payload（vector_muladd_plain）校准。

## 1. pipeOccupancy（流水线占用总览）

每项：`id` / `label` / `ratio`（0~1 占比）/ `absoluteValue`（μs）/ `side`。

**提取算法**：
1. 按 ratio 降序，取第一项为主瓶颈 pipe，输出 `label (ratio%, absoluteValue μs)`
2. 次高项 ratio < 5% 时 → "单 pipe 主导"；两项均 > 30% → "流水线重叠良好"或"多 pipe 并行"
3. `icache` 无 absoluteValue → 只输出 ratio，为 0 时输出 "ICache 无缺失"
4. ratio 总和 > 1.05 时提示分片口径可疑

**解读要点**（回答"这个占比说明什么"）：

| 现象 | 含义 | 追问引导 |
|------|------|---------|
| vector ≈ 0.99 | 向量单元几乎无空闲，Vector 计算为当前瓶颈；继续优化需减少向量指令数或提高单指令效率 | "向量指令数能否通过融合/位宽提升减少？" |
| scalar ≈ 0.01~0.03 | 标量占比小但非零，通常是循环控制/地址计算 | "scalar 时间能否下放为向量化的索引计算？" |
| mte2/mte3 ≈ 0.0001 | 搬运与计算完全重叠（搬运隐藏在计算下）→ **不是** memory bound 的证据 | "若改大 tiling 块，搬运时间是否仍可隐藏？" |
| scalar > 0.1 | 标量瓶颈，典型 ScalarBound，查循环内标量操作 | "是否存在逐元素的条件分支或标量累加？" |

## 2. PipeUtilization.csv（逐 block 流水线占用）

关键列（aiv_ 前缀，aic_ 同理）：

| 列 | 解读 |
|----|------|
| `aiv_time(us)` / `aiv_total_cycles` | block 执行时长。cycles 与 μs 之比 ≈ 主频，可用于交叉验证 |
| `aiv_vec_time / aiv_vec_ratio` | 向量单元忙碌时间/占比 |
| `aiv_scalar_time / aiv_scalar_ratio` | 标量 |
| `aiv_mte2_time / ratio / active_bw` | GM→UB 搬入。**active_bw 是搬运发生期间的带宽，不是全程平均带宽**，判 memory bound 时必须换算：全程平均 ≈ active_bw × mte2_ratio |
| `aiv_mte3_*` | UB→GM 搬出 |
| `aiv_icache_miss_rate` | > 0.01 时提示取指瓶颈（循环体过大/分支过多） |

**必做**：
- §3.1 逐 block 统计（tail 识别尤其重要：本表常见末尾 block 减半）
- 全 block `vec_ratio` 的 min：若 min < 0.9，找出该 block 并比对其 scalar_ratio（通常是 tail 或调度抖动）

## 3. ArithmeticUtilization.csv（算力利用率）

| 列 | 解读 |
|----|------|
| `aiv_vec_ratio` | 向量总算力利用率（应与 PipeUtilization 的 vec_ratio 一致，不一致则数据可疑） |
| `aiv_vec_vf_ratio` | 向量浮点（FP16/FP32/FP64 按位宽折算） |
| `aiv_vec_sfu_ratio` | 特殊函数单元（exp/sin/rsqrt 等），高时提示换 SFU 实现或查表 |
| `aiv_vec_simt_vf_ratio` | SIMT 向量浮点。**若 simt_vf == vec 而 vf == 0 → 算子走 SIMT 模式（C2 类核），优化手段与普通向量指令不同**（如 vector_muladd_plain 全列 simt_vf=0.98、vf=0） |

**解读问题模板**：
- "算力利用率 98% 还有优化空间吗？" → 依据：利用率是时间占比不是效率占比；98% 只说明向量单元没空闲，**单条指令的位宽利用率**（128b 是否吃满）此处不可见 → 归入"不能回答"，需指令级数据或源码
- "浮点和特殊函数哪个是热点？" → vf vs sfu ratio 直接对比

## 4. ResourceConflictRatio.csv（资源冲突）

| 列 | 解读 |
|----|------|
| `aiv_vec_stu_cflt_ratio` | Store 单元冲突（写回碰撞） |
| `aiv_vec_ldu_cflt_ratio` | Load 单元冲突 |
| `aiv_vec_sfu_cflt_ratio` | SFU 冲突 |
| `aiv_vec_wait_ratio` | 向量单元等待（队列满） |
| `aiv_mte2/mte3_wait_ratio` | 搬运等待（通常是同步 barrier 或带宽不足） |

**解读规则**：
- 全 0 → 明确输出"无资源冲突证据，冲突不是本算子瓶颈"（这是有效结论，不是数据缺失）
- 任一列 > 0.05 → 该列即冲突证据，按冲突类型给出排查方向（LDU→访存粒度、STU→写回碰撞、SFU→特殊函数）
- `wait_ratio` > 0 但 cflt = 0 → 等待来自上游供给不足（如 MTE 等 GM），需 memory scope 佐证 → 归入"本 scope 不能定论"

## 5. 必输出清单（填入 SKILL.md §4 固定框架的"4. 关键指标"节，scope=compute 时）

1. 主瓶颈 pipe（label + ratio + μs）
2. 核型（纯 Vector / 纯 Cube / 混合；SIMT 与否）
3. block 均衡性（median / max / min / tail block）
4. 冲突结论（有 → 最大冲突列；无 → "无证据"）
5. mte2 全程平均带宽换算值（active_bw × ratio，标注为推算）
6. 瓶颈细粒度标签与分级（主瓶颈为 vector 时按 [bound-heuristics.md](bound-heuristics.md) §2 给轻度/中度/深度；cast/超越函数占比需指令级 trace，缺则列入数据缺口）

**瓶颈判定补充规则**（详见 [bound-heuristics.md](bound-heuristics.md)）：
- vector 主导时按占比分级：50–65% 轻度 / 65–80% 中度 / >80% 深度（接近理论极限）
- 高 mte2_ratio 不足以判 memory-bound：须证据三件套（搬运利用率高 + 计算/搬运单元等待气泡 + 计算密度低），MC² 算子另查 MTE2 污染
- 时间轴确认按 [bound-heuristics.md](bound-heuristics.md) §4 条件化触发：本 scope 初判为 mixed/疑似/数据不足，或命中 §1.1 / §2.1 / §2.6 等需时间轴证据的条目时才读 PipeTrace.json；否则不读，标注"未经时间轴确认（未触发读取条件）"

**本 scope 常触发的优化建议**（先读 [optimization-advice.md](optimization-advice.md) 索引：按本表现象命中条目号后，**只读对应正文文件** [advice/general.md](advice/general.md) / [advice/matmul.md](advice/matmul.md) 等；未命中条目不读正文也不输出）：

| 本表提取到的现象 | 触发条目 |
|----------------|---------|
| mte2_ratio + vec_ratio ≈ 1 且单侧均不高 / 时间片串行 | §1.1 双缓冲 |
| 各单元利用率均低 + 元素量小 | §1.2 核数裁剪 |
| 离散度 > 1.10 或存在 tail block | §1.3 尾块处理 |
| vec_ratio 高（≥ 65%）且 scalar 非零 / sfu 明显 | §1.6 Vector 计算效率 |
| scalar_ratio > 0.1（或伴 icache_miss > 0.01） | §1.7 Scalar 编码原则 |
| simt_vf == vec 且 vf == 0 | §1.8 SIMT 手段切换 |
| aic 各 pipe 串行、Cube busy 低（matmul 族） | §2.1 pingpong |
| 各流水 busy ≤ 70% 且 PING/PONG 有 gap（matmul 族） | §2.6 MTE2 预加载 |
| 反向排除成立（mte2≈0.0001 / scalar < 0.1 / 冲突全 0 / 离散度 < 1.10） | §5 已排除的方向 |

## 6. 本 scope 能回答 / 不能回答（摘要用）

**能回答**：
- 哪条 pipe 是时间瓶颈？各 pipe 占比多少？
- Cube 与 Vector 哪个在干活？
- 各 block 负载是否均衡？有没有 tail 浪费？
- 有没有计算资源冲突（LDU/STU/SFU）？
- 搬运是否与计算重叠（MTE ratio 极小 = 重叠好）？

**不能回答**（→ data-boundary 话术）：
- HBM/L2 实际带宽离峰值多远？（需 memory scope 的 bandwidthCards）
- L2 命中率？（需 L2Cache.csv）
- 数据搬运总量和理论最优搬运比？（需 shape + dtype 源信息）
- 单条向量指令位宽利用率？（需指令级 profile 或源码）
- 这是不是稳态性能？（单次快照，无 repeat，需重复采集确认）
