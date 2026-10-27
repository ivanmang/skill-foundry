---
name: generate-report
description: >
  Turn normalized run results (run.json) into a Markdown summary and a
  standalone HTML report. Use when asked to generate a report or dashboard from
  a regression run, or after the pipeline has produced results.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3.
---

# Generate Report

Produce a reviewable, human-readable report from normalized results.

## Steps

1. Generate from one or more run records:

   ```bash
   python3 scripts/build_report.py --run reports/<run-id>/run.json \
     --out reports/<run-id>/report
   ```

2. The report must include, per suite:
   - pass / fail / skip counts and total
   - per-case failures (name + first evidence line)
   - duration (total and per-suite)
3. When diffing is requested, embed the `review-inconsistencies` output
   (regressions, fixes, new/removed cases, perf flags) instead of duplicating it.

## Report sections (canonical)

1. Header — run id, target, repo commit, date, host, toolchain/CANN version.
2. Summary matrix — suite × {passed, failed, skipped, status, duration}.
3. Failures — grouped by suite, with evidence.
4. Perf — avg and p99 deltas vs baseline (p99 +15% = regression flag).
5. Notes — env issues, timeouts, known failures matched from the triage corpus.

## Gotchas

- Never rewrite a FAIL into a PASS in the report; annotate it as "known failure"
  using the adapter's `known-failures.md` if applicable.
- HTML output must be self-contained (inline CSS/JS) so it can be served from
  the dashboard without extra assets.

## Output

- `report.md` and `report.html` under the run directory.
