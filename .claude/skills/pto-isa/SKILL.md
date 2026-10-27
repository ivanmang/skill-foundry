---
name: pto-isa
description: >
  Run and triage pto-isa regression: CPU simulator ST and NPU simulator ST
  (A5/A3/A6, incl. the A6 dav_9201 / v200 workflow), plus env/soc handling and
  known failure patterns. Use when working in the pto-isa repo, running pto-isa
  tests, or asked for a pto-isa regression run or failure triage.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. CPU-ST needs clang++>=15 or g++>=13; NPU-sim needs a CANN simulator (A6 dav_9201 runs on the yellow machine).
---

# PTO-ISA regression adapter

Target-specific knowledge for the generic pipeline skills. The machine-readable
version is `config/suites.json` + `config/arches.json`; this skill documents the
commands, env, and triage.

## Repo

- `~/pto-isa` (override with `PTO_ISA_REPO`).
- Build/test/lint entry points are in `~/pto-isa/AGENTS.md` and
  `~/pto-isa/tests/README.md`.

## Suite commands (M1)

| Suite | Command |
|---|---|
| CPU-ST | `python3 tests/run_cpu.py --clean --verbose` (needs clang++>=15 or g++>=13) |
| NPU-sim A5 | `python3 tests/script/run_st.py -r sim -v a5 -t all` |
| NPU-sim A3 | `python3 tests/script/run_st.py -r sim -v a3 -t all` |
| NPU-sim A6 | `python3 tests/script/run_st.py -r sim -v a6 -t all` |

Single testcase / filter:

```bash
python3 tests/run_cpu.py --testcase tadd --gtest_filter 'TADDTest.case_float_64x64_64x64'
python3 tests/script/run_st.py -r sim -v a5 -t tadd -g TADDTest.case_float_64x64_64x64
```

## Env

- `source <cann>/set_env.sh` sets `ASCEND_HOME_PATH` and friends (driver does
  this via `env_setup`).
- A6 (dav_9201): pto-isa arch headers MUST precede CANN include — set
  `PTO_ISA_PATH` and put `-I $PTO_ISA_PATH` FIRST. CANN 9.1.0 ships the A6 sim
  but not the A6 compile headers.

## Arch / soc

| -v | soc | note |
|---|---|---|
| a3 | Ascend910B1 | A2/A3 (Ascend910B/C) |
| a5 | Ascend950PR_9599 → Ascend910_9599 | Ascend950 |
| a6 | dav_9201 | A6 sim, march dav-920r1-vec |

Full table: `references/env.md`.

## Triage

1. Read the first concrete error line from the raw log.
2. Classify: compile / link / camodel / numeric-wrong / alignment / soc-mismatch
   / env-leak / timeout.
3. Match against `references/known-failures.md` before treating as new.
4. If the user corrects the triage, or the cause is new and reusable, log it
   so it can be promoted: `./scripts/teach "symptom -> fix -> where"`.

## References

- `references/suite-matrix.md` — full regression surface + entry points
- `references/known-failures.md` — triage corpus
- `references/env.md` — arch/soc/env/version pins

## Gotchas

- CPU-ST cannot build on the blue laptop (g++11); run on ecs/yellow/b10.
- NPU-sim `-v` auto-derives the simulator soc; do not pass an extra soc flag.
- Comm async tests need CANN 9.0+ — keep them gated (M3).
- Lint pins: clang-format v18.1.8, `~/.local/bin/ruff` v0.14.14.
