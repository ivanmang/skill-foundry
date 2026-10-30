# tilelangGym target

## Why

skill-foundry USE/IMPROVE already covers `pto-isa` / `pto-vmi`. SoftLib/ST clean
regress needs Motif ladder, Done-bar, TRACE, PRC, and forced PR9 overlays — encoded
here as target **tilelangGym** so agents follow the same suites → skills → teach →
promote loop without replacing multi-hour opencode runners.

## Suites

| Suite | Mode | What it checks |
|-------|------|----------------|
| `sv567-1xg-clean` | static gate | SoftLib 1×G Motif + dual_drain G16–128 + PR9 both arms + TRACE/PRC/RESULT |
| `sv567-nx1-outer` | static gate | VMI outer Nx1 pure VMAX + dual-era + VAND alternate-builder |
| `opencode-full` | disabled M3 | Placeholder — full opencode stays custom |

## Pack contract (`TILELANGGYM_PACK`)

Must contain (names flexible via shallow search):

- `EXPLORATION_TRACE.md` — required sections + Coverage COMPARE
- `ANALYSIS.md` — PRC-id cites
- `RESULT.tsv` — `era=` / `reduce_axis=` / motif
- `*_running_ipc_pr9.png` — reject IPC-only

## Skills

Under `.claude/skills/tilelanggym-*`. Motif seed + PRC knowledge under
`hub/tilelanggym/`.

## Out of scope

- Launching multi-hour opencode / tip peanut jobs from CI
- Pasting dig el/cyc into Motif seeds or gate fixtures
- Replacing tip ST harness L0–L9 inventories (skills point at concepts; live SoT from tip packs)
