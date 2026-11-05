# CA instruction-analysis constants

Facts for interpreting CA (cycle-accurate) instruction dumps and converting
counts to bandwidth/throughput. The authoritative extractor is
`npu_skills/pto-as/ca-instruction-breakdown/scripts/ca_instr_analysis.py`
(in the pto-isa repo); `skill_foundry/lib/perf_metrics.py` mirrors it. Keep
this doc and that code in agreement.

## Clock frequency

- `Ascend950pr_9599_model.toml` sets `core_period` = **200 ps**, so the camodel
  clock is **5 GHz**.
- Convert bytes/cycle → GB/s by multiplying by 5:
  `GB/s = bytes_per_cycle × 5`.

## SIMT `[type:]` width codes

`[type:]` codes encode **bytes per lane**, not total width:

| type | width |
|---|---|
| 1 | B8 |
| 2 | B16 |
| 4 | B32 |
| 5 | B64 |

With a 32-lane `execMask`, `type:2` = 2 B/lane × 32 lanes = **64 B per
instruction** (exact, not an estimate). `type:2` previously estimated near
48 B is wrong.

## MTE3 write bytes

- `MTE3 MOV_SRC_TO_DST` (UB → GM teardown store) is issued by the host at
  teardown and **not logged** in `core0.veccore0.instr_log.dump` — a raw read
  of the dump undercounts output bandwidth.
- Estimate the write bytes as `mte3_busy × 128 / 5.5` (calibrated factor
  5.3–6.4 across measured cast kernels; earlier 1.8 assumption is wrong).
- MTE2 read bytes come exactly from the XT descriptor low 16 bits — no estimate
  needed there.