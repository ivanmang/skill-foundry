# AscendC 文档生成 Skill 使用说明

`ascendc-doc-gen` 用于从 AscendC 源码生成 API 参考文档。完整流程由四步组成：

```text
AscendC 文件或目录
    │
    ├─ 1. detect-interfaces.js
    │      输出接口清单 JSON，供用户选择接口
    │
    ├─ 2. ascendc-preprocess.mjs
    │      根据所选接口生成 0_* 静态提取产物
    │
    ├─ 3. ascendc-doc-gen skill
    │      执行 chipdiff → extract → generate → review
    │      生成 1_chipdiff.md 至 4_review.md
    │
    └─ 4. ascendc-finalize.mjs
           校验并生成带时间戳的最终文档
```

四步通过同一个文档接口身份串联：

```text
接口检测结果
  name + apiType + callingConvention + files
        ↓
预处理 manifest
  documentApiName + memberApis + callingConvention + sourceFiles
        ↓
skill 阶段目录
  outputs/<documentApiName>/
        ↓
最终文档
  <documentApiName>_YYYYMMDDHHmm.md
```

运行原则：

- 接口检测、预处理和最终合成由外部脚本执行。
- skill 只执行需要模型判断的四个阶段，不运行外部脚本。
- 一个输出目录只处理一个确定的接口身份。批量任务应逐接口独立执行完整流程。
- 所有命令建议在 skill 根目录执行。

## 1. 准备路径

以下示例使用 PowerShell：

```powershell
$SkillRoot = "C:\Users\tzh19\.config\opencode\skills\ascendc-doc-gen"
$ProjectRoot = "D:\work\canndoc-project\asc-devkit"
$InputPath = "$ProjectRoot\include"
$DetectionJson = "$ProjectRoot\outputs\ascendc_interfaces.json"

Set-Location $SkillRoot
```

- `$InputPath`：一个 AscendC 头文件或任意待扫描目录。
- `$ProjectRoot`：代码库根目录，通常包含 `include`、`impl`、`examples` 和 `outputs`。
- Node.js 必须可用。

## 2. 检测并选择接口

### 2.1 生成接口清单

```powershell
node scripts\detect-interfaces.js `
  $InputPath `
  $ProjectRoot `
  --output $DetectionJson
```

命令格式保持为：

```text
node scripts/detect-interfaces.js <AscendC文件或目录> [代码库根目录] --output <JSON文件> [--compact]
```

检测脚本只扫描和写出 JSON，不执行预处理或模型阶段。它会递归扫描输入目录中的源码文件。

JSON 中最重要的字段：

| 字段 | 作用 |
|---|---|
| `interfaces` | 可供用户选择并生成文档的接口列表。 |
| `interfaces[].id` | 由 API 类型、调用约定和接口名组成的唯一身份。 |
| `interfaces[].name` | 传给预处理脚本的 `--interface`。 |
| `interfaces[].apiType` | 传给 `--api-type`。 |
| `interfaces[].callingConvention` | 传给 `--calling-convention`。 |
| `interfaces[].members` | 同一文档应包含的公开成员，例如常规接口、`_sync` 接口及 `_padN` 变体。 |
| `interfaces[].files` | 定义该接口的源码文件。 |
| `symbols` | 未做文档成员归并的具体函数身份，通常不直接用于用户选择。 |
| `summary` | 扫描文件数、函数符号数和可选接口数。 |

同名接口可能分别属于 `__aicore__`、`__simd_callee__` 或其它调用约定，因此应按 `id` 选择，不能只按 `name` 选择。

检测和预处理共用文档族规则：`<base>_padN`、`<base>_padN_sync` 固定归入 `<base>`，不会作为独立可选接口；`nd2nz`、`align` 等其它后缀仍独立识别。

### 2.2 展示并选择接口

检测脚本只负责生成 JSON，不规定调用方必须使用命令行、GUI、网页或其它交互形式。调用方应读取 `interfaces`，向用户展示足以区分接口身份的信息，并保留用户选中的完整接口对象。

参考展示样式：

```text
检测到 3 个可生成文档的接口，请选择：

1. asc_copy_gm2l1
   ID：c_api|__aicore__|asc_copy_gm2l1
   API 类型：c_api
   调用约定：__aicore__
   成员：asc_copy_gm2l1、asc_copy_gm2l1_sync、asc_copy_gm2l1_pad1 … asc_copy_gm2l1_pad8_sync
   源文件：include/c_api/cube_datamove/cube_datamove.h

2. asc_half2float
   ID：c_api|__aicore__|asc_half2float
   API 类型：c_api
   调用约定：__aicore__
   成员：asc_half2float
   源文件：include/c_api/reg_compute/reg_convert.h

3. asc_half2float
   ID：c_api|__simd_callee__|asc_half2float
   API 类型：c_api
   调用约定：__simd_callee__
   成员：asc_half2float
   源文件：include/c_api/reg_compute/reg_convert.h

请输入序号或接口 ID：
```

以上只是参考样式。调用方可以调整字段顺序、分页、搜索和选择控件，但至少应展示 `name`、`apiType`、`callingConvention`、`members`，同名接口必须展示调用约定。

最简单的 PowerShell 调用参考：

```powershell
$Detection = Get-Content -Raw -Encoding UTF8 $DetectionJson | ConvertFrom-Json

$Detection.interfaces |
  Select-Object id, name, apiType, callingConvention,
    @{Name="members"; Expression={ $_.members.name -join "," }} |
  Format-Table -AutoSize
```

用户选择后，调用方应保留完整接口对象。例如按唯一 `id` 选择：

```powershell
$Selected = $Detection.interfaces |
  Where-Object { $_.id -eq "c_api|__aicore__|asc_copy_gm2l1" }

$Selected | Format-List id, name, apiType, callingConvention, files
```

后续预处理直接使用 `$Selected.name`、`$Selected.apiType` 和 `$Selected.callingConvention`。如果 `callingConvention` 为 `unknown`，不要传入 `unknown`；应将输入路径缩小到具体头文件，让预处理脚本从源码确定调用约定。

## 3. 预处理

将检测结果直接映射为预处理参数：

```powershell
node tools\ascendc-preprocess.mjs `
  $InputPath `
  $ProjectRoot `
  --interface $Selected.name `
  --api-type $Selected.apiType `
  --calling-convention $Selected.callingConvention
```

建议继续使用检测时的原始输入路径。若 `interfaces[].files` 只有一个文件，也可以把 `$InputPath` 改为该文件路径，以减少扫描范围。

常用参数：

| 参数 | 作用 |
|---|---|
| `--interface <名称>` | 指定请求接口。自动化执行时建议必传。 |
| `--api-type <类型>` | 可选值为 `adv_api`、`basic_api`、`c_api`、`simt_api`。 |
| `--calling-convention <约定>` | 区分同名但调用约定不同的接口。命中多个约定时必须传入。 |
| `--exact-interface` | 只处理指定函数，不自动归并符合条件的常规接口和 `_sync` 接口。 |
| `--related-interface <名称>` | 显式加入同一文档的关联公开接口，可重复使用。 |
| `--isa-reference <文件或目录>` | 可重复使用；生成可选的 `0_isa_reference.md`。 |
| `--scripts-dir <目录>` | 使用指定的底层预处理脚本目录，通常无需设置。 |

预处理会确定规范文档名和文档成员，并写入：

```text
<ProjectRoot>\outputs\<documentApiName>\
```

主要产物：

| 文件 | 作用 |
|---|---|
| `0_preprocess_manifest.json` | 本次任务的身份边界和执行记录，包括 `documentApiName`、`memberApis`、调用约定和源文件。 |
| `0_prototype.md` | 目标成员的完整函数原型和重载集合。 |
| `0_cross_dir.md` | 声明、实现、校验及关联代码的检索范围。 |
| `0_semantic_links.json` | 参数沿调用链的传播关系和语义追踪线索。 |
| `0_call_example.md` | 从代码库提取的调用示例；未找到时写入缺失提示。 |
| `0_isa_reference.md` | 可选参考产物，仅传入 `--isa-reference` 时生成。 |
| `0_<阶段>_FAILED.md` | 对应预处理步骤失败时的错误摘要。 |

预处理结束后检查：

1. 控制台中的所有步骤均为 `[OK]`。
2. 输出目录中不存在 `0_*_FAILED.md`。
3. `0_preprocess_manifest.json` 中的 `documentApiName`、`memberApis` 和 `callingConvention` 符合预期。

从这一步开始，后续目标 API 和目录一律使用 manifest 中的 `documentApiName`，不再使用可能被归并的请求接口名。例如请求 `<base>_sync` 后，规范文档名可能是 `<base>`。

## 4. 执行 Skill

在 OpenCode 中为一个接口启动一个独立任务，使用以下提示词：

```text
使用 ascendc-doc-gen skill 生成 AscendC API 文档。

代码库根目录：
<ProjectRoot>

目标 API：
<documentApiName>

阶段产物目录：
<ProjectRoot>\outputs\<documentApiName>

外部预处理已经完成。请读取 0_preprocess_manifest.json，并只执行：
chipdiff → extract → generate → review

不要运行预处理脚本。
不要执行最终合成脚本。
```

skill 会依次生成：

| 文件 | 作用 |
|---|---|
| `1_chipdiff.md` | 分析产品支持、原型、数据类型、参数约束和功能差异。 |
| `2_extract.md` | 从源码和预处理线索中提取功能、参数、返回值、约束和示例证据。 |
| `3_generate.md` | 生成结构完整的文档初稿。 |
| `4_review.md` | 校验并修正初稿，作为后处理输入。 |

阶段之间按文件串联：

```text
0_* + 源码
   ↓
1_chipdiff.md
   ↓
2_extract.md
   ↓
3_generate.md
   ↓
4_review.md
```

skill 必须以 `0_preprocess_manifest.json` 的成员闭集为边界，并保证 `4_review.md` 中的函数原型与 `0_prototype.md` 一致。

## 5. 后处理并生成最终文档

skill 生成 `4_review.md` 后执行：

```powershell
node tools\ascendc-finalize.mjs `
  $ProjectRoot `
  --interface <documentApiName>
```

`--interface` 对应 `outputs` 下的目录名。省略时，脚本会扫描包含 `4_review.md` 的目录并要求用户选择。

后处理读取：

```text
4_review.md
0_call_example.md
0_prototype.md
0_preprocess_manifest.json
```

处理规则：

1. 如果 `0_call_example.md` 中存在有效脚本示例，用它替换 `4_review.md` 的调用示例章节。
2. 如果脚本没有提取到示例，保留 skill 在 `4_review.md` 中生成的示例。
3. 对与 `0_prototype.md` 精确匹配、仅缺少末尾分号的单行函数声明自动补 `;`；原型被改写、遗漏或折行时仍报错。
4. 按 manifest 校验文档成员、调用约定和原型完整性。
5. 校验调用示例、表格和正文格式；校验失败时不生成最终文件。
6. 校验通过后生成：

```text
<ProjectRoot>\outputs\<documentApiName>\<documentApiName>_YYYYMMDDHHmm.md
```

例如：

```text
asc_copy_gm2l1_202608101530.md
```

## 6. 批量执行和常见问题

### 批量执行

先检测一次，再逐个遍历 `interfaces`。每个接口必须独立执行：

```text
预处理 → 独立 skill 任务 → 后处理
```

不要让多个接口共享同一个 skill 上下文。建议串行执行；同名但调用约定不同的接口会使用相同的 `outputs\<name>` 目录，禁止并发处理，且应在切换调用约定前完成后处理并留存最终文档。

### 未传 `--interface`

预处理会扫描输入路径：

- 未检测到接口：报错。
- 检测到一个接口：自动选择。
- 检测到多个接口：在终端要求选择。

自动化流程应显式传入接口检测结果中的 `name`。

### 同名接口命中多个调用约定

必须根据接口检测结果传入 `--calling-convention`。不能把不同调用约定的原型写入同一文档。

### 聚合头文件检测不到接口

只包含 `#include`、没有直接接口定义的聚合头文件可能检测不到接口。应扫描其所属目录或具体定义头文件。

### 没有真实调用示例

预处理会在 `0_call_example.md` 中记录缺失。skill 仍需根据原型、参数语义和实现代码生成可指导使用的示例；后处理在没有有效脚本示例时保留该模型示例。

### 预处理失败

存在 `0_*_FAILED.md` 或 manifest 中某一步失败时，应先修复预处理问题，不要继续执行 skill。
