# matmul 族条目正文（§2.1–§2.6，含量化与 batch 变体）

> 由 [optimization-advice.md](../optimization-advice.md) 索引命中后读取。前置：算子为 matmul 族（`matmul` / `matmul_mxfp4` / `matmul_a16w16` / `batch_matmul` 等，`aic_*` 列有效、Cube 参与）。**pingpong 是本族基线**，其余优化默认以其已启用为前提。

## 2.1 Cube 与搬运串行 → pingpong 双缓冲（基线）

- **证据**：`aic_*` 各 pipe（MTE2 / MTE1 / Fixpipe / Cube）时间片串行，Cube busy 低；GM→L1→L0→CUBE→L0C→GM 逐步等待
- **方向**：L1 与 L0 双缓冲，搬运与 Cube 计算流水化，用 MTE2 / MTE1 / Fixpipe 三级事件同步串起来。`L1_BUFFER_NUM` 取满足 L1 预算的最大整数
- **收益**：case 总时间缩短至原来的 50%–60%
- **代价与前置检查**：L1/L0 占用按缓冲数倍增，须核算 L1 预算；这是其他 matmul 优化的前置，未开时先开这个
- **排除条件**：已启用 pingpong（时间片已见 PING/PONG 交替）→ 转 §2.5 / §2.6
- **如何验证见效**：Cube busy 上升、各 pipe 时间片出现交替

## 2.2 MN 够并行但尾碎片不均 → SWAT 调度

- **证据**：`totalBlockCnt > aicNum` 数倍（MN 够并行）+ 逐 block 离散度高，尾部明显薄片；或 B 侧流式加载下 MTE2 带宽成为瓶颈
- **方向**：三个互相独立的机制按需组合——① Serpentine 行窗口遍历，改变全局遍历顺序让 B 侧片段在窗口内复用，缓解流式带宽压力；② 尾部基块合并，把 `M % baseM` / `N % baseN` 的边缘薄片与相邻块重排，避免薄片"省算"收益被同窗口满块的关键路径吃掉；③ 末轮二维再切分，把 `totalCnt` 不整除 `aicNum` 时最后一轮的空闲核填上。三者共用同一行窗口高度常量，保持 host tiling / scheduler / kernel 三层切分边界对齐
- **收益**：需实测；收益来源是 Cube 算力利用率与末轮空闲核的回收
- **代价与前置检查**：调度逻辑复杂度显著上升，三层边界必须对齐；分 A 侧是否常驻 L1 两种子模式（都流式 / A 常驻只流式 B），后者机制 ③ 被简化。需要 `baseM/baseN/aicNum/mCnt/nCnt`，报告不可见 → 须用户提供 tiling data
- **排除条件**：`totalBlockCnt < aicNum`（MN 欠并行，走 §2.3 而非 SWAT）；末轮 tile 数很少或 `baseM/baseN` 已接近 Cube 粒度下限时，机制 ③ 因子块太小、Cube 启动开销反超而失效
- **如何验证见效**：逐 block 离散度下降、末轮空闲核减少、Cube busy 上升

## 2.3 MN 欠并行 + 长 K → StreamK 调度

- **证据**：`totalBlockCnt < aicNum`（大量核无原 tile 可分，kernel 被少数核的 K 向串行拖住）+ K 较长（≥ 2048）；或 `baseM/baseN` 已到 Cube 粒度下限的 MN 不整除情形
- **方向**：把空闲核拉去参与 K 维累加，再用一块 workspace 做跨核 K 归约（由 AIV 完成归约）。两个子模式由 host tiling 按 shape 自动选：**SK**——`mCnt·nCnt ≤ aicNum/2` 且 K 足够长（FP16 下 ≥ 4096 列）时，所有 MN 块都切 K，`kCnt = aicNum / (mCnt·nCnt)`；**DP+SK**——`mCnt·nCnt ≥ aicNum`、不整除、余数 ≤ `aicNum/2` 且 K 更长（FP16 下 ≥ 8192）时，稳态轮走 DP 不切 K，只对最后一整轮的 tail tile 切 K
- **收益**：原本少数核的活拆成 `核数 × K 切分数` 份，接近满核利用率（举例：`M=N=512, K=16384, baseM=baseN=256` 时 `mCnt·nCnt = 4`，24 核只有 4 个在工作，切 K 后可填满）
- **代价与前置检查**：需要 workspace 与跨核归约，引入 AIV 侧归约开销与额外 GM 往返；K 不够长时归约开销吃掉收益。需 `mCnt/nCnt/aicNum/K/dtype`，报告不可见 → 须用户提供
- **排除条件**：K 短（归约开销占比过大）；`totalBlockCnt > aicNum` 数倍（MN 已够并行，走 §2.2）；**与 A/B-Full-Load 互斥**（§2.4 不能与本条叠加）
- **如何验证见效**：参与计算的核数上升、Cube busy 上升、总耗时下降（归约段耗时应显著小于回收的空闲核收益）

## 2.4 真 MTE2 bound + 有小侧矩阵 → A/B-Full-Load

- **证据**：**真** MTE2 bound（MTE2 busy 高**且**带宽利用率高）+ 一侧矩阵较小（`≤ L1/2`）+ 对侧循环次数 `T ≥ 2`
- **方向**：把小侧矩阵（A 或 B，含随路 Scale）从"每轮流式搬入"改为"一次性驻留 L1"，消除它在对侧循环中的重复 GM→L1 搬运。等效把 MTE2 总字节压缩 `(T-1)/T`
- **收益**：`T = 5` 时 MTE2 总字节降约 16%–20%，Task 总时间降 5%–15%（实测参考：MXFP4 `M=128, K=4096, N=81920` 由 183.87 μs → 170.07 μs，约 −7.5%）
- **代价与前置检查**：小侧矩阵长期占据 L1，压缩对侧与 pingpong 的 L1 预算，须整体核算 `baseM × K × dtype ≤ L1/2` 是否成立
- **排除条件**：**假** MTE2 bound（MTE2 busy 高但带宽利用率 < 70%）→ 走 §2.5，这是本族最易混淆的一对；`T = 1`（无重复搬运可消）；**与 StreamK 互斥**。可与 SWAT 各机制、pingpong、§2.5 叠加
- **如何验证见效**：MTE2 总字节数与 MTE2 段耗时同时下降（只降耗时不降字节说明改的不是这个问题）

## 2.5 假 MTE2 bound（小块搬运）→ 小数据块合并载入

- **证据**：MTE2 busy 高**但带宽利用率 < 70%**（典型 50%–70%）+ 存在单次 < 20 KB 的 scale / bias / 小 LUT / 少量常量张量搬运
- **方向**：把 K 方向上被 `baseK`/`kL1` 切碎的多片小数据合并成一次大搬运（合并若干个 `kL1` 的 scale 一次性载入）。适用面不限于 scale——任何被反复从 GM 搬进 L1、单次量显著小于 20 KB、且 K 方向"内容相邻 + 读模式一致"的侧输入都适用
- **收益**：MTE2 带宽利用率由 50%–70% 拉回 80%+，同时削减等价指令条数与 MTE2 段气泡
- **物理根因（判据依据）**：MTE2 发起一次 GM→L1 搬运有固定头开销（地址建立、Burst 描述符、DMA 通道配置）。单次约 20 KB 时头开销被摊薄到 < 5%；低于 20 KB 则头开销占比拉高，表现为 cycles/byte 远高于 HBM 理论峰值
- **代价与前置检查**：合并后的 scale 占用 L1 增大（按合并倍数），须与 pingpong / Full-Load 联合核算 L1 预算
- **排除条件**：带宽利用率已 > 80%（搬运已高效）；无 < 20 KB 的重复小块搬运；真 MTE2 bound（带宽已打满）→ 走 §2.4
- **如何验证见效**：MTE2 带宽利用率升到 80%+ 且 MTE2 段耗时下降；MTE2 总字节数基本不变（这条优化改的是"怎么搬"而非"搬多少"，字节数大幅变化说明改错了对象）

## 2.6 准无 bound + PING/PONG 存在 gap → MTE2 预加载

- **证据**：pingpong 已开 + 各流水 busy 均 ≤ 70%（"准无 bound"形态，既非 MTE2 带宽 bound 也非 Cube bound）+ trace 中 `MTE2_PONG` 事件起点远晚于理论起点（≈ `MTE2_PING` 终点），PING↔PONG 间存在确定性 gap + `kL1TileNum ≥ 2`
- **方向**：首轮一次性预加载两份 A/B tile 到 L1，让 `MTE2_PONG` 提前发射，绕开芯片指令队列深度上限导致的被动等待。主循环改造为「段 1 首轮 PING / 段 2 预取 PONG / 段 3 消费」三段结构
- **收益**：Task 时间 −3%–10%，MTE2 段降幅更明显（实测参考：BF16 `M=1024, K=4096, N=2048` 由 66.0 μs → 63.3 μs 约 −4%；MTE2 段 37.6 μs → 32.7 μs 约 −13%）
- **代价与前置检查**：**零 TilingData 数值改动**（`baseM/baseN/baseK`、`stepK`、`kL1`、`nBufferNum` 等全保持原值），只改 Kernel 主循环的 MTE2 发射时序，风险低；但需要 trace 级别的 PING/PONG 事件时间才能确认 gap
- **排除条件**：某条流水 busy 明显高（有真 bound，先解决 bound）；`kL1TileNum < 2`（无第二份 tile 可预取）。**不要用"继续缩减 kL1"替代本条**：缩减 kL1 虽能减少 PING/PONG 间插入的指令数从而化解阻塞，但单次覆盖 K 减少 → 外层循环次数上升 → 循环起停开销上升、Cube busy 下降，净收益为负
- **叠加**：与 SWAT / Full-Load / StreamK / 小数据块合并载入**正交**，可任意叠加（叠加后仍须满足各层 L1 预算）
- **如何验证见效**：trace 中 PING↔PONG 的 gap 消失或显著收窄，MTE2 段耗时下降
