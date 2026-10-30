# API Locator

从 Ascend C 接口文档出发，定位所有关联代码文件（声明文件、实现文件、测试文件）。

## 前置条件

- **Node.js >= 22**（使用内置 `fs.promises.glob`，无需外部依赖）

```bash
node --version  # 确认版本 >= 22
```

## 使用方式

```bash
node src/locate-api.js <文档路径> --repo <仓库路径>
```

- `<文档路径>`：接口文档的相对路径（基于 `--repo`）或绝对路径
- `--repo`：代码仓库根目录，默认为当前目录

## 示例

```bash
# 在仓库根目录下运行
cd asc-devkit-master
node ../api_locator/src/locate-api.js docs/api/SIMD-API/基础API/工具接口/数学计算/NumericLimits/Lowest.md

# 指定仓库路径
node src/locate-api.js docs/api/SIMD-API/基础API/工具接口/数学计算/NumericLimits/Lowest.md --repo ./asc-devkit-master
```

输出：

```
[include]
  include/basic_api/kernel_operator_limits_intf.h
[tests]
  tests/api/basic_api/ascendc_case_mc62cm12aa/ascendc_case_mc62cm12aa_basic/test_operator_numeric_limits.cpp
  tests/api/basic_api/ascendc_case_ascend950pr_9599/ascendc_case_ascend950pr_9599_aiv_basic/test_operator_numeric_limits.cpp
```

## 输出说明

按文件所在顶层目录分类输出：

| 类别 | 含义 |
|------|------|
| `include` | API 声明头文件 |
| `impl` | API 实现文件 |
| `tests` | 测试用例文件 |

## 支持的 API 类型

basic_api、adv_api、simt_api、tensor_api、c_api、aicpu_api、utils

## 作为模块使用

```js
import { APILocator } from "./src/api-locator.js";

const locator = new APILocator("/path/to/asc-devkit");
const apiName = APILocator.extractApiName("/path/to/doc.md");
const info = locator.determineType(apiName);
const implFiles = await locator.findImplFiles(info.api_type, info.decl_file, apiName);
const testFiles = await locator.findTestFiles(info.api_type, apiName);
```
