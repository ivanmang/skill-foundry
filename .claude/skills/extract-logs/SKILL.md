---
name: extract-logs
description: >
  Parse raw gtest / ctest / run_cpu.py / run_st.py logs into a normalized
  results object (passed/failed/skipped counts + per-case status). Use after a
  run, or when asked to extract or normalize test logs into structured results.
---

# Extract Logs

Turn messy runner output into a stable `results` object consumed by the rest of
the pipeline. This is the single normalization point.

## Steps

1. Point the parser at one log file (or a run directory):

   ```bash
   python3 scripts/parse_gtest.py --log reports/<run-id>/<suite>.log \
     --suite <suite> --out reports/<run-id>/<suite>.results.json
   ```

   `run-testcase` already calls this automatically after each suite.

2. If a log format is not recognized, extend `parse_gtest.py` with a new
   pattern **and** add a fixture log under `reports/` for regression of the
   parser itself.
3. Keep the output shape stable:

   ```json
   {
     "suite": "cpu-st",
     "summary": {"passed": 0, "failed": 0, "skipped": 0, "total": 0, "status": "UNKNOWN"},
     "cases": [{"name": "...", "status": "PASS", "duration_s": 0.0}],
     "evidence": []
   }
   ```

## Gotchas

- `run_cpu.py` emits per-case `[PASS] name (Ns)` lines at the Python level even
  when gtest output is suppressed — prefer those over gtest state tracking.
- gtest `[  FAILED  ]` in the per-case list is different from the final summary
  line `[  FAILED  ] N tests, listed below:`; parse both but do not double count.
- A missing or empty log must yield `status: "UNKNOWN"`, never a fake PASS.

## Output

- A `results` JSON object embedded in `run.json` (or a standalone
  `<suite>.results.json`).
