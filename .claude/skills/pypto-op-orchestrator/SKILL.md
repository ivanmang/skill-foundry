---
name: pypto-op-orchestrator
description: PyPTO operator development and performance-tuning workflow entry. Triggers: generate/develop/implement a PyPTO operator, tune/optimize an existing PyPTO operator, or explicitly request the pypto-op-develop / pypto-op-tune workflows.
category: ops-dev
---

使用 workflow-orchestrator skill 启动对应工作流：

- 开发/生成算子：`workflows/pypto-op-develop.yaml`
- 性能调优：`workflows/pypto-op-tune.yaml`

安装态下 yaml 位于 `<工作区>/.cannbot/plugins/pypto-op-orchestrator/workflows/`；仓内开发态位于 `plugins-official/pypto-op-orchestrator/workflows/`。
