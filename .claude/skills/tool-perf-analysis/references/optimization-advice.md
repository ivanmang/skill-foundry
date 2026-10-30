# optimization-advice 索引：条目路由 + 全局规则（先读本文件，命中条目再读正文）

> 本文件是「2. 建议」节的**路由层**：全局规则（§0）+ 全部条目的触发条件与排除条件速查（§1–§4 表）。**不要**把 references/advice/*.md 全部读入——按算子族先选组，再按表中触发证据命中 2–4 条，只读命中条目的正文文件。未命中的条目不得输出（改写入数据缺口）。
> 边界：只出**优化方向与判据**（做什么、为什么、代价多大、怎么验证），不出代码实现（API 签名、Kernel 骨架、TilingData 字段定义）。

## 0. 全局规则（每次输出前执行）

**五槽位格式**（槽位标题一字不改，缺数据的槽位写"报告不可见（需 <什么>）"）：

```markdown
### 优先级 <N>：<一句话方向>（预期收益：<区间或"需实测">）

**证据**：<报告实测数值 + 为何指向此方向；数值须与第 4 节一致>
**方向**：<改什么、改成什么形态、为什么能快>
**代价与前置检查**：<资源开销、必须先确认的条件>
**排除条件**：<什么情况下这条不适用>
**如何验证见效**：<重采看哪个指标怎么变；方向性判据>
```

槽位正文写结论句（每槽 1–3 句），方向/代价/验证细节以"（详见 §<条目号>）"指向条目正文；用户追问时再展开全文。

**排序**：① 证据强度（多指标交叉印证 > 单指标）→ ② 收益量级（区间大者在前，"需实测"殿后）→ ③ 叠加依赖（§5 表，被依赖方在前）。

**收益引用纪律**：标注区间均为**典型收益/实测参考**，不得表述为对本算子的预测；报告未采到的量（tiling data、shape、dtype、指令级构成、隔离测试 R 值）一律不推算；single-shot 时所有收益判定附"非稳态，需 warmup=10 / repeat=5 / median 复核"。

**「已排除的方向」小节**（必须输出，与建议项同等重要）——每条一行 `**不是 <类型>**：<数值证据> → <省掉的排查>`：

| 排除结论 | 数值依据 |
|---------|---------|
| 不是 memory-bound | 带宽利用率 < 30% 且计算单元高占用；或 `mte2_ratio ≈ 0.0001`（搬运完全隐藏） |
| 不是 scalar bound | `scalar_ratio < 0.1` |
| 不是负载不均 | 离散度 < 1.10 且无 tail block |
| 不是资源冲突 | 冲突各列全 0（**有效结论**，非数据缺失） |
| 不是真 MTE2 bound | MTE2 busy 高但带宽利用率 < 70%（matmul 族） |
| UB 不是瓶颈 | UB 带宽 ≫ GM 带宽 |

反向排除全不成立时写"无"。

## 1. 通用类（所有算子先判，正文在 references/advice/general.md）

| 条目 | 触发证据 | 排除条件（成立则不出） |
|------|---------|---------------------|
| §1.1 双缓冲 | 时间轴 MTE2/VECTOR 串行无交替；或 `mte2_ratio + vec_ratio ≈ 1` 且单侧均不高 | `mte2_ratio ≈ 0.0001`；时间轴已见交替 |
| §1.2 核数裁剪 | 各单元利用率均低 + 带宽利用率低 + `aicore_parallel_utilization` 偏低 + 元素量小 | Cube 类（核数由 L1 切分决定）；`A1/core_num` 已足够大 |
| §1.3 尾块处理 | 离散度 `max/min > 1.10` 或存在 tail block；`aicore_parallel_balance` 偏低 | 离散度 < 1.10 且无 tail；tail 绝对耗时占比极小 |
| §1.4 UB/TBuf 常驻复用 | `mte2_ratio` 高但带宽利用率不高（次数多而非量大）；或小参数被多 tile 反复读 | `mte2_ratio ≈ 0`；纯流式逐元素无跨迭代复用 |
| §1.5 DataCopy 优化 | 带宽利用率低但 `mte2/mte3_ratio` 不低；`mte2_wait_ratio > 0` 而冲突为 0 | 带宽利用率已 > 80%；搬运总量极小 |
| §1.6 Vector 计算效率 | `vec_ratio ≥ 65%` 且 `scalar_ratio` 非零；或 sfu 明显；多步链落地 GM 痕迹 | `vec_ratio > 80%` 且指令级确认超越函数主导；scalar 与 mte 次数均已低 |
| §1.7 Scalar 编码原则 | `scalar_ratio > 0.1`；或 `icache_miss_rate > 0.01` 伴高 scalar | `scalar_ratio < 0.1` |
| §1.8 SIMT 手段切换 | `simt_vf_ratio == vec_ratio` 且 `vf_ratio == 0` | `vf_ratio > 0`（改 §1.6） |

## 2. matmul 族（`aic_*` 有效、Cube 参与；pingpong 为基线。正文在 references/advice/matmul.md）

| 条目 | 触发证据 | 排除条件 |
|------|---------|---------|
| §2.1 pingpong 双缓冲（基线） | `aic_*` 各 pipe 时间片串行，Cube busy 低 | 已启用（时间片已见 PING/PONG 交替）→ 转 §2.5/§2.6 |
| §2.2 SWAT 调度 | `totalBlockCnt > aicNum` 数倍 + 离散度高/尾部薄片；或 B 侧流式 MTE2 带宽瓶颈 | `totalBlockCnt < aicNum`（走 §2.3） |
| §2.3 StreamK 调度 | `totalBlockCnt < aicNum` + K 长（≥2048） | K 短；MN 已够并行（走 §2.2）；**与 §2.4 互斥** |
| §2.4 A/B-Full-Load | **真** MTE2 bound：MTE2 busy 高**且**带宽利用率高；一侧矩阵 ≤ L1/2 且对侧循环 T ≥ 2 | **假** MTE2 bound（带宽利用率 < 70%）→ 走 §2.5；T=1；与 StreamK 互斥 |
| §2.5 小数据块合并载入 | **假** MTE2 bound：MTE2 busy 高但带宽利用率 < 70%（典型 50–70%）+ 存在 < 20 KB 重复小块搬运 | 带宽利用率已 > 80%；真 MTE2 bound（走 §2.4） |
| §2.6 MTE2 预加载 | pingpong 已开 + 各流水 busy 均 ≤ 70% + trace 中 PING↔PONG 有确定性 gap + `kL1TileNum ≥ 2` | 某流水 busy 明显高；`kL1TileNum < 2`。勿用缩减 kL1 替代 |

> 真/假 MTE2 bound 分界 = **带宽利用率**（口径须单块/Σ块核对一致）。**MC² 算子在 MTE2 污染排除前禁止据 `mte2_ratio` 推 §2.4/§2.5。**

## 3. MC² 通算融合族（matmul_all_reduce / allgather_matmul / *_grouped_matmul_* 等。正文在 references/advice/mc2.md）

**前置陷阱**：`CrossCoreWaitFlag` 挂 MTE2 等通信 → `mte2_ratio` 含通信空转，高值不得判 memory-bound、不得推 §2.4/§2.5（报告内无法排除，须隔离测试）。

| 条目 | 触发证据 | 排除条件 |
|------|---------|---------|
| §3.1 Local Matmul 分离（首选） | 算子属 MC² 融合类即可（**不依赖 bound 判定**） | Local 数据量极小 |
| §3.2 流水配平（长短块） | 通信计算串行或掩盖率 50–70% | 掩盖率已 > 85%；未先做 §3.1 |
| §3.3 叠加 matmul 族优化 | 隔离测试确认计算 bound（不能只凭报告 mte2_ratio） | 未完成隔离测试 |

## 4. conversion 族（Transpose / Concat / Split 等，选型判据而非调参。正文在 references/advice/conversion.md）

| 条目 | 触发证据 | 排除条件 |
|------|---------|---------|
| §4.1 策略选型 | 算子属 conversion 族；带宽利用率极低（逐元素）或 `mte3` 大量小 strided 搬运 | dtype/shape/perm 须用户提供，否则只指出"需重新选型" |
| §4.2 SMALL_SHAPE 向量化读写 | 已走 SMALL_SHAPE + 带宽利用率极低（基线 ~6.25%） | 末轴参与转置（改走 GATHER/VCONV） |
| §4.3 N_LAST 写出退化 | 已走 N_LAST + `mte3` 大量小 strided 搬运 | 写出已连续 |

## 5. 叠加顺序与冲突表（多条同时成立时定序；顺序错会让后一条判据失真）

| 关系 | 条目 |
|------|------|
| 必须先做 | §1.1 → §1.2；§2.1 pingpong → §2.2/§2.3/§2.4/§2.5/§2.6；§3.1 → §3.2；族优化 → §1.7 Scalar |
| 互斥 | §2.3 StreamK ⊥ §2.4 Full-Load |
| 易混二选一 | §2.4（真 MTE2 bound，带宽高）vs §2.5（假，< 70%） |
| 竞争同一资源 | §1.1 / §1.4 / §1.6 争 UB 预算；§2.1 / §2.4 / §2.5 争 L1 预算 |
| 正交可叠加 | §2.6 与 §2.2–§2.5；§3.3 与 §3.1/§3.2（但优先级最低） |
| 前置封锁 | MC² 族：MTE2 污染未排除前不得据 `mte2_ratio` 推 §2.4/§2.5 |
