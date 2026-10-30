# CANNBot skills architecture — study notes for SoftLib / ST (t783u)

**Purpose:** Understand how [hicann/cannbot-skills](https://github.com/hicann/cannbot-skills) (canonical mirror also on gitcode `cann/cannbot-skills`) structures plugins, skills, and PRC knowledge **before** SoftLib adds more PRC content or more category groups.

**Sources (fetched 2026-10-29 Asia/Hong_Kong; do not invent beyond these):**
- Repo README, `AGENTS.md`, `docs/architecture-design.md`, `docs/STANDARDS.md`, `docs/feature-list.md`
- Plugin `plugins-official/ops-perf-optimize/` (`plugin.json` v4.1.0, `AGENTS.md`, `quickstart.md`)
- Skills under that plugin, especially `ascendc-performance-review/` (`SKILL.md`, `references/perf-review-checklist.md`, `references/perf-review-knowledge/`, `_template.md`, sample `mem/PRC-MEM-009-ub-bank-conflict.md`)
- Stage skill `ops-perf-analysis/SKILL.md`, orchestrator `ops-perf-optimize-workflow/` + `references/workflow-contract.md`
- Gate test `plugins-official/ops-perf-optimize/tests/test_perf_review_checklist.py`
- Compare target: our `/workspace/REGRESSION_salvage_2026-09-17/perf-review-knowledge/` + sand workflows `tilelanggym-*`

**Non-goals this note:** authoring new SoftLib PRC cards; inventing SoftLib category taxonomy; dumping harness L0–L8 into cards.

---

## 1. Top-level layout — how the stack loads

### 1.1 Repo layout (skills + plugins)

From README / architecture-design:

```text
cannbot-skills/
├── ops/                  # domain Skills (AscendC / TileLang / PyPTO / …)
├── model/                # model-infer Skills
├── graph/                # torch.compile / npugraph Skills
├── runtime/              # Runtime Skills
├── infra/                # governance / GitCode toolkit Skills
├── tools/                # asys / msaicerr / npu-compute / …
├── plugins-official/     # official Plugins (dev-path entry: Agents + Workflows)
├── plugins-community/    # community Plugins
├── docs/                 # architecture, STANDARDS, feature-list
└── tests/
```

Related sister repos (README): `cannbot`, `cannbot-knowledge`, `cannbot-dsl`, `cann-bench`, `cannbot-sentry`. Some plugins migrate to `cannbot`; Skills for Triton-style paths may keep knowledge in `cannbot-knowledge`. **`ascendc-performance-review` keeps its PRC tree inside the skill’s `references/`**, not in a separate knowledge repo.

### 1.2 Four + one layers (AGENTS.md)

Bottom-up:

| Layer | Where | Role |
|-------|--------|------|
| **Infrastructure** | `infra/`, `tools/` | shared tooling Skills |
| **References (knowledge)** | inside each Skill’s `references/` | progressive disclosure; how to do better |
| **Skills (capability)** | `ops/`, `model/`, … or `plugins-*/…/skills/` | **how** to do a task |
| **Agents (roles)** | `plugins-*/…/agents/` or plugin `AGENTS.md` | **what** role owns |
| **Plugins (apps)** | `plugins-official/*`, `plugins-community/*` | orchestrate Agents + Skills for a product path |

Eval/tests cut **horizontally** across layers.

### 1.3 How Skills load each other (observed patterns)

CANNBot does **not** embed full sibling Skill bodies into one mega-file. Loading is:

1. **Plugin primary Agent frontmatter** — e.g. `ops-perf-optimize/AGENTS.md` lists `skills: [ops-perf-optimize-workflow]` and says: on trigger, **fully read** that Skill; do not reinvent Stage rules from memory.
2. **Orchestrator Skill → stage Skills by name** — `ops-perf-optimize-workflow` + `workflow-contract.md` map ROLE → Skill (`ops-perf-baseline-evaluate`, `…-preparation`, `…-analysis`, `…-implementation`, `…-postprocess`). Subagents get a thin envelope; stage Skill is the execution SoT.
3. **Conditional load inside a stage** — e.g. `ops-perf-analysis` says: load `ascendc-performance-review` **only when static review is useful**; load `ops-perf-profile-feature-extractor` when aggregate CSV is not enough; route operator-family lore to `ascendc-performance-best-practices`; API lookup via `ascendc-docs-search`. Stage Skills are forbidden from loading the orchestrator or other stage Skills.
4. **Cross-skill markdown pointers** — checklist rows can be `skill:ascendc-performance-best-practices` + relative path + `#prc-mm-001` anchor (family chapters live in another Skill; index still owns the checkpoint ID).
5. **Progressive disclosure (STANDARDS / AGENTS)** — `SKILL.md` = thin workflow + triggers; deep text in `references/`; scripts in `scripts/`; assets optional.
6. **Single-source / no reverse dependency** — STANDARDS: mark the true-source Skill for a domain; downstream Skills consume it; **do not reverse-cite or fork the same facts into many Skills**.

Install path: marketplace / `init.sh` registers Agents + Skills + workflow tools; Agent Skills Spec (`npx skills add …`) for single-Skill installs.

### 1.4 Skill taxonomy (STANDARDS “分类体系”) — not the same as PRC folders

Functional classes of Skills:

| Class | Role | Examples |
|-------|------|----------|
| 知识库类 | Passive reference; usually dependency of others | `npu-arch`, `ascendc-tiling-design`, `ascendc-performance-best-practices` |
| 工程模板类 | Scaffolding | direct/registry invoke templates |
| 调试与诊断类 | Active debug workflows | precision / runtime / crash / sync-audit |
| 测试开发类 | UT/ST/review methodology | `ascendc-code-review`, `ascendc-st-design` |
| 工具辅助类 | Env / profiling helpers | `ascendc-env-check`, `ops-profiling` |

`ascendc-performance-review` behaves as a **static-review methodology Skill** whose knowledge payload is a **PRC card tree** under `references/` (knowledge-base *content*, review *workflow* in `SKILL.md`).

---

## 2. Focus: `ascendc-performance-review` structure

Path:
`plugins-official/ops-perf-optimize/skills/ascendc-performance-review/`

### 2.1 Split: workflow Skill vs knowledge tree vs checklist

| Artifact | Role |
|----------|------|
| **`SKILL.md`** | Trigger, discipline, delivery format. Explicit: read-only; no profiling; no invented checkpoints; findings must cite checkpoint ID + evidence. |
| **`references/perf-review-checklist.md`** | **Index SoT** for checkpoint IDs, applies_to, link to card (or foreign skill+anchor), per-row `status`. Index itself has `status: ready`. |
| **`references/perf-review-knowledge/`** | One file per checkpoint (local cards). |
| **`_template.md`** | Authoring scaffold for new cards. |
| **Foreign chapters** | arch22 MM/FA criteria live under `ascendc-performance-best-practices` family guides; checklist still owns `PRC-MM-*` / `PRC-FA-*` IDs. |

`SKILL.md` quote of intent (paraphrase of published text): checklist + knowledge cards are the **only** checkpoint SoT; Agent must not invent checkpoints; only `status=ready` and scope-matching rows are executed; full card (including 误报边界) before filing a finding; findings are **hypothesis-level**, need measurement to become perf conclusions.

### 2.2 Knowledge directory layout

```text
perf-review-knowledge/
├── _template.md
├── arch/     # PRC-ARCH-*
├── mem/      # PRC-MEM-*
├── vec/      # PRC-VEC-*
├── vf/       # PRC-VF-*   (RegBase / dav-3510)
├── simt/     # PRC-SIMT-*
└── sca/      # PRC-SCA-*  (scalar / header overhead)
```

Naming: `PRC-<CAT>-<NNN>-<slug>.md`. IDs once allocated are never reused.

**Category folders here are content groups for one Skill’s knowledge tree** — not separate Skills, not plugins.

Checklist counts (from published index): **53 rows (ready 51 / draft 2)**.

### 2.3 Card front matter + required sections

Template / PRC-MEM-009 / gate test agree on:

**Front matter:** `id`, `name`, `category`, `applies_to`, `status` (`draft` | `ready`).

**Body sections (all required for local cards):**
1. `## 知识点` — mechanism; arch split when needed; measured facts only with provenance
2. `## 错误写法` — anti-pattern snippet
3. `## 正确写法` — good pattern
4. `## 识别方法` — how to find in source + false-positive boundaries
5. `## 证据要求` — what a finding must attach
6. `## 参考` — docs / sibling skill paths / bench dates

Optional long code under `code/` beside the card.

`draft` = evidence incomplete (e.g. gain numbers from another SoC). **Only `ready` enters review.**

### 2.4 Indexing & finding workflow

Agent procedure (checklist + SKILL):

1. Read **checklist** → full ID list + applies_to + status.
2. Filter: `status=ready` **and** applies_to hits current op/SoC.
3. **Fully read** each linked card (or best-practices chapter section).
4. Search source; apply 误报边界 before filing.
5. Finding = ID + file:line + evidence shape from card + expected impact + fix direction.
6. Arch-macro conclusions → always PRC-ARCH-001 table first; platform constants → PRC-ARCH-002.
7. arch22 vs A5 applicability matrix lives in best-practices; A5 must not load arch22-only MM/FA cards.

### 2.5 Machine gate (why the index is real)

`tests/test_perf_review_checklist.py` enforces:

- Index declares valid status
- Every row resolves to a file (local or `skill:` + path); anchors exist for foreign chapters
- **No orphan `PRC-*.md`** under knowledge (unindexed card = silent skip risk)
- Card `id`/`status` match index row
- IDs unique
- Summary line `统计：N 条（ready X / draft Y）。` matches parse
- Local cards contain all six `##` sections

This is the architectural answer to “more content”: **content that is not indexed and status-gated does not exist for the Agent.**

### 2.6 Sibling Skills inside `ops-perf-optimize` (plugin skill package)

| Skill | Role |
|-------|------|
| `ops-perf-optimize-workflow` | Orchestrator SoT (`workflow-contract.md`) |
| `ops-perf-baseline-evaluate` | Stage: baseline |
| `ops-perf-preparation` | Stage: strip demo |
| `ops-perf-analysis` | Stage: profile + plan; **optionally** calls review Skill |
| `ops-perf-implementation` | Stage: candidates |
| `ops-perf-postprocess` | Stage: integrate |
| `ops-perf-acceptance-criteria` | Cross-stage gates |
| `ops-perf-profile-feature-extractor` | Deep profile features |
| **`ascendc-performance-review`** | Static PRC checklist review |

Plugin `AGENTS.md` is a thin trigger; `quickstart.md` is human UX; `workflows/prompts/*.md` are stage envelopes; `scripts/` hold deterministic tools.

Outside the plugin but referenced: `ops-profiling`, `ascendc-performance-best-practices`, `ascendc-perf-optimize`, docs-search, sync-audit, etc. (domain Skills under `ops/`).

---

## 3. What is a **group** vs **content** in their model

Lok’s question (“more content or some more group”) maps to **several different CANNBot nouns**. Do not collapse them.

| Term | Meaning in CANNBot | SoftLib analogy |
|------|--------------------|-----------------|
| **Plugin** | Product path / Team packaging Agents+Skills | We do **not** need a SoftLib plugin yet (no five-stage AscendC optimize Team) |
| **Skill package (plugin `skills/`)** | Set of workflow Skills for that path | Our `tilelanggym-*` sand workflows (+ harness) |
| **Skill class** (STANDARDS 分类) | 知识库 / 模板 / 调试 / 测试 / 工具 | `st-report` = workflow/test-dev; PRC tree = 知识 |
| **Operator-family group** | Folders under `ascendc-performance-best-practices/references/{matmul,reduce,fa,…}` | Optional later: SoftLib motif / Case family guides — **separate** from PRC static cards |
| **PRC category group** | `mem/`, `vf/`, `simt/`, … under one review Skill | `sch/`, `ipc/`, `mem/` today |
| **Content** | One `PRC-*-NNN-*.md` (+ optional `code/`) with status | One measured SoftLib lore card |
| **Checklist row** | Indexed, status-gated checkpoint | **Missing** in our tree today (README table ≠ checklist SoT) |

**Rules implied by their design:**

- **Add content** = new card + index row + status + six sections + evidence; preferably after measure.
- **Add a PRC category group** = only when several cards share a stable acronym and review routing; empty dirs are not groups.
- **Add an operator-family group** = belongs in a *best-practices* Skill, not as empty folders under perf-review-knowledge.
- **Add a Skill** = new workflow/responsibility (STANDARDS single responsibility), not a place to dump dig prose.
- **Add a Plugin** = multi-agent orchestration need.

---

## 4. Recommendation for SoftLib / ST — **mirror layers; do not dump cards yet**

### 4.1 Mirror these layers (yes)

| CANNBot layer | SoftLib / ST mirror | Action now |
|---------------|---------------------|------------|
| Workflow Skill (`SKILL.md` thin) | Keep `tilelanggym-st-report`, `st-explore-from-prompt`, `softlib-simt-schedule`, `st-semantics-gate`, `simd-per-g-mapping`, … | Already correct direction: enforce lists + Done-when; **cite PRC-id**, don’t paste digs |
| Checklist index | Add `perf-review-checklist.md` (or rename README index into a **machine-checkable** checklist) next to knowledge | **Highest leverage next step** — before mass card authoring |
| Knowledge tree + `_template` | Keep `perf-review-knowledge/` + `PRC_TEMPLATE.md` + `GAPS.md` | Keep; tighten status discipline (`ready` / `draft` / `needs-measure`) |
| Gate test | Port a slim `test_softlib_prc_checklist.py` (link resolve, no orphans, section presence, status sync) | After checklist exists |
| Stage “load review when useful” | ANALYSIS / explore skills: load PRC cards **on cause claims**; not every dig | Already sketched in `tilelanggym-st-report` |
| Best-practices Skill (family chapters) | Optional later: SoftLib motif / Case-3 schedule atlas as **separate** skill or harness L-doc — not PRC spam | **Defer** |
| Plugin / five-stage Team | Not needed for gym ST close-loop | **Defer** |

### 4.2 Do **not** do yet

1. **Do not mass-author PRC cards** from harness L0–L8 “one piece by one piece” until checklist + status gate exist — orphans are invisible to Agents (CANNBot’s own test comment).
2. **Do not invent more empty category groups.** Snapshot 2026-10-29: empty dirs already present under our tree — `axis/`, `frontend/`, `hw/`, `sem/`, `shape/`, `simd/`, `simt/`, `theory/`. That is “more group” without content. Prefer **delete or mark frozen** until the first **ready** card needs a new acronym.
3. **Do not fork CANNBot IDs** (`PRC-MEM-009` etc.) for SoftLib topics — keep SoftLib namespace (`PRC-SCH-*`, `PRC-IPC-*`, SoftLib-local `PRC-MEM-*`) and **cite** CANNBot cards as references when overlapping.
4. **Do not thicken `SKILL.md`** with measured tables — violates both CANNBot progressive disclosure and our own st-report contract.
5. **Do not create a SoftLib `ops-perf-optimize`-style plugin** until there is a real multi-stage orchestration need (baseline→implement→integrate). Gym ST is closer to “analysis + knowledge cards + harness scripts.”

### 4.3 Suggested SoftLib category policy (minimal)

Keep only categories that already have cards or a near-term measured gap:

| Keep | Why |
|------|-----|
| `sch/` | SoftLib schedule / clobber / scale path (2 cards) |
| `ipc/` | PR9 overlay enforce (1 card) |
| `mem/` | KEEP-X / SMEM_BAR (2 cards) |
| `simt/` | SoftLib SIMT gaps in `GAPS.md` — **create files only when measured** |

Defer new acronyms (`axis`, `frontend`, `theory`, …) until ≥1 ready card forces them. Align new categories with **review routing questions** (how would an Agent decide to open this folder?), not harness chapter names.

### 4.4 Order of work (architecture-first)

1. Write this architecture note (done: this file).
2. Promote README card table → **`perf-review-checklist.md`** with status column + applies_to + links; add summary counts line.
3. Add orphan/section/status gate script (CANNBot-inspired).
4. Collapse empty category dirs.
5. **Then** promote one `GAPS.md` row at a time to a card when digs land numbers — content, not groups.
6. Only if family-length narrative appears (e.g. SoftLib dual_drain atlas), consider a **best-practices-style** companion skill with chapters + checklist anchors — same pattern as MM/FA.

---

## 5. Short compare: us vs CANNBot

| Dimension | CANNBot `ascendc-performance-review` | Our SoftLib tree + `tilelanggym-*` |
|-----------|--------------------------------------|-------------------------------------|
| Host | Skill under **plugin** `ops-perf-optimize` | Sand workflows + harness tree under `REGRESSION_salvage_…` (not a plugin) |
| Workflow | Thin `SKILL.md` + optional call from `ops-perf-analysis` | Multiple specialized workflow Skills (report / explore / semantics / SoftLib / SIMD) — **richer** than one review Skill |
| Index SoT | `perf-review-checklist.md` + machine test | `README.md` table only — **no checklist gate, orphans possible** |
| Categories | arch/mem/vec/vf/simt/sca (+ MM/FA via other Skill) | sch/ipc/mem + **8 empty dirs** |
| Cards ready | 51 ready / 2 draft (53 indexed) | 5 seed cards (measured SB8/G32 era) |
| Status model | `ready` \| `draft` | template allows `needs-measure`; GAPS separate — good, but not index-enforced |
| Card sections | Fixed six Chinese headings | Template mirrors them (知识点 / 错对 / 识别 / 证据 / 参考) — aligned |
| Cross-skill lore | Family deep-dives in `ascendc-performance-best-practices` | Harness L2/L6 + skills still hold a lot of lore that **should** migrate only when carded |
| Evidence bar | Official docs + samples + dated board microbench (see PRC-MEM-009) | Camodel/opsim digs + RESULT paths — appropriate for gym; keep provenance strict |
| Finding use | Static hypothesis for optimize Team | Cite in ANALYSIS / MB DONE gates (PR9 etc.) — correct use |

**Bottom line:** We copied the **card shape** early; we have not yet copied the **index + status + orphan gate + “no empty groups”** discipline that makes CANNBot’s tree readable and Agent-safe. Architecture lesson for t783u: **fix / content / checklist before more groups or mass content.**

---

## Appendix A — Useful URLs

- Repo: https://github.com/hicann/cannbot-skills  
- Architecture: https://raw.githubusercontent.com/hicann/cannbot-skills/master/docs/architecture-design.md  
- STANDARDS: https://raw.githubusercontent.com/hicann/cannbot-skills/master/docs/STANDARDS.md  
- Review Skill: https://github.com/hicann/cannbot-skills/blob/master/plugins-official/ops-perf-optimize/skills/ascendc-performance-review/SKILL.md  
- Checklist: https://github.com/hicann/cannbot-skills/blob/master/plugins-official/ops-perf-optimize/skills/ascendc-performance-review/references/perf-review-checklist.md  
- Example card: https://github.com/hicann/cannbot-skills/blob/master/plugins-official/ops-perf-optimize/skills/ascendc-performance-review/references/perf-review-knowledge/mem/PRC-MEM-009-ub-bank-conflict.md  
- Checklist gate test: https://github.com/hicann/cannbot-skills/blob/master/plugins-official/ops-perf-optimize/tests/test_perf_review_checklist.py  

## Appendix B — Inventory snapshot (our tree, 2026-10-29)

**Cards present:** PRC-SCH-001, PRC-SCH-002, PRC-IPC-001, PRC-MEM-001, PRC-MEM-002.  
**Empty category dirs:** axis, frontend, hw, sem, shape, simd, simt, theory.  
**Meta:** `README.md`, `PRC_TEMPLATE.md`, `GAPS.md`, this file.

