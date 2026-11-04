# SoftLib / ST perf-review checkpoint index (PRC)

status: ready

本文件是 SoftLib / tilelangGym ST 性能检视检查点索引**真源**（mirror CANNBot `ascendc-performance-review` → `perf-review-checklist.md`）。知识点正文在本目录各类别子目录下，每个检查点一个文件。Agent **不得自拟**检查点；**只有本索引里 `status=ready` 且 applies_to 命中当前臂／形态的条目**才算可见知识。未入索引的 `PRC-*.md` 视为孤儿（gate 失败）。

知识树根：`REGRESSION_salvage_2026-09-17/perf-review-knowledge/`  
架构说明：[`CANNBOT_SKILLS_ARCHITECTURE.md`](CANNBOT_SKILLS_ARCHITECTURE.md)  
模板：[`PRC_TEMPLATE.md`](PRC_TEMPLATE.md)  
未量缺口（非检查点）：[`GAPS.md`](GAPS.md) — **不**进入本索引，直至升为 `ready`/`draft` 卡并登记。

证据口径：A5 camodel/opsim digs + RESULT/ANALYSIS 路径（gym）；禁止无出处 invent。勿 fork CANNBot ID（`PRC-MEM-009` 等）；重叠主题用 SoftLib 本地 ID，并在卡「参考」里 cite CANNBot。

## 使用方式

1. Agent **先读本索引**，得到全部检查点 ID、适用范围、status、链接。
2. 过滤：`status=ready` **且** applies_to 命中当前 op／G／臂／era。
3. **完整读取**链接的知识点文件（含误报边界）后再写 finding / ANALYSIS 因果句。
4. Finding / 因果句必须引用 **PRC-id**；证据形态以该卡「证据要求」为准。
5. `draft` / `needs-measure` 或仅出现在 `GAPS.md` 的主题 → **不得**当检查点引用；需测完再升卡并登记本索引。
6. SoftLib≻SIMD / both-arm compare 类结论：索引里 **PRC-IPC-001** 为强制配套（PR9 overlay），与 workflow skill `tilelanggym-st-report` 一致。
7. 跑门禁：`python3 REGRESSION_salvage_2026-09-17/scripts/check_prc_index.py`（断链／孤儿／status／六节）。

## 目录约定

```text
perf-review-knowledge/
├── perf-review-checklist.md   # 本文件 · 索引 SoT
├── PRC_TEMPLATE.md
├── GAPS.md                    # 未升卡缺口（非索引）
├── CANNBOT_SKILLS_ARCHITECTURE.md
├── README.md                  # 人读导航 → 指向本 checklist
└── <类别>/                    # 仅当有卡时存在；禁止空目录当 group
    └── PRC-<CAT>-<NNN>-<slug>.md
```

- ID：`PRC-<类别缩写>-<三位序号>`，一经分配不复用。
- 类别目录（现有）：`sch/` · `ipc/` · `mem/`。新类别仅在 **≥1 张 ready/draft 卡** 需要时再建。
- 卡 front matter：`id` · `name` · `category` · `applies_to` · `status`（`ready` | `draft` | `needs-measure`）。
- 本地卡必含六节：`## 知识点` · `## 错误写法` · `## 正确写法` · `## 识别方法` · `## 证据要求` · `## 参考`。

## 检查点索引

### SCH——调度 / compiler / scale 路径

| ID | 名称 | 适用范围 | 知识点文件 | status |
|---|---|---|---|---|
| PRC-SCH-001 | Compiler asm memory clobber vs HW SMEM_BAR | SoftLib SIMT（SV1 fence1 · Case-3 dual_drain G32）vs SIMD VMI VL-res；命名陷阱 SoftLib “membar” tag | [sch/PRC-SCH-001](sch/PRC-SCH-001-asm-memory-clobber-vs-smem-bar.md) | ready |
| PRC-SCH-002 | Scale：VDIV／paint／VMUL vs SoftLib FDIV_I+FMUL | SV8/SB8 Case-3 G32 · era=case3-quant-bcast · KEEP-X · SoftLib dual_drain vs SIMD VL-res | [sch/PRC-SCH-002](sch/PRC-SCH-002-scale-path-vdiv-vs-fdiv.md) | ready |
| PRC-SCH-003 | Case-3 pack-UB／keeplive_vbrc vs VSEL range-paint | SV8/SB8 Case-3 G32 · era=case3-quant-bcast · SIMD VMI pack_ub / keeplive_vbrc vs VL-res VSEL paint; VL×gold-G candidates (t591u) | [sch/PRC-SCH-003](sch/PRC-SCH-003-case3-pack-ub-vs-vsel-paint.md) | ready |
| PRC-SCH-005 | load-ahead (load-4, load-2) versus dual-drain | SIMT Case-3 G32 · era=case3-quant-bcast · float32 · axis=1xG · 64×64, 64×128, 128×128 | [sch/PRC-SCH-005](sch/PRC-SCH-005-groups-ahead-load4.md) | ready |

### IPC——running-IPC / PR9 overlay

| ID | 名称 | 适用范围 | 知识点文件 | status |
|---|---|---|---|---|
| PRC-IPC-001 | PR9 running-IPC + opcode-lane overlay（强制） | 任何 SB*/SV* ANALYSIS 宣称 SoftLib≻SIMD／SIMD≻SoftLib／SIMT≻SIMD／both-arm compare／mix-split stage mid-IPC；A5 opsim dump | [ipc/PRC-IPC-001](ipc/PRC-IPC-001-pr9-running-ipc-opcode-overlay.md) | ready |

### MEM——驻留 / HW barrier

| ID | 名称 | 适用范围 | 知识点文件 | status |
|---|---|---|---|---|
| PRC-MEM-001 | KEEP-X / VL-resident vs UB 再載 X | SV8/SB8 Case-3 G32 SoftLib dual_drain + SIMD VL-res；对比 G16 size-1 UB-reload | [mem/PRC-MEM-001](mem/PRC-MEM-001-keep-x-vl-resident.md) | ready |
| PRC-MEM-002 | HW SMEM_BAR：G16 size-1 scratch vs G32 无 bar | SV8/SB8 Case-3 · G16 size-1 SIMD scratch vs G32 SoftLib/VL-res；S_sync | [mem/PRC-MEM-002](mem/PRC-MEM-002-smem-bar-g16-vs-g32.md) | ready |

### SIMT——SoftLib 调度

| ID | 名称 | 适用范围 | 知识点文件 | status |
|---|---|---|---|---|
| PRC-SIMT-001 | Dual-drain fence count versus el/cyc | SoftLib SIMT Case-3 G32 · era=case3-quant-bcast · R64×C128 E=8192 T=512 · walls 0/1/2/3 | [simt/PRC-SIMT-001](simt/PRC-SIMT-001-dual-drain-fence-count.md) | ready |
| PRC-SIMT-003 | LDS.32 versus LDS.64 on within-group Case-3 | SoftLib SIMT Case-3 G32 · era=case3-quant-bcast · R64×C128 E=8192 · T=128 and T=256 | [simt/PRC-SIMT-003](simt/PRC-SIMT-003-lds32-vs-lds64.md) | ready |

统计：9 条（ready 9 / draft 0）。
