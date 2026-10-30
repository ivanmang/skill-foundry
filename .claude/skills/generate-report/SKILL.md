---
name: generate-report
description: >
  Turn normalized run results into a Markdown summary and a standalone HTML
  report. Use when asked to generate a report or dashboard from a regression
  run, or after the pipeline has produced results.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. The report itself is plain Markdown + inline HTML.
category: regression
origin: native
---

# Generate Report

Produce a reviewable, human-readable report from normalized results. This skill
is **portable**: the report is just Markdown — write it from the `extract-logs`
results following the canonical sections below.

## Portable procedure

Build `report.md` with these canonical sections:

1. **Header** — run id, target, repo commit, date, host, toolchain/CANN version.
2. **Summary matrix** — suite × {passed, failed, skipped, status, duration}.
3. **Failures** — grouped by suite, each with the first concrete evidence line.
4. **Perf** — avg and p99 deltas vs baseline (p99 +15% = regression flag).
5. **Notes** — env issues, timeouts, known failures matched from the triage corpus.

If writing `report.html`, keep it **self-contained** (inline CSS/JS) so it can be
served without extra assets.

## Accelerator (optional — if skill-foundry is checked out)

```bash
python3 -m skill_foundry.workflow.report --run reports/<run-id>/run.json \
  --known .claude/skills/pto-isa/references/known-failures.md \
  --out reports/<run-id>/report
```

## Gotchas

- Never rewrite a FAIL into a PASS; annotate it as a known failure using the
  adapter's `known-failures.md` when applicable.
- When diffing is requested, embed `review-inconsistencies` output instead of
  duplicating it.

## Output

- `report.md` (and, when asked, a self-contained `report.html`).