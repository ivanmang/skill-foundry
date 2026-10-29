# CANN → arch support matrix

Which CANN package can **compile** for and **simulate** which pto-isa arch.

Check any machine with:

```bash
python3 -m skill_foundry.lib.cann                 # ASCEND_HOME_PATH or scan ~/Ascend
python3 -m skill_foundry.lib.cann --home /path/to/toolkit
python3 -m skill_foundry.lib.cann --scan --json
```

This reads two indicators from the toolkit:

- **headers** = `include/pto/npu/<arch>` → which arches the toolkit compiles for.
- **simulator** = `tools/simulator/<soc>` (or `x86_64-linux/simulator`) → which SoCs it
  can run/simulate.

The machine-readable mapping lives in `config/cann.json`:
`soc → arch` names and `header dir → arch` flags, plus `arch_min_cann` and the
known-toolkits notes.

## Verified on our machines (2026-10)

| CANN version | Where | Headers (compile) | Simulator (run) |
|---|---|---|---|
| 9.0.0-alpha.1 | blue `~/Ascend/cann-9.0.0-alpha.1` | a3 a5 **a6** kirin9030 kirinX90 kirinDev0000 | a3 a5 kirin9030 kirinX90 (no A6 sim) |
| 9.0.0-beta.2 | blue `~/Ascend_new` | a3 a5 kirin9030 | a3 a5 **a6** kirin9030 kirinX90 |
| 9.0.0-beta.2 | blue `~/Ascend_full` | a3 a5 kirin9030 | kirin9030 kirinX90 (partial install) |
| 9.1.0-beta.1 | blue `~/Ascend_new910` | a3 a5 kirin9030 kirinX90 | a3 a5 **a6** |
| 9.1.0 | yellow | a3 a5 kirin (A6 headers from pto-isa) | A6 `dav_9201` |
| 9.2.0 | v200 machine | v200/v926 (`dav-926`) | v926 == A6 ISA for VEC |

## Key takeaways for pto-isa

- **A6** is the arch with split support: some toolkits have the **sim** but not
  the **headers** (and vice versa). To compile for A6 you need an A6-header
  toolkit (9.0.0-alpha.1 on blue) **or** `pto-isa` headers (`PTO_ISA_PATH`
  first); to *run* A6 you need a toolkit with the `dav_9201` simulator
  (9.0.0-beta.2 / 9.1.0+ on yellow).
- **a3** and **a5** are supported (headers + sim) everywhere from CANN 9.0.0.
- **v200/v926** = CANN 9.2.0; v926 is ISA-identical to A6 for VEC, so the A6
  march (`dav-920r1-vec`) is the bridge.

## soc → arch names used by pto-isa `run_st.py -v`

| `-v` | simulator soc |
|---|---|
| a3 | `Ascend910B1` |
| a5 | `Ascend950PR_9599` (→ `Ascend910_9599`) |
| a6 | `dav_9201` |
| kirin9030 | `Kirin9030` |
| kirinX90 | `KirinX90` |
| kirinDev0000 | `KirinDev0000` |

See also: `../env.md` (arch/soc/env) and `./suite-matrix.md` (what regression runs).