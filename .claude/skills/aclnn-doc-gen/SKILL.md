---
name: aclnn-doc-gen
description: Generate Huawei CANN ACLNN operator API reference documentation. Use when asked to: generate ACLNN operator docs; analyze chip/product support differences; extract operator info (parameters, constraints, formulas); compare related interfaces (V1 vs V2, WeightNz variants); or understand an operator's function/params/constraints from its source directory. Follows the external orchestration flow (preprocess -> extract+compare in parallel -> formula+generate_skeleton in parallel -> review).
  生成华为 CANN ACLNN 算子 API 参考文档。当用户提到以下场景时必须使用此技能：
  - 生成 ACLNN 算子文档、生成 aclnn 文档、生成算子文档、写算子API文档
  - 分析 CANN 算子的芯片/产品差异、芯片差异分析、产品支持情况
  - 提取算子信息（参数、约束、公式）、提取算子信息、分析算子参数
  - 对比相关算子接口（V1 vs V2、WeightNz 变体）、接口对比
  - 生成公式分析报告、算子公式生成、推导算子计算公式
  - 用户提供算子目录路径，要求生成该算子的完整 API 参考文档
  - 用户提到 aclnn、ACLNN、CANN 算子相关文档任务
  - 用户给了一个算子代码目录，想了解该算子的功能、参数、约束
  即使只是问"这个算子支持哪些芯片"或"帮我分析这个算子的约束"，也应使用此技能。
  按外部编排流水线执行：外部预处理 → 阶段1 extract 与阶段2 compare 必须并行启动 → 阶段3 formula 与阶段4 generate_skeleton 必须并行启动 → 阶段5 review patch → 外部合成最终文档。skill 只执行 LLM 分析阶段，不运行预处理脚本，不执行最终拼接脚本。禁止使用旧流程：不得输出“阶段2+3 formula 和 compare 并行”，不得输出“阶段4 generate 文档生成”。
version: 1.0.0
metadata:
  author: tzh
  category: doc-generation
category: doc-gen
license: CANN Open Software License Agreement Version 2.0
origin: cannbot
---

# ACLNN 文档生成技能

> **强制执行计划，必须优先遵守**：不要使用历史的五阶段串行模板。当前唯一允许的 LLM 阶段计划是：
> - 阶段 1：extract，写入 `1_extract.md`。
> - 阶段 2：compare，写入 `2_compare.md`，必须与阶段 1 extract 并行启动，不得等待 `1_extract.md`。
> - 阶段 3：formula，写入 `3_formula.md`，必须在阶段 1 extract 完成后与阶段 4 generate_skeleton 并行启动。
> - 阶段 4：generate_skeleton，写入 `4_generate_skeleton.md`，不是 generate，不生成完整文档；必须与阶段 3 formula 并行启动。
> - 阶段 5：review patch，写入 `5_review_patch.json`，不输出完整文档。
> 禁止输出“阶段2+3：formula 和 compare 并行执行”，禁止输出“阶段4：generate（文档生成）”，禁止把并行阶段改为串行。

## 概述

生成华为 CANN ACLNN 算子 API 参考文档。skill 只负责 LLM 分析阶段；预处理产物准备、函数原型拼接、公式块拼接、第二段执行接口固定章节拼接、4_generate.md 合成、review 补丁应用、调用示例拼接、空格规范化和最终文档写入由外部程序执行。

> **路径基准说明**：本文件（SKILL.md）所在目录即为**技能根目录**。下文所有 `references/`、`config/`、`tasks/`、`tools/` 路径均以技能根目录为基准，**与用户提供的算子目录和项目根目录无关**。执行任何读文件操作前，必须先确定 SKILL.md 的绝对路径，并以此推算技能根目录的绝对路径，再拼出目标文件的完整路径。例如，若 SKILL.md 位于 `C:\Users\foo\.config\opencode\skills\aclnn-doc-gen\SKILL.md`，则 `references/quantization_introduction.md` 的完整路径为 `C:\Users\foo\.config\opencode\skills\aclnn-doc-gen\references\quantization_introduction.md`。

### 执行步骤

1. **加载领域知识** — 按顺序读取以下参考文件，**所有步骤之前执行，每次会话只读一次**（路径相对于技能根目录）：
   - `references/quantization_introduction.md` — 量化概念（pertensor/perchannel/pergroup 等模式、组合量化、静态/动态量化），在算子代码中大量出现，不理解会导致误解参数语义和约束逻辑
   - `references/数据类型.md` — ACL 数据类型与文档简写形式的对照表，参数 dtype 描述必须使用表中简写形式
   - `references/broadcast关系.md` — 广播规则与限制，理解参数间 broadcast 约束的基础
   - `references/sparse_mode参数说明.md` — sparseMode 各取值的语义、mask 矩阵形态及适用场景，涉及 sparseMode 参数时必须参考
   - `references/chip_mapping.md` — 芯片/产品映射规则说明、匹配优先级、最终产品输出规范；用于解释如何匹配，不作为用户可编辑的生效映射表
   - `references/terminology_dict.yml` — 术语字典，统一 API 文档中的中文术语、英文缩写、参数描述和约束表述；后续所有阶段都应遵循
   - `config/error_codes.yml` — ACLNN 文档允许输出的错误码数值映射；不存在时使用默认 4 个
   - `config/product_mapping.yml` — 当前生效的产品型号映射表，已包含默认映射；用户可直接修改或新增。与 `chip_mapping.md` 默认表冲突时，以该 YAML 为准
2. **检测算子目录与接口** — 若用户已明确指定接口名，跳过接口检测。若未指定接口名，应由外部程序完成接口检测和选择；skill 内不运行检测脚本。
3. **确定路径变量** — 确定技能根目录、算子目录、项目根目录、目标接口名和输出目录 `{算子目录}/outputs/{目标接口名}/`。目标接口名使用完整 ACLNN 执行接口名，例如 `aclnnGroupedMatmulV5`；若输入是 `GetWorkspaceSize` 接口，规范化为对应执行接口名。
4. **检查外部预处理产物** — skill 不运行预处理脚本，只检查外部程序已生成的文件。至少应存在：
   - `0_extract_plan.json` — extract 预分析计划，推荐读取路径、函数和批量工具调用路线
   - `0_prototype.md` — 函数原型
   - `0_cross_dir.md` — 跨目录引用追踪
   - `0_chip_evidence.md` — 芯片证据
   - `0_error_codes.md` — 错误码证据
   - `0_call_example.md` — 调用示例，供外部最终合成使用

   若缺少必需预处理产物，停止对应阶段并报告缺失文件；不要在 skill 内临时运行预处理脚本。
5. **执行 LLM 阶段** — 必须按外部编排步骤执行，阶段产物都写入输出目录。注意：`1_extract.md`、`2_compare.md`、`3_formula.md`、`4_generate_skeleton.md`、`5_review_patch.json` 中的数字只是兼容既有产物命名，不代表执行顺序。并行阶段是强制要求，不是优化建议；不得为了简化执行而改为串行。

   **步骤 A：extract 与 compare 必须并行启动**

   - extract：读取 `tasks/extract.md`、`0_extract_plan.json`、`0_cross_dir.md`、`0_chip_evidence.md`、`0_error_codes.md`，写入 `1_extract.md`
   - compare：读取 `tasks/compare.md`、`0_prototype.md`、`0_cross_dir.md`，探索关联接口代码，写入 `2_compare.md`

   **步骤 B：formula 与 generate_skeleton 必须并行启动**

   等待 extract 完成后，formula 与 generate_skeleton 必须并行启动；generate_skeleton 同时要求 compare 已完成。不得先完成 formula 再启动 generate_skeleton，也不得先完成 generate_skeleton 再启动 formula。若 `3_formula.md` 与 `4_generate_skeleton.md` 已存在且非空，步骤 B 必须直接视为完成，禁止再次启动 formula 或 generate_skeleton；若只缺失其中一个产物，只启动缺失阶段。

   - formula：读取 `tasks/formula.md`、`1_extract.md`，生成公式块和变量映射，写入 `3_formula.md`
   - generate_skeleton：读取 `tasks/generate_skeleton.md`、`1_extract.md`、`2_compare.md`、`0_prototype.md`，生成不含公式正文、函数原型正文和第二段执行接口固定章节的文档骨架，写入 `4_generate_skeleton.md`

   **步骤 C：review patch 校验**

   等待 formula 与 generate_skeleton 都完成。读取 `tasks/review.md`，并将 `1_extract.md`、`2_compare.md`、`3_formula.md`、`4_generate_skeleton.md`、`0_prototype.md` 作为可按需读取的证据源；禁止默认全文读取这些上游产物。review 初始只读取完成校验所需的最小片段：`4_generate_skeleton.md` 的标题结构和目标章节、`0_prototype.md` 的目标接口原型片段、`3_formula.md` 的 `## 最终文档公式块`、`1_extract.md` 的 `## 文档生成语义基准`。仅在证据不足、索引冲突或需要构造唯一 `oldText` 时，才补读对应文件的最小相关片段。只输出分离补丁 `5_review_patch.json`。

6. **外部最终合成** — skill 到 `5_review_patch.json` 为止。外部程序负责将 `0_prototype.md` 的函数原型、`3_formula.md` 的最终公式块和第二段执行接口固定章节拼入 `4_generate_skeleton.md`，合成 `4_generate.md`，应用 `5_review_patch.json`，合成 `5_review.md`，追加 `0_call_example.md`，执行空格规范化，并写入 `{目标接口名}_YYYYMMDDHHMM.md`。
7. **最终输出** — skill 向用户报告本次已生成的阶段产物路径，以及仍需外部程序完成的合成步骤；不要宣称已生成最终交付物，除非外部程序已经完成最终合成。

**核心原则**：先搜索，后推理；按优先级提取；记录证据来源；通过文件传递阶段产出；skill 不执行外部预处理和最终拼接。

---

## 接口选择

**若用户在请求中已明确指定接口名（如"为 aclnnXxx 生成文档"），直接使用该接口名。**

若未指定接口名，skill 不运行接口检测脚本；应由外部程序先完成接口检测和选择，再把目标接口名传给 skill。接口选择规则：

- **多个算子目录**：列出目录供用户选择（可多选），每个选中算子独立执行后续流程；只有一个目录时直接使用
- **多个接口**：列出接口名供用户选择（可多选），每个选中接口独立生成一份文档；只有一个接口时直接使用

---

## 外部编排流水线

### 阶段间数据流

```text
外部预处理
  ├─ 0_extract_plan.json
  ├─ 0_prototype.md
  ├─ 0_cross_dir.md
  ├─ 0_chip_evidence.md
  ├─ 0_error_codes.md
  └─ 0_call_example.md
        │
        ├──────────────┬──────────────┐
        │              │              │
        ▼              ▼              │
   1_extract.md   2_compare.md        │
        │              │              │
        ├──────┬───────┘              │
        │      │                      │
        ▼      ▼                      │
  3_formula.md 4_generate_skeleton.md │
        │      │                      │
        └──────┴──────────┐           │
                          ▼           │
                  5_review_patch.json │
                          │           │
                          ▼           ▼
                 外部合成 4_generate.md
                 外部合成 5_review.md
                 外部拼接调用示例并生成最终文档
```

### 跨阶段公共规则

**任务描述读取**：每个阶段执行前必须读取对应 `tasks/*.md`。阶段输出格式由任务文件定义，不能凭记忆复现。

**外部产物优先**：预处理产物已经包含函数原型、跨目录引用、芯片证据、错误码、调用示例和 extract 计划。阶段开始时先读取这些文件；缺失时报告外部预处理未完成，不在 skill 内补跑脚本。函数原型正文以 `0_prototype.md` 为唯一来源，模型只能用它对齐参数表，不得自行生成或修改函数原型。

`0_extract_plan.json` 只作为读取路线图和加速索引，不是证据全集：
- 不能替代 `0_cross_dir.md`、`0_chip_evidence.md`、`0_error_codes.md`。
- 不得只根据 extract plan 输出产品支持、芯片差异、参数约束或错误码结论。
- 当 plan 信息不足、结论无法闭环或其他预处理产物提示额外命中时，按需补读对应片段和必要源码上下文。
- 补读目标是补齐证据闭环，不要求默认读完整预处理产物全文。

**extract 语义基准**：`1_extract.md` 必须输出 `## 文档生成语义基准`。formula 和 generate_skeleton 都以该节作为参数描述、公式变量和变量映射的共同基准，确保并行生成后仍能对齐。generate_skeleton 和 review 阶段禁止读取源码；若 `1_extract.md` 信息不足，只能保守标注 `<span style="color:#dc2626;">【需用户补齐】</span>`、输出 issue 或失败，不得回源码补证。

**芯片标识替换**：输出面向外部用户，内部芯片标识必须转换为固定 6 个对外产品型号。`references/chip_mapping.md` 只说明匹配规则和默认表；实际映射以 `config/product_mapping.yml` 为准。若 YAML 中缺少某项，可参考 `chip_mapping.md` 的默认规则理解；最终文档允许出现的产品型号白名单固定，不允许通过配置新增。不得泄漏代码层面的芯片/架构标识。

**错误码范围**：ACLNN 文档只输出 `ACLNN_ERR_PARAM_NULLPTR`、`ACLNN_ERR_PARAM_INVALID`、`ACLNN_ERR_INNER_INFERSHAPE_ERROR`、`ACLNN_ERR_INNER_TILING_ERROR` 这 4 个错误码；数值码从 `config/error_codes.yml` 读取，文件不存在或非法时使用默认值。

**跨目录引用追踪**：代码分析前读取 `0_cross_dir.md`，追踪到的外部文件与本算子目录内文件同等对待。

**代码分析清单**：仅 extract、compare、formula 这三类分析报告允许在末尾附 `## 代码分析清单`。`4_generate_skeleton.md` 是对外文档骨架，严禁输出 `## 代码分析清单`、源码路径、分析原因或任何分析痕迹。

**失败标志文件**：阶段无法产出有效结果时写入 `{N}_{阶段名}_FAILED.md`，不写不完整的正常产物。下游阶段发现依赖缺失且存在 `_FAILED.md` 时立即停止。

**阶段幂等与防重复执行（强制）**：每个 LLM 阶段启动前必须先检查对应目标产物是否已经存在且非空。若目标产物已经存在，且不存在同阶段 `_FAILED.md`，该阶段必须直接判定为已完成，禁止再次启动 task、禁止覆盖已有产物，除非用户明确要求“重新生成/覆盖”。同一会话内某阶段 task 已返回成功后，必须记录为 completed；后续推理再次进入该步骤时只能复用已有产物，不得重新执行。

**并行阶段幂等规则（强制）**：步骤 A 和步骤 B 的“必须并行启动”只适用于两个目标产物都未成功生成的首次执行。若并行组中某个产物已存在且非空，只启动缺失的阶段；若两个产物都已存在且非空，整个并行组直接视为完成。尤其是 `3_formula.md` 与 `4_generate_skeleton.md` 均已存在时，步骤 B 禁止再次启动 formula 或 generate_skeleton。

**子任务 prompt 最小化（强制）**：启动各阶段 task 时，只允许传递阶段名、技能根目录、算子目录、目标接口、输出目录、任务文件路径、必须读取的输入文件路径和阶段禁止项。禁止把 `1_extract.md`、`2_compare.md`、`3_formula.md`、`4_generate_skeleton.md`、`0_prototype.md` 或源码分析结果大段内联进子任务 prompt；禁止手写、复述或压缩 `tasks/*.md` 中的详细规则；禁止把旧规则、历史总结、领域知识摘要、参数列表、产品支持结论、dtype/shape 摘要、返回值规则、约束规则注入子任务。子任务必须自行读取对应 `tasks/*.md` 和所需输入片段，以任务文件为准。

**子任务 prompt 模板（强制）**：每个 task prompt 只能使用以下结构，不得新增 `Critical rules`、`Domain knowledge references`、`Process`、`核心要求` 等大段规则区块：
```text
执行 {阶段名} 阶段。
技能根目录：{skillRoot}
算子目录：{operatorDir}
目标接口：{interfaceName}
输出目录：{outputsDir}
任务文件：{taskFile}
输入文件：
- {inputFile1}
- {inputFile2}
输出文件：{outputFile}
禁止项：{stageForbiddenItems}
请先读取任务文件，再按任务文件要求读取输入文件的必要片段，生成输出文件。不得复述任务规则，不得读取未列出的文件，除任务文件明确允许的按需补读外不得扩展输入范围。
```

### 各阶段任务（按执行步骤）

#### 步骤 A1：extract（算子信息提取，输出 `1_extract.md`）

- 读取 `tasks/extract.md`
- 读取 `0_extract_plan.json`、`0_cross_dir.md`、`0_chip_evidence.md`、`0_error_codes.md`
- 按 extract 计划优先使用推荐路径、函数和批量读取路线，减少反复探索
- 输出 `1_extract.md`
- 必须包含 `## 文档生成语义基准`，供 formula 与 generate_skeleton 并行使用

#### 步骤 A2：compare（接口对比，输出 `2_compare.md`）

- 读取 `tasks/compare.md`
- 读取 `0_prototype.md`、`0_cross_dir.md`
- 必须与 extract 并行启动，不依赖 `1_extract.md`；不得等待 extract 完成后再执行
- 输出 `2_compare.md`

#### 步骤 B1：formula（公式生成，输出 `3_formula.md`）

- 读取 `tasks/formula.md`
- 读取 `1_extract.md`，特别是 `## 文档生成语义基准`
- 生成公式分析报告和可直接拼入最终文档的 `## 最终文档公式块`
- 输出 `3_formula.md`

#### 步骤 B2：generate_skeleton（正文骨架生成，输出 `4_generate_skeleton.md`）

- 读取 `tasks/generate_skeleton.md`
- 读取 `1_extract.md`、`2_compare.md`、`0_prototype.md`
- 禁止读取源码或主动探索算子目录；所有结论必须来自上游阶段产物
- 输出 `4_generate_skeleton.md`
- `## 功能说明` 的 `- 计算公式：` 位置只放占位符 `{{ACLNN_FORMULA_BLOCK_PLACEHOLDER}}`，不推导、不改写公式
- `## 函数原型` 章节只放占位符 `{{ACLNN_PROTOTYPE_BLOCK_PLACEHOLDER}}`，不生成、不补写、不改写函数签名
- 第二段执行接口固定章节只放占位符 `{{ACLNN_EXECUTE_INTERFACE_BLOCK_PLACEHOLDER}}`，不生成、不补写、不改写固定参数表和返回值说明

#### 步骤 C：review（一致性校验补丁，输出 `5_review_patch.json`）

- 读取 `tasks/review.md`
- 禁止读取源码或主动探索算子目录；只校验阶段产物之间的语义一致性和明显内部实现泄漏
- 将 `1_extract.md`、`2_compare.md`、`3_formula.md`、`4_generate_skeleton.md`、`0_prototype.md` 作为按需证据源，禁止默认全文读取
- 初始只读取 `4_generate_skeleton.md` 的标题结构和目标章节、`0_prototype.md` 的目标接口原型片段、`3_formula.md` 的 `## 最终文档公式块`、`1_extract.md` 的 `## 文档生成语义基准`
- 仅在语义证据不足、语义冲突或需要构造唯一 `oldText` 时补读对应文件的最小相关片段；纯格式类问题由外部 finalize 脚本处理，review 不做全量格式审查
- 只输出 `5_review_patch.json`
- 不输出完整文档，不应用补丁，不合成最终文档

---
## 外部程序边界

skill 不运行任何脚本。临时外部工具脚本放在技能根目录的 `tools/` 下，仅供外部程序或用户手动调用；LLM 阶段不得自行执行这些脚本。

外部程序在调用 skill 前必须完成预处理，并在输出目录生成以下文件：
- `0_extract_plan.json`
- `0_prototype.md`
- `0_cross_dir.md`
- `0_chip_evidence.md`
- `0_error_codes.md`
- `0_call_example.md`

skill 只读取这些文件，不负责生成它们。

skill 执行到 `5_review_patch.json` 后结束。外部程序负责：
- 将 `0_prototype.md` 的函数原型替换到 `4_generate_skeleton.md` 的 `{{ACLNN_PROTOTYPE_BLOCK_PLACEHOLDER}}`
- 将 `3_formula.md` 的 `## 最终文档公式块` 拼入 `4_generate_skeleton.md`
- 将第二段执行接口固定章节替换到 `4_generate_skeleton.md` 的 `{{ACLNN_EXECUTE_INTERFACE_BLOCK_PLACEHOLDER}}`
- 生成 `4_generate.md`
- 应用 `5_review_patch.json` 生成 `5_review.md`
- 拼接 `0_call_example.md`
- 执行格式/空格规范化
- 写入最终文档

---
## 外部最终合成约定

`## 调用示例` 章节不由模型生成，`4_generate_skeleton.md` 和 `5_review_patch.json` 中不得包含该章节。外部程序负责最终合成：

1. 从 `0_prototype.md` 读取函数原型正文。
2. 从 `3_formula.md` 读取 `## 最终文档公式块`。
3. 将函数原型替换到 `4_generate_skeleton.md` 的 `{{ACLNN_PROTOTYPE_BLOCK_PLACEHOLDER}}`。
4. 将公式块替换到 `4_generate_skeleton.md` 的 `{{ACLNN_FORMULA_BLOCK_PLACEHOLDER}}`。
5. 将第二段执行接口固定章节替换到 `4_generate_skeleton.md` 的 `{{ACLNN_EXECUTE_INTERFACE_BLOCK_PLACEHOLDER}}`，生成 `4_generate.md`。
6. 应用 `5_review_patch.json` 中的 `skeletonEdits` 和 `formulaBlockEdits`，生成 `5_review.md`。
7. 读取 `0_call_example.md`，在底稿末尾拼接 `## 调用示例` 章节。
8. 执行空格规范化。
9. 写入最终交付物 `{目标接口名}_YYYYMMDDHHMM.md`。

skill 不执行以上步骤，只描述产物与合成要求。

---
## 阶段产出目录

所有产出写入 `{算子目录}/outputs/{目标接口名}/`，其中 `{目标接口名}` 是完整 ACLNN 执行接口名，例如 `aclnnGroupedMatmulV5`：

```text
{算子目录}/outputs/{目标接口名}/
├── 0_extract_plan.json          # 外部预处理：extract 计划
├── 0_prototype.md               # 外部预处理：函数原型
├── 0_cross_dir.md               # 外部预处理：跨目录引用分析
├── 0_chip_evidence.md           # 外部预处理：芯片证据
├── 0_error_codes.md             # 外部预处理：错误码证据
├── 0_call_example.md            # 外部预处理：调用示例
├── 1_extract.md                 # skill：产品支持、芯片差异、参数、约束、语义基准
├── 1_extract_FAILED.md
├── 2_compare.md                 # skill：接口对比，必须与 extract 并行启动
├── 2_compare_FAILED.md
├── 3_formula.md                 # skill：公式分析与最终文档公式块
├── 3_formula_FAILED.md
├── 4_generate_skeleton.md       # skill：正文骨架，含公式、函数原型、执行接口固定章节占位符
├── 4_generate_skeleton_FAILED.md
├── 5_review_patch.json          # skill：问题驱动修正补丁
├── 5_review_patch_FAILED.md
├── 4_generate.md                # 外部合成：骨架 + 函数原型 + 公式块 + 执行接口固定章节
├── 5_review.md                  # 外部合成：应用 review patch 后的底稿
└── {目标接口名}_YYYYMMDDHHMM.md  # 外部合成：最终交付物
```









