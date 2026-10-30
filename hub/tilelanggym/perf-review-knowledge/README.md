# perf-review-knowledge — SoftLib / ST PRC cards

Lok t781u–t784u: CANNBot-style split — **SKILL.md = workflow**; **measured lore = PRC cards**; **index SoT = checklist**.

## Index SoT (load first)

**[`perf-review-checklist.md`](perf-review-checklist.md)** is the only checkpoint index Agents may use.

- Only rows with `status=ready` (and applies_to hit) count.
- Unindexed `PRC-*.md` = orphan (gate fail).
- `GAPS.md` topics are **not** checkpoints until promoted + indexed.
- Architecture: [`CANNBOT_SKILLS_ARCHITECTURE.md`](CANNBOT_SKILLS_ARCHITECTURE.md).

```bash
python3 REGRESSION_salvage_2026-09-17/scripts/check_prc_index.py
```

## Layout

| Path | Role |
|------|------|
| `perf-review-checklist.md` | **Index SoT** (status + applies_to + links) |
| `PRC_TEMPLATE.md` | Six-section authoring scaffold |
| `GAPS.md` | Unmeasured candidates — not indexed |
| `sch/` `ipc/` `mem/` | Category dirs **with** cards only (no empty groups) |

Root: `/workspace/REGRESSION_salvage_2026-09-17/perf-review-knowledge/`

## How skills / harness use this

1. **Load checklist first** → filter ready + applies_to.
2. Open linked card in full; cite **PRC-id** in ANALYSIS / TRACE.
3. Do **not** invent checkpoints or paste dig tables into SKILL.md.
4. Gate before claiming knowledge tree healthy.

Skills: `tilelanggym-st-report` · `tilelanggym-st-explore-from-prompt` · `tilelanggym-softlib-simt-schedule` · `tilelanggym-st-semantics-gate`.  
Harness: `L6_ANALYSIS_INVENTORY.md` · `SKILLS_REBUILD.md` §2.5.
