---
id: PRC-XXX-NNN
name: <短名 · short title>
category: SCH | IPC | MEM | SIMT | ALU | ...
applies_to: <架構／前端／形態 · e.g. SoftLib SIMT Case-3 G32 · SIMD VL-res · A5 camodel>
status: ready | draft | needs-measure
---

# PRC-XXX-NNN：<短名>

> **Style:** mirror CANNBot `ascendc-performance-review` PRC cards
> (`plugins-official/ops-perf-optimize/.../perf-review-knowledge/`).
> Skills stay **workflow**; measured lore lives **here**. ANALYSIS claiming a
> perf cause **prefers cite `PRC-id`** instead of pasting dig prose into SKILL.md.

## 知识点

- What the mechanism is (compiler vs HW vs schedule vs opcode path).
- Arch / frontend split when it matters (SoftLib SIMT vs SIMD VMI; G16 vs G32; size-1 vs VL-res).
- Measured numbers **only** when cited to a RESULT/ANALYSIS/REPORT path (no invent).
- Misname traps (e.g. SoftLib tag “membar” ≠ `RV_SMEM_BAR`).

### 口径对齐（optional）

Unify names / VF rows / era= / plot VF vs official VF when digs conflicted historically.

### 实测摘要（optional）

| arm / config | VF | el/cyc | note |
|--------------|---:|-------:|------|
| … | … | … | cite path |

## 错误写法

Anti-pattern that caused (or would cause) a wrong perf claim / wrong schedule.
Prefer real ASC / PTO-DSL snippets from digs; mark `示意` if constructed.

```text
// 反例 …
```

## 正确写法

Correct pattern as measured, with path to ASC / kernel.

```text
// 正例 …
```

## 识别方法

How an agent / reviewer finds this in dumps / ASC / instr_exe:

1. …
2. …

误报边界：when **not** to open a finding (wrong G, wrong era, HW bar vs compiler clobber, IPC-only PNG mistaken for PR9, …).

## 证据要求

A finding / ANALYSIS claim citing this PRC **must** give:

- Artifact paths (ASC / dump / instr_exe / RESULT.md)
- Counts or tables that match the card (or explicit remeasure)
- For SoftLib≻SIMD compare claims: also satisfy **PRC-IPC-001** (PR9 overlays both arms)

## 参考

- Dig / RESULT / ANALYSIS paths (box + b10 when known)
- Sibling PRC-ids
- Harness L\* inventory sections / skill names (workflow only — no lore dump)

---

## Authoring rules (this tree)

1. **No invent.** Unmeasured → `status: needs-measure` + open Gaps list; do not fake tables.
2. **One mechanism per card.** Split SCH vs MEM vs IPC when names collide (compiler clobber ≠ SMEM_BAR).
3. Chinese section headers stay (知识点 / 错误写法 / 正确写法 / 识别方法 / 证据要求 / 参考) for CANNBot consistency; body may be EN / 粵 / 中.
4. YAML frontmatter required: `id`, `name`, `category`, `applies_to`, `status`.
5. Skills link PRC-id; they do **not** copy card body into SKILL.md.
