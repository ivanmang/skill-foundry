# ACLNN 文档生成 skill 使用说明

本文说明 `aclnn-doc-gen` skill 的完整运行流程。当前流程面向单个算子目录、单个 ACLNN 接口生成；如果一个目录下检测到多个接口，预处理脚本会提示选择其中一个接口。

## 1. 流程总览

```text
外部预处理脚本
    ↓
skill 执行 LLM 阶段
    ↓
外部合成脚本
    ↓
最终 ACLNN 文档
```

各部分职责：

- 外部预处理脚本：执行确定性的静态分析，生成 `0_*.md/json` 中间产物。
- skill LLM 阶段：执行 `extract`、`compare`、`formula`、`generate_skeleton`、`review patch`。
- 外部合成脚本：把骨架、`0_prototype.md` 函数原型、`3_formula.md` 公式块、review 补丁和调用示例合成为最终文档。

注意：skill 内部不执行预处理脚本，也不执行最终合成脚本。

## 2. 以 gmm 为例

示例算子目录：

```text
D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul
```

示例目标接口：

```text
aclnnGroupedMatmulV5
```

最终阶段产物目录：

```text
D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul\outputs\aclnnGroupedMatmulV5
```

## 3. 第一步：执行预处理

在 skill 根目录执行：

```powershell
cd C:\Users\tzh19\.config\opencode\skills\aclnn-doc-gen

node tools\aclnn-preprocess.mjs D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul --interface aclnnGroupedMatmulV5
```

如果不指定 `--interface`，脚本会检测接口并提示选择：

```powershell
node tools\aclnn-preprocess.mjs D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul
```

预处理成功后，输出目录中应生成：

```text
0_prototype.md
0_cross_dir.md
0_chip_evidence.md
0_error_codes.md
0_call_example.md
0_extract_plan.json
```

## 4. 第二步：执行 skill LLM 阶段

预处理完成后，在 opencode 中使用 `aclnn-doc-gen` skill。可以直接复制下面这一段任务给模型：

```text
使用 aclnn-doc-gen skill 生成 ACLNN 文档。

算子目录：
D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul

目标接口：
aclnnGroupedMatmulV5

阶段产物目录：
D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul\outputs\aclnnGroupedMatmulV5

预处理已经完成。请按 skill 中定义的流程执行 LLM 阶段。
必须按 skill 要求并行启动指定阶段；不得改为串行执行。
不要执行预处理脚本。
不要执行最终拼接脚本。
```

LLM 阶段完成后，阶段产物目录中应存在：

```text
1_extract.md
2_compare.md
3_formula.md
4_generate_skeleton.md
5_review_patch.json
```

## 5. 第三步：执行最终合成

等 LLM 阶段产物都生成后，在 skill 根目录执行：

```powershell
cd C:\Users\tzh19\.config\opencode\skills\aclnn-doc-gen

node tools\aclnn-finalize.mjs D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul --interface aclnnGroupedMatmulV5
```

合成脚本会从 `0_prototype.md` 拼入函数原型、从 `3_formula.md` 拼入公式块，并生成：

```text
4_generate.md
5_review.md
aclnnGroupedMatmulV5_YYYYMMDDHHmm.md
```

最终文档位于：

```text
D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul\outputs\aclnnGroupedMatmulV5
```

## 6. 配置文件

默认配置放在 skill 根目录的 `config/` 下：

```text
config\error_codes.yml
config\product_mapping.yml
```

说明：

- `error_codes.yml`：配置文档允许输出的 ACLNN 错误码映射，当前只保留 4 类错误码。
- `product_mapping.yml`：已包含默认芯片标识、架构标识到固定产品型号的映射，可直接修改或新增。

最终文档允许出现的产品型号是固定白名单，用户配置只能调整映射方式，不能新增最终产品型号名称。








