---
name: ascendc-doc-gen
description: |
  生成华为 CANN AscendC API 参考文档。用于 AscendC API 文档生成、芯片与产品支持分析、函数原型/参数/约束提取，以及从 C++ 头文件生成完整 API 参考文档。
  按外部编排流程执行：外部预处理 -> chipdiff -> extract -> generate -> review -> 外部最终合成。skill 只执行四个 LLM 阶段，不检测接口，不运行预处理或后处理脚本。
metadata:
  author: tzh
  category: doc-generation
---

# AscendC API 文档生成

## 职责边界

处理一个已经完成外部预处理的 AscendC API 文档族，依次生成芯片差异报告、信息提取报告、文档底稿和审阅后底稿。

- 接口检测、接口选择、文档族归并和 `0_*` 产物生成由外部预处理完成。
- skill 不运行 `tools/ascendc-preprocess.mjs`、`tools/ascendc-finalize.mjs` 或底层提取脚本。
- skill 以 `4_review.md` 为终点；带时间戳的最终文档由外部后处理生成。
- 详细分析方法、输出结构和格式规则以对应 `tasks/*.md` 为唯一准则，`SKILL.md` 不重复阶段细则。

## 启动条件

开始四阶段流程前，确定技能根目录、代码库根目录、目标 API 名和 `./outputs/{API名}/`。

技能启动时只读取一次：

- `references/terminology_dict.yml`
- `references/ascend_950_npu_architecture.md`

架构参考仅用于理解和规范昇腾950相关术语，不得作为产品支持、函数原型、参数约束、数据类型或 API 行为的事实证据。

确认输出目录包含以下必需预处理产物：

- `0_prototype.md`
- `0_cross_dir.md`
- `0_semantic_links.json`
- `0_call_example.md`
- `0_preprocess_manifest.json`

缺少任一必需文件时，停止执行并报告缺失文件，不得在 skill 内补跑脚本。若存在 `0_isa_reference.md`，extract 阶段按 `tasks/extract.md` 的证据规则读取。

## 文档边界

首先读取 `0_preprocess_manifest.json`，并在全部阶段保持同一 identity：

- `documentApiName`：最终文档名称。
- `memberApis`：允许进入当前文档的公开接口闭集。
- `callingConvention`：当前文档唯一允许的调用约定。
- `sourceFiles`：预处理确定的源码范围。

不得遗漏 `memberApis` 成员，也不得混入成员闭集之外、其它调用约定或其它源码 identity 的接口。函数名、参数名和文件名相似不能改变 manifest 边界。

## 四阶段流程

严格串行执行。每个阶段开始前必须完整读取对应 task 文件，再读取 task 列出的输入与参考文件，并按 task 定义的结构写入指定产物。

| 阶段 | 必须先读 | 上游核心输入 | 输出 |
|---|---|---|---|
| chipdiff | `tasks/chipdiff.md` | `0_preprocess_manifest.json`、`0_cross_dir.md`、源码 | `1_chipdiff.md` |
| extract | `tasks/extract.md` | `1_chipdiff.md`、全部必需 `0_*` 产物、源码 | `2_extract.md` |
| generate | `tasks/generate.md` | `1_chipdiff.md`、`2_extract.md`、原型与 manifest | `3_generate.md` |
| review | `tasks/review.md` | `1_chipdiff.md`、`2_extract.md`、`3_generate.md`、原型与 manifest | `4_review.md` |

不得跳过阶段、合并阶段输出或自创章节结构。上游必需文件缺失时停止当前阶段。

## 跨阶段约束

- **证据优先**：先读取代码和预处理产物，再形成结论。名称相似、参数名直译、文件位置和模型常识不能单独证明用户语义。
- **源码范围**：以 `0_cross_dir.md` 和 task 规则确定读取范围；需要精确旁路追踪时，遵循 `tasks/extract.md`，禁止宽泛扫描和无证据类比。
- **阶段分层**：`1_chipdiff.md`、`2_extract.md` 保留代码证据和代码分析清单；`3_generate.md`、`4_review.md` 只保留面向用户的技术结论，不暴露本地路径、内部 intrinsic/helper 或生成过程。
- **事实缺口**：缺少证据或证据冲突时，严格使用 task 文件定义的标记口径，不得臆测补齐。
- **输出纯净**：只输出 task 要求的报告或文档正文，不附加思考过程、自我说明、阶段总结或无关内容。
- **格式归属**：固定 7 个产品项、Markdown 表格、空章节格式、函数原型、参数与约束、调用示例等最终格式只以 `tasks/generate.md` 和 `tasks/review.md` 为准。

## 批量执行

- **单个 API**：直接由当前 agent 串行执行 chipdiff、extract、generate、review 四个阶段，不得启动 subagent 或 worker。
- **多个 API**：仅当同一次请求明确包含两个或以上 API 文档族时，才为每个 API 使用独立的 `./outputs/{API名}/` 目录和独立 worker；上一个 API 完成后再处理下一个。父任务只负责调度、等待和汇总，不在同一上下文展开多个 API 的源码分析。
- 多 API 场景下环境不支持独立 worker 时，先告知用户并取得确认后再退化为普通串行执行；不得把该降级规则应用于单个 API。

## 资源索引

- `tasks/chipdiff.md`：芯片与产品差异分析规则。
- `tasks/extract.md`：源码证据、参数语义和约束提取规则。
- `tasks/generate.md`：最终文档结构、内容与格式规则。
- `tasks/review.md`：逐项校验和修正规则。
- `references/chip_mapping.md`：代码芯片标识到固定产品项的映射。
- `references/common_terminology.yml`：最终审阅术语规范。
- `references/terminology_dict.yml`：技能启动时读取的术语字典。
- `references/ascend_950_npu_architecture.md`：技能启动时读取的架构背景知识。