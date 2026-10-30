---
name: markdown-filename-quality-checker
description: Check Markdown filenames for spec/correctness on a single file or a directory of files.
category: doc-quality
license: CANN Open Software License Agreement Version 2.0
origin: cannbot
---

# 生态资料文档名称质检技能

## 概述

此 SKILL 用于对 Markdown 文档名称进行全面的质量检查，包括规范性与正确性。支持三种输入场景：直接输入单个 Markdown 文档路径、多个 Markdown 文档路径或目录路径。技能严格按照“前置条件处理 - 准备工作 - 执行分析 - 汇总结果 - 清理临时文件”的五步工作流执行检查。

## 使用场景

1. **一个Markdown文档**：用户输入一个 Markdown 文档的绝对路径
2. **多个Markdown文档/目录**：用户输入多个 Markdown 文档的绝对路径（用英文逗号分隔）或一个文档目录

## 详细检查工作流程（必须逐个步骤执行）

在执行任何步骤前，在对话中先输出当前检查点：[CHECKPOINT: 开始]

**规则**：如果前一个CHECKPOINT未输出，禁止执行后一步骤。

### 步骤1：前置条件处理

- 获取用户输入中是否包含 `--rules` 参数列表（如果存在）
- 确保 `output` 目录存在（当前项目根目录下的 output 文件夹）
    - 如果 `output` 目录下存在 `filename` 文件夹，则删除 `filename` 文件夹
    - 如果 `output` 目录下存在 `filename-markdown-check-result.json` 文件，则删除 `filename-markdown-check-result.json`
- 读取用户输出的Markdown文档路径

完成后必须在对话中输出 [CHECKPOINT: 前置条件处理完成]

### 步骤2：准备工作

#### 2.1 准备规则

- `RULE_PATH`：当前技能目录下的 `assets/rules.json` 文件的绝对路径
- `OUTPUT_PATH`：当前项目根目录下的 `output/filename/rules` 文件夹绝对路径
- `RULE_LIST`：获取的规则参数列表（如果未提供则为空字符串）
- 创建必要的输出目录结构

执行 `scripts/rule_processor.py` 脚本：
```bash
python scripts/rule_processor.py <RULE_PATH> <OUTPUT_PATH> [RULE_LIST]
```
完成后先检查 `output/filename/rules` 文件夹下是否有规则文件，如果有文件则必须在对话中输出 [CHECKPOINT: 准备规则完成]；如果没有规则文件，则重新执行该步骤。

#### 2.2 准备文档

- `WHITE_FILE_PATH`：当前技能目录下的 `assets/exclude-files.json` 文件的绝对路径
- `FILE_PATH`：获取处理后的文档路径
- `STATUS_OUTPUT_PATH`：当前项目根目录下的 `output/filename/status` 文件夹绝对路径 output

执行 `scripts/process_markdown_files.py` 脚本：
```bash
python scripts/process_markdown_files.py <WHITE_FILE_PATH> <FILE_PATH> <STATUS_OUTPUT_PATH>
```
完成后必须在对话中输出 [CHECKPOINT: 准备文档完成]

### 步骤3：执行分析

#### 3.1 基础准备

- 确保 `output` 文件夹存在，如果不存在则创建
- 确保 `output/filename/markdown-check-result` 文件夹存在，如果不存在则创建

完成后必须在对话中输出 [CHECKPOINT: 基础准备完成]

#### 3.2 逐个检查文档

对于每个待检查文档：

1. **检查文档状态**：
    - 如果文档状态为 `completed`，跳过该文档
    - 如果文档状态为 `pending`，继续处理
2. 更新 `output/filename/status/file_status.json` 中文档状态为 `in_progress`
3. 获取规则文件列表：
    - 遍历 `output/filename/rules` 目录
    - 筛选所有 .json 文件作为规则文件
    - 排序规则文件以确保处理顺序一致性
4. 对于每个规则文件：
    - 逐个应用规则：
        - **读取规则文件**：读取对应的规则 JSON 文件
        - **读取文档名称**：仅读取待检查的 Markdown 文档名称，不读取文档内容
        - **读取参考资料**：读取当前规则的 `reference_doc_path` 字段，查看是否有值
            - 如果有值，则根据路径读取参考资料内容
            - 如果没值，则继续执行检查逻辑
        - **执行检查逻辑**：根据规则文件中的每个规则 `rule_desc` 的内容只检查读取到的文档名称，不读取文档内容，不允许根据常识或经验进行扩展性检查
        - **检查结果格式**：检查出来的问题按照 **汇总结果说明** 和 **返回值字段说明** 的要求以及格式输出
        - **检查结果验证**：检查每个问题是否都有明确的规则依据
            - 如果没有明确的规则依据，则剔除该问题结果
        - **保存结果**：将检查结果保存到 `output/filename/markdown-check-result/` 目录中，文件名为“文档名称_规则项名称.json”
            - 如果是非问题或者未发现问题，禁止输出到结果文件中
5. 更新 `output/filename/status/file_status.json` 中文档状态为 `completed`

完成后必须在对话中输出 [CHECKPOINT: 逐个检查文档完成]

### 步骤4：汇总结果

- 检查所有文档状态是否都为 `completed`
- 如果存在未完成的文档，重复步骤3处理这些文档
- 汇总所有结果到 `output/filename-markdown-check-result.json` 文件

完成后必须在对话中输出 [CHECKPOINT: 汇总结果完成]

### 步骤5：清理临时文件

- 删除`output` 目录下的 filename 文件夹

完成后必须在对话中输出 [CHECKPOINT: 清理临时文件完成]

## 重要执行原则

- **必须严格按规则描述的检查对象执行，禁止自行推断检查范围，宁可遗漏问题，也不能超出规则定义进行检查**
- **必须严格按照规则的描述检查，禁止将规则发散**
- **必须严格按照技能步骤执行**
- **步骤必须按顺序执行,严禁跳过任何步骤**
- **每次启动技能都必须按照用户输入重新读取Markdown文档**
- **严格按照文档名称检查，英文大小写必须按照文档中的内容匹配**
- **必须为每个Markdown文档单独读取、分析**
- **步骤4中的 逐个检查文档 完成后必须更新进度状态为completed**
- **只有在所有步骤都完成后才能退出skill**

## 禁止行为

- 禁止超出规则描述范围进行检查，即便发现明显错误，遇到规则描述不明确的情况，必须跳过而非自行解读
- 禁止基于常识或经验进行扩展性检查，避免主观推断
- 禁止超出规则定义的检查范围进行检查
- 禁止不按照技能步骤执行
- 禁止不按技能步骤顺序执行
- 禁止跳过任何步骤
- 禁止合并或简化规则分类
- 禁止复制待检查文档到临时文件夹
- 禁止修改或增减规则内容
- 禁止修改文件内容，检查过程中只需要读取文件内容
- 禁止按照问题行号合并检查出的问题
- 禁止生成 CHECKPOINT 文档

## 规则文件说明

规则文件 `assets/rules.json` 包含检查规则的定义，每个规则包含以下字段：
- `rule_no`: 规则编号
- `rule_item_name`: 规则项名称
- `rule_name`: 规则名称
- `rule_type`: 规则类型
- `rule_desc`: 规则描述
- `rule_level`: 规则级别
- `reference_doc_path`: 参考文档路径（可选）
- `description_format`: 检查出来问题的描述按照模板样例输出

## 参数说明

用户输入可以包含 `--rules` 参数：

- 格式：`--rules 规则序号列表`
- 示例：`--rules 1,2,3`
- 多个规则序号用英文逗号分隔

## 汇总结果说明

最终的汇总结果只需要汇总 `output/` 目录下的执行的结果，不需要按照问题类型、问题行数等合并检查结果。结果严格按照以下格式输出：

```json
[
   {
      "rule_group": "xxx",
      "rule_item": "xxx",
      "rule_type": "xxx",
      "rule_name": "xxx",
      "snippet": "xxx",
      "description": "xxx",
      "rule_level": "xxx",
      "file_name": "xxx",
      "line_number": "xxx",
      "location": "xxx",
      "suggestion": "xxx"
   }
]
```

### 返回值字段说明

- **rule_group**：问题大类。固定是 **通用规则**；
- **rule_item**：问题类型。必须是发现问题的核心检查规则的**rule_item_name**；
- **rule_type**：问题类型。必须是发现问题的核心检查规则的**rule_type**；
- **rule_name**：问题名称。必须是发现问题的规则的**rule_name**；
- **snippet**：问题内容片段，如果是文档名称有问题，就输出文档名称即可。
- **description**：根据规则的实际检查内容来生成的相应描述信息，需要简介明了，不要包含问题行号；
- **rule_level**：问题级别。必须是发现问题的核心检查规则的**rule_level**；
- **file_name**：文档名称。必须是用户输入的Markdown文档的名称；
- **line_number**：问题行号。必须是发现文档的文档里问题所在行号；
- **location**：问题所在的行链接。文档的绝对路径且支持点击跳转，超链接默认支持VS Code。示例为：vscode://file/D:\\8.vs_workspace\\markdown_quality_checker\\bookmap.md:4
- **suggestion**：模型给出的问题修改建议。不要出现问题行号。

## 文件结构

```
markdown-filename-quality-checker/
├── SKILL.md (本文件)
├── scripts/
│   ├── rule_processor.py (规则处理脚本)
│   ├── process_markdown_files.py (文档处理脚本)
│   └── [其他必需脚本]
├── references/
│   └── [其他参考文档]
└── assets/
    ├── rules.json (检查规则定义)
    ├── exclude-files.json (Markdown文件白名单)
    └── [其他必需资产]
```

## 注意事项

1. 所有使用的文件路径都应是相对路径，在执行时转换为绝对路径
2. output 目录是在当前项目根目录下
3. 第三步的分析必须逐个检查用户输入的所有文档
4. 检查完成后需要清理临时文件，仅保留最终结果文件
5. 支持 `.md` 文件扩展名的质量检查