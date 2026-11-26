---
name: task-observe
description: >
  Record skill usage and human interventions so the skill-health loop can see
  which skills were used, which were missing, and why a human had to step in.
  MUST use at task start and whenever loading a skill, searching for a skill, or
  logging a correction: load skills via `./harness skills load <name>` (never a
  bare file read) and search via `./harness skills --search <intent>` so the
  usage lands in .cache/metrics.jsonl and shows up in docs/SKILL_HEALTH.md.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and a skill-foundry checkout (the ./harness CLI).
category: regression
origin: native
maturity: ready
owner: skill-foundry
---

# Task Observe

Make skill usage observable. The coverage report
(`python3 -m skill_foundry.workflow.coverage --write`) can only answer "which
skills did the AI use / miss, and why did a human intervene" if the agent runs
the instrumented verbs below. A bare `read` of a SKILL.md is **silent** — it
produces no telemetry.

## Rules

> **CRITICAL**: run the exact commands below. Do not just state that you loaded
> or searched. The event is only recorded when the command runs.

### 1. LOAD — before using any skill

Instead of `read .claude/skills/<name>/SKILL.md`, run:

```bash
./harness skills load <name>
```

This prints the SKILL.md **and** records a `skill.load` event. If it prints
`skill '<name>' not found`, that is a `skill.load` miss — a missing-skill signal.

### 2. SEARCH — when no skill obviously matches (or to confirm routing)

```bash
./harness skills --search "<intent>"
```

Zero hits records a missing-skill (gap) signal; the output is your routing aid.

### 3. INTERVENE — when a human corrects you

```bash
./harness teach "wrong -> correct -> action" --attribution <attribution>
```

`<attribution>` is one of:

| attribution | meaning |
|---|---|
| `missing_skill` | no skill covered this |
| `wrong_skill` | a skill exists but is wrong/outdated |
| `not_followed` | a skill was correct but you skipped it |
| `env_changed` | tool/env/CANN/simulator changed |
| `new_knowledge` | nothing was wrong; a genuinely new fact |

## Why exact commands

The agent's default path (reading the file directly) is invisible to the loop.
`skills load` and `skills --search` are the only agent-agnostic capture points;
running them is what turns usage into data. The same pattern as `task-progress`:
either the command runs or it doesn't.

## Output

- `.cache/metrics.jsonl` events: `skill.load`, `skill.search`, `intervention`
- readable via `python3 -m skill_foundry.workflow.coverage [--write]`
