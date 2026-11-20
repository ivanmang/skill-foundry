# Run a TileLang case on Ascend

The generic procedure for compiling, launching, and reading a TileLang kernel on Ascend hardware or its simulator. Compile and launch are the same for SIMT and SIMD; only the VF opcode and the issue opcodes differ. This file holds the mechanism, not machine paths. Read the formula's `analyze.md` for what the counters mean for that formula.

## Pieces

Three environment pieces are needed. Their locations are machine-specific and are not written here.

- **CANN** — the Ascend toolkit. Provides the compiler toolchain and `libascendcl.so`.
- **Simulator library** — the camodel runtime used when running under the simulator rather than on a device.
- **npusim** — the recorder that wraps a launch and writes the instruction trace.

## Compile

Compile the TileLang function to a loadable object. This step is identical for SIMT and SIMD; the mode is chosen inside the TileLang source (`T.SimtVF` versus `T.SimdVF`), not by a compile flag.

```text
compiled = tilelang.compile(
    build(...),
    target="ascend",
    out_idx=-1,
    execution_backend="cython",
    compile_flags=[...],
    pass_configs={"tl.disable_data_race_check": True},
)
kernel.cpp  = compiled.get_kernel_source()
kernel.so   = compiled.adapter.libpath
```

`target="ascend"` selects the Ascend backend. `execution_backend="cython"` produces a callable object. The kernel source is written next to the object for inspection.

Optional: add `"tl.disable_thread_storage_sync": True` to `pass_configs` to drop compiler-inserted `asc_syncthreads` from the thread-storage-sync pass. **Opt-in only** when every shared-buffer write in the VF is thread-private (no cross-thread UB cells). Re-check `PASS` after enabling. When and why: `tilelang/techniques/schedule-patterns.md` §8.

## Launch

Load the runtime and run the object. Under the simulator, point `TL_CAMODEL_LIB` at the simulator library directory and preload the camodel runtime before loading `libascendcl.so`.

```text
sim = os.environ["TL_CAMODEL_LIB"]
ctypes.CDLL(os.path.join(sim, "libruntime_camodel.so"), mode=ctypes.RTLD_GLOBAL)
lib = ctypes.CDLL("libascendcl.so")
# aclInit, aclrtSetDevice, allocate, copy in, run, copy out
```

Wrap the launch in `npusim record` so the instruction trace is written:

```text
npusim record -s <soc> -g -n 0 "<the launch command>"
```

Run one launch at a time. After a PASS the recorder can return a non-zero teardown status; that is not a failure of the kernel.

## Read the counters

Counters come from veccore0 (`core == 0`, `sub == 1`). The recorder writes two dumps per core: `*.instr_popped_log.dump` holds each instruction's **start** (issue) tick, `*.instr_log.dump` holds its **completion** tick. Pair each instruction by PC and ID across the two. `is_popped == 1` is the start tick and `0` is the completion tick.

- **VF** — completion of the mode's VF opcode minus its start, both ticks included: `VF` on SIMD, `VF_SIMT` on SIMT. That opcode is the only counter that changes name between modes.
- **el/cyc** — N/VF.
- **Issue counts** — the opcodes the body issues. SIMT uses `SIMT_LDS`, `REDUX`, `BAR`, `LDK`, `STK`. SIMD uses the `RV_*` vector opcodes. The pairing and the VF window are read the same way for both.

The pairing and busy-cycle accounting for one opcode are computed by `tools/op-busy-cycles.py`; it takes the popped log and the instruction log and refuses to run on one alone. Instr IPC and Warp IPC figures are drawn with `tools/instr-ipc-plot.py` (`visualization/instr-ipc.md`).

## npusim note

The simulator maps a SoC name to a specific package revision. Check the local mapping before quoting a SoC name in a note.
