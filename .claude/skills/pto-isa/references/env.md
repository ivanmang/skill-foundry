# PTO-ISA env & version pins

See also `cann-matrix.md` for the full CANN→arch support matrix (which CANN
package can compile/simulate which arch), and run `python3 -m skill_foundry.lib.cann` to detect it
on any machine.


## Arch → soc (NPU ST via `run_st.py -v`)

| -v | chip | simulator soc | march | notes |
|---|---|---|---|---|
| a3 | Ascend910B/C | Ascend910B1 | — | A2/A3 shared |
| a5 | Ascend950 | Ascend950PR_9599 → Ascend910_9599 | — | |
| a6 | A6 sim | dav_9201 | dav-920r1-vec | yellow only; pto-isa headers first |
| v200 | V200/v926 | v926 | dav-920r1-vec | v926 ISA-identical to A6 for VEC |

## Toolchain pins

| Tool | Pin | Path |
|---|---|---|
| C++ CPU-ST compiler | clang++>=15 **or** g++>=13 | — |
| clang-format | v18.1.8 | `~/.local/bin/clang-format` |
| ruff | v0.14.14 | `~/.local/bin/ruff` (absolute path) |
| CANN (A6 sim) | 9.1.0 | `~/Ascend/cann-9.1.0` on yellow |

## Env variables

| Var | Meaning |
|---|---|
| `ASCEND_HOME_PATH` | CANN toolkit root (set by `set_env.sh`) |
| `PTO_ISA_REPO` | pto-isa checkout used by the harness (default `~/pto-isa`) |
| `PTO_ISA_PATH` | pto-isa include root; must precede CANN include for A6 |
| `MPI_HOME` / `MPI_LIB_PATH` | comm ST (M3) |

## Required sourcing before sim runs

NPU-sim runs need the CANN environment sourced in the **execution** shell — a
non-login SSH session does not pick up `.bashrc`, so `run_st.py` fails
immediately with `ASCEND_HOME_PATH` unset:

```bash
source /usr/local/CANN/cann-9.1.0/bin/setenv.bash
```

`config/suites.json` `env_setup` sources `set_env.sh` only as a fallback; on
machines like ecs where the login shell is non-interactive, source
`setenv.bash` first (or in the run wrapper).

## Machines (team zones)

| Zone | Host | Role |
|---|---|---|
| Blue | LAPTOP-T0BUNFB1 | source edits, wheel release, push |
| Yellow | m00922072@7.246.99.145 | A6 sim `dav_9201`; pull-only from gitcode |
| b10 | pto-b10.ddns.net:8022 | dashboard host |
| ecs | 115.175.35.144 | A5 dashboard + CPU/NPU runs |
