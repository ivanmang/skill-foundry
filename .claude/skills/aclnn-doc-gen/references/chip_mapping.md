# 芯片→产品型号映射表

> **使用场景**：从算子代码中识别出芯片标识后，将其替换为面向外部用户的对外产品型号。

## 完整映射表

### chip_mapping（芯片标识 → 产品型号）

共 **20 条**映射规则：

| 芯片标识（代码中） | 映射到的产品型号 | 匹配方式 |
|------------------|----------------|---------|
| Ascend 910D | Ascend 950PR/Ascend 950DT | 精确匹配 |
| Ascend 910_95 | Ascend 950PR/Ascend 950DT | 精确匹配 |
| Ascend 950 | Ascend 950PR/Ascend 950DT | 精确匹配 |
| Ascend 910C | Atlas A3 训练系列产品/Atlas A3 推理系列产品 | 精确匹配 |
| Ascend 910_93 | Atlas A3 训练系列产品/Atlas A3 推理系列产品 | 精确匹配 |
| Ascend 910B* | Atlas A2 训练系列产品/Atlas A2 推理系列产品 | **前缀匹配** |
| Ascend 310B* | Atlas 200I/500 A2 推理产品 | **前缀匹配** |
| Ascend 310P AIC | Atlas 推理系列产品AI Core | 精确匹配 |
| Ascend 310P AIV | Atlas 推理系列产品Vector Core | 精确匹配 |
| Ascend 310P* | Atlas 推理系列产品 | **前缀匹配** |
| Ascend 910 | Atlas 训练系列产品 | 精确匹配 |
| Ascend 910A | Atlas 训练系列产品 | 精确匹配 |
| 1952 | MC62CM12AA AI处理器 | 精确匹配 |
| Ascend 610Lite | BS9SX2A AI处理器 | 精确匹配 |
| Ascend 310M | AS31XM1X AI处理器 | 精确匹配 |
| Ascend 610B | BS9SX1A AI处理器 | 精确匹配 |
| Ascend 610 AIC | 昇腾610 AI处理器AI Core | 精确匹配 |
| Ascend 610 VEC | 昇腾610 AI处理器Vector Core | 精确匹配 |
| Hi3796CS | SoC（TsnsC） | 精确匹配 |
| SD3403 | SoC（OPTG） | 精确匹配 |
| Ascend035 | IPV350 | 精确匹配 |

### npu_arch_mapping（__NPU_ARCH__ 值 → 产品型号）

共 **11 条**映射规则：

| __NPU_ARCH__ 值 | 映射到的产品型号 |
|-----------------|----------------|
| 3510 | Ascend 950PR/Ascend 950DT |
| 3101 | Ascend 950PR/Ascend 950DT |
| 2201 | Atlas A3 训练系列产品/Atlas A3 推理系列产品 |
| 2201 | Atlas A2 训练系列产品/Atlas A2 推理系列产品 |
| 3002 | Atlas 200I/500 A2 推理产品 |
| 2002 | Atlas 推理系列产品AI Core、Atlas 推理系列产品Vector Core |
| 1001 | Atlas 训练系列产品 |
| 5102 | MC62CM12AA AI处理器 |
| 3102 | BS9SX2A AI处理器 |
| 2102 | BS9SX1A AI处理器 |
| 3505 | IPV350 |

## 映射规则

### 匹配优先级

1. **精确匹配优先于前缀匹配**：当芯片标识同时满足精确匹配和前缀匹配时，使用精确匹配的结果。例如 `Ascend 910` 精确匹配 → `Atlas 训练系列产品`，不会被 `Ascend 910B*` 前缀捕获
2. **较长的标识优先于较短的标识**：当两个前缀都能匹配时，较长的优先。例如 `Ascend 310P AIC`（精确）优先于 `Ascend 310P*`（前缀）

### 前缀匹配规则

映射表中带 `*` 号的标识表示前缀匹配：
- `Ascend 910B*`：标识以 `910B` 开头即匹配（如 `ascend910b`、`ascend910b3`、`ASCEND910B_DI`）
- `Ascend 310B*`：标识以 `310B` 开头即匹配（如 `ascend310b`、`ascend310b4`）
- `Ascend 310P*`：标识以 `310P` 开头即匹配（如 `ascend310p`、`ascend310p3`）

匹配时忽略大小写、空格和下划线差异。

### 易混淆映射（高频出错）

以下芯片标识只有一个字母之差，但映射结果完全不同，映射时必须逐字母核对：

| 芯片标识 | 映射到 | 易混淆点 |
|---------|--------|---------|
| `Ascend 310P*` | **Atlas 推理系列产品** | P → 推理系列 |
| `Ascend 310B*` | **Atlas 200I/500 A2 推理产品** | B → 200I/500 A2 |
| `Ascend 910`（精确） | **Atlas 训练系列产品** | 无后缀 |
| `Ascend 910A`（精确） | **Atlas 训练系列产品** | A 后缀 |
| `Ascend 910B*`（前缀） | **Atlas A2 训练系列产品/Atlas A2 推理系列产品** | B 前缀 |
| `Ascend 910C`（精确） | **Atlas A3 训练系列产品/Atlas A3 推理系列产品** | C 后缀 |
| `Ascend 910_93`（精确） | **Atlas A3 训练系列产品/Atlas A3 推理系列产品** | 下划线数字后缀 |
| `Ascend 910_95`（精确） | **Ascend 950PR/Ascend 950DT** | 下划线数字后缀 |

### 代码中芯片标识的常见形式

代码中同一芯片可能以不同形式出现，它们映射到同一产品型号：

| 芯片标识在代码中的常见形式 | 统一映射到 |
|----------------------|----------|
| `AddConfig("ascend910b", ...)` | 对 `Ascend 910B*` 做前缀匹配 |
| `SocVersion::ASCEND910B` | 对 `Ascend 910B*` 做前缀匹配（去掉 `SocVersion::` 前缀和下划线） |
| `NpuArch::DAV_2201` | 查 `npu_arch_mapping` 表中 `2201` → 同时映射到 `Atlas A3 训练系列产品/Atlas A3 推理系列产品` 和 `Atlas A2 训练系列产品/Atlas A2 推理系列产品` |
| `__NPU_ARCH__ == 2201` | 同上 |
| `IsRegBase(...)` / `isRegbase(...)` | 直接映射到 `Ascend 950PR/Ascend 950DT`（无需查表） |
| `__DAV_C220_CUBE__`、`__DAV_C220_VEC__` | `C220` 对应 `__NPU_ARCH__` 值 `2201`，查 `npu_arch_mapping` 表 |

### 代码标识 → 映射表的匹配方法

1. `AddConfig("xxx", ...)` 中的 `xxx`：直接用 `xxx` 去 `chip_mapping` 表匹配
2. `SocVersion::ASCEND_XXX`：将枚举名转换为芯片标识格式（如 `ASCEND910B` → `Ascend 910B`），再查 `chip_mapping` 表
3. `NpuArch::DAV_NNNN` 或 `__NPU_ARCH__ == NNNN`：提取数字部分 `NNNN`，查 `npu_arch_mapping` 表
4. `IsRegBase` / `isRegbase`：直接映射到 `Ascend 950PR/Ascend 950DT`
5. `__DAV_xxx__` 宏：`xxx` 中的数字部分对应 `__NPU_ARCH__` 值（如 `C220` → `2201`），查 `npu_arch_mapping` 表

## 文档输出规范

### 文档中允许出现的产品型号

最终文档**只允许**出现以下 6 个产品型号，其余均不得出现在文档中：

1. Ascend 950PR/Ascend 950DT
2. Atlas A3 训练系列产品/Atlas A3 推理系列产品
3. Atlas A2 训练系列产品/Atlas A2 推理系列产品
4. Atlas 200I/500 A2 推理产品
5. Atlas 推理系列产品
6. Atlas 训练系列产品

映射表中的其他产品（MC62CM12AA AI处理器、BS9SX2A AI处理器、昇腾610 AI处理器、SoC、IPV350 等）**只在内部分析报告中作为证据引用时使用芯片标识，不作为独立产品出现在最终文档中**。

### 文档中禁止出现的内容

以下内部标识严禁出现在最终文档中，必须替换为上述产品型号：

| 禁止出现 | 应替换为 |
|---------|---------|
| `ascend910b`、`ASCEND910B` | Atlas A2 训练系列产品/Atlas A2 推理系列产品 |
| `ascend910_93` | Atlas A3 训练系列产品/Atlas A3 推理系列产品 |
| `ascend910_95`、`昇腾910_95 AI处理器` | Ascend 950PR/Ascend 950DT |
| `ascend310p`、`ASCEND310P` | Atlas 推理系列产品 |
| `ascend310b`、`ASCEND310B` | Atlas 200I/500 A2 推理产品 |
| `SocVersion::`、`NpuArch::DAV_` 等枚举值 | 对应产品型号 |
| `3510`、`2210`、`2201`、`2002` 等 NPU_ARCH 数值 | 对应产品型号 |
