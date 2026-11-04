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

## Adding an entry

Append, don't overwrite. Keep the signature greppable (first error line) so the
triage step can match mechanically.
