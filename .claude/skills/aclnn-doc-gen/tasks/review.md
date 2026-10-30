# 一致性校验与修正任务

## 任务目标

对生成的文档骨架和公式块进行一致性校验，输出问题驱动修正补丁 `5_review_patch.json`。
不新增未证实信息，只提出最小必要修正，不输出完整文档。

## 输入输出约定

### 输入

**阶段产出（按需读取证据源）**：

以下文件是 review 阶段可用的证据源，**不是默认全文输入**：
1. 算子信息提取报告：`{算子目录}/outputs/{目标接口名}/1_extract.md`
2. 接口差异分析报告：`{算子目录}/outputs/{目标接口名}/2_compare.md`（如存在）
3. 公式分析报告：`{算子目录}/outputs/{目标接口名}/3_formula.md`
4. 文档骨架：`{算子目录}/outputs/{目标接口名}/4_generate_skeleton.md`
5. 函数原型：`{算子目录}/outputs/{目标接口名}/0_prototype.md`

**读取策略（强制）**：
- 禁止为了“全面检查”一次性读取上述上游产物全文。
- 禁止把上述上游产物全文粘贴进 review prompt。
- 禁止把上游报告重新总结成大段 prompt 注入。
- 禁止读取算子源码、禁止探索算子目录，包含但不限于 `op_api/`、`op_host/`、`op_kernel/`、`*.cpp`、`*.cc`、`*.c`、`*.h`、`*.hpp`。review 只做阶段产物之间的一致性校验，不回源码确认事实。
- 若阶段产物证据不足，输出 issue 或保守 patch 为 `<span style="color:#dc2626;">【需用户补齐】</span>`；不得通过读取源码补充结论。
- review 开始时只读取完成校验所需的最小片段：`4_generate_skeleton.md` 的标题结构和待校验目标章节、`0_prototype.md` 的目标接口原型片段、`3_formula.md` 的 `## 最终文档公式块`、`1_extract.md` 的 `## 文档生成语义基准`。
- 只有当当前片段无法支撑校验结论、发现索引/内容冲突、或需要构造唯一 `oldText` 时，才补读对应文件的最小相关片段。
- 构造 `skeletonEdits` 时，只补读 `4_generate_skeleton.md` 中 `oldText` 所在章节及必要相邻上下文，确保 `oldText` 唯一匹配。
- 构造 `formulaBlockEdits` 时，只补读 `3_formula.md` 的 `## 最终文档公式块` 及必要相邻上下文，确保 `oldText` 唯一匹配。

**按需补读矩阵（强制）**：
- 参数表与原型一致性：补读 `0_prototype.md` 的目标接口原型片段，以及 `4_generate_skeleton.md` 的对应参数表片段。
- 参数语义、dtype、format、shape、空Tensor、非连续Tensor 不确定：补读 `1_extract.md` 中对应参数的小节或 `## 文档生成语义基准` 的对应条目。
- 公式变量与参数表不一致：补读 `3_formula.md` 的 `## 最终文档公式块`、`1_extract.md` 的语义基准相关条目、`4_generate_skeleton.md` 的功能说明和参数表片段。
- 接口版本差异位置不确定：补读 `2_compare.md` 的差异结论小节，以及 `4_generate_skeleton.md` 的功能说明片段。
- 返回值表问题：补读 `4_generate_skeleton.md` 的返回值章节，以及 `1_extract.md` 的错误码或参数约束相关片段。
- 约束说明问题：补读 `4_generate_skeleton.md` 的约束说明片段，以及 `1_extract.md` 的对应产品、场景或参数约束片段。
- 内部实现细节泄漏：补读 `4_generate_skeleton.md` 的疑似泄漏章节；必要时只扩大到相邻章节，不得全文读取。

**参考资源**：
- references/common_terminology.yml — 完整术语规范
- references/terminology_dict.yml — 术语字典（会话开始已读取；review 阶段再次按此核对）
- config/error_codes.yml — ACLNN 文档允许输出的 4 个错误码数值映射；不存在时使用默认 4 个
- config/product_mapping.yml — 用户产品型号映射覆盖配置；不存在时使用默认映射，最终文档允许出现的 6 个产品型号固定

### 输出

**review 产出**：
- 写入位置：`{算子目录}/outputs/{目标接口名}/5_review_patch.json`
- 内容要求：只输出 JSON 补丁，不输出完整文档、不应用补丁、不合成最终文档
- 必须写入 JSON 对象本身，文件首个非空字符必须是 `{`。禁止把整个 JSON 对象作为字符串写入，例如禁止输出 `"{"status":"pass"}"` 或带反斜杠转义的 `\"status\"`。

**JSON 结构（必须严格遵守）**：

```json
{
  "status": "pass | fix | fail",
  "issues": [
    {
      "severity": "error | warning",
      "section": "章节名",
      "message": "问题说明",
      "basis": "依据的阶段产物或规则"
    }
  ],
  "skeletonEdits": [
    {
      "section": "章节名",
      "oldText": "4_generate_skeleton.md 中唯一匹配的原文片段",
      "newText": "替换后的文本",
      "reason": "修改原因"
    }
  ],
  "formulaBlockEdits": [
    {
      "section": "最终文档公式块",
      "oldText": "3_formula.md 的 ## 最终文档公式块中唯一匹配的原文片段",
      "newText": "替换后的文本",
      "reason": "修改原因"
    }
  ],
  "failureReason": "status 为 fail 时填写，否则为空字符串"
}
```

**status 判定规则（强制）**：
- `pass`：未发现需要自动修改的问题，`skeletonEdits` 和 `formulaBlockEdits` 必须均为空数组。
- `fix`：发现可自动修正的问题，且 `skeletonEdits` 或 `formulaBlockEdits` 至少一个非空。只要输出任意编辑项，`status` 必须为 `fix`，不得为 `pass`。
- `fail`：无法完成正常校验或无法构造有效补丁，`failureReason` 必须填写原因，且不得携带编辑项。
- `issues` 可记录 warning 或 error；`issues` 非空不必然代表 `fix`。是否为 `fix` 只取决于是否输出编辑项。

`oldText` 必须能在对应文件中唯一匹配。若无法构造唯一匹配片段，不得输出该编辑项，应在 `issues` 中说明需要人工确认。

## 校验范围（轻量 review）

review 只负责 **语义一致性** 与 **明显内部实现泄漏**，不再承担确定性格式全量校验。

### 1. 必查语义一致性

- **公式与参数语义一致性**：`3_formula.md` 的 `## 最终文档公式块` 中出现的接口参数变量，必须能在 `1_extract.md` 的 `## 文档生成语义基准` 和 `4_generate_skeleton.md` 参数表中找到对应关系；参数表描述中引用的公式变量必须存在于公式块。
- **参数表与提取结论一致性**：只检查会影响语义的冲突，例如 dtype/format/shape/空Tensor/非连续 Tensor 与 `1_extract.md` 明确结论相反，或把产品/场景差异写进参数表公共列。
- **约束说明与提取结论一致性**：`## 约束说明` 不得遗漏 `1_extract.md` 明确要求必须进入约束说明的跨参数、跨场景、跨产品差异约束；不得把 `1_extract.md` 未支持的产品或场景写成支持约束。
- **接口差异作用域一致性**：版本差异、接口间差异只允许出现在 `## 功能说明` 的 `- 接口功能：` 项中，不得扩散到参数说明、返回值或约束说明。
- **返回值语义一致性**：只检查返回值表是否出现与参数表/约束说明相矛盾的错误场景，或把芯片/产品差异写入返回值章节。

### 2. 明显内部实现泄漏检查

- 若 `4_generate_skeleton.md` 或 `3_formula.md` 的最终文档公式块中出现源码证据、内部实现流程、源码路径、行号、内部函数/类/宏/枚举、`op_kernel`、`op_host`、`op_tiling`、`tiling`、`AddConfig`、`OP_TYPE_REGISTER`、`SocVersion`、`NpuArch`、`__NPU_ARCH__`、`__CCE_AICORE__`、`DAV_`、`.cpp`、`.cc`、`.c`、`.h`、`.hpp`、`代码中`、`源码中`、`实现中`、`分支中`、`命中`、`证据` 等内部痕迹，必须通过 patch 删除或改写为面向用户的接口行为。
- 若某段内容只是解释内部实现过程，且无法转换为用户需要遵守的接口行为或约束，必须删除。
- 允许保留公开接口和公开文档概念：目标 ACLNN 接口名、公开参数名、公开 ACL 类型、公开错误码、公开数据类型、公开数据格式、`workspace` 与 `executor`。

### 3. 不再由 review 负责的确定性格式项

以下确定性格式项由外部 finalize 脚本校验、规范化或失败处理，review 不再逐项扫描，不得为了这些项目全文读取上游产物：

- 函数原型占位符、公式占位符、执行接口占位符是否存在。
- 第二段执行接口固定章节生成。
- `## 调用示例` 章节拼接位置。
- `## 代码分析清单` 删除。
- 基础 Markdown 空白、公式块 `$$` 独立成行、函数原型分号。
- review patch 的 `oldText` 唯一匹配校验。
- 返回值表列顺序、HTML 表格 wrapper、`rowspan`、`colgroup`、固定链接、标题标记说明块等纯格式问题。

若上述格式问题同时造成明显语义错误，可以在 `issues` 中记录，但不要展开全量格式审查。

## 修正要求

- 发现语义冲突或明显泄漏时直接输出最小 patch，不要标注“已修正”。
- 不新增任何未在 `1_extract.md`、`2_compare.md`、`3_formula.md` 或 `4_generate_skeleton.md` 中出现的信息。
- 保持技术事实不变。
- 仅允许最小必要内容修改，禁止重写整篇文档。
- `oldText` 必须能在对应文件中唯一匹配；若无法构造唯一匹配片段，不得输出编辑项，应在 `issues` 中说明需要人工确认。
- 如某项修正会导致大范围格式变化，放弃该修正，保留原格式并记录 issue。
- 输出 `5_review_patch.json`（不是完整文档、不是 Markdown diff）。

---
## 失败处理

若本阶段无法完成正常产出，**不写** `5_review_patch.json`，改为写入失败标志文件；外部最终合成不得继续执行。

**文件路径**：`{算子目录}/outputs/{目标接口名}/5_review_patch_FAILED.md`

**触发条件**（满足任一即触发）：
- `4_generate_skeleton.md` 缺失且存在 `4_generate_skeleton_FAILED.md`（上游阶段失败）
- `1_extract.md`、`3_formula.md` 或 `0_prototype.md` 缺失且存在对应 `_FAILED.md`（校验依据不可用）

**文件结构**（照此格式逐字段填写）：

- 标题：`# 一致性校验（review）失败`
- `**失败时间**`：当前时间，格式 `YYYY-MM-DD HH:MM`
- `**失败阶段**`：`阶段5 — review（一致性校验）`
- `## 失败原因`：一句话描述失败原因，例如"上游文件 4_generate_skeleton.md 缺失"
- `## 缺失或无法读取的输入`：逐项列出缺失文件的完整路径及缺失说明；无缺失文件时省略此节
- `## 已完成的操作`：列出本阶段已成功执行的步骤；无则写"无"






