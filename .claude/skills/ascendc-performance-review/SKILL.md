---
name: ascendc-performance-review
description: Use when statically reviewing AscendC code for performance bad smells (no execution), or gathering static evidence for bottleneck analysis. Indexed PRC checklist.
category: perf-optimize
license: CANN Open Software License Agreement Version 2.0
origin: cannbot
maturity: ready
owner: cannbot
---

# AscendC 性能静态检视

只读检视：不修改代码、不运行 profiling、不派发子代理。检查点唯一真源是 [references/perf-review-checklist.md](references/perf-review-checklist.md)（索引）与 `references/perf-review-knowledge/`（知识卡，每卡含说明、错误写法、正确写法、识别方法、误报边界）。

## 检视纪律

1. 先读索引，得到全部检查点 ID 与适用范围；只排查 `status=ready` 且适用范围命中当前算子的检查点；不得自拟检查点。
2. 每个命中检查点**完整读取**其知识卡后再排查源码；卡片的误报边界（含证伪知识）与命中条件同等重要，报出前逐条核对。
3. 每条 finding 必须引用检查点 ID + 文件/行号 + 证据形态（按卡片要求）。
4. 结论依赖 `#if` 架构宏取值的，一律先按 PRC-ARCH-001 的打表命令取证目标 SoC 的宏取值，禁止从宏名反推平台。
5. 平台参数（核数/UB/L2）先看代码怎么取的、是否真正参与切分表达式，再谈数值（PRC-ARCH-002）；环境取不到真实数值时注明"不可得"，不据此标 blocker。
6. arch22（A2/A3）目标先读 [arch22 适用性矩阵](skill:ascendc-performance-best-practices) `reference/common/arch22/perf_review_applicability.md`（`skill:` 指向 external cannbot-skills 域 skill，经 `npx skills add` 装配；未装配时 arch22 MM/FA 专项卡片不可加载），按矩阵加载通用卡片，再加载 `PRC-MM-*`/`PRC-FA-*` 专项；A5 目标不得加载 arch22 专项卡片。A2/A3 共用同一套实现，验证结论可互换；保留实际测试型号与证据引用。

## 交付

findings 列表：每条含检查点 ID、位置（文件/行）、证据、预期影响、修复方向。静态检视结论是**假设级证据**——预期影响需经实测确认，不作为性能结论。

## See also

- [npu-loop-patterns](skill:npu-loop-patterns) — the measured anti-pattern catalog (A5/A6) behind this checklist.
