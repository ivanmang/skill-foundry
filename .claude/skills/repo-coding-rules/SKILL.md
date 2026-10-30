---
name: repo-coding-rules
description: CANN Bench candidate-operator implementation authenticity, wrapper boundaries, project interfaces, and Ascend C code-quality requirements. Use when coding, fixing, or reviewing.
category: repo-ops
license: CANN Open Software License Agreement Version 2.0
origin: cannbot
---

# 仓库编码规则

算子计算必须来自本工程的真实 NPU kernel，并符合 CANN Bench 的提交与运行接口。读取 [编码检查表](references/red-lines.md)，按实际代码和证据检视；不要把静态规则套到测试 golden 上，也不把样例结构当作所有算子都适用的算法方案。

违规项给出位置、影响和修正要求。规则只定义代码与交付质量，不持有调度状态、不指定流程回退。
