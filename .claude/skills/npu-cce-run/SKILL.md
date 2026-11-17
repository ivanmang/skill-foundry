---
name: npu-cce-run
description: >
  Compile, launch, record, and decode a hand-written CCE body (`.asc`) on the
  Ascend simulator. Use when you have a __simt_vf__ / __vector__ body — a
  single-op Schedule from skill:npu-op-burst, a hand-written kernel draft, or a
  formula's CCE spelling — and need the bisheng compile + npusim record +
  counter-decode recipe. Documents the launch/decode harness contract and the
  buffer-staging sync the staged bodies depend on.
license: CANN Open Software License Agreement Version 2.0
compatibility: >
  Requires the CANN toolkit (bisheng + set_env.sh), the TileLang tl_templates
  headers, the camodel runtime, and npusim. A launch.py + decode.py harness is
  required (contract below); it is case-local, not bundled here.
category: ascendc-dev
origin: native
maturity: ready
owner: skill-foundry
---

# Run a CCE body on Ascend

Compile, launch, record, and decode a hand-written CCE body. A CCE body is a
`.asc` compiled with `bisheng` (not `tilelang.compile`); the `.asc` suffix makes
`bisheng` treat the file as CCE. One shared library holds the device kernel and
the host `call`. Replace `<cann-set_env.sh>`, `<tilelang-repo>`, `<python>`, and
`<plot-python>` with the values for the machine.

## Environment

Source the CANN environment so `bisheng` and the headers resolve.

```bash
source <cann-set_env.sh>
```

The simulator library is not on the default library path; `launch.py` loads it
through `TL_CAMODEL_LIB`. Point it at the simulator tree for the target and
prepend it to the library path.

```bash
SIM_LIB="${ASCEND_HOME_PATH}/tools/simulator/<soc-simulator>/lib"
export TL_CAMODEL_LIB="${SIM_LIB}"
export LD_LIBRARY_PATH="${SIM_LIB}:${ASCEND_HOME_PATH}/runtime/lib64/stub:${ASCEND_HOME_PATH}/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
```

The record command uses `-s Ascend950`. The stub can report a different soc
revision than the simulator tree; `TL_CAMODEL_LIB` stays on the tree that
contains `libruntime_camodel.so`.

Use the TileLang python for the launch and the decode. The chart step can use a
different interpreter with matplotlib.

## Compile

Compile the `.asc` into one shared library.

```bash
cd <the .asc directory>

bisheng -O2 -fPIC -std=c++20 -shared --npu-arch=dav-3510 \
  -I <tilelang-repo>/src \
  -Wl,--no-mmap-output-file \
  body.asc -o body.so
```

| Flag | Role |
|---|---|
| `-O2` | Same optimization level as the TileLang Ascend object compile |
| `-fPIC -shared` | Host `.so` with `init`, `call`, and `get_last_error` |
| `-std=c++20` | Matches the TileLang bisheng wrapper |
| `--npu-arch=dav-3510` | Ascend 950 vector arch. This is the flag `bisheng` takes — not `--cce-aicore-arch=dav-c310-vec` |
| `-I <tilelang-repo>/src` | `tl_templates/ascend/common.h` and `debug.h` |
| `-Wl,--no-mmap-output-file` | Avoids an mmap write of the `.so` on some filesystems |

The headers pulled in by `common.h` (`acl/acl.h`, `simt_api/asc_simt.h`) resolve
from the CANN tree after `set_env.sh`. No extra `-I` is required for those.

The compile can print warnings of `'cce_global' attribute ignored` for the
`__gm__` casts inside `call()`. The `.so` is still produced.

Do not set `CPLUS_INCLUDE_PATH` to the gcc headers for this compile — that is for
TileLang kernel builds that mix the bisheng device compile with the host gcc,
and it breaks a normal host compile.

## Record

Wrap the launch in `npusim record`, one launch at a time.

```bash
npusim record -s Ascend950 -o ./npusim -g -n 0 \
  "<python> launch.py ./body.so 4096 32"
```

`-n 0` turns on core 0 logs. `-g` writes the report when the simulation ends.
`npusim record` returns after the child exits; a later teardown message is not a
failed kernel. Each run writes a timestamped directory; decode the newest
`instr.bin` under it.

## The launch/decode harness (contract — not bundled)

The `.asc` body exposes a uniform `call(void* dst, void* src, void* stream)`.
Two case-local scripts drive it. They are **not bundled here** (they are
per-case and machine-specific); reproduce this contract:

- **`launch.py`** — builds the inputs with a fixed seed, computes the fp32
  reference, and prints `PASS maxabs=<value>`. It calls `body.so`'s `call()`.
- **`decode.py`** — reads veccore0 (`core == 0`, `sub == 1`) and prints VF,
  el/cyc, mac/cyc, IPC, and spill counts. The last argument is `thread` for any
  SIMT trace (`VF_SIMT`), `simd` for a SIMD trace (`VF`).

For one opcode's busy cycles, use `skill:npu-single-opcode-rate`'s
`op-busy-cycles.py` (pairs the popped log starts with the instruction log
completions — busy union, both ends inclusive, overlap counted once):

```bash
BIN=$(find ./npusim -name instr.bin | head -1)
<python> op-busy-cycles.py SIMT_LDS "$BIN" "$BIN"
```

```bash
BIN=$(find ./npusim -name instr.bin | head -1)
<python> decode.py "$BIN" 4096 32 thread
```

VF is the completion of `VF_SIMT` minus its start, both ticks included, summed
across launches. el/cyc is output elements, `N / VF`. mac/cyc is products,
`N × K / VF`.

## Charts

Draw the instruction and IPC figures per `skill:npu-single-opcode-rate`
(`instr-ipc-plot.py`). One figure is the full window; a second is the first
ticks for detail. Address math is counted in the IPC line and left off the
instruction rows.

## Sync that the source depends on

A staged body copies `A` for a slab into the buffer, then signals and waits on
the copy before calling the VF. The measured GEMV body uses
`asc_sync_notify(PIPE_MTE2, PIPE_V, ev)` and `asc_sync_wait` on that event, and
only then calls the VF. A later slab also waits before reusing the buffer, and
the store to GM waits on its own pipe event. A run that skipped the first wait
left the first slab wrong. The sync is part of the body, not an optimization.

## Gotchas

- `npusim record` can return non-zero teardown; trust the `PASS` line, not the
  exit code.
- Do not set `CPLUS_INCLUDE_PATH` to gcc headers for the `.asc` bisheng compile.
- The stub soc name may differ from the simulator tree — `TL_CAMODEL_LIB` must
  point at the tree with `libruntime_camodel.so`.

## Output

- `body.so` (compiled device + host)
- a recorded `instr.bin` + the two per-core dumps
- decode output: VF, el/cyc, mac/cyc, IPC, spills

## See also

- `references/simt-vf.md` — the `__simt_vf__` language shape (lane = `tid & 31`).
- `skill:npu-op-burst` — runnable single-op Schedule bodies.
- `skill:npu-single-opcode-rate` — trace pairing, busy union, and charts.