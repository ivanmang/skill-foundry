---
name: tool-perf-analysis
description: Use when interpreting an NPU Profiling .npu-rep report or deciding how to optimize an operator — metrics, bottleneck verdict, and optimization directions with evidence.
category: perf-analysis
license: CANN Open Software License Agreement Version 2.0
origin: cannbot
maturity: ready
---

# Profiling 报告快照解析（tool-perf-analysis）

> 输入是 asc-toolkit Profiling Report 面板发送的**最小信封 payload**（JSON：version / scope / report_id / report_name / report_path / op_name / collected_at，不含 data 表）。
> 数据主路径：解包 `report_path` 指向的 `.npu-rep` 原始报告获取全部明细文件；payload 只做路由与定位。
> 本技能做四件事：**提取 → 解读 → 给优化方向与判据 → 指出数据缺口**。
> 边界：出**优化方向、代价、排除条件、验证方式**（内置于 [references/optimization-advice.md](references/optimization-advice.md)，知识自带、不依赖外部文档）；**不出代码实现**（API 签名、Kernel 骨架、TilingData 字段定义），不出采集命令。

## 0. 总流程

本技能收到报告后的完整执行流程（调用方只需说"分析报告"，其余全在本技能内部）：

```
1. 校验信封 payload（§1）
2. 解包 report_path 的 .npu-rep（§2.5）→ Summary.jsonl + 各 CSV + HardwareInfo.jsonl
3. 按 payload.scope 路由到对应 references/scope-*.md（§2.6）；scope 缺失则全量解读
4. 跑 scripts/summarize_tables.py 产出逐 block 统计（§3.1，脚本固化规则），按对应 scope-*.md 解读
5. 数据边界判定（能答/不能答，references/data-boundary.md）
6. 按 references/optimization-advice.md 索引匹配触发证据 → 只读命中条目的 advice/*.md 正文，生成优化建议条目（含反向排除项）
7. 按 §4 固定框架输出：四节结构（报告概览 / 建议 / 瓶颈判定 / 关键指标），数据缺口与补采项并入"建议"节
```

## 1. 输入校验（三 scope 通用）

必查字段，缺失即报"payload 不完整"并停止：

| 字段 | 说明 | 缺失处理 |
|------|------|---------|
| `version` | 目前为 "1.0" | 非 1.0 时提示解析规则可能不适用，继续但标注 |
| `scope` | `compute` / `memory` / `summary`；可选 | 缺失 → 全量解读（三 scope 输出合并）；未知值 → 按解包后文件内容判断并标注 |
| `report_id` | 报告唯一标识（多报告对比时区分用） | 缺失时用 report_name 代替 |
| `report_name` / `report_path` | 报告名与本地路径 | path 缺失则无法解包 → 走 §5 边界话术停止 |
| `op_name` | 算子名 | 可从 Summary.jsonl 的 OpInfoSummary 补 |
| `collected_at` | 采集时间 | 用于提示快照时效 |

**NA 规则（必须遵守）**：
- `"NA"` = 该指标对此算子不适用（如纯 Vector 算子的 `aic_*` 列），**不是 0、不是缺失**，统计时剔除而非当 0 参与平均
- 若某前缀（`aic_*`）整列 NA → 输出"本算子未使用 Cube 核（AI Core 为 Vector 型）"
- 空字符串列名（headers 末尾的 `""`）是 CSV 拖尾逗号产物，忽略

## 2. 取数与 scope 路由

### 2.5 解包 report_path（数据主路径）

`.npu-rep` 是二进制容器（NpuRepHead + 文件表 + 数据，支持嵌套子报告），解包后得到全部明细：

| 解包产物 | 内容 | 供哪个 scope |
|---------|------|-------------|
| `Summary.jsonl` | 全量汇总（文档明示"所有数据都能在这找到"）：各 CSV 的块均值 + `OpInfoSummary`（算子名/耗时/Block Dim/频率/并行度/SOL 带宽） | summary（主）+ compute/memory（交叉验证） |
| `PipeUtilization.csv` / `ArithmeticUtilization.csv` / `ResourceConflictRatio.csv` | 逐 block 计算负载三表 | compute |
| `Memory.csv` / `MemoryUB.csv` / `MemoryL0.csv` / `L2Cache.csv` | 逐 block 访存四表 | memory |
| `HardwareInfo.jsonl` | 芯片型号/架构/核数/频率/HBM | summary（hardwareDetails） |
| `PipeTrace.json` / `Sampling.json` | Chrome Trace 流水时间片 + 利用率采样 | 条件化触发时用（bound-heuristics §4）：初判 mixed/疑似/数据不足、命中需时间轴证据的条目（双缓冲/pingpong/PING-PONG gap）、或用户追问时间线 |

解包方式（按优先级）：
1. 使用技能自带脚本：`python3 scripts/unpack_npu_rep.py <report_path> <临时目录>`（位置参数：输入 rep、输出目录；递归解包 type=1 的嵌套报告；输出目录必须不存在）
2. 脚本不可用时按容器格式自行解析：magic `npu-rep\0`，小端头 36 字节 `<8sIHHIIIQ>`（version=1.0.0、origin=profile、fileInfoCount/fileInfoLength/npuRepLength），每项文件信息 160 字节 `<8s128sHHIQQ>`（magic + 128B basename + uint16 type + 保留字段 + 长度 + 数据偏移），type∈{1:npu-rep(嵌套), 2:json, 3:jsonl, 4:csv, 5:sqlite3, 6:protobuf}；嵌套项名称必须以 `.npu.rep` 或 `.rep` 结尾
3. 解包失败 → §5 边界话术，**不要臆造**；注意嵌套：根 rep 内每个算子一个 `opN.npu.rep` 子报告，多算子时按 report_id/op_name 定位对应子报告再解一层

### 2.6 scope 路由表

payload 无 data 表，scope 决定**优先解读哪些明细文件**：

| scope | 优先读的明细文件 | 详细规则 |
|-------|----------------|---------|
| `compute` | PipeUtilization / ArithmeticUtilization / ResourceConflictRatio + Summary.jsonl（均值行） | [references/scope-compute.md](references/scope-compute.md) |
| `memory` | Memory / MemoryUB / MemoryL0 / L2Cache + Summary.jsonl（带宽行） | [references/scope-memory.md](references/scope-memory.md) |
| `summary` | Summary.jsonl（OpInfoSummary + 各 category 行）+ HardwareInfo.jsonl | [references/scope-summary.md](references/scope-summary.md) |
| 缺失/全量 | 上述全部文件，三 scope 输出合并 | 三份 scope-*.md 全用 |

字段对应关系（旧版 payload 字段 → 解包来源）：`pipeOccupancy`/`computeTables` ← 三张计算 CSV；`memoryTables`/`memoryTopology` ← 四张访存 CSV；`bandwidthCards`/`computeCard`/`roofline` ← Summary.jsonl 派生；`hardwareDetails` ← HardwareInfo.jsonl。

## 3. 通用提取规则

### 3.1 逐 block 统计（脚本固化，不手算）

对解包出的 CSV 统一执行：

```
python3 scripts/summarize_tables.py <解包目录> [CSV 名…]
```

脚本一次产出全部 §3.1 规则的结果，报告直接引用其数值（不再在上下文里逐 block 手算）：

- 每数值列 **min / median / max / mean**（附离群 block 号）；带宽/数据量/计数列附 **Σ**
- **tail 识别**：末尾 block 时间 < median 的 60% 且为全表最小 → 标注 `tail_block`（总元素数不整除 block 数导致），该 block 的 ratio 不可与全量 block 直接比较
- **离散度**：max/min > 1.10 标注"block 间负载不均衡"（有 tail 时另给剔除 tail 后的 max/min，避免 tail 虚增离散度）
- **ratio 列约束**：各 pipe ratio 之和应约等于 1，偏离时提示数据可疑
- NA 规则自动处理：全 NA 列单列（`aic_*` 整组 NA → "未使用 Cube 核"）；全 0 列标注"真实零，有效结论"；`*_rate` 列不做 max/min 离散度与 Σ
- **交叉验证**：cycles/μs ≈ 主频（不一致则数据可疑）；`active_bw × ratio` 全程平均带宽（推算）；跨表同名列一致性（不一致标注可疑）

脚本不可用时按上述规则手工抽查关键列（主瓶颈 pipe 的 time/ratio 列 + 均衡性），不必全列展开。

### 3.2 指标名解码

完整对照见 [references/metric-glossary.md](references/metric-glossary.md)。速查：

| 片段 | 含义 |
|------|------|
| `aic_` / `aiv_` | Cube 核 / Vector 核 |
| `vec` | 向量计算单元 |
| `cube` | 矩阵计算单元 |
| `mte1/2/3` | 搬入 MTE1（L0→UB）/ MTE2（GM→UB）/ MTE3（UB→GM） |
| `fixpipe` | Cube 结果回写通路 |
| `scalar` | 标量单元 |
| `cflt` | conflict，资源冲突率 |
| `wait_ratio` | 等待占比 |
| `icache_miss` | 指令缓存未命中 |
| `vf / sfu / simt_vf` | 向量浮点 / 特殊函数单元 / SIMT 向量 |

### 3.3 与旧版大 payload 的兼容

若消息中的 payload 仍带 `data`（旧版完整快照），跳过解包直接按旧路径解析 data；两版并存时**以解包明细为准**（更全、口径单一）。

## 4. 输出契约（固定框架，任何 scope / 数据组合都必须遵循）

**规则**：无论 scope 是什么、解包出哪些文件，输出**永远**由以下 4 个固定小节按序构成。小节标题一字不改；某节无内容时保留标题写"无"或规定占位语，**不得删除小节、不得增减小节、不得改标题**。各 scope 只是往固定槽位填不同的数据。

```markdown
## 1. 报告概览
- 算子: <op_name> | 类型: <Op Type> | 报告: <report_id> | 采集于 <collected_at>
- 硬件: <芯片型号 + 架构> | 核数: <block 数>/<对应核数> | 主频: <Current/Rated Freq，降频需标注>
- 数据来源: 解包 report_path（<明细文件数> 个文件） | scope: <compute|memory|summary|全量（缺省）>

## 2. 建议
<按 [references/optimization-advice.md](references/optimization-advice.md) 生成。该文件是**索引**（全局规则 + 触发/排除速查表），先读它：
- 按其 §1–§4 表匹配触发证据，**只读命中条目的正文**（references/advice/general.md / matmul.md / mc2.md / conversion.md），未命中条目不读正文、不输出（改写入数据缺口）
- 每条建议用 `### 优先级 <N>：<方向>（预期收益：…）` 三级标题，正文含 **证据** / **方向** / **代价与前置检查** / **排除条件** / **如何验证见效** 五个槽位，槽位标题一字不改；槽位正文为结论句（每槽 1–3 句），细节以"（详见 §<条目号>）"指向
- 通用类先判，再按算子族叠加族特化条目：matmul 族 / MC² 族 / conversion 族
- 必须输出 `### 已排除的方向` 小节（依据见索引 §0 表）；反向排除全不成立时写"无"
- 收益数值按索引 §0 纪律引用（"典型收益"/"实测参考"，不得表述为对本算子的预测）；多条并存时按索引 §5 叠加顺序表定序并处理互斥
- 末尾以 `### 数据缺口与补采` 小节列出不能回答的问题 + 缺什么 + 如何获取；数据充足时写"无已知缺口">

## 3. 瓶颈判定
<bound 类型结论（compute-bound / memory-bound / mixed / workload_limited / 数据不足无法判定）+ 证据链：每条证据引用第 4 节的具体数值（数值取自 summarize_tables.py 输出，不另行手算）。多 scope 全量时给综合判定。有逐 block 数据时附均衡性结论（median/max/min、tail/离群 block 及量化数字，直接引脚本输出）；无逐 block 数据的 scope 写"本 scope 无逐 block 数据（卡片级汇总）"。
细粒度分级与误判排除按 [references/bound-heuristics.md](references/bound-heuristics.md) 执行：主结论后附细粒度标签（如 vec 型 / scalar 型 / 小 case / 流水未重叠 / 疑似 MTE2 污染）；vec 型按占比分级（轻度/中度/深度）；memory-bound 须证据三件套齐全，缺项降级"疑似"；时间轴确认按该文件 §4 的**条件化触发**执行（非每案必做）；MC² 算子高 mte2_ratio 不直接判 memory-bound。

## 4. 关键指标
<按 scope 填充该 scope 的"必输出清单"数值；每条一行"指标: 值（单位）"；无 scope 全量时三组各出，用 **计算 / 访存 / 汇总** 三个粗体子标题分组；某组数据缺失则该子标题下写"明细缺失（<原因>）"。口径提示（single-shot 标注、带宽单块/Σ块口径、active_bw 换算说明等）随相关指标附注，无则省略>
```

**框架自检**（输出前逐条核对）：
1. 四个小节齐全、标题逐字一致、顺序不变（报告概览 / 建议 / 瓶颈判定 / 关键指标）
2. 第 4 节每条数值带单位；第 3 节每条证据能回溯到第 4 节
3. 第 2 节每条建议五槽位齐全，且"证据"槽位的数值与第 4 节一致；触发条件不成立的条目**不得输出**（改写入数据缺口）
4. 第 2 节含"已排除的方向"与"数据缺口与补采"两个小节（数据充足可全答时后者写"无已知缺口"）
5. 第 2 节不含代码实现（API 签名 / Kernel 骨架 / TilingData 字段定义）——越界即删
6. NA 数据不参与统计；推算值必须标"推算"；收益数值标"典型收益"或"实测参考"
7. MC² 算子：MTE2 污染未排除前，第 2 节不得出现基于 `mte2_ratio` 的 Full-Load / 小块合并建议



## 5. 数据边界话术（回答"不能回答"时使用）

统一口径，不得自行发挥：

> "该项数据在报告 <report_id> 中不存在。<缺什么>。可通过 ① 检查采集时是否勾选对应指标（如 L2Cache 需采集开关）后重新采集，或 ② 使用 msprof 进行 warmup=10 / repeat=5 / median 的重复采集获取。"

解包失败专用话术：
> "报告 <report_path> 解包失败（<原因>）。无法读取明细数据。请确认文件完整或重新采集。"

禁止行为：
- 用近似值/理论值代替实测值
- 声称"我帮你查一下"（报告是静态文件，可随时重读但内容不会变）
- 把单次采集说成稳态结论（无 repeat 样本时必须标注 single-shot）
- scope 缺失时假装用户指定过 scope
- 输出触发条件未被报告数值支持的优化建议（无证据的建议一律改写入数据缺口）
- 把优化的典型收益区间说成对本算子的收益预测
- 在建议里给出 API 签名、Kernel 代码骨架或 TilingData 字段定义（越出本技能边界）
- 报告不可见的量（tiling data、shape、dtype、指令级构成、隔离测试 R 值）自行推算或假设成具体数值
