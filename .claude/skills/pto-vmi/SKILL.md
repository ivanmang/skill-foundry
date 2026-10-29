---
name: pto-vmi
description: >
  Run and triage pto-vmi regression: DSL ST and CCE ST on the A5 simulator
  (ptoas-vmi msprof / bisheng + camodel), plus the CCE-vs-VMI CA metrics workflow
  (EX / IPC / vf_real / dual-issue / stalls). Use when working in the pto-vmi
  repo, running pto-vmi kernels, or asked for a CCE/DSL regression run or triage.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. Needs ASCEND_HOME_PATH + the ptoas-vmi venv (.venv-ptoas312) and the A5 simulator (Ascend950PR_9599); full runs run on ecs.
---

# PTO-VMI regression adapter

Target-specific knowledge for the generic pipeline skills. The
machine-readable version is `config/suites.json` + `config/arches.json`; this
skill documents the commands, env, and triage.

## Repo

- `~/pto-vmi` (override with `PTO_VMI_REPO`).
- CCE kernels live under `cce/`, DSL under `dsl/`, TileLang under `tilelang/`.
- `scripts/sim_dsl.sh` runs a DSL/TileLang kernel under `msprof op simulator`.

## Suite commands

| Suite | Command |
|---|---|
| DSL ST (A5) | `bash scripts/sim_dsl.sh dsl/<kernel>` (ptoas-vmi msprof) |
| CCE ST (A5) | bisheng + camodel (M2 — see the daily-refresh runner) |
| TileLang ST (A5) | `bash scripts/sim_dsl.sh tilelang/<kernel>` |

Via the harness (recommended — one entry point):

```bash
./harness status                          # what can run here (auto-detected)
./harness list --target pto-vmi
./harness run --target pto-vmi --suite dsl-st --testcase SoftmaxGradKernel --dry-run
./harness run --target pto-vmi --suite dsl-st --testcase SoftmaxGradKernel
./harness run --target pto-vmi --all-suites --parallel
```

## Env

- `source <cann>/set_env.sh` sets `ASCEND_HOME_PATH` (the driver does this via
  `env_setup`).
- The DSL runner needs the **ptoas-vmi** venv (`.venv-ptoas312` on ecs); set
  `PYTHON_BIN` or run from that venv.
- Full CCE+DSL refresh lives in `npu_skills/pto-as/ca-instruction-breakdown/`.

## CA metrics (CCE vs VMI)

The vmi-dashboard compares CCE vs VMI per kernel on cycle-accurate metrics from
`core0.veccore0.instr_log.dump`: EX / SU / LD / ST / pred / scalar / dma,
dual-issue, stalls, IPC / EX-IPC / vf_real, and EX subcategories. The harness
records the same metrics per suite (`skill_foundry/lib/perf_metrics.py`) when the dump is
present, and `./harness review` flags vf_real/EX up >15% or IPC down >15%.

## Triage

1. Read the first concrete error line from the raw log.
2. Classify: compile (bisheng/ptoas) / camodel / numeric-wrong / sim-crash /
   toolchain-bug (e.g. `pto.static_range()` unrolled to SLDI/SSTI) / env-leak.
3. Match against `references/known-failures.md` before treating as new.
4. If the user corrects the triage, or the cause is new and reusable, log it:
   `./harness teach "symptom -> fix -> where"`.

## References

- `references/known-failures.md` — triage corpus
- `references/env.md` — env/venv/arch pins

## Gotchas

- `sim_dsl.sh` runs **one** kernel; a suite "all" needs a wrapper (run with
  `--testcase <kernel>`).
- `pto.range()` maps to the hardware loop primitive; `pto.static_range()` was
  unrolled to scalar ops in ptoas-vmi 0.1.6 (CA numbers then untrustworthy).
- A6 (dav_9201) runs on the yellow machine — see the `a6-yellow-zone` skill.
