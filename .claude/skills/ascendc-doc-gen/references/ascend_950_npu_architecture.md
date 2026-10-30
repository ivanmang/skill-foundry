# 昇腾950 NPU架构前置知识

> 来源：`C:\Users\tzh19\Downloads\昇腾950 NPU架构白皮书.pdf`。
> 用途：本文件作为 `ascendc-doc-gen` skill 执行前读取的领域知识，帮助理解 AscendC API 文档中的架构术语、存储层级、执行单元和数据搬运语义。
> 说明：架构事实来自上述白皮书；TPosition、Tensor 类型和最终文档写作边界结合当前 skill 既有术语规则与文档生成规则整理。
> 边界：本文件只作为领域背景和术语约束，不作为 API 产品支持、函数原型、参数约束或数据类型支持的代码证据。API 事实仍必须来自源码、预处理产物和各阶段报告。


## 1. 与当前 skill 直接相关的结论

- 昇腾950系列包含昇腾950PR和昇腾950DT，两者采用共架构设计，面向不同应用场景配置不同片上内存容量和带宽。
- 当前 skill 最终文档仍只能使用 `references/chip_mapping.md` 中定义的对外产品型号。涉及昇腾950PR/昇腾950DT时，最终文档应沿用 `<term>Ascend 950PR/Ascend 950DT</term>` 这一产品口径，不得新增“昇腾950PR芯片”“昇腾950DT芯片”“AI Die”等产品支持表行。
- 昇腾950基于第三代DaVinci架构。与 AscendC 文档生成相关的重点是 AI Core 内部的 Cube Core、Vector Core、Local Memory、数据搬运和同步机制。
- 白皮书中的架构能力只能帮助理解术语和表述方式，不能据此推断某个 API 在 Ascend 950PR/Ascend 950DT 上可用。产品支持必须由 `__NPU_ARCH__`、有效代码链路、预处理产物和 `chipdiff` 阶段确认。

## 2. 产品与系统层级

- 昇腾950芯片由 AI Die、IO Die 和高速片上内存模块构成，整体呈现统一内存访问的 Chiplet 架构。
- AI Die 是计算 Die，IO Die 是通信 Die。二者是芯片内部组成，不是最终 API 文档中的产品型号。
- Device 指 Host-Device 架构中的设备侧，在白皮书语境下指昇腾950系列 NPU 芯片；Host 指主机侧 CPU。
- AI CPU 是芯片内通用处理核心，主要承担控制类任务、调度类任务和部分 CPU 类算子任务。AscendC API 文档通常不应把 AI CPU 写成 AI Core 计算单元。
- STARS 是系统任务和资源调度模块，可调度 AIC、AIV、AI CPU、DVPP、SDMA、UB、CCU 等资源。除非 API 约束或源码明确涉及调度行为，否则最终 API 文档不需要展开 STARS 机制。

## 3. AI Core、AIC 和 AIV

- 昇腾950的 AI 子系统基于第三代 DaVinci 架构。一个 AI 子系统包含 Cube Core 和 Vector Core。
- 在 AI Core 分离架构下：
  - AIC 指 AI Cube Core，是一组 Cube Core 和 Vector Core 组合中的 Cube Core。
  - AIV 指 AI Vector Core，是一组 Cube Core 和 Vector Core 组合中的 Vector Core。
- Cube Core 面向矩阵/张量计算，适合 GEMM、FlashAttention 等以矩阵运算为核心的场景。
- Vector Core 面向向量计算、元素级计算、格式转换、量化/反量化和不规则控制流辅助计算。
- 文档中不得把 AIC/AIV、Cube Core/Vector Core 拆成产品支持表行。若源码显示执行单元差异，只能写入约束说明或功能差异描述。

## 4. Cube Core 相关知识

- Cube Core 是矩阵/张量计算核心，支持矩阵乘、张量计算和部分低精度格式相关能力。
- 第三代 Cube Core 增强了低精度格式支持，白皮书提到 HiF8、MXFP8、FP8、MXFP4 等格式能力。
- Cube Core 侧与 AscendC API 文档相关的存储层级主要包括：
  - L1 Buffer：较大容量的本地缓存，常用于缓存矩阵输入数据。
  - L0A Buffer：通常用于矩阵计算的左矩阵分块。
  - L0B Buffer：通常用于矩阵计算的右矩阵分块。
  - L0C Buffer：通常用于矩阵计算结果分块。
- Cube Core 可在结果回写 Unified Buffer 过程中进行数据格式转换或排布转换。最终文档只有在源码或提取报告明确说明时，才可把此能力写入某个 API 的功能或约束。

## 5. Vector Core 相关知识

- Vector Core 是向量计算核心，负责向量 ALU 计算、元素级处理、Softmax/GELU 等非矩阵类计算相关能力，以及多种格式转换。
- 昇腾950 Vector Core 支持 SIMD/SIMT 混合编程：
  - SIMD 适合规则访存、元素级计算和高吞吐向量计算，是主要算力路径。
  - SIMT 适合离散访问、Gather/Scatter、复杂分支等更强调编程灵活性的场景。
- Vector Core 在 Unified Buffer 与 Vector ALU 之间引入 RegFile 作为临时存储，以提升带宽和数据复用。
- AscendC 文档中涉及 SIMD/SIMT 时，应只在 API 类型、编程模型或约束有明确证据时描述；不得把白皮书中的一般架构能力写成某个 API 的支持能力。

## 6. 存储层级与表述规则

### 6.1 片上和片内存储层级

- 高速片上内存是缓存全局性数据的 DRAM，可理解为设备侧全局数据主要所在位置。
- L2 Cache 主要服务于 AIC/AIV 的 AI 计算，可缓存输入、输出和中间数据，减少访问片上内存的开销。
- AI CPU 有独立的 CPU L1/L2/L3 Cache 体系，不应与 AI Core 的 Local Memory 混写。
- AIC/AIV 内部 Local Memory 主要包括 L1 Buffer、L0 Buffer、Unified Buffer 等，缓存计算过程所需数据。

### 6.2 昇腾950主要本地存储容量

以下容量用于理解架构背景，不应在最终 API 文档中作为某个 API 的参数约束，除非源码、接口注释或阶段产物明确给出约束：

| 存储层级 | 白皮书中的容量口径 |
|---|---|
| L1 Buffer | 512KB per AI Core |
| L0A Buffer | 64KB per AI Core |
| L0B Buffer | 64KB per AI Core |
| L0C Buffer | 256KB per AI Core |
| Unified Buffer | 512KB per AI Core |
| L2 Cache | Up to 128MB |

### 6.3 TPosition 与 Buffer 表述

本节不是白皮书直接给出的 TPosition 定义，而是结合当前 skill 既有术语规则，对白皮书中的 Buffer/Memory 术语做文档生成约束。生成 AscendC API 文档时必须区分三层概念：

- Tensor 类型：`LocalTensor`、`GlobalTensor`。
- 逻辑位置：`TPosition`，如 A1、A2、B1、B2、CO1、VECIN、VECCALC、VECOUT。
- 物理存储/内存空间：L1 Buffer、L0A Buffer、L0B Buffer、L0C Buffer、Unified Buffer、Global Memory。

推荐表述：

- `类型为LocalTensor，支持的TPosition为A2/B2。`
- `TPosition为A2时，对应L0A Buffer。`
- `TPosition为B2时，对应L0B Buffer。`
- `TPosition为CO1时，对应L0C Buffer。`
- `TPosition为VECIN/VECCALC/VECOUT时，对应Unified Buffer。`
- `类型为GlobalTensor。`

禁止表述：

- `LocalTensor（L1 Buffer）`
- `GlobalTensor（Global Memory）`
- `L0A Buffer（A2）`
- `L0B Buffer（B2）`
- `L0ABuffer`、`L0BBuffer`
- 把 `LocalTensor`/`GlobalTensor` 直接拼成数据通路，如 `Local->Local`、`GM->Local`

## 7. 数据搬运与排布转换

- NDDMA 是 AI Core 内置的多维 DMA 数据搬运引擎，支持多维数据 Layout 搬运和变换。
- 白皮书描述 NDDMA 可用于全局内存到 Unified Buffer 的多维重排、转置或规律间隔数据搬运，并可降低手工地址生成复杂度。
- 若某个 AscendC API 明确涉及 NDDMA、DataCopy、多维搬运、layout 转换、NCHW/NHWC、转置或对齐转换，文档可使用“数据搬运”“数据排布转换”“多维重排”等表述。
- 只有源码或阶段产物明确说明 API 使用 NDDMA 时，才可写“该 API 使用 NDDMA”或把 NDDMA 作为功能特性；否则只能作为理解背景。

## 8. Cube-Vector 融合与内部数据通路

- 昇腾950支持 Cube Core 和 Vector Core 之间的内部数据通路，白皮书强调该能力可降低 Cube-Vector 融合算子中的数据搬运开销。
- 支持 Cube L1 Buffer 和 Vector Unified Buffer 的直接数据传递通道。
- 该知识可帮助理解涉及 FlashAttention、GEMM 后处理、量化、Softmax 等 Cube-Vector 融合 API 的数据流描述。
- 最终 API 文档中只有在 `2_extract.md` 或源码明确给出数据通路时，才写具体通路；否则保留为 `【待开发补齐】`，不要自行推断。

## 9. 同步机制

- 白皮书提到昇腾950新增 BufferID 同步机制，可通过类似 `get_buf()` / `rel_buf()` 的方式表达内部存储占用和释放。
- 旧式 `set_flag` / `wait_flag` 同步和 BufferID 同步都属于同步机制背景。
- 最终 API 文档只有在函数原型、接口注释、示例或实现代码直接暴露同步要求时，才需要描述同步约束；不要把架构级同步能力写成所有 API 的通用使用要求。

## 10. L2 Cache、Cache Hint 与 CMO

- 昇腾950的 L2 Cache 可缓存 AIC/AIV 输入、输出和中间数据，降低访问片上内存成本。
- L2 Cache 支持 Cache Hint 相关策略，软件可根据数据复用关系影响缓存分配和替换。
- CMO 是通过 SDMA 实现的 L2 Cache 管理机制，包含预取、预写回、无效化、冲刷等策略。
- 这些内容通常属于性能优化和系统调优背景。除非某个 API 的参数、配置结构体或示例明确包含 cache hint、CMO、prefetch、writeback、invalid、flush 等字段或调用，否则最终 API 文档不应主动添加相关约束。

## 11. 数据类型和精度格式

- 白皮书提到昇腾950架构支持 TF32、FP16、BF16、FP8、MXFP8、HiF8、INT8、MXFP4 等精度格式。
- 这只是架构级能力，不等价于所有 AscendC API 都支持这些数据类型。
- 生成 API 文档时，数据类型支持必须来自接口注释、模板约束、`SupportType`、`static_assert`、kernel_check、tiling 校验、底层 intrinsic 或 `1_chipdiff.md`/`2_extract.md`。
- 不得因为白皮书出现某种格式，就在参数说明中加入该 API 支持该格式。

