# PTO-ISA suite matrix

What "pto-isa regression" covers, and the canonical entry points. Source:
`~/pto-isa/AGENTS.md` and `~/pto-isa/tests/README.md`.

## Tiers

| Tier | Suite | Entry point | Needs | M1 |
|---|---|---|---|---|
| Correctness (fast) | CPU-ST | `python3 tests/run_cpu.py --clean --verbose` | clang++>=15 or g++>=13 | ✅ |
| Correctness (sim) | NPU-sim A5/A3/A6 | `python3 tests/script/run_st.py -r sim -v {a5,a3,a6} -t all` | CANN simulator | ✅ |
| Correctness (hw) | NPU hw | `run_st.py -r npu -v {a5,a3}` | device + ASCEND_HOME_PATH | — (M2) |
| Cost | Costmodel | `./tests/run_costmodel_tests.sh`, `run_costmodel.py` | CANN | — (M2) |
| Comm | Comm ST | `./tests/run_comm_test.sh` | MPI + HCCL | — (M3) |
| Structural | Coverage/names | `tests/validate_op_coverage.py`, `validate_testcase_names.py` | none | — (M2) |

## One-click / CI parity

- `./build.sh --run_all --a3 --sim`
- `./build.sh --run_simple --a5 --npu`
- `.gitcode/workflows/`: `compile_action.yml`, `staticcheck_action.yml`,
  `llt_action.yml`, `PR-pipeline_pto-isa.yml`

## Layout inside pto-isa

- `tests/cpu/st/` — CPU simulator ST
- `tests/npu/{a2a3,a5,a6,kirin9030,kirinX90,kirinDev0000}/src/st/` — NPU ST
- `tests/costmodel/` — cost model ST / fit / perf-sim
- `tests/script/` — `run_st.py`, `build_st.py`, `all_cpu_tests.py`
- `kernels/manual/` — manual-mode kernels

## Single case

```bash
python3 tests/run_cpu.py --testcase tadd --gtest_filter 'TADDTest.case_float_64x64_64x64'
python3 tests/script/run_st.py -r sim -v a5 -t tadd -g TADDTest.case_float_64x64_64x64
```

## Long runs & monitoring

- **Full `--all-suites` can run 16h+** on the A5 simulator (many cases, each minutes). Plan a long window, use `--parallel`, or poll progress and re-poll rather than waiting synchronously.
- **`run.json` is written only at completion.** The newest `reports/*/run.json` is NOT the current run's result until `pgrep -f workflow.run` is empty AND the `nohup` wrapper has appended `EXITCODE:` to the log; confirm the report dir is newer than the run start.
- **Log line-growth over ~60s confirms liveness** — `wc -l <log>` twice; growth means the simulator is progressing even when no new suite markers appear.
- **`npu-sim-a6` auto-skip is expected** on a machine missing either A6 compile headers or the `dav_9201` simulator — treat it as an environment limitation, not a regression (see cann-matrix.md).

## Lint / format (part of the regression gate, M2+)

- C++: `clang-format -i -style=file <file>` — pinned v18.1.8
- Python: `~/.local/bin/ruff format <file>` / `~/.local/bin/ruff check <file>` — pinned v0.14.14
