# MC² 通算融合族条目正文（§3.1–§3.3）

> 由 [optimization-advice.md](../optimization-advice.md) 索引命中后读取。前置：算子为通算融合类（`matmul_all_reduce` / `allgather_matmul` / `matmul_reducescatter` / `alltoall_matmul` / `*_grouped_matmul_*` 等，fork 多 rank + CrossCore 同步）。纯通信算子（无计算融合）不属本族。

**本族的判定陷阱（必须先声明）**：`CrossCoreWaitFlag` 挂在 MTE2 流水线上等待通信，会使 `mte2_ratio` 含通信等待空转。因此本族高 `mte2_ratio` **不得**直接判 memory-bound，也**不得**据此推 matmul 族 §2.4 / §2.5——报告内无法排除该污染，须隔离测试对比纯计算口径的 `mte2_ratio`。

## 3.1 Local 数据与通信未重叠 → Local Matmul 分离（首选）

- **证据**：算子为 MC² 融合类即可。**本条不依赖 bound 判定**——这也是它作为首选的原因：即使报告因 MTE2 污染无法定 bound，这条依然可以推进
- **方向**：本 rank 自身数据（Local 数据，无需通信）的 matmul 从通信块循环里分离出来，前置或后置独立执行，与首次通信重叠。前置形态：AIC 先算全量 M 的 Local matmul，再等通信 flag 逐块算；后置形态：先算远程块，最后算 Local。Local matmul 用独立的 tiling data（以全量 M 为计算规模），与通算切分块的长/短块 tiling 互不相干
- **收益**：需实测；收益上限约等于首次通信的耗时（被 Local 计算掩盖掉的部分）
- **代价与前置检查**：需要一份独立 tiling data 与额外的执行段；须确认算子的融合模式以决定前置还是后置——通信→计算类（如 TP 权重聚合 `allgather_matmul`、EP 专家分发 `alltoallv_grouped_matmul`）用前置，计算→通信类（如 TP 输出分发 `matmul_reducescatter`、全局归约 `matmul_all_reduce`、EP 反向分发 `grouped_matmul_alltoallv`）用后置
- **排除条件**：Local 数据量极小（可掩盖的通信时间有限）
- **如何验证见效**：看首次通信段是否被计算覆盖、总耗时下降幅度是否接近 Local matmul 的独立耗时

## 3.2 通算掩盖率不足 → 流水配平（长短块排布）

- **证据**：通信与计算呈串行或掩盖不充分；均匀切分下掩盖率处于 50%–70% 区间
- **方向**：由"均匀切分 + 通信计算串行"改为"长短块配平 + AIC/AIV 分离流水掩盖"。AIV 负责通信并用 CrossCore 事件通知 AIC 数据就绪，AIC 算完回通知 AIV；按结果矩阵行（M）切块，相邻块的通信与计算重叠。长短块排布按 bound 类型确定，最优切分（如 longMSize）必须靠**TilingData 驱动的系统搜索**（多条剪枝 + Top-N 候选实测）确定，**不用经验值**
- **收益**：通算掩盖率由 50%–70% 提升至 85%+
- **代价与前置检查**：**强前置**——实施前须先打印 TilingData（`baseM` / `baseN` / `usedCoreNum`）并执行隔离测试获取 R 值；这两项报告都不可见，缺失时本条只能作为方向提出，不能给具体切分建议。应在 §3.1 之上叠加，而非替代
- **排除条件**：掩盖率已 > 85%（配平空间有限）；未做 §3.1（先做 Local Matmul，它不依赖 bound 判定且实施更简单）
- **如何验证见效**：掩盖率（计算与通信重叠时长 / 总时长）上升；跨 rank 对比时**看 max 而非均值**——多卡协同性能由最慢 rank 决定（木桶效应）

## 3.3 计算 Bound 时叠加 matmul 族优化（最低优先级）

- **证据**：隔离测试已确认为计算 Bound（**不能只凭报告 `mte2_ratio` 推断**，见本文件开头的污染说明）
- **方向**：提升单块 matmul 自身效率，即套用 matmul 族各条（pingpong / SWAT / StreamK / Full-Load 等，见 [matmul.md](matmul.md)）
- **代价与前置检查**：与 §3.1 / §3.2 正交可叠加，但优先级最低——通算融合算子的主要收益通常在通信与计算的重叠上，而非单块计算效率
- **排除条件**：未完成隔离测试（bound 类型未定，贸然优化计算侧可能完全无效）
- **如何验证见效**：单块 matmul 耗时下降，且总耗时同步下降（若总耗时不动，说明计算已被通信掩盖，本方向无收益）
