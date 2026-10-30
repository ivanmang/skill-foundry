# 术语和缩略语

## A-E

| 术语/缩略语 | 含义 |
|------------|------|
| A1 | AscendC::TPosition::A1代表设备上用于矩阵计算的逻辑内存，用于存放左矩阵，物理存储对应AI Core的L1 Buffer。 |
| A2 | AscendC::TPosition::A2代表设备上用于矩阵计算的逻辑内存，用于存放小块左矩阵（如经过分割、适配L0A Buffer容量的分块），物理存储对应AI Core的L0A Buffer。 |
| AddrReg | Address Register（地址寄存器），是用于存储地址偏移量的寄存器。 |
| AIC | 在AI Core分离模式下，一组Cube Core和Vector Core组合中的Cube Core。 |
| AIV | 在AI Core分离模式下，一组Cube Core和Vector Core组合中的Vector Core。 |
| AccumulatedRelativeError | 累积相对误差算法。精度比对算法之一，计算结果取值范围为0到无穷大，值越接近于0，表明越相近，值越大，表明差距越大。 |
| ADK | Ascend Development Kit，解决方案提供的开发者套件包。通过安装相关软件包后获得开发必需的API、库、工具链等开发组件。 |
| AHS | Active Hot-Standby，主备热倒换系统。主要指两个完整独立的SoC主备双活子系统，各自有完整独立的Sensor输入、算力和资源，运行相互备份的业务，支持异常时主备热倒换功能。 |
| AI | Artificial Intelligence，人工智能。研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。 |
| AI Core | AI处理器的计算核心，负责执行矩阵、矢量、标量计算密集的任务。使用Ascend C编程语言开发的算子运行在AI Core上。 |
| AI CPU | 昇腾AI处理器上提供的用于通用计算的CPU，主要负责AI CPU算子计算和确定性任务的调度。 |
| AIPP | Artificial Intelligence Pre-Processing，AI预处理。AIPP用于在AI Core上完成图像预处理，包括改变图像尺寸、色域转换（转换图像格式）、减均值/乘系数（改变图像像素），数据处理之后再进行真正的模型推理。 |
| AMCT | Ascend Model Compression Toolkit，昇腾模型压缩工具。是一个针对昇腾芯片亲和的深度学习模型压缩工具包，提供量化、张量分解等多种模型压缩特性，压缩后模型体积变小，部署到AI处理器上后可使能低比特运算，提高计算效率，达到性能提升的目标。 |
| AOE | Ascend Optimization Engine，昇腾调优引擎。用于封装调优过程中的ATC编译及acl运行服务接口，提供并行调优功能。 |
| AOL | Ascend Operator Library，昇腾算子库。 |
| AOS | AtelierOS，无人驾驶操作系统。 |
| AOS-Core | AOS-Core，AOS安全隔离运行环境。从标准Linux内核中划分出一些核、内存，进行独立的管理、调度、中断处理、内存管理等，必要时转调Linux标准内核完成复杂的系统调用。通过这种方式提供比标准Linux内核更高隔离性、安全性、实时性的专用调度、执行环境。 |
| AscendCL | Ascend Computing Language，昇腾编程语言。提供运行时管理、单算子调用、模型推理、媒体数据处理等API，能够实现利用底层硬件计算资源，在CANN平台上进行深度学习推理计算、图形图像预处理、单算子加速计算等。 |
| Ascend EP | Ascend Endpoint昇腾AI处理器作为终端节点（从控节点）。主要功能是配合主设备（X86，ARM等各种Server），快速高效的处理推理、训练、图像识别等工作，例如PCIe加速卡。 |
| Ascend IR | Ascend Intermediate Representation，昇腾AI处理器专用的、用于表达计算流程的抽象数据结构。在本文档中，若无特殊说明，IR默认指代Ascend IR。 |
| Ascend RC | Ascend Root Complex，昇腾AI处理器作为根组件（主控节点）。提供主机控制功能，主要应用于边缘侧。 |
| ATC | Ascend Tensor Compiler，昇腾张量编译器。是异构计算架构CANN体系下的模型转换工具，它可以将开源框架的网络模型以及Ascend IR定义的单算子描述文件（json格式）转换为AI处理器支持的.om格式离线模型。模型转换过程中，ATC会进行算子调度优化、权重数据重排、内存使用优化等具体操作，对原始的深度学习模型进行进一步的调优，从而满足部署场景下的高性能需求，使其能够高效执行在AI处理器上。 |

## B

| 术语/缩略语 | 含义 |
|------------|------|
| B1 | AscendC::TPosition::B1代表设备上用于矩阵计算的逻辑内存，用于存放右矩阵，物理存储对应AI Core的L1 Buffer。 |
| B2 | AscendC::TPosition::B2代表设备上用于矩阵计算的逻辑内存，用于存放小块右矩阵（如经过分割、适配L0B Buffer容量的分块），物理存储对应AI Core的L0B Buffer。 |
| BiasTable Buffer | 偏置存储，AI Core内部物理存储单元，通常用于存储矩阵计算所需的Bias（偏置）数据，与逻辑内存AscendC::TPosition::C2相对应。 |
| Block | Block在不同场景下具有多种含义，通常情况下指AI Core的逻辑核。典型场景有：AI Core逻辑核：一个Block表示一个AI Core的逻辑核，其BlockID是以0为起始的逻辑编号；DataBlock：一个DataBlock表示一条NPU矢量计算指令处理的数据单元，大小通常为32字节，一条指令可同时处理多个DataBlock；基本块：表示一次计算需要的典型数据块大小。 |
| BlockID | 以0为起始的AI Core逻辑编号，可以比实际硬件核数大。 |
| BlockDim | 参与计算的逻辑AI Core核数，在调用核函数时由开发者指定，其值一般等于或大于实际物理核数。 |
| Broadcast | 广播，一种张量操作机制。通过广播，较小的张量可以自动扩展以匹配较大的张量的形状。 |
| Batch | 模型训练的一次迭代（即一次梯度更新）中使用的样本集。 |
| Batch size | 模型迭代一次，使用的样本集的大小。 |
| BIU | Bus Interface Unit，总线接口单元。AI Core与总线交互的接口。 |

## C

| 术语/缩略语 | 含义 |
|------------|------|
| CANN | Compute Architecture for Neural Networks，异构计算架构。CANN是昇腾针对AI场景推出的异构计算架构，对上支持多种AI框架，对下服务AI处理器与编程，发挥承上启下的关键作用，是提升昇腾AI处理器计算效率的关键平台。同时针对多样化应用场景，提供高效易用的编程接口，支持用户快速构建基于昇腾平台的AI应用和业务。 |
| CCU | Collective Communication Unit，集合通信加速单元。 |
| Cluster | Cluster Dashboard SubSystem，仪表显示子系统。汽车仪表盘子系统，除掉负责显示传统的油量、车速、转速及车身状态基本信息以外，下一代仪表盘还要强调酷炫的显示效果和丰富的显示内容，甚至包括地图、感知规控结果、联网的实时信息等，运行于虚拟化隔离出的泰山核上。 |
| CMI | Camera Management Platform Interface，相机管理平台接口。 |
| CNN | Convolutional Neural Network，卷积神经网络。是一种前馈神经网络，人工神经元可以响应周围单元，可以进行大型图像处理。 |
| CosineSimilarity | 余弦相似度算法。精度比对算法之一，计算结果取值范围为[-1,1]，比对的结果如果越接近1，表示两者的值越相近，越接近-1意味着两者的值越相反。 |
| CTRL CPU | Control CPU，用于外部通信、管理面以及非确定性调度的任务。 |
| Cube | AI Core上的Cube计算单元，负责执行矩阵运算。Cube每次执行可完成两个float16类型的16x16矩阵的乘法操作。 |
| CQE | Completion Queue Element，RDMA技术中的完成队列元素。CQE是硬件完成任务后返回给软件的完成报告，用于告知操作是否成功及结果。 |
| C1 | AscendC::TPosition::C1代表设备上用于矩阵计算的逻辑内存，用于存放Bias（偏置）数据，物理存储对应AI Core的L1 Buffer或Unified Buffer。 |
| C2 | AscendC::TPosition::C2代表设备上用于矩阵计算的逻辑内存，用于存放小块Bias（偏置）数据（如经过分割、适配BT Buffer容量的分块），物理存储对应AI Core的BT Buffer或L0C Buffer。 |
| C2PIPE2GM | AscendC::TPosition::C2PIPE2GM代表设备上用于矩阵计算的逻辑内存，用于存放量化参数，物理存储对应AI Core的Fixpipe Buffer。 |
| Cache Line | 缓存（DCache、ICache、L2 Cache）中的最小数据单位。 |
| Core | 拥有独立Scalar计算单元的计算核，Scalar计算单元承担了核内的指令发射等功能，也称之为核内的调度单元。 |
| CO1 | AscendC::TPosition::CO1代表设备上用于矩阵计算的逻辑内存，用于存放小块矩阵计算结果（如经过分割的矩阵计算结果分块），物理存储对应AI Core的L0C Buffer。 |
| CO2 | AscendC::TPosition::CO2代表设备上用于矩阵计算的逻辑内存，用于存放矩阵计算结果（如原始矩阵的最终计算结果），物理存储对应Global Memory或AI Core的Unified Buffer。 |
| Compute | Ascend C算子编程范式中典型的三个阶段之一，负责完成计算任务。 |
| CopyIn | Ascend C算子编程范式中典型的三个阶段之一，负责将待计算数据从Global Memory搬运到Local Memory。 |
| CopyOut | Ascend C算子编程范式中典型的三个阶段之一，负责将计算结果从Local Memory搬运到Global Memory。 |
| Core ID | AI Core核的物理编号，与实际硬件核数一一对应。 |
| Cube Core | 矩阵计算核，专注于矩阵计算。由Scalar调度单元、矩阵计算单元、搬运单元等组成，不包括矢量计算单元。 |

## D

| 术语/缩略语 | 含义 |
|------------|------|
| DataFlow | 用于描述完整的计算流，该计算流由一个或多个计算处理点采用数据队列以数据驱动方式组成。 |
| DCLS | Dual Core Lockstep，成对锁步执行核。同一条指令通过两个核并行执行，执行结果相互校验结果是否一致以确定是否发生了指令执行异常，以这种方法提高系统的指令执行安全性。 |
| DDP | Distributed Data Parallel，分布式数据并行。 |
| DDR | Double Data Rate，双倍数据速率。严格的说DDR应该叫DDR SDRAM，人们习惯称为DDR，其中，SDRAM是Synchronous Dynamic Random Access Memory的缩写，即同步动态随机存取存储器。而DDR SDRAM是Double Data Rate SDRAM的缩写，是双倍速率同步动态随机存储器的意思。DDR内存是在SDRAM内存基础上发展而来的，仍然沿用SDRAM生产体系，因此对于内存厂商而言，只需对制造普通SDRAM的设备稍加改进，即可实现DDR内存的生产，可有效的降低成本。与传统的单数据速率相比，DDR技术实现了一个时钟周期内进行两次读/写操作，即在时钟的上升沿和下降沿分别执行一次读/写操作。 |
| DDS | Data Distribution Service，数据分布式通信服务。由OMG（Object Management Group）定义的一套弹性、实时性、高性能、可交互的基于发布、订阅模型的分布式数据通信规范。 |
| DL | Deep Learning，深度学习。是机器学习的分支，是一种试图使用包含复杂结构或由多重非线性变换构成的多个处理层对数据进行高层抽象的算法。 |
| DP | Data Processing SubSystem，数据处理子系统。主要用于运行IO外设接入、管理，数据采集、接收，数据感知计算，以及各种辅助驾驶相关业务，如定位、融合、推理、路径规划等，处理各种辅助驾驶管理面业务软件和云端互联的子系统。 |
| DSF | Deterministic Schedule Framework，确定性调度框架。主要用于承载数据面各个业务节点之间的确定性调度、通信需求，由AI Daemon、BufferMgr、EventQueue、QueueScheduler、EventScheduler等模块相互配合、支撑实现的基于消息队列调度+共享内存零拷贝实现的跨进程时间确定的通信调度框架。 |
| DSS | Display Subsystem，显示子系统。 |
| DVPP | Digital Vision Pre-Processing，数字视觉预处理。提供对特定格式的视频和图像的进行解码、缩放等预处理操作，以及对处理后的视频、图像进行编码再输出的能力。 |
| DataBlock | 矢量计算指令处理的数据单元，大小通常为32字节，矢量计算指令执行一次，可同时处理多个DataBlock。 |
| DataBlock Stride | 矢量计算指令单次Repeat内DataBlock的间隔大小，即下次处理的起始数据地址与本次处理的起始数据地址之间的DataBlock个数。 |
| DCache | Data Cache，数据缓存。用于缓存Scalar计算单元近期可能被重复访问的数据段，以提升访问效率。 |
| Device | Device指安装了昇腾AI处理器的硬件设备，利用PCIe接口与主机Host侧连接，为Host提供神经网络计算能力。若存在多个Device，多个Device之间的内存资源不能共享。 |
| Dim3 | Dim3是用于定义单个线程块中三维线程结构的数据类型。使用AscendC::Simt::Dim3在启动SIMT VF时指定3个维度的取值，3个维度的乘积必须小于等于2048。 |
| DMA | Direct Memory Access，直接内存访问单元。负责数据搬运，包括Global Memory和Local Memory之间的数据搬运以及不同层级Local Memory之间的数据搬运 ，包含搬运单元MTE2、MTE3等。 |
| DoubleBuffer/DB | 双缓冲，并行领域常用的优化方式，通过创建多个持有数据的缓冲区（Buffer）提高数据处理的并行性。 |
| 单算子比对 | 精度比对工具里Tensor比对的一种方式。选择网络模型中一个或多个参与计算的算子进行精度比对。 |

## E

| 术语/缩略语 | 含义 |
|------------|------|
| ECC | Error Checking and Correction，错误检查和纠错技术。该技术在原来的数据位中增加校验位，通过检验位来检测数据错误，并具备错误纠正能力。 |
| EID | Entity ID，用于唯一标识功能实体的标识符，作为事务通信中发起或接收对象的标识。 |
| EMMC | Embedded Multimedia Card，多媒体存储卡。是一种新的存储技术，外部提供的接口和SD卡接口类似，内部存储介质为Flash，并且内建坏块管理系统。 |
| Epoch | 数据集的一次完整遍历。 |
| Elementwise | 元素级操作是对张量的每个元素独立进行的操作。每个元素的结果仅依赖于对应的输入元素。 |

## F-J

| 术语/缩略语 | 含义 |
|------------|------|
| Fixpipe | AI Core中负责将矩阵计算结果从L0C Buffer搬运到Global Memory或L1 Buffer的单元，搬运过程中随路完成量化、激活等操作。 |
| Fixpipe Buffer | AI Core内部物理存储单元，通常用于存储Fixpipe搬运过程中所需的量化参数等数据，与逻辑内存AscendC::TPosition::C2PIPE2GM相对应。 |
| FLOPS | Floating-Point Operations Per Second，每秒所执行的浮点运算次数。常被用来估算电脑的执行效能，尤其是在使用到大量浮点运算的科学计算领域中。正因为FLOPS字尾的那个S，代表秒，而不是复数，所以不能省略掉。 |
| Framework | NN框架执行引擎。包括开源主流框架TensorFlow、PyTorch、Caffe等，自研框架MindSpore。系统针对开源主流框架提供适配插件，从而可利用AI处理器加速计算能力。 |
| G | |
| GE | Graph Engine，图引擎。提供了Graph/Operator IR作为安全易用的构图接口集合，用户可以调用这些接口构建网络模型，设置模型所包含的图、图内的算子、以及模型和算子的属性。 |
| GEA | General Execution Area，通用执行区。运行在DP域AOS-Linux的通用OS环境，用于部署执行功能安全无关的管理类应用。 |
| Global Memory/GM | 设备端的主内存，AI Core的外部存储，用于存储大规模数据，但需要优化访问模式以提升性能。 |
| GPU | Graphics Processing Unit，图形处理器。GPU是一种专门在个人电脑、工作站、游戏机和一些移动设备（如平板电脑、智能手机等）上做图像和图形相关运算工作的微处理器。 |
| Graph模式 | MindSpore的静态图模式，将神经网络模型编译成一整张图，然后下发执行，性能高。 |
| H | |
| HCC | Huawei Compiler Collection，华为编译器。 |
| HCCL | Huawei Collective Communication Library，华为集合通信库。HCCL提供了深度学习场景中服务器间高性能集合通信的功能。 |
| HCCS | Huawei Cache Coherence System，华为缓存一致性系统。HCCS用于CPU/NPU之间的高速互联。 |
| HCCP | Huawei Collective Communication adaptive Protocol，集合通信适配协议。提供跨NPU设备通信能力，向上屏蔽具体通讯协议差异。 |
| HDC | Host Device Communication，主机设备通信。用于Host和Device之间通信模块，在Host和Device里面均有部署。 |
| HDR | High Dynamic Range，高动态范围。摄影术语，用来描述媒体应用，如数字影像和数字音频。 |
| HiCAID | Hisilicon Compute Architecture for Intelligent Device，海思智能设备计算架构。 |
| HiVA | Hisilicon Vehicle Application，海思车载应用统一通信运行时框架。 |
| HISS | High Security Susbsystem，高安全子系统 |
| HSM | Hardware Security Module，硬件安全模块。主要用于根证书保护、秘钥链验证、关键验签确认的高等级安全服务的子系统。 |
| Host | 指与设备端Device相连接的X86服务器、ARM服务器，会利用Device提供的NN（Neural-Network ）计算能力，完成业务。 |
| I | |
| IAM | Identity Access Management，身份接入管理。 |
| ICC | Inter-Cores Communication，单SoC内跨同构泰山核且跨OS间通信同步机制。 |
| IPC | IP Camera，网络摄像机。 |
| IPC | Inter-Process Communications，单SoC内跨异构核之间的简短通信同步机制。 |
| ISP | Image Signal Processing，图像信号处理。主要用来对前端图像传感器输出信号处理的单元，以匹配不同厂商的图像传感器。 |
| IBShare | IntraBlock Share，MIX场景下L1 Buffer上相同的A矩阵或B矩阵数据复用的一种机制。MIX场景下，A矩阵或B矩阵GM地址相同的时候，通过共享L1 Buffer，减少MTE2搬运。 |
| ICache | Instruction Cache，指令缓存。用于缓存最近或频繁使用的指令。极致性能优化时，需要关注如何降低ICache Miss（指令缓存未命中）。 |
| InferShape | 算子shape推导，仅在GE图模式时才使用。 实际的网络模型生成过程中，会先进行Tensor shape以及datatype的推导。这样可以在图执行之前，就知道各Tensor的数据类型和形状，提前校验其正确性；同时提前推理出算子的输出张量描述，包括张量的形状、数据类型及数据排布格式等信息，算子构图准备阶段就可以为所有的张量静态分配内存，避免动态内存分配带来的开销。 |
| J | |
| JPEGD | JPEG Decoder，JPEG图像解码器。提供对JPEG格式的图像进行解码的能力。 |
| JPEGE | JPEG Encoder，JPEG图像编码器。提供对图像进行编码输出为JPEG格式的能力。 |
| 精度比对 | 通过NPU运行生成的dump数据与Ground Truth（基于GPU/CPU运行生成的npy数据）进行比对。实现自主研发算子与业界标准算子运算结果的差异比较。 |

## K-O

| 术语/缩略语 | 含义 |
|------------|------|
| K | |
| Kernel | 核函数，是Device设备上执行的并行函数。核函数通过__global__修饰，多个核并行执行相同的核函数，其主要区别是不同核函数运行时具有不同的BlockID。 |
| Kernel Launch | 将kernel程序提交至硬件进行启动执行的过程。 |
| KFC | Kernel Function Call，是Ascend C提供的一种AI Cube和AI Vector核通信机制，可以让开发者以AI Vector核为视角直接编程，而无需关注AI Cube和AI Vector的核间同步与通信。此外，KFC的性能与手工实现核间同步和通信的性能基本持平，部分场景下通过流水隐藏实现更好的性能。 |
| KullbackLeiblerDivergence | KL散度算法。精度比对算法之一，计算结果取值范围为0到无穷大。KL散度越小，真实分布与近似分布之间的匹配越好。 |
| L | |
| L2 Cache | 二级缓存，专门用于存储频繁访问的数据，以便减少对Global Memory的读写。 |
| Lane | Warp中的每个线程称为Lane。 |
| LCM | Local Cache Memory，AscendC::TPosition::LCM代表临时共享的Unified Buffer空间，与VECCALC实现同样的功能。 |
| LocalTensor | 存放AI Core中Local Memory本地数据的Tensor。 |
| L0A Buffer | AI Core内部物理存储单元，通常用于存储矩阵计算的左矩阵，与逻辑内存AscendC::TPosition::A2相对应。 |
| L0B Buffer | AI Core内部物理存储单元，通常用于存储矩阵计算的右矩阵，与逻辑内存AscendC::TPosition::B2相对应。 |
| L0C Buffer | AI Core内部物理存储单元，通常用于存储矩阵计算的结果，与逻辑内存AscendC::TPosition::CO1相对应。 |
| L1 Buffer | AI Core内部物理存储单元，空间相对较大，通常用于缓存矩阵计算的输入数据。 矩阵计算的输入一般需要从GM搬运到L1 Buffer，然后分别搬运到L0A Buffer和L0B Buffer。L1 Buffer与逻辑内存AscendC::TPosition::A1、AscendC::TPosition::B1相对应。 |
| LLC | Last Level Cache，最后一级Cache。在访问内存之前调用的共享最高级别缓存通常称为最后一级缓存（LLC）。 |
| LLMs | Large Language Model，大语言模型。大语言模型是一种语言模型，由具有许多参数（通常数十亿个权重或更多）的人工神经网络组成，使用自监督学习或半监督学习对大量未标记文本进行训练。 |
| Local Memory | AI Core的内部存储，包括L1 Buffer、L0A Buffer、L0B Buffer、L0C Buffer、Unified Buffer等存储单元。 |
| Loss | 损失，预测值与实际值的偏差，深度学习用于判断模型好坏的一个标准。 |
| LPM | Low Power Management Subsystem，低功耗管理子系统。低功耗管理子系统，处于Always ON区域，用于系统的待机、唤醒等不同模式之间的进入和切换，运行于独立R52上。 |
| M | |
| MaxAbsoluteError | 最大绝对误差算法。精度比对算法之一，计算结果取值范围为0到无穷大，值越接近于0，表明越相近，值越大，表明差距越大。 |
| MaxRelativeError | 最大相对误差算法。精度比对算法之一，计算结果取值范围为0到无穷大，值越接近于0，表明越相近，值越大，表明差距越大。 |
| MeanAbsoluteError | 平均绝对误差算法。精度比对算法之一，计算结果取值范围为0到无穷大。MeanAbsoluteError趋于0，RootMeanSquareError趋于0，说明测量值与真实值越近似。MeanAbsoluteError趋于0，RootMeanSquareError越大，说明存在局部过大的异常值。MeanAbsoluteError越大，RootMeanSquareError等于或近似MeanAbsoluteError，说明整体偏差越集中。MeanAbsoluteError越大，RootMeanSquareError越大于MeanAbsoluteError，说明存在整体偏差，且整体偏差分布分散。不存在以上情况的例外情况，因为RMSE ≥ MAE恒成立。 |
| MeanRelativeError | 平均相对误差算法。精度比对算法之一，计算结果取值范围为0到无穷大，值越接近于0，表明越相近，值越大，表明差距越大。 |
| MD | Multi-Domains，多域。主要指单个SoC被物理隔离或虚拟化隔离出多个独立的运行域，如SD、DP、Cluster、ComIsolator，每个域具有自己独立的核、内存、IO、OS及软件栈。 |
| MDC | Mobile Data Center，移动数据中心。用于辅助驾驶的移动数据中心。 |
| MoE | Mixture-of-Experts，混合专家系统，是一种用于训练万亿参数量级模型的技术。MoE将预测建模任务分解为若干子任务，在每个子任务上训练一个专家模型（Expert Model），开发一个门控模型（Gating Model），该模型会根据输入数据分配一个或多个专家，最终综合多个专家计算结果作为预测结果。 |
| MP | Multi-Planes，多平面。主要指单个OS内的进程和资源被划分到多个不同的平面上，如管理面、数据面、通信面，相互具有访问隔离、权限控制、资源限制等约束。 |
| MTE1 | Memory Transfer Engine 1，AI Core的数据传递引擎，负责将数据从L1 Buffer搬运到L0A Buffer或L0B Buffer等。注意：不同硬件能力可能有差异。 |
| MTE2 | Memory Transfer Engine 2，AI Core的数据传递引擎，负责将数据从GM搬运到L1 Buffer、L0A Buffer、L0B Buffer、Unified Buffer等。注意：不同硬件能力可能有差异。 |
| MTE3 | Memory Transfer Engine 3，AI Core的数据传递引擎，负责将数据从Unified Buffer搬运到Global Memory、L1 Buffer等。注意：不同硬件能力可能有差异。 |
| Mask | 用于控制矢量计算指令每次Repeat内参与计算的元素，可通过连续模式和逐比特模式两种方式进行设置。 |
| MaskReg | 掩码寄存器，是一个256位的寄存器，用于指示在计算过程中RegTensor的哪些元素参与计算。 |
| Membase | Membase是指基于内存的架构。Membase架构中所有操作均基于内存进行，这意味着每次计算都需要从Local Memory加载数据，计算完成后将结果搬回Local Memory，中间计算结果都需要暂存在Local Memory上。 |
| N | |
| NCS | Neural Compute Server，神经计算服务器。NCS封装acl运行服务接口，可接受外部的上板请求，并且返回对应的性能数据。 |
| NIC | Network Interface Controller，网络接口控制器。也称为网络接口卡，网络适配器，LAN适配器，以及类似术语。是将计算机连接到计算机网络的计算机硬件组件。 |
| NN | Neural Network，神经网络。在机器学习和认知科学领域，是一种模仿生物神经网络的结构和功能的数学模型或计算模型。 |
| NPU | Neural-Network Processing Unit，神经网络处理器单元。采用"数据驱动并行计算"的架构，专门用于处理人工智能应用中的大量计算任务。 |
| NC1HWC0 | 一种五维数据格式，其中C0与硬件架构强相关，采用该格式可提升矩阵乘法的计算效率。 |
| NCHW | 按照[Batch, Channels, Height, Width]的排列顺序存储特征图数据。 |
| ND | 普通格式，N维张量。 |
| NHWC | 按照[Batch, Height, Width, Channels]的排列顺序存储特征图数据。 |
| O | |
| OP | 算子（Operator，简称OP），是深度学习算法中执行特定数学运算或操作的基础单元，例如激活函数（如ReLU）、卷积（Conv）、池化（Pooling）以及归一化（如Softmax）。通过组合这些算子，可以构建神经网络模型。 |
| OPAT | Operator Auto Tuning，算子自动调优。OPAT是一种提升算子性能的优化器。AOE将一张整图输入给OPAT，OPAT内部进行算子融合，将融合得到的图进行算子粒度切分，针对每一个融合算子子图生成不同的算子调优策略，从而实现最优的算子性能，并将得到的最优策略保存在算子知识库。 |
| OPP | Operator Package，算子库。 |
| OpType | 算子类型，一类算子的统称。例如，在网络中可能会出现多个Add算子，名称分别为Add1、Add2，但这类算子的OpType均为Add。 |

## P-T

| 术语/缩略语 | 含义 |
|------------|------|
| P | |
| Pipe | Ascend C编程范式核心概念之一，用于统一管理Device端内存等资源，一个Kernel函数必须且只能初始化一个Pipe对象。 |
| Preload | 在计算任务开始前，预先将必要的指令或数据加载到缓存中，用于减少指令或数据访问的延迟，提高计算效率。 |
| PCIe | Peripheral Component Interconnect Express，高速外围组件互联。一种串行外设扩展总线标准，常用于计算机系统中的外设扩展。 |
| PMU | Performance Monitor Unit，性能监视单元。PMU是CPU提供的一个单元，属于硬件的范畴。PMU通过访问相关的寄存器能读取到CPU的一些性能数据。 |
| PNGD | PNG Decoder，PNG图像解码器。提供对PNG格式的图像进行解码的能力。 |
| ProcMgr | Process Manager，进程管理。主要用于系统各个业务进程的初始化、启动、停止、进程级状态监测等服务。 |
| PTQ | Post-Training Quantization，训练后量化。在模型训练结束之后进行的量化，对训练后模型中的权重由浮点数量化到低比特整数，并通过少量校准数据基于推理过程对数据（activation）进行校准量化，从而尽可能减少量化过程中的精度损失 |
| PWM | Pulse Width Modulation，脉冲宽度调制。脉冲载波的脉冲持续时间脉宽随调制波的样值而变的脉冲调制方式。 |
| Q | |
| QAT | Quantization-Aware Training，量化感知训练。在重训练过程中引入量化，通过重训练提高模型对量化效应的能力，从而获得更高的量化模型精度的一种量化方式。 |
| QP | Queue Pair，队列对。QP是远程直接内存访问技术的核心通信单元，由发送队列（Send Queue，SQ）和接收队列（Receive Queue，RQ）组成，用于管理数据传输任务。 |
| R | |
| RDMA | Remote Direct Memory Access，远程直接内存访问技术，它将数据直接从一台机器的内存传输到另一台机器，无需双方操作系统的介入，一般指可以跨过网络的内存访问方式。 |
| RelativeEuclideanDistance | 欧氏相对距离算法。精度比对算法之一，计算结果取值范围为0到无穷大，值越接近于0，表明越相近，值越大，表明差距越大。 |
| RoCE | RDMA over Converged Ethernet，承载在融合以太网上的RDMA技术，即跨越以太网的RDMA通信方式。 |
| RootMeanSquareError | 均方根误差算法。精度比对算法之一，计算结果取值范围为0到无穷大。MeanAbsoluteError趋于0，RootMeanSquareError趋于0，说明测量值与真实值越近似。MeanAbsoluteError趋于0，RootMeanSquareError越大，说明存在局部过大的异常值。MeanAbsoluteError越大，RootMeanSquareError等于或近似MeanAbsoluteError，说明整体偏差越集中。MeanAbsoluteError越大，RootMeanSquareError越大于MeanAbsoluteError，说明存在整体偏差，且整体偏差分布分散。不存在以上情况的例外情况，因为RMSE ≥ MAE恒成立。 |
| ROS | Robot Operating System，机器人操作系统。 |
| RTC | Real Time Camera system，实时环视小系统，用于实现环视快启性能极致优化。 |
| Runtime | 为应用程序提供了针对AI处理器的内存管理、Device管理、Stream管理、Event管理、Kernel加载与执行等功能。 |
| Reduce | 减维操作，用于减少多维张量的维度。常见的减维操作包括求和、求平均、求最大值、求最小值等。 |
| RegTensor | 矢量数据寄存器，微指令计算基本单元，用于矢量计算。 |
| Regbase | Regbase是指基于寄存器的架构。Regbase架构下，中间结果可暂存在寄存器中，无需数据搬出到Local Memory的开销。 |
| Repeat | 矢量计算指令执行一次，读取8个DataBlock数据进行计算，称之为一个迭代（Repeat）。通常情况下，需要循环执行多次才能完成所有数据的读取与计算。 |
| Repeat Stride | 矢量计算指令循环执行时，下一次Repeat起始数据地址与当前Repeat起始数据地址之间的DataBlock个数。 |
| Repeat Times | 矢量计算指令循环执行的次数。 |
| S | |
| SafeIsland | Safety Island，功能安全采集岛。用于对MDC实施带外管理和监测的功能安全模块，具有独立的片内RAM、电源域，对整个MDC的功能安全及健康状态实施检测，并跟MCU之间保持紧密联系，必要时启动主备倒换或者紧急停车功能，运行于独立R52上。 |
| Scalar | AI Core上的标量计算单元，主要负责标量数据运算和对其他单元（如MTE数据搬运单元、Vector矢量计算单元、Cube矩阵计算单元）的指令发射。 |
| SD | Safety Driving SubSystem，安全驾驶子系统。主要部署高功能安全等级的辅助驾驶业务模块，如规控、功能安全检查、系统顶级状态控制等。主要用于运行车控命令下发及功能安全监测的子系统，没有或几乎没有IO外设，以尽可能达到整系统车规安全ASIL-D级别。 |
| SDMA | System Direct Memory Access，系统直接内存访问技术，简称DMA，允许外围设备直接访问系统内存，而不需要CPU的干预。 |
| SEA | Safety Execution Area，安全执行区。在AOS-Linux系统内划分出的一个AOS-Core区，用于部署执行功能安全适度相关的应用。 |
| SecIsland | Security Island，数据安全隔离岛。主要运行HSM模块，用于根证书保护、秘钥链验证、关键验签确认的高等级安全服务的子系统。 |
| SecVFS | Secure Virtual File System，安全虚拟文件。由IAM协助应用和资源管理模块之间建立的基于管道+共享内存封装的虚拟文件，用以支撑跨进程间通信和资源访问，不同于DSF，SecVFS需要集中鉴权才能够建立基于模拟文件读写访问的通信通道。 |
| SGAT | SubGraph Auto Tuning，子图自动调优。SGAT是一种提升子图性能的优化器。一张完整的网络，会被拆分成多个子图。针对每一个子图，通过SGAT生成不同的调优策略。SGAT的调优算法通过获取每个迭代的调优策略性能数据，找到最优的调优策略，从而实现对应子图的最优性能。 |
| SIFM | Safety Isolation and Filter Mechanism，功能安全隔离过滤器。为关键的IP提供相应功能安全等级的访问权限控制过滤检查机制，可以通过高安全等级的模块对其实施配置。 |
| SPI | Serial Peripheral Interface，串行外设接口。SPI总线系统是一种同步串行外设接口，它可以使MCU（Microcontroller Unit，微控制单元）与各种外围设备以串行方式进行通信以交换信息。 |
| SQE | Send Queue Element，RDMA中的发送队列元素，是工作队列（WQ）中的基本单元，用于描述发送请求的具体任务。 |
| StandardDeviation | 标准差算法。精度比对算法之一，计算结果取值范围为0到无穷大。标准差越小，离散度越小，表明越接近平均值。 |
| STARS | System Task and Resource Scheduler，系统任务和资源调度器。 |
| SIMD | SIMD：Single Instruction, Multiple Data，一条指令同时对多个数据进行相同的操作。 |
| SIMT | SIMT：Single Instruction, Multiple Threads，一条指令被多个线程并行执行，每个线程处理不同的数据。 |
| SPMD | Single-Program Multiple-Data，一种并行程序设计模型，其主要思想是使用同一个程序在多个核上并行执行，但每个核处理不同数据。 |
| SSBuffer | AI Core内部物理存储单元，分离模式下，Cube Core和Vector Core 1:2通信可选择使用SSBuffer在Cube Core和Vector Core的Scalar单元之间通信。 |
| SuperKernel | SuperKernel是一种算子的二进制融合技术，与源码融合不同，它聚焦于内核函数 (Kernel) 的二进制的调度方案，展开深度优化，于已编译的二进制代码基础上融合创建 一个超级Kernel函数（SuperKernel），以调用子函数的方式调用多个其他内核函数，也就是子Kernel。相对于单算子下发，SuperKernel技术可以减少任务调度等待时间和调度开销，同时利用Task间隙资源进一步优化算子头开销。 |
| T | |
| Tensor | Tensor张量是算子计算数据的容器，是N维数据结构，最常见的是标量、矢量或矩阵。张量的元素可以包含整数值、浮点值或字符串值。 |
| Tensor比对 | 张量比对，两个张量之间进行不同算法评价指标的数据比对操作，支持整网比对和单算子比对。 |
| TSN | Time Sensitive Networking，时间敏感网络。基于802.1Q扩展协议实现的高精度时间同步网络，精度可以达到us级甚至ns级，支撑对时间和系统时间同步高度敏感的网络或系统。 |
| Thread Block | 线程块，一个线程块最大支持2048个线程（Thread）。SIMT VF一次在AI Core上运行一个线程块（Block）。 |
| Tiling | Tiling指数据的切分和分块。计算数据量较大时，需要将数据进行多核切分、每个核也需要分块多次计算。 |
| TilingData | TilingData指数据切分和分块的相关参数（如每次搬运的块大小、循环次数）。鉴于设备端Scalar计算能力限制，一般Tiling参数在Host侧计算完成，然后传输到设备侧供Kernel函数使用。 |
| TilingFunc | 算子工程提供的在Host侧计算Tiling的默认函数。 |
| TilingKey | 用来区分Kernel函数不同版本的特例实现，不同的TilingKey会编译生成不同二进制。 |
| TPosition | Ascend C管理不同层级的物理内存时，用一种抽象的逻辑位置（TPosition）来表达各级别的存储，代替了片上物理存储的概念，达到隐藏硬件架构的目的。TPosition类型包括：VECIN、VECOUT、VECCALC、A1、A2、B1、B2、CO1、CO2等，其中VECIN、VECCALC、VECOUT主要用于矢量编程，A1、A2、B1、B2、CO1、CO2用于矩阵编程。 |
| TSCM | AscendC::TPosition::TSCM表示L1 Buffer空间对应的逻辑内存，需开发者自行管理以高效利用硬件资源，主要用于Matmul计算。比如，开发者可缓存一份TSCM数据，在不同使用场景中灵活配置为Matmul操作的A矩阵、B矩阵或Bias偏置矩阵，实现内存复用与计算效率优化。 |
| 图模式 | 图模式是神经网络模型的一种运行模式，在图模式下用户首先将模型的计算过程构造成一张图，然后通过GE图引擎下发到昇腾硬件执行。该图模式下，可通过计算图优化、多流并行、内存复用和模型下沉等技术手段，加速模型执行效率，减少模型内存占用。 |

## U-Z

| 术语/缩略语 | 含义 |
|------------|------|
| U | |
| UnalignRegForLoad | 非对齐寄存器，用作缓冲区来优化UB和RegTensor之间连续不对齐地址访问的开销，适用于连续非对齐搬入场景。 |
| UnalignRegForStore | 非对齐寄存器，用作缓冲区来优化UB和RegTensor之间连续不对齐地址访问的开销，适用于连续非对齐搬出场景。 |
| Unified Buffer | AI Core内部存储单元，主要用于矢量计算。 |
| Unified Bus | 统一总线。 |
| UDF | User Defined Function，用户自定义功能。 |
| UEFI | Unified Extensible Firmware Interface，统一可扩展固件接口。 |
| V | |
| VDEC | Video Decoder，视频解码器。提供对特定格式的视频进行解码的能力。 |
| VENC | Video Encoder，视频编码器。提供将图片编码为特定格式视频的能力。 |
| Vector | AI Core上的Vector计算单元，负责执行矢量运算。其算力低于Cube，但灵活度高于Cube（如支持数学中的求倒数，求平方根等）。 |
| VOS | Vehicle Control OS，智能车控操作系统。 |
| VPC | Vision Preprocessing Core，视觉预处理核。处理YUV、RGB等格式的图片，包括缩放、抠图、图像金字塔、色域转换等。 |
| VECCALC | Vector Calculation，AscendC::TPosition::VECCALC代表设备上用于矢量计算的逻辑内存，用于存放临时变量，物理存储对应AI Core的Unified Buffer。 |
| VECIN | Vector Input，AscendC::TPosition::VECIN代表设备上用于矢量计算的逻辑内存，用于存放矢量计算的输入数据，物理存储对应AI Core的Unified Buffer。 |
| VECOUT | Vector Output，AscendC::TPosition::VECOUT代表设备上用于矢量计算的逻辑内存，用于存放矢量计算的输出数据，物理存储对应AI Core的Unified Buffer。 |
| Vector Core | 矢量计算核，专注于矢量计算，由Scalar调度单元、矢量计算单元、搬运单元等组成，不包括矩阵计算单元。 |
| VF | Vector Funtion（向量函数）是由标量计算单元调用的一组连续的向量指令，用__simt_vf__或__simd_vf__标记。 |
| VL | Vector Length，RegTensor的位宽，通常取值为256Byte。 |
| W | |
| WQE | Work Queue Element，RDMA技术中的工作队列元素。WQE用于描述软件下发给硬件的任务请求，包含硬件执行任务的详细指令。 |
| Warp | 每个线程块被切分成多个Warp，Warp是执行相同指令的线程集合，每个Warp包含32个线程（thread），一个Block的多个Warp被依次调度到AI Core中的同一个AIV核执行。 |
| Workspace | 通常情况下指一个预分配的、临时使用的Global Memory内存，用于存储中间结果或临时数据。 |
| Z | |
| 整网比对 | 精度比对工具里Tensor比对的一种方式。对网络模型中参与计算的所有算子进行精度比对。 |

## 产品名术语

| 产品型号 | AI处理器类型 | NPU_ARCH | 当前开源状态 |
|----------|--------------|----------|--------------|
| Ascend 950PR/Ascend 950DT | Ascend 910D | 3510 | |
| Atlas A3 训练系列产品/Atlas A3 推理系列产品 | Ascend 910C | 2201 | |
| Atlas A2 训练系列产品/Atlas A2 推理系列产品 | Ascend 910B | 2201 | |
| Atlas A3 训练系列产品 | Ascend 910C | 2201 | |
| Atlas A2 训练系列产品 | Ascend 910B | 2201 | |
| Atlas A3 推理系列产品 | Ascend 910C | 2201 | |
| Atlas A2 推理系列产品 | Ascend 910B | 2201 | |
| Atlas 200I/500 A2 推理产品 | Ascend 310B | 3002 | |
| Atlas 推理系列产品AI Core | Ascend 310P AIC | 2002 | |
| Atlas 推理系列产品Vector Core | Ascend 310P AIV | 2002 | |
| Atlas 训练系列产品 | Ascend 910 | 1001 | |
| Atlas 200/300/500 推理产品 | Ascend 310 | | |
| MC62CM12AA AI处理器 | 1952 | | |
| BS9SX2A AI处理器 | Ascend 610Lite | | |
| AS31XM1X AI处理器 | Ascend 310M | | |
| BS9SX1A AI处理器 | Ascend 610B | | |
| 昇腾610 AI处理器AI Core | Ascend 610 AIC | | |
| 昇腾610 AI处理器Vector Core | Ascend 610 VEC | | |
| SoC（TsnsC） | Hi3796CS | | |
| SoC（OPTG） | SD3403 | | |
| IPV350 | Ascend035 | | |

## 其它中文术语

| 术语/缩略语 | 含义 |
|------------|------|
| CPU域调试 | Ascend C提供的一种孪生调试方法，在CPU上模拟设备侧Kernel函数的执行和调试，仅调试算子功能和精度。 |
| 基本块 | 一次计算需要的典型数据块大小。 |
| 静态Tensor编程 | 静态Tensor编程方式，相比基于Pipe的编程方式，这种方式避免了TPipe内存管理初始化过程（约数百纳秒），从而减少了运行时开销，更有助于开发者实现极致性能。通过直接构造指定地址和存储位置的LocalTensor，并将其传递给计算、搬运等API进行编程，提供了更高的灵活性。 |
| Kernel直调 | 一种简单直接的Kernel调用方式。完成Kernel侧算子实现和Host侧Tiling实现后，即可通过运行时接口，完成算子Kernel直调。该方式下Tiling开发不受CANN框架的限制，简单直接，多用于算子功能的快速验证。 |
| NPU域调试 | Ascend C提供的一种孪生调试方法，指基于NPU仿真软件或NPU硬件调试。 |
| Tiling下沉 | Tiling下沉是指将Tiling计算下沉至Device侧的AI CPU上执行，从而实现计算全程在Device侧高效完成。 |
| 分离模式 | AI Core的一种工作模式，其矩阵计算单元和矢量计算单元分别由独立的Scalar调度单元进行调度，并分离部署在Cube Core和Vector Core上。将Cube Core和Vector Core按照一定比例（1：N）进行组合，这样的组合视为一个AI Core，AI Core的核数以Cube Core为准。 |
| 孪生调试 | Ascend C提供的算子调试方法，支持在CPU域调试精度和NPU域调试精度/性能。 |
| 流水任务 | Ascend C编程范式是一种流水线式的编程范式，把算子核内的处理程序，分成多个流水任务。流水任务是指单核处理程序中主程序调度的并行任务。在核函数内部，可以通过流水任务实现数据的并行处理，进一步提升性能。 |
| 连续模式 | 使用Mask控制矢量计算每次Repeat内参与计算的元素时，可选择的模式之一，表示前面连续的多少个元素参与计算。 |
| 耦合模式 | AI Core的一种工作模式，采用同一个Scalar调度单元同时调度矩阵计算单元、矢量计算单元，所有的单元部署在一个AI Core上。 |
| 融合算子 | 融合算子由多个独立的小算子融合而成，其功能与多个小算子的功能等价，性能方面通常优于独立的小算子。用户可以根据实际业务场景诉求，按照具体算法自由融合矢量（Vector）、矩阵（Cube）算子以达到性能上的收益。 |
| 算子入图 | 算子入图指通过GE图模式运行算子，在图模式下首先将所有算子构造成一张图，然后通过GE将图下发到AI处理器执行。 |
| 算子原型 | 算子原型是算子的抽象描述，定义了算子的输入、输出、属性等信息。 |
| 通算融合算子 | 通算融合算子是融合集合通信任务和计算任务的算子，在算子执行过程中，计算和通信任务可以实现部分流水并行，从而提升性能。 |
| 微指令 | 微指令API是面向RegBase架构开发的API，用户可以通过微指令API直接对芯片中涉及Vector计算的寄存器进行操作，实现更大的灵活性和更好的性能。 |
| 逐比特模式 | 使用Mask控制矢量计算每次Repeat内参与计算的元素时，可选择的模式之一，可以按位控制哪些元素参与计算，bit位的值为1表示参与计算，0表示不参与。 |
| 自定义算子工程 | Ascend C提供的基于msOpGen工具生成的算子工程。 |