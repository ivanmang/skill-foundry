# bound-heuristics：瓶颈判定经验规则（蒸馏自 ascendc-perf-optimize）

> 本文件承接 ascendc-perf-optimize skill 的 bound 判定经验，用于强化"瓶颈判定"节的细粒度分级与误判排除。
> **只出判定证据与细分标签，不出优化策略**；优化方向引导见"建议"节（指向 ascendc-perf-optimize skill）。
> 本文件的分类体系**不替代** SKILL.md §4 的五分类结论（compute-bound / memory-bound / mixed / workload_limited / 数据不足无法判定），只在其后附加细粒度标签与严重程度。

## 1. 细分标签映射（五分类 → 细粒度）

瓶颈判定结论 = 五分类主结论 + 细粒度标签（括号内），标签取自下表：

| 五分类主结论 | 细粒度标签 | 判定条件 |
|-------------|-----------|---------|
| compute-bound | `vec 型` | `aiv_vec_ratio` 耗时主导，MTE2/Cube 相对空闲 |
| compute-bound | `vec 型（SIMT）` | simt_vf == vec 且 vf == 0（C2 类核 SIMT 模式，优化手段不同） |
| compute-bound | `cube 型` | aic cube 相关 pipe 主导 |
| compute-bound | `scalar 型` | scalar 占比 > 0.1（典型 ScalarBound，查循环内标量操作/逐元素条件分支） |
| memory-bound | `访存型` | 见 §3 证据三件套 |
| workload_limited | `小 case` | 计算量极小（element count 低）+ 各单元利用率均不高 |
| workload_limited | `流水未重叠` | 见 §4 DoubleBuffer 判定 |
| 数据不足无法判定 | `疑似 MTE2 污染` | 见 §5（MC² 算子） |

## 2. VEC bound 严重程度分级（scope=compute 时必查）

按 `aiv_vec_ratio`（剔除 tail block 后的全 block 统计）：

| vec 占比 | 等级 | 含义（仅作判定结论的严重程度注记，不展开优化手段） |
|---------|------|---------|
| 50–65% | 轻度 | 向量主导但未吃满，距离理论极限有空间 |
| 65–80% | 中度 | 向量接近主导，仍有一定空间 |
| >80% | 深度 | VEC 已接近理论极限，单算子层面优化空间有限 |

进一步细分证据（需 PipeTrace.json 指令级统计，缺 trace 时归入数据缺口）：

- Cast 类指令（`vcvt_f2f/f2s/s2f`）占 VEC 时间 > 20% → 标注"类型转换密集"
- 超越函数指令（`vec_exp/log/rsqrt/tanh` 等）占 > 30% → 标注"超越函数主导（深度）"

## 3. memory-bound 证据三件套（防单指标误判）

带宽利用率高**单独**不足以判 memory-bound，须三件套齐全（缺项时降级为"疑似"并列入数据缺口）：

1. **MTE2/搬运单元利用率高**：带宽接近理论峰值（对 SOL，如 1600 GB/s，注意单块/Σ块口径）
2. **计算单元存在等待气泡**：vec/cube ratio 偏低 + wait_ratio > 0（上游供给不足）
3. **计算密度低**：算术强度 Ops/Byte 低于硬件平衡点（roofline 转折点左侧）

反向排除（任一成立则**不是** memory-bound）：
- mte2 ratio ≈ 0.0001 → 搬运完全隐藏在计算下（搬运不是瓶颈）
- 带宽利用率 < 30% 且 vector 高占用 → 带宽大量富余
- UB 带宽 ≫ GM 带宽 → UB 不是瓶颈（GM 侧另议）

## 4. 时间轴确认（条件化触发，非每案必做；排除"访存等计算 vs 计算等访存"误判）

PipeTrace.json 体积可观且常与本算子无关（如纯 vector 算子只采到 cubecore 事件），**仅在下列任一条件成立时才读它**做时间轴确认；不满足时跳过读取，结论标注"未经时间轴确认（按条件化触发规则未读 trace）"即可：

1. 初判为 **mixed / 疑似 memory-bound / 数据不足无法判定**（结论有分歧，需时间轴裁决）
2. 命中了**需要时间轴证据的建议条目**：§1.1 双缓冲（串行/交替判据）、matmul 族 §2.1（pipe 串行）、§2.6（PING/PONG gap）
3. 用户追问时间线 / 流水重叠细节（evals 的 trace-sampling-files 场景）

单一明确标签（如 vec 深度型）且多指标交叉印证一致 → 不读 trace，直接下结论并附上述标注。

读取后按 pid/tid 聚合各核各 pipe 时间片：
- **DoubleBuffer 判定法**：
  - MTE2 与 VECTOR 时间片**交替出现** → 搬入与计算重叠，流水健康（若总耗时仍高，瓶颈在单侧单元本身）
  - MTE2 集中在前、VECTOR 集中在后（**串行**）→ 流水未重叠 → `workload_limited（流水未重叠）`强证据
- **等待方向区分**：MTE2 忙 + VECTOR 空 → 计算等访存（访存侧瓶颈）；VECTOR 忙 + MTE2 空 → 访存等计算（计算侧瓶颈或搬运已隐藏）
- trace 覆盖核与本算子核型不符（如 Op Type=vector 却只有 cubecore 事件）→ 标注"trace 数据可疑，无法确认"，列入数据缺口，不据此下任何结论

## 5. MC² 场景 MTE2 污染判定（防高 mte2_ratio 误判）

MC² 通算融合算子中 `CrossCoreWaitFlag` 挂在 MTE2 流水线上等待通信，会使 `mte2_ratio` **含通信等待空转**，高 mte2_ratio 不代表真实访存瓶颈。

- 报告内无法直接排除污染（需隔离测试对比纯计算口径的 mte2_ratio）
- 判定：算子为 MC² 通算融合类（fork 多 rank + CrossCoreFlag 同步，算子名如 *allreduce/allgather/reducescatter/alltoall* + matmul 组合）且 mte2_ratio 高 → 结论写"疑似 MTE2 污染"，**不得**直接判 memory-bound（访存型）；数据缺口注明需隔离测试
- 多 rank 场景补充提示：木桶效应——多卡协同性能由最慢 rank 决定，跨卡对比时关注 max 而非均值

## 6. 采集口径注记（判定结论的边界条件）

- 单次采集（single-shot，无 repeat）→ 判定结论标注"非稳态"；稳态取值须循环 ≥10 次、前 5 次 warm-up（L2 预热、DVFS 爬频）、取后 5 次均值
- 首次执行耗时 > 后续均值 3 倍 → warm-up 样本，应剔除后再统计
- 降频采集（Current Freq < Rated × 0.9）→ 判定结论标注"降频失真"
