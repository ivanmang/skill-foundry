---
name: extract-logs
description: >
  Parse raw gtest / ctest / run_cpu.py / run_st.py logs into a normalized
  results object (passed/failed/skipped counts + per-case status). Use after a
  run, or when asked to extract or normalize test logs into structured results.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3. A standalone parser ships in scripts/parse_gtest.py.
category: regression
origin: native
maturity: ready
owner: skill-foundry
---

# Extract Logs

Turn messy runner output into a stable `results` object. This is the single
normalization point, and it is **portable**: the parser is bundled with this
skill, so it works with no repo dependency.

## Portable procedure

1. Run the bundled parser on one log file (or a run directory):

   ```bash
   python3 scripts/parse_gtest.py --log <run>/<suite>.log \
     --suite <suite> --out <run>/<suite>.results.json
   ```

   (`scripts/parse_gtest.py` is relative to this skill's folder — find it next
   to this SKILL.md.)

2. If a log format is not recognized, extend the bundled `scripts/parse_gtest.py`
   with a new pattern and add a fixture log for the parser itself.
3. Keep the output shape stable — every downstream stage depends on it:

   ```json
   {
     "suite": "cpu-st",
     "summary": {"passed": 0, "failed": 0, "skipped": 0, "total": 0, "status": "UNKNOWN"},
     "cases": [{"name": "...", "status": "PASS", "duration_s": 0.0}],
     "evidence": []
   }
   ```

## Accelerator (optional — if skill-foundry is checked out)

The bundled parser is a copy of `skill_foundry/lib/parse_gtest.py`; either one
works. `run-testcase`'s accelerator driver calls it automatically after each suite.

## Gotchas

- `run_cpu.py` emits per-case `[PASS] name (Ns)` lines at the Python level even
  when gtest output is suppressed — prefer those over gtest state tracking.
- gtest `[  FAILED  ]` in the per-case list is different from the final summary
  line `[  FAILED  ] N tests, listed below:`; parse both but do not double count.
- A missing or empty log must yield `status: "UNKNOWN"`, never a fake PASS.

## Output

- A `results` JSON object (`<suite>.results.json`), embedded in `run.json` when
  using the accelerator.