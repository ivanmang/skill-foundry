# PTO-VMI known failures (triage corpus)

Classify a failure against these before treating it as new. Format:

```markdown
### <signature>
- Symptoms: ...
- Cause: ...
- Fix / workaround: ...
- Seen in: <run-id or date>
```

## Seed entries

### pto.static_range() fully unrolled to SLDI/SSTI scalar ops
- Symptoms: `FaDnSoftmaxMxfp8NotInitKernel` VMI EX/vf_real inflated; VMI sim
  instruction mix not representative of real hardware.
- Cause: ptoas-vmi 0.1.6 lowers `pto.static_range()` to scalar load/store ops
  instead of the hardware loop primitive.
- Fix: rework the kernel to use `pto.range()` (which maps 100% to the hardware
  loop); exclude the pair until a ptoas fix lands (see §0b of the CA report).

### Correctness failed on CCE side (Quant*Kernel)
- Symptoms: CCE kernel `FAIL`/errored, VMI `PASS`, in a matched pair.
- Cause: CCE lowering bug or test-harness issue in the kernel (e.g. QuantBf16toMXFp8CeilKernel produced
  incorrect output / timed out).
- Fix: triage the CCE kernel compile/output; out of VMI/DSL scope.

Append, don't overwrite. Keep the signature greppable (first error line) so the
triage step can match mechanically.