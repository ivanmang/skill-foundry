---
name: pypto-op-orchestrator
description: Use when developing or tuning a PyPTO operator — start the pypto-op-develop or pypto-op-tune workflow.
category: ops-dev
entry: true
license: CANN Open Software License Agreement Version 2.0
origin: cannbot
---

使用 workflow-orchestrator skill 启动对应工作流：

- 开发/生成算子：`workflows/pypto-op-develop.yaml`
- 性能调优：`workflows/pypto-op-tune.yaml`

安装态下 yaml 位于 `<工作区>/.cannbot/plugins/pypto-op-orchestrator/workflows/`；仓内开发态位于 `plugins-official/pypto-op-orchestrator/workflows/`。
