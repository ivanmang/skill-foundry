---
name: run-testcase
description: >
  Run one or more benchmark/regression suites declared in config/suites.json and
  produce a normalized run record (run.json + raw log). Use when asked to run a
  regression, run the suite matrix, execute a single suite/testcase, or re-run a
  suite for a specific target such as pto-isa.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. NPU-sim suites additionally require a CANN toolkit with the matching simulator.
---

# Run Testcase

Execute a declared suite through the shared driver and capture a reproducible
run record. Do **not** hand-edit test results.

## Steps

1. Resolve the target and suite. The adapter skill (e.g. `pto-isa`) is the
   source of truth for commands, env, and gotchas; `config/suites.json` is the
   machine-readable version.
2. Record context before running:
   - target repo git commit + dirty status
   - harness git commit
   - toolchain / CANN version when relevant
3. Run the suite:

   ```bash
   # one suite
   ./scripts/run_suite.sh --target pto-isa --suite cpu-st
   # all enabled suites for a target
   ./scripts/run_suite.sh --target pto-isa --all-suites
   ```

4. The driver writes `reports/<run-id>/run.json` and the raw log, and runs
   `extract-logs` automatically.
5. Hand the `run.json` to `generate-report` and `review-inconsistencies`.

## Gotchas

- NPU-sim suites must run on a machine with the matching CANN simulator
  (`tools/simulator/<soc>`); A6 sim lives on yellow.
- CPU-ST needs clang++>=15 or g++>=13 (the blue laptop has neither — run on
  ecs/yellow/b10).
- Re-`source` the CANN env per suite block; env leaks between suites corrupt
  results.
- `--all-suites` continues past a failed suite and records each suite's status.

## Output

- `reports/<run-id>/run.json` — metadata + per-suite results
- `reports/<run-id>/<suite>.log` — raw log
