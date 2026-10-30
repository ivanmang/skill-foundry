---
name: run-testcase
description: >
  Run one or more pto-isa benchmark/regression suites (CPU simulator ST and NPU
  simulator ST) and capture a reproducible run record. Use when asked to run a
  regression, run the suite matrix, execute a single suite/testcase, or re-run a
  suite for a target such as pto-isa.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. NPU-sim suites additionally require a CANN toolkit with BOTH the compile headers AND the matching simulator.
category: regression
---

# Run Testcase

Execute a suite and capture a reproducible run record. This skill is **portable**:
run the real pto-isa commands directly — no skill-foundry checkout required.

## Portable procedure

1. Resolve the target + suite. The `pto-isa` adapter skill is the source of
   truth for commands, env, and gotchas. The suites are:

   | Suite | Command | Prereq |
   |---|---|---|
   | `cpu-st` | `python3 tests/run_cpu.py --clean --verbose` | clang++>=15 or g++>=13 |
   | `npu-sim-a5` | `python3 tests/script/run_st.py -r sim -v a5 -t all` | CANN headers + A5 sim |
   | `npu-sim-a3` | `python3 tests/script/run_st.py -r sim -v a3 -t all` | CANN headers + A3 sim |
   | `npu-sim-a6` | `python3 tests/script/run_st.py -r sim -v a6 -t all` | CANN headers + A6 sim (yellow) |

2. Record context before running (reproducibility):
   ```bash
   git -C "$PTO_ISA_REPO" rev-parse HEAD        # target commit
   hostname                                     # machine
   # CANN version when relevant
   ```

3. Run the suite(s) from the pto-isa checkout and capture the raw log.

4. Normalize the log with the `extract-logs` skill (bundled parser), then hand
   to `generate-report` and `review-inconsistencies`.

## Accelerator (optional — if skill-foundry is checked out)

One command replaces steps 2–4 (writes `reports/<run-id>/run.json` + report):

```bash
python3 -m skill_foundry.workflow.run --all-suites --report --open --review
python3 -m skill_foundry.workflow.run --suite npu-sim-a5 --testcase tpartargmax
```

## Gotchas

- NPU-sim suites must run on a machine with the matching CANN simulator
  (`tools/simulator/<soc>`); the A6 sim lives on yellow.
- CPU-ST needs clang++>=15 or g++>=13 (the blue laptop has neither — run on
  ecs / yellow / b10).
- Re-`source` the CANN env per suite block; env leaks between suites corrupt results.
- Narrow a run with `-t <case>` and `-g <gtest-pattern>` (run_st.py) /
  `--testcase` `--filter` (run_cpu.py).

## Output

- raw log from the runner
- a normalized `results` object (see `extract-logs`)
- (accelerator) `reports/<run-id>/run.json`
