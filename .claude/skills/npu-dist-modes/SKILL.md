---
name: npu-dist-modes
description: >
  Use when choosing vlds/vsts distribution modes (NORM/DINTLV/E2B/BRC/UNPK/BLK
  loads, NORM/PK/PK4/INTLV stores) or deciding whether a data rearrangement
  should be an EXU instruction or a load/store mode. LSU-path semantics with a
  per-mode validation matrix; A5-validated, carries to A6 unless noted.
category: ascendc-dev
license: CANN Open Software License Agreement Version 2.0
origin: local
maturity: draft
owner: skill-foundry
---

# LSU dist-modes: rearrangement is free if you fold it into the memory op

**Core rule (R3)**: `vlds DINTLV_*` / `vsts INTLV/PK_*` execute on the **LSU**,
not the EXU — zero EXQ cost. Always prefer a dist-mode over the corresponding
vintlv/vdintlv/vpack instruction. DINTLV load ≈ 2 loads of cost; 2-dst INTLV
store ≈ 2 stores; 1-dst PK ≈ 1 store.

## Load modes (each: source consumed → VL produced)
| Mode | Reads | Produces |
|---|---|---|
| NORM | 256 B | contiguous VL |
| DINTLV_B16/B32 | 2×256 B | 2 VLs even/odd split |
| E2B_B16 | 8×B16 | each elem ×16 (its 32 B block) |
| **E2B_B32** | 8×B32 (32 B) | **each elem ×8** — stack on a ×4-dup source for per-32-elem scales |
| BRC_B32 | 1 elem | whole-VL broadcast |
| UNPK4_B8 | 64 B | 64 B repeated ×4 (PART_P0 then recovers all 64) |
| BLK | 32 B | 32 B block ×8 |

## Store modes
| Mode | Effect |
|---|---|
| NORM_BX | contiguous |
| PK_B32 | 2:1 narrow during store (bf16→packed) |
| PK4_B32 | 4:1 narrow (f32→u8) |
| INTLV_B16/B32 | interleave 2 source regs during store (512 B out) |

## Validation matrix (mode × dtype) — camodel status 2026-11
| Pairing | Status |
|---|---|
| UNPK4_B8 + PART_P0 → f8e4m3 | ✅ sim-verified (golden PASS) |
| **UNPK4_B8 + PART_P0 → f4e2m1x2** | ❌ **mis-decodes on 9.2β2/9.1β3 camodels** (quarter-scramble from byte 128; values from no input byte). Use NORM + 4-way PART as reference; golden-verify per camodel build |
| E2B_B32 from ×4-dup f32 source | ✅ sim-verified (DequantMXFp8 −43% port) |
| INTLV_B32 self-interleave (v,v) | ✅ sim-verified (×2 dup in registers→memory) |
| E2B_B16 from ×2-dup bf16 source | ✅ (quant kernels' per-32 scale broadcast) |

## Killer pattern: scale-broadcast without expansion loops
Never expand per-block scales with a 512-iteration BRC+masked-store loop
(measured 813 cyc for 512 scales). Build a dup buffer with **self-INTLV stores**
(each pass doubles every element: ×1→×2→×4) and let **E2B** replicate the rest
(×8 per element) in the consuming load. A5-sim measured: scale phase 813→194 cyc.

## Gotchas

- Drafted hub/inbox/npu-dist-modes/SKILL.md: mode tables, validation matrix (mode x dtype x camodel status), killer scale-broadcast pattern. Source: npu_skills load/store-dist-modes + DequantMXFp8 campaign. (was: Rearrangement done with vintlv/vdintlv/vpack EXU instructions (serializing the slide FU) and per-block scales expanded with per-element BRC+masked-store loops (measured 813 cyc for 512 scales); no validation matrix exists for dist-mode x dtype pairs, so the UNPK4_B8+f4 camodel mis-decode ships silently.) — `dissection of npu_skills case-writing (2026-11-04)`
