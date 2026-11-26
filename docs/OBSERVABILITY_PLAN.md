# Observability Plan — skill-foundry

**Status:** implemented (all pieces below are live; verified 2026-11-26).

This document locks the reasoning behind the skill-usage observability layer so
the next person or agent can see *why* it's shaped the way it is, not just *what*
it is. The motivation was a single, recurring problem:

> "Every time the AI does a task, it may work or not. Sometimes a human has to
> interfere. But we never know **which part** has the problem and **which skills
> the AI used or was missing** — so we can't systematically make next time better."

---

## 1. The problem, restated

The original loop was strong at capturing **known knowledge** but blind to
**task-level attribution**:

| gap | consequence |
|---|---|
| no record of *which skills the AI actually used* | "we don't know what it read" |
| no record of *which skill was missing* | "we can't see coverage gaps" |
| no attribution on a *human intervention* | "we don't know why it failed" |
| no before/after metric | "we can't tell if it's improving" |

The capture→promote machinery (teach → LRN ledger → gated promote → human merge)
already existed and was not the problem. The problem was the **missing
observability spine** in front of it.

## 2. Two candidate mechanisms, one chosen

| | transcript scraping | boundary instrumentation |
|---|---|---|
| how it works | parse each agent's session log for tool calls | record at shared in-process entry points |
| generality | **agent-specific** (pi's `.jsonl` ≠ Claude Code's ≠ Cowork's) | **agent-agnostic** |
| drift risk | breaks with each agent's release | none (we own the boundary) |
| captures raw `read` of SKILL.md | yes | no |

**Chosen: boundary instrumentation.** The pi session schema was verified (tool
calls are `toolCall` blocks inside assistant `message.content`, results are
`role: "toolResult"` messages joined by `toolCallId`) — confirming transcript
scraping *works* for pi. But it is pi-only, so it is rejected as the primary
mechanism. The general mechanism is the two boundaries every agent already
passes through:

1. **MCP server** (`mcp/server.py`) — `skills_load` / `skills_list` / `teach` /
   `promote` / `capture_skill` (any MCP-capable agent).
2. **Harness verbs** (`./harness …`, routed via `skill_foundry/dispatch.py`) —
   shell agents.

## 3. The audit (what a naive first plan got wrong)

The first draft was audited against the real code; seven defects were found and
all are baked into the final design:

1. **Don't put `attribution` in the LRN entry.** The learning format is strictly
   enumerated (`promote.FIELD_ORDER`), so an extra field would be dropped on
   round-trip and leak into promoted skill content. → Attribution is a *separate
   telemetry event*, not a learnings field.
2. **Don't create a second event store.** `.cache/metrics.jsonl` already exists.
   → Task events reuse `metrics.record()`; no `task.jsonl`.
3. **Location.** `reports/` is git-tracked state; operational telemetry is
   gitignored `.cache/`. → events live in `.cache/metrics.jsonl`.
4. **Self-report is unreliable.** Agents acknowledge but skip file ops. → The
   verbs are the capture points (either the command runs or it doesn't); the
   transcript remains only a pi-specific *supplement*, not the source of truth.
5. **Ground "missing skill" in a real search**, not an agent's feeling. →
   `skill.search` with `hits == 0`.
6. **Don't auto-draft skills.** Emit a gap shortlist; a human/agent runs
   `capture-skill` deliberately. → `coverage` lists candidates, never writes inbox.
7. **Track a baseline.** Interventions/task and a daily trend are required for
   "better next time" to be measurable, not asserted.

## 4. Final architecture

```text
        agent (pi / Claude Code / Cowork / any MCP client)
                         │
        ┌────────────────┴─────────────────┐
        │  MCP tools        ./harness verbs │   ← the two instrumented boundaries
        │  skills_load      skills load     │
        │  skills_list      skills --search │
        │  teach(attribution) teach --attribution │
        └────────────────┬─────────────────┘
                         │  metrics.record(...)
                         ▼
            .cache/metrics.jsonl   (gitignored, operational)
                         │
                         ▼
        skill_foundry/workflow/coverage.py  →  docs/SKILL_HEALTH.md
```

The store is single, append-only JSONL, written through
`skill_foundry/lib/metrics.py::record()`.

## 5. Event schema

All events are `{"ts": …, "event": …, "event_id": …, …fields}`.

| event | fields | emitted by |
|---|---|---|
| `skill.load` | `skill`, `via` (`mcp`\|`cli`), `found` | `skills load` / `skills_load` |
| `skill.search` | `query`, `via`, `hits` | `skills --search` / `skills_list` |
| `intervention` | `attribution`, `skill?`, `note?`, `lrn?` | `teach --attribution` / MCP `teach` |
| `capture` | `id` (LRN), `skill` | `teach` (pre-existing) |
| `promote` / `promote_skill` / `judge` / `calibrate` | — | promote flow (pre-existing) |

Attribution taxonomy (`metrics.ATTRIBUTIONS`, single source of truth):

| value | meaning | next action it should trigger |
|---|---|---|
| `missing_skill` | no skill covered this | `capture-skill` a new skill |
| `wrong_skill` | skill exists but wrong/outdated | `teach` → promote |
| `not_followed` | skill correct but agent skipped it | harden skill wording (bash-command style) |
| `env_changed` | tool/env/CANN/simulator changed | update known-failures / env docs |
| `new_knowledge` | nothing was wrong; genuinely new fact | `teach` → promote as reference |

## 6. Components

| file | change | role |
|---|---|---|
| `skill_foundry/lib/metrics.py` | extended | `ATTRIBUTIONS`, `skill_load()`, `skill_search()`, `intervention()`, `skill_health()` (loads / searches / interventions / daily trend) |
| `skill_foundry/lib/loader.py` | **new** | `skill_body()` + `render_loaded()` — one skill resolver shared by both channels |
| `skill_foundry/cli/skills.py` | `load <name>` subcommand | shell load path → `skill.load`; records `skill.search` on `--search` |
| `skill_foundry/cli/teach.py` | `--attribution` flag | `intervention` event on correction |
| `skill_foundry/cli/learn.py` | `--attribution` forward | one-step capture+promote with attribution |
| `mcp/server.py` | `skills_load` + `teach` | MCP load/search/intervention path |
| `skill_foundry/workflow/coverage.py` | **new** | renders `docs/SKILL_HEALTH.md` / `--json` / `--write` |
| `.claude/skills/task-observe/SKILL.md` | **new** | mandates the instrumented verbs (exact-command pattern) |
| `AGENTS.md` | step 1 directive | "load via `skills load`, search via `skills --search`" |
| `.gitignore` | `docs/SKILL_HEALTH.md` | report is local/operational, not committed |
| `skill_foundry/verbs.py` | help text | `load <name>` documented |

## 7. The commands (user + agent surface)

```bash
# agent: load a skill (records skill.load) — NOT a bare `read`
./harness skills load <name>

# agent: search / confirm routing (records skill.search; 0 hits = gap)
./harness skills --search "<intent>"

# agent: log a human correction with attribution (records capture + intervention)
./harness teach "wrong -> correct -> action" --attribution <taxonomy>
./harness learn  "wrong -> correct -> action" --attribution <taxonomy> --pr

# anyone: read the health report
python3 -m skill_foundry.workflow.coverage          # markdown to stdout
python3 -m skill_foundry.workflow.coverage --json   # machine-readable
python3 -m skill_foundry.workflow.coverage --write  # + docs/SKILL_HEALTH.md
```

MCP equivalents: `skills_load(name)`, `skills_list(search=…)`,
`teach(wrong, correct, action, attribution=…)`.

## 8. User flow (end to end)

1. User expresses intent.
2. Agent loads the skill(s) via `skills load` (or `skills_load`), searches via
   `skills --search` when nothing matches — **both recorded**.
3. Agent does the work (thin scripts, per the skills).
4. Works → done. Fails / human corrects → step 5.
5. Agent logs the correction with `teach --attribution <why>`.
6. `promote --pr` → mechanical gates + LLM judge → **human merges**.
7. `coverage --write` → `docs/SKILL_HEALTH.md` shows loads, misses, gaps,
   interventions, and the daily trend.

Only three things are ever human-only: intent/triage judgment, the `--pr` merge,
and a deliberate baseline re-pin.

## 9. Decisions log

| decision | rationale |
|---|---|
| instrument boundaries, not transcripts | generality across agents; no per-agent drift |
| attribution is telemetry, not an LRN field | keeps learnings format + promote logic untouched |
| one store (`.cache/metrics.jsonl`) | reuse existing `metrics.record`/`summarize` |
| report is gitignored | data source is gitignored; committing would be a stale snapshot |
| vendor library (`~/skills-library/AGENTS.md`) left untouched | it's a self-contained import; harness coupling stays in `skill-foundry/AGENTS.md` |
| `skills load` prints the SKILL.md | makes the load command *also* the read, so usage is captured for free |

## 10. Remaining / possible follow-ups

- **pi-only supplement:** a transcript-derived `skill.load` verifier that
  cross-checks `read` tool calls against recorded loads (catches agents that
  bypassed `skills load`). Deliberately deferred — it's pi-specific.
- **Intervention calibration:** a human `calibrate` event confirming the
  attribution tag, mirroring the existing judge-calibration in `metrics.py`.
- **Auto-draft from gaps:** `coverage` currently *lists* gap candidates; wiring
  them into `capture-skill` drafts is a deliberate future step (not unattended).

## 11. Verification done

- `./harness skills load skill-maintainer` → prints SKILL.md, records `skill.load found=true`.
- `./harness skills load no-such-skill` → exit 1, records `skill.load found=false`.
- `./harness skills --search zzz-no-such-skill-xyz` → 0 hits, appears in `missing_skill_queries`.
- `./harness teach … --attribution wrong_skill --file /tmp/…` → `capture` + `intervention` events.
- `coverage --write` → `docs/SKILL_HEALTH.md` with loads / misses / gaps / interventions / trend.
- `validate_skills --strict` → OK (132 skills, spec + reference integrity).
