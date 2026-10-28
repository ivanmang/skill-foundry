---
name: review-inconsistencies
description: >
  Compare a regression run against the pinned baseline (or another run):
  detect pass->fail regressions, fail->pass fixes, new/removed cases, and perf
  regressions using avg and p99 (flag p99 +15% even if avg is stable). Use when
  asked to review a run or compare it to the baseline.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3.
---

# Review Inconsistencies

The regression signal lives here. Diff a run against `reports/baseline/<target>.json` (the baseline for the run's target — cross-target diffs are refused).

## Steps

1. Run the diff:

   ```bash
   ./harness review --run reports/<run-id>/run.json
   ```

2. Classify every delta:
   - **regression** — PASS in baseline, FAIL now
   - **fix** — FAIL in baseline, PASS now
   - **new** / **removed** — case present only on one side
   - **perf regression** — p99 duration up >15% (report avg too)
3. For each regression, open the raw log and attach the first concrete error
   line (compile error, link error, numeric mismatch, timeout, soc mismatch).
4. Consult the adapter's `known-failures.md` — known failures get annotated,
   not silently dropped.

## Perf rule (agreed)

- Flag when **p99 increases >15%** even if the average is stable.
- Always show both avg and p99 deltas in the summary; do not report avg alone.

## Gotchas

- A seed baseline (`"generated": false`) has no case data — the first real run
  should be **promoted** to baseline (`./harness baseline`), not diffed.
- Durations only exist where the parser captured them; treat missing durations
  as "no perf data", never as zero.
- Different hosts have different speeds — only compare runs from the same
  canonical machine for perf.

## Output

- Human summary (stdout) + a machine-readable delta object.
