# PTO-ISA known failures (triage corpus)

Classify a failure against these before treating it as new. Format:

```markdown
### <signature>
- Symptoms: ...
- Cause: ...
- Fix / workaround: ...
- Seen in: <run-id or date>
```

## Seed entries

### `ld.lld: error: unable to find library -lruntime_camodel`
- Symptoms: NPU-sim link fails immediately.
- Cause: simulator soc not resolved; older wrappers needed an explicit `--soc`.
  Current `run_st.py` auto-derives soc from `-v` (a5 → Ascend950PR_9599 →
  Ascend910_9599; a3 → Ascend910B1; a6 → dav_9201).
- Fix: run with `-v {a3,a5,a6}` and let it derive; ensure `ASCEND_HOME_PATH` set.

### `[ERROR] Failed to get file. Path = ../<case>/golden.bin`
- Symptoms: NPU testcase errors while golden file is missing.
- Cause: new testcase name not added to `gen_data.py` `case_name_list`.
- Fix: add the exact `Suite.case_...` name to `gen_data.py`; golden is generated
  in-memory, so also check the actual `max diff` before declaring failure.

### Custom PadValue bytes swapped
- Symptoms: padding value wrong (e.g. -1.0f instead of expected).
- Cause: encoding built as `0xBF80000100000000` instead of `0xBF80000000000001`
  (upper 32 bits = float bits, lower 32 bits = 0x1 marker).
- Fix: `(floatBits << 32) | 0x00000001`; use `PadValueCustom(-1.0f)` on host,
  a `constexpr static_cast<PadValue>` on NPU.

### `Cannot select: intrinsic %llvm.hivm.*`
- Symptoms: device compile fails selecting a vector intrinsic.
- Cause: intrinsic name exists but the target arch has no selection pattern.
- Fix: probe the backend — `strings $(readlink -f <cann>/bin/bisheng) | grep -oE
  'llvm\.hivm\.[a-z0-9_.]*'`, dump real IR via `ptoas --emit-vpto-llvm-ir`,
  `sed`-swap the candidate in the real kernel.ll, re-run bisheng. Keep the
  intrinsic result USED (else -O2 DCE fakes "selectable").

### vcvt round-field swap (bf16→fp16 / fp32)
- Symptoms: numeric wrongness in bf16→fp16 vector convert on the device side.
- Cause: round-field semantics swapped in the generated vcvt.
- Fix: see `~/pto-isa/tools/` (`proof_vcvt_regression.sh`,
  `diff_vcvt_round.sh`, `verify_bf16fp16_fix.sh`) and the issue notes
  `~/pto-isa/bf16_fp16_vcvt_*.md`.

### A6 sim (dav_9201) teardown / UB-parser crash
- Symptoms: segfault in `TmSim::reset()` teardown, or UB-parser heap corruption
  during `SetDevice`.
- Cause: CANN camodel bugs (100% CANN frames, zero PTOAS).
- Fix: sidestep — run a kernel then `aclrtResetDevice`+`aclFinalize`; call
  `aclInit`/`aclrtSetDevice` BEFORE importing pto machinery.
  See `.pi/skills/a6-yellow-zone` / `~/a6-vmi-dashboard/cann-a6-camodel-bug-report.md`.

### `tcvt_common.hpp:2883:21: no matching function for call to 'castData_2D_NoPostUpdate'` (A6)
- Symptoms: A6 device compile of `tcvt_fp4_lut` fails with the above; the generic FP4→FP8 path has no `castData` overloads.
- Cause: the FP4 E2M1→E4M3 LUT dispatch guard was A5-only (`#if defined(PTO_NPU_ARCH_A5)`), so A6 fell through to `implTCVT`.
- Fix: pair A6 with A5 at `tcvt_common.hpp:2915` and `:3259` (`#if defined(PTO_NPU_ARCH_A5) || defined(PTO_NPU_ARCH_A6)`); fixed by pto-isa `7c0141eb`.
- Seen in: 2026-11-03 A6 `tcvt_fp4_lut` port

### `copy_gm_to_ubuf` does not support the given target feature (A6)
- Symptoms: A6 device compile fails at a raw `copy_gm_to_ubuf` call in a ported a5 kernel.
- Cause: the 7-arg `copy_gm_to_ubuf` builtin is A5-only; A6 needs the 13-arg `copy_gm_to_ubuf_align_v2`.
- Fix: use `pto_copy_gm_to_ubuf_align_v2` (`arch_cce_intrinsic.hpp`), which forwards `pre_allocation`/`non_eod_ctrl=false` on A6.
- Seen in: 2026-11-03 A6 `tcvt_fp4_lut` port

### `ScheTop.cpp:126 thrId < s_thrCnt` SIGABRT (npu-sim-a5)
- Symptoms: 8 layout-conversion kernels SIGABRT with `ScheTop.cpp:126` assertion; deterministic per data-movement testcase (e.g. `tload_mix` case #65 NCHW2FZ4D_int8_t), reproduced in a **serial** run — not a concurrency/load artifact.
- Cause: camodel `esl_top_thread_cnt` is 32 while the cases need 64. Config lives at `/usr/local/CANN/cann-9.1.0/x86_64-linux/simulator/dav_3510/camodel/camodel_v100.json` and is root-owned read-only.
- Fix: `sudo sed -i` the in-place file (`"esl_top_thread_cnt"` 32 → 64) on both sim-dir copies. Repro requires a full no-timeout binary run — `tload_mix` looks green under a 120/180 s manual timeout only because it stops before case 65.
- Seen in: 2026-11-05 npu-sim-a5 full + serial rerun

### `camodel_v100.json` overrides ignored
- Symptoms: a CWD copy of `camodel_v100.json` (or env override) has no effect; the in-place file is root-owned read-only.
- Cause: camodel loads the config by hardcoded basename from the sim dir next to `libpem_davinci.so`; only an in-place edit works.
- Fix: edit the in-place file with sudo (`esl_top_thread_cnt` 32 → 64); CWD/env override is silently ignored.
- Seen in: 2026-11-05 npu-sim-a5

### `TMOVTest.case_nz2nd_3` flaky (3×OK + 2×FAIL in one run)
- Symptoms: the same testcase reports OK 3 times and FAILED 2 times within a single run.
- Cause: pto-isa numeric/nondeterminism, not a camodel failure.
- Fix: triage backlog — treat as a pto-isa numeric issue; re-run to confirm stability before attributing to camodel.
- Seen in: 2026-11-05 npu-sim-a5

## Adding an entry

Append, don't overwrite. Keep the signature greppable (first error line) so the
triage step can match mechanically.
