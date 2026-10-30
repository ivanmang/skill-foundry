# ACLNN skill 外部工具

本目录提供 `aclnn-doc-gen` skill 流程配套的外部脚本，用于把耗时但确定性的工作从 skill 内部移出。

这些脚本不属于 `packages/` 主项目实现，不修改当前 canndoc-template 的核心生成逻辑。它们的定位是临时外部执行工具：预处理阶段先生成静态中间产物，skill 只负责 LLM 阶段，最后再由外部脚本合成最终文档。

## 1. 目录位置

当前支持两种放置方式。

在仓库中使用：

```text
D:\work\canndoc-template\external-aclnn-skill-tools
```

在 opencode skill 中使用：

```text
C:\Users\tzh19\.config\opencode\skills\aclnn-doc-gen\tools
```

两处脚本内容应保持一致。推荐实际运行时使用 skill 目录下的 `tools/`，这样配置文件和脚本都集中在 skill 内。

## 2. 预处理

预处理脚本会扫描算子目录下的 ACLNN 接口；如果没有通过参数指定接口，会提示用户选择要生成的接口。选定接口后，会执行静态提取脚本并生成后续 skill 阶段需要读取的中间产物。

在 skill 目录下运行：

```bash
node tools/aclnn-preprocess.mjs <operatorDir>
```

在仓库目录下运行：

```bash
node external-aclnn-skill-tools/aclnn-preprocess.mjs <operatorDir>
```

常用可选参数：

```bash
node tools/aclnn-preprocess.mjs <operatorDir> --interface aclnnXxx --project-root <projectRoot>
```

完整可选参数：

```bash
node tools/aclnn-preprocess.mjs <operatorDir> --interface aclnnXxx --project-root <projectRoot> --scripts-dir <scriptsDir> --skill-root <skillRoot> --error-codes-file <file> --product-mapping-file <file>
```

参数说明：

- `--interface`：指定 ACLNN 接口名；不指定时由脚本检测并提示选择。
- `--project-root`：指定项目根目录，用于跨目录追踪；不指定时脚本会尝试自动推断。
- `--scripts-dir`：指定静态提取脚本目录；默认使用当前工具目录下的 `scripts/`。
- `--skill-root`：指定 skill 根目录；默认是 `C:\Users\tzh19\.config\opencode\skills\aclnn-doc-gen`。
- `--error-codes-file`：指定错误码映射配置文件。
- `--product-mapping-file`：指定产品型号映射配置文件。

预处理产物写入：

```text
<operatorDir>/outputs/<interfaceName>/
```

生成文件：

- `0_prototype.md`
- `0_cross_dir.md`
- `0_chip_evidence.md`
- `0_error_codes.md`
- `0_call_example.md`
- `0_extract_plan.json`

## 3. 批量预处理

批量脚本只做外部编排，不重新实现预处理逻辑。它会先调用现有接口检测脚本识别算子目录下的 ACLNN 接口，再逐个调用 `aclnn-preprocess.mjs`。

在 skill 目录下运行：

```bash
node tools/aclnn-batch.mjs preprocess <operatorDir>
```

在仓库目录下运行：

```bash
node external-aclnn-skill-tools/aclnn-batch.mjs preprocess <operatorDir>
```

只检测接口，不生成产物：

```bash
node tools/aclnn-batch.mjs detect <operatorDir>
```

常用筛选参数：

```bash
node tools/aclnn-batch.mjs preprocess <operatorDir> --include aclnnXxx,aclnnYyy
node tools/aclnn-batch.mjs preprocess <operatorDir> --exclude aclnnZzz
```

`preprocess` 模式可继续透传单接口预处理脚本已有参数：

```bash
node tools/aclnn-batch.mjs preprocess <operatorDir> --project-root <projectRoot> --product-mapping-file <file>
```

## 4. 配置文件

映射配置默认从 skill 目录读取：

```text
C:\Users\tzh19\.config\opencode\skills\aclnn-doc-gen\config\error_codes.yml
C:\Users\tzh19\.config\opencode\skills\aclnn-doc-gen\config\product_mapping.yml
```

兼容旧路径：如果 `config/*.yml` 不存在，脚本会回退读取 `references/*.yml`。

`error_codes.yml` 只支持 4 个文档允许输出的 ACLNN 错误码：

- `ACLNN_ERR_PARAM_NULLPTR`
- `ACLNN_ERR_PARAM_INVALID`
- `ACLNN_ERR_INNER_INFERSHAPE_ERROR`
- `ACLNN_ERR_INNER_TILING_ERROR`

`product_mapping.yml` 已写入默认芯片标识、`NPU_ARCH` 到固定产品型号白名单的映射。用户可以直接修改已有项或新增项；配置缺失时脚本内置默认值兜底。

最终文档只允许出现以下 6 个产品型号，用户配置只能改变映射方式，不能新增最终可输出的产品型号：

- `Ascend 950PR/Ascend 950DT`
- `Atlas A3 训练系列产品/Atlas A3 推理系列产品`
- `Atlas A2 训练系列产品/Atlas A2 推理系列产品`
- `Atlas 200I/500 A2 推理产品`
- `Atlas 推理系列产品`
- `Atlas 训练系列产品`

## 5. Skill 阶段

预处理完成后，使用 `aclnn-doc-gen` skill 执行 LLM 阶段。

当前新流程按执行步骤编排。注意：`1_extract.md`、`2_compare.md`、`3_formula.md`、`4_generate_skeleton.md`、`5_review_patch.json` 的数字只是兼容既有产物命名，不代表执行顺序。

```text
extract 和 compare 并行
        ↓
formula 和 generate_skeleton 并行
        ↓
review patch
        ↓
外部 finalize 合成最终文档
```

skill 阶段会读取预处理产物，但不应该重新执行预处理脚本，也不应该在 skill 内完成最终拼接。

## 6. 最终合成

LLM 阶段完成后，执行 finalize 脚本从 `0_prototype.md` 拼入函数原型、从 `3_formula.md` 拼入公式块，并按目标接口名生成第二段执行接口固定章节，合成 `4_generate.md`、`5_review.md` 和最终文档。

在 skill 目录下运行：

```bash
node tools/aclnn-finalize.mjs <operatorDir>
```

在仓库目录下运行：

```bash
node external-aclnn-skill-tools/aclnn-finalize.mjs <operatorDir>
```

指定接口：

```bash
node tools/aclnn-finalize.mjs <operatorDir> --interface aclnnXxx
```

finalize 期望以下 skill 阶段产物已经存在：

- `0_prototype.md`
- `3_formula.md`
- `4_generate_skeleton.md`
- `5_review_patch.json`
- `0_call_example.md`

`4_generate_skeleton.md` 中应包含以下占位符，由 finalize 统一替换：

- `{{ACLNN_PROTOTYPE_BLOCK_PLACEHOLDER}}`
- `{{ACLNN_FORMULA_BLOCK_PLACEHOLDER}}`
- `{{ACLNN_EXECUTE_INTERFACE_BLOCK_PLACEHOLDER}}`

生成文件：

- `4_generate.md`
- `5_review.md`
- `<interfaceName>_YYYYMMDDHHmm.md`

## 7. 批量最终合成

批量合成脚本只做外部编排，不重新实现合成逻辑。它会扫描 `outputs/` 下的接口产物目录，检查 LLM 阶段产物是否齐全，然后逐个调用 `aclnn-finalize.mjs`。

在 skill 目录下运行：

```bash
node tools/aclnn-batch.mjs finalize <operatorDir>
```

在仓库目录下运行：

```bash
node external-aclnn-skill-tools/aclnn-batch.mjs finalize <operatorDir>
```

finalize 批量模式要求每个接口目录中存在：

- `0_prototype.md`
- `3_formula.md`
- `4_generate_skeleton.md`
- `5_review_patch.json`
- `0_call_example.md`

缺少上述文件的接口会跳过并在汇总中说明。

## 8. 推荐使用示例

以 `grouped_matmul` 的 `aclnnGroupedMatmulV5` 为例：

```bash
node tools/aclnn-preprocess.mjs D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul --interface aclnnGroupedMatmulV5
```

然后执行 skill 的 LLM 阶段，生成：

```text
1_extract.md
2_compare.md
3_formula.md
4_generate_skeleton.md
5_review_patch.json
```

最后执行：

```bash
node tools/aclnn-finalize.mjs D:\work\canndoc-project\ops-transformer\gmm\grouped_matmul --interface aclnnGroupedMatmulV5
```




