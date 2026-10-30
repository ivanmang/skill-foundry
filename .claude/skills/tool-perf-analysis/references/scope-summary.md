# scope-summary：汇总快照解析规则

输入：`data.summary` + `data.computeCard` + `data.bandwidthCards` + `data.roofline` + `data.pipeOccupancy` + `data.memoryTopology` + `data.hardwareDetails`

> 字段语义已用 npu-rep 明细数据（vector_muladd_plain）校准。口径来源：npu-tools `NPU-Compute.md`。

## 1. summary / OpInfoSummary（算子基础信息）

来源 `summary.jsonl → category: OpInfoSummary`：

| 字段 | 解读 |
|------|------|
| `Op Name` / `Op Type` | 算子名与类型（vector / cube / mix） |
| `Task Duration(us)` | Task 总耗时（注意：> 逐 block aiv_time，含调度/首尾开销） |
| `Block Dim` | Task 切分（并行 block 数） |
| `Mix Block Dim` | Cube+Vector 混合切分（纯 vector 为 null） |
| `Current Freq` / `Rated Freq` | 实际/额定主频（降频 → 性能数据失真，必须检查：Current < Rated × 0.9 时标注"降频采集"） |
| `aicore_parallel_utilization` | AI Core 并行使用率：Σ block busy / (N × T_kernel)。样例 0.981 → 核并行度良好 |
| `aicore_parallel_balance` | 负载均衡度（当前口径 1 − σ/μ）。> 0.9 均衡；低 → 某些 block 拖尾 |

**核心派生关系**（回答"用了多少核"）：
- Op Type = vector → 显示 Block Dim / ai_vector_count
- Op Type = cube → Block Dim / ai_cube_count
- Op Type = mix → Block Dim / ai_core_count
- 样例：64 block / 72 vector 核 → 理论并行度 0.89，配合 parallel_utilization 0.981 判定并行充分

## 2. hardwareDetails（HardwareInfo.jsonl）

按 category 逐行：

| category | 关键字段 |
|----------|---------|
| Host Info | CPU 逻辑核数、内存、磁盘 |
| Device Info | 芯片型号（如 Ascend950PR_9599 V100）、**架构代次（如 3510 → DAV_3510）** |
| CPU Information | 控制 CPU / AI CPU 数与频率 |
| AI Core Information | ai core/cube/vector count、频率 |
| Memory Information | HBM 总量/用量、频率 |

**用途**：
- 理论算力公式（按执行器×dtype）：
  - cube fp16 = cube_num × 4096 × 2 × freq / 1000（TFLOPS）
  - cube int8 = cube_num × 8192 × 2 × freq / 1000
  - vector fp16 = vector_num × 128 × 2 × freq / 1000
  - vector fp32/int32 = vector_num × 64 × 2 × freq / 1000
- 理论带宽：SOL 固定参数（样例 1600 GB/s）
- 架构代次（DAV_2201 vs DAV_3510）→ 不同架构的规格上限与指令特性不同，解读时注明
- HBM used 高 → 提示其他任务挤占，性能数据可能受干扰

## 3. pipeOccupancy

与 compute scope 同结构同规则（scope-compute.md §1）。

## 4. computeCard（算力卡片）

| 数值 | 公式 |
|------|------|
| 实测算力 | cube: aic_total_cycles × cube_ratio × 4096(或 8192/2048) × 2 / task_time；vector: aiv_total_cycles × vec_ratio × 128(或 64) × 2 / task_time |
| 理论算力 | 见 §2 公式 |
| score | 实测/理论 × 100% |

**解读问题模板**：
- "我的算子还有几倍空间？" → 100%/score 即倍数。样例：vec fp16 理论 ≈ 72×128×2×1.65GHz ≈ 30.4 TFLOPS；实测需 vec_ratio × cycles 推算
- "为什么利用率高 score 还是低？" → ratio 高只说明向量单元没空，不代表单指令位宽吃满（fp16 128b vs 实际用了 int32 64b 等情况）

## 5. roofline（Roofline 瓶颈分析）

坐标轴：
- X（算术强度 Ops/Byte）= 总计算量 / 总搬运量（Memory 表 Σ datas）
- Y（TOps/s）= 实测算力（§4 公式）
- 屋顶：峰值带宽 1600 GB/s 斜线 × 峰值算力水平线

**解读规则**：
1. 点在转折点左侧（强度低）→ memory-bound 区；右侧贴近屋顶 → compute-bound；右侧远低于屋顶 → 延迟/占用受限（launch、同步、负载不均）
2. 输出：当前点位置、距屋顶倍数、要到达屋顶需提升哪个轴
3. L2 点需要 L2 搬运字节数——L2Cache.csv 只有命中计数**没有字节数**，L2 强度点位标注"数据不可得"（已知缺口，勿估算）
4. roofline 定位是 memory-bound 区时，仍须按 [bound-heuristics.md](bound-heuristics.md) §3 证据三件套复核（带宽利用率 + 等待气泡 + 计算密度），缺项降级"疑似"；"延迟/占用受限"对应细粒度标签 `workload_limited（流水未重叠/小 case）`，时间轴确认按该文件 §4 条件化触发（本 scope 命中该条件时读 PipeTrace.json 判 DoubleBuffer 是否生效、等待方向）

## 6. bandwidthCards

同 scope-memory.md §1（OpInfoSummary 带宽字段 + SOL 1600 GB/s）。

## 7. 必输出清单（填入 SKILL.md §4 固定框架的"4. 关键指标"节，scope=summary 时）

1. 算子：名称/类型/总耗时/block 数 vs 核数（按 Op Type 选分母）
2. 主频状态（是否降频）+ HBM 占用情况
3. AI Core 并行使用率 + 负载均衡度
4. 算力 score（实测/理论）与带宽 score
5. roofline 定位（memory/compute/延迟受限区 + 距屋顶倍数）
6. 芯片型号 + 架构代次
7. 综合结论：bound 方向 + 建议下一步（去 compute/memory scope 拿细节，或补采确认）；细粒度标签按 [bound-heuristics.md](bound-heuristics.md) §1 映射表附注

**本 scope 常触发的优化建议**（先读 [optimization-advice.md](optimization-advice.md) 索引：按本表现象命中条目号后，**只读对应正文文件**；未命中条目不读正文也不输出）：

| 本 scope 提取到的现象 | 触发条目 |
|--------------------|---------|
| roofline 落"延迟/占用受限"区（右侧远低于屋顶） | §1.1 双缓冲 / §1.2 核数裁剪（按元素量与并行度二选） |
| `aicore_parallel_balance` 偏低（< 0.9） | §1.3 尾块处理 |
| `aicore_parallel_utilization` 偏低 + 元素量小 | §1.2 核数裁剪 |
| 算力 score 低但 vec ratio 高（位宽未吃满） | §1.6 Vector 计算效率（指令级构成不可见时同时写入数据缺口） |
| roofline 落 memory-bound 区（转折点左侧） | 先按 bound-heuristics §3 三件套复核，再据带宽利用率走 §1.5 / §2.4 / §2.5 |
| Op Type 为 mix / Mix Block Dim 非空 + 算子名含集合通信语义 | §3 MC² 族全节（先声明 MTE2 污染前置） |
| 降频采集（Current < Rated × 0.9） | 不出优化建议，先写入数据缺口：性能数据失真，须定频重采 |

> summary scope **无逐 block 数据**，本 scope 触发的条目其"证据"槽位只能引卡片级汇总值；需要逐 block 或时间轴佐证的条目（如 §1.1 的时间片交替判据）须标注"未经逐 block/时间轴确认"，并把对应明细列入数据缺口。

## 8. 本 scope 能回答 / 不能回答

**能回答**：
- 这个算子整体 bound 方向？（roofline + 双 score 交叉）
- 并行度和负载均衡怎么样？用了多少核？
- 理论上限还有几倍？
- 什么芯片、什么频率（是否降频）、HBM 被占多少？

**不能回答**：
- 逐 block 细节、tail、资源冲突？（→ compute scope）
- L2 命中率、逐层带宽？（→ memory scope）
- L2 屋顶线的精确强度？（L2 字节数无字段）
- 稳态？（单次采集，无 repeat）
