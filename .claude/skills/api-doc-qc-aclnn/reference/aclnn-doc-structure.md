# ACLNN 算子文档结构

## 1. 文档顶层结构

```
aclnn<算子名>.md
├── 标题：# aclnnXxx&aclnnInplaceXxx（算子名称）
├── 在线文档链接
├── 产品支持情况
├── 功能说明
├── 函数原型
├── [接口 1] aclnnXxxGetWorkspaceSize
│   ├── 参数说明（8 列表格）
│   └── 返回值（错误码表格）
├── [接口 2] aclnnXxx
│   ├── 参数说明（3 列表格）
│   └── 返回值
├── [接口 3] aclnnInplaceXxxGetWorkspaceSize（如有）
│   ├── 参数说明（8 列表格）
│   └── 返回值（错误码表格）
├── [接口 4] aclnnInplaceXxx（如有）
│   ├── 参数说明（3 列表格）
│   └── 返回值
├── 约束说明
└── 调用示例
```

---

## 2. 各章节详细说明

### 2.1 产品支持情况

**位置**: 文档开头
**格式**: 表格形式

| 字段 | 说明 |
|------|------|
| 产品 | 必须使用 `<term>` 标记，符合 HTML 语法 |
| 是否支持 | 支持打 √，不支持打 × |

**产品列表顺序（固定）**:
1. Ascend 950PR/Ascend 950DT
2. Atlas A3 训练系列产品/Atlas A3 推理系列产品
3. Atlas A2 训练系列产品/Atlas A2 推理系列产品
4. Atlas 200I/500 A2 推理产品
5. Atlas 推理系列产品
6. Atlas 训练系列产品

**注意事项**:
- aclnn 不涉及麒麟芯片
- 产品名必须加 `term` 标记

---

### 2.2 功能说明

**位置**: 产品支持情况之后
**内容要求**:
1. 接口功能：说明接口功能、计算逻辑、使用场景
2. 计算公式：复杂算子需提供公式，变量需解释
3. 多个接口区别：如多个 aclnn 接口在同一文档，说明区别

**格式示例**:
```markdown
- 接口功能：xxx
- 计算公式：
  $$
  out_i = self_i + alpha \times other_i
  $$
```

---

### 2.3 函数原型

**位置**: 功能说明之后
**内容要求**:
1. 介绍两段式接口调用流程
2. 每个接口一个单独的代码块
3. 每行一个参数，参数缩进对齐
4. 标明 Cpp 语言类型

**接口顺序**:
1. aclnnXxxGetWorkspaceSize
2. aclnnXxx
3. aclnnInplaceXxxGetWorkspaceSize（如存在）
4. aclnnInplaceXxx（如存在）

---

### 2.4 各接口详细说明

#### 2.4.1 第一段接口（GetWorkspaceSize）

**小节标题**: `## aclnnXxxGetWorkspaceSize`

**子结构**:
```
- 参数说明（8 列表格）
- 返回值（错误码表格）
```

**参数说明表格（8 列）**:
| 列名 | 宽度 | 说明 |
|------|------|------|
| 参数名 | 180px | 参数名 (类型)，不能换行 |
| 输入/输出 | 120px | 输入/输出/输入输出 |
| 描述 | 300px | 参数含义 + 公式变量映射 |
| 使用说明 | 350px | 空 Tensor 支持度、约束等 |
| 数据类型 | 250px | 仅 aclXxx 类型参数需填写 |
| 数据格式 | 100px | ND、FRACTAL_NZ 等 |
| 维度 (shape) | 100px | 维度范围如 0-8 |
| 非连续 Tensor | 100px | √/×/- |

**返回值表格（3 列）**:
| 列名 | 宽度 | 说明 |
|------|------|------|
| 返回值 | 300px | 错误码名称，不能换行 |
| 错误码 | 150px | 错误码数值 |
| 描述 | 550px | 导致错误的原因 |

---

#### 2.4.2 第二段接口（执行接口）

**小节标题**: `## aclnnXxx`

**子结构**:
```
- 参数说明（3 列表格）
- 返回值
```

**参数说明表格（3 列）**:
| 列名 | 宽度 | 说明 |
|------|------|------|
| 参数名 | 180px | 不能换行 |
| 输入/输出 | 100px | 输入/输出 |
| 描述 | 720px | 参数功能描述 |

**返回值格式**:
```markdown
aclnnStatus：返回状态码，具体参见 [aclnn 返回码](链接)。
```

---

### 2.5 约束说明

**位置**: 所有接口说明之后
**内容要求**:

**必选项**:
1. 确定性计算说明（三选一）:
   - aclnnXxx默认确定性实现。
   - aclnnXxx默认非确定性实现，支持通过aclrtCtxSetSysParamOpt开启确定性。
   - aclnnXxx默认非确定性实现，不支持通过aclrtCtxSetSysParamOpt开启确定性。

**可选项**:
- 输入 shape 限制
- 输入值域限制
- 输入属性限制
- 输入数据类型限制
- 其他限制（按产品区分）

**复杂约束格式**（使用 details/summary）:
```markdown
- <term>产品名</term>:

  <details>
  <summary>场景名称约束</summary>

  - 约束内容

  </details>
```

---

### 2.6 调用示例

**位置**: 文档末尾
**内容要求**:
1. 编译运行话术固定
2. 不同芯片 demo 不同时，区分芯片写作
3. 代码段设置语言类型 Cpp

**格式**:
```markdown
- <term>产品名 1</term>、<term>产品名 2</term>:

  ```Cpp
  // 示例代码
  ```
```

---

## 3. 表格样式规范

### 3.1 8 列表格（第一段接口参数说明）

```html
<table style="undefined;table-layout: fixed; width: 1500px">
<colgroup>
<col style="width: 180px">
<col style="width: 120px">
<col style="width: 300px">
<col style="width: 350px">
<col style="width: 250px">
<col style="width: 100px">
<col style="width: 100px">
<col style="width: 100px">
</colgroup>
...
</table>
```

### 3.2 3 列表格（错误码/第二段接口参数）

```html
<table style="undefined;table-layout: fixed; width: 1000px">
<colgroup>
<col style="width: 300px">
<col style="width: 150px">
<col style="width: 550px">
</colgroup>
...
</table>
```

---

## 4. 质检规则映射

| 章节 | 质检规则 |
|------|----------|
| 产品支持情况 | 检查产品列表完整性、term 标记、支持度说明 |
| 功能说明 | 检查接口功能描述、计算公式、示例 |
| 函数原型 | 检查两段式接口说明、代码块格式 |
| 参数说明 | 检查表格字段完整性、数据类型、约束说明 |
| 返回值 | 检查错误码表格、返回值说明 |
| 约束说明 | 检查确定性说明、芯片差异约束 |
| 调用示例 | 检查代码完整性、芯片区分 |

