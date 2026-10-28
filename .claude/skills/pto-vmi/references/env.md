# Env — pto-vmi target

| Var | Meaning | Default |
|---|---|---|
| `PTO_VMI_REPO` | pto-vmi checkout used by the harness | `~/pto-vmi` |
| `ASCEND_HOME_PATH` | CANN toolkit (needs A5 sim Ascend950PR_9599) | unset |
| `PYTHON_BIN` | Python running the PTODSL example in `sim_dsl.sh` | `python3` (on ecs use `.venv-ptoas312`) |
| `PTOAS_MSPROF_LOG_MODE` | `sim_dsl.sh` simulator log rendering (`quiet`/`verbose`) | `quiet` |

## Arch / soc

| -v | soc | note |
|---|---|---|
| a5 | Ascend950PR_9599 | A5 sim (ecs has CANN 9.1.0 + ptoas-vmi 0.1.6) |
| a6 | dav_9201 | yellow machine (`a6-yellow-zone` skill) |

## Toolchain

The CCE side uses bisheng from the CANN 9.1.0 toolkit on ecs; the ptoas-vmi 0.1.6
venv (`.venv-ptoas312`) drives DSL + the CA metrics pipeline.