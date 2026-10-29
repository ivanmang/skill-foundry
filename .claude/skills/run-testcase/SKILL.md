---
name: run-testcase
description: >
  Run one or more benchmark/regression suites declared in config/suites.json and
  produce a normalized run record (run.json + raw log). Use when asked to run a
  regression, run the suite matrix, execute a single suite/testcase, or re-run a
  suite for a specific target such as pto-isa.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. NPU-sim suites additionally require a CANN toolkit with BOTH the compile headers AND the matching simulator.
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
3. Run through `python3 -m skill_foundry.workflow.run` (requires an explicit `--suite` or `--all-suites`):

   ```bash
   python3 -m skill_foundry.workflow.status                          # pre-flight: what can run here
   python3 -m skill_foundry.workflow.run --all-suites --dry-run      # preview (no run.json)
   python3 -m skill_foundry.workflow.run --suite cpu-st                          # one suite
   python3 -m skill_foundry.workflow.run --all-suites --quiet                    # everything, summary only
   python3 -m skill_foundry.workflow.run --all-suites --parallel                 # independent suites concurrently
   python3 -m skill_foundry.workflow.run --suite npu-sim-a5 --testcase tpartargmax      # one testcase
   python3 -m skill_foundry.workflow.run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'  # one gtest case
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
- `--dry-run` previews what WOULD run (no run.json); `--parallel` runs
  independent suites concurrently (implies per-suite quiet).
- Narrow a run with `--testcase <name>` and `--filter <gtest-pattern>` (requires
  a single `--suite`; invalid with `--all-suites`).

## Output

- `reports/<run-id>/run.json` — metadata + per-suite results
- `reports/<run-id>/<suite>.log` — raw log
