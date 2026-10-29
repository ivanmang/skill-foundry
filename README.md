# skill-foundry

A **skill-ops platform** built on open Agent Skills (`SKILL.md`): agents and
humans capture reusable knowledge as Skills during work, and it flows — through
a promote step (`--direct` push or `--pr` MR) — into a shared hub every
teammate's agent can discover and use.

The first bundled workflow is **regression** (`run → report → review` on the
`pto-isa` and `pto-vmi` targets), but the product is the loop:
**capture → promote → hub → discover**.

- [Vision](docs/VISION.md) — the product framing
- [Architecture](docs/ARCHITECTURE.md) — user / agent / harness / MCP roles & interaction
- [AGENTS.md](AGENTS.md) — the agent-facing contract

> **New here?** Start with the [Handbook](docs/HANDBOOK.md) (canonical
> reference) or the [User Journey](USER_JOURNEY.md). One entry point for
> everything: `./harness help`.

---

## The two loops

```text
USE      run → report → review     (thin scripts · diff vs pinned baseline)
IMPROVE  teach → promote --direct | --pr    (corrections become skills)
```

- **USE** — the bundled regression workflow: run suites, extract logs, render
  reports, and diff against the pinned baseline. Run directly:
  `python3 -m skill_foundry.workflow.run --all-suites --report --open --review`.
- **IMPROVE** — the product loop: capture a correction (append-only), propose a
  diff (no write), then publish. Capture is automatic; `--direct` pushes to
  `origin/main` (no token), `--pr` keeps the merge human-gated.

See both loops in ~2 minutes: `python3 -m skill_foundry.cli.demo`.

---

## Quick start

```bash
git clone git@gitcode.com:ivanmang/skill-foundry.git
cd skill-foundry

# the product — the skill-ops loop (all ./harness does):
./harness skills                                   # what skills exist?
./harness capture-skill code-review                # draft a new skill
./harness teach "symptom -> correct -> action"     # log a correction
./harness promote --direct                         # publish learnings (push to main)

# the bundled regression workflow (thin scripts; see .claude/skills/):
python3 -m skill_foundry.cli.onboarding            # env.sh, CANN, pto-isa (one-time)
python3 -m skill_foundry.workflow.run --all-suites --report --open --review
```

Only `python3` + `git` are required for the harness itself. Optional: make the
CLI available anywhere as `skill-foundry`:

```bash
pip install -e .        # needs setuptools>=64, pip>=21.3
skill-foundry version
```

---

## Set up your agent

Your agent uses the harness through two things: **skills** (the knowledge) and
**MCP** (the tools). Three ways to wire them up:

### 1. Skills — project-level (zero setup)

If you work *inside* this repo, skills are discovered automatically:

- **Claude Code** reads `.claude/skills/`
- **Pi** and open-standard agents read `.agents/skills/` (a symlink to the same skills)

Nothing to run.

### 2. Skills — always-on (any directory)

Make all 8 skills available in every project:

```bash
./harness skills --install     # symlinks each skill into ~/.claude/skills/, ~/.pi/skills/, ~/.agents/skills/
```

It auto-detects which agents are installed and prints the reload hint for each.
Remove with `./harness skills --uninstall`.

### 3. Tools — MCP (optional, typed calls)

Point your agent at the hosted server (or run it locally) so it can call
`skills_list`, `skills_load`, `capture_skill`, `teach`, and `promote` as typed
tools instead of shelling out:

```jsonc
// .mcp.json — read by any MCP-capable agent that supports project config
{
  "mcpServers": {
    "skill-foundry": { "type": "http", "url": "https://pto-b10.ddns.net/mcp" }
  }
}
```

Or install it as a **Claude Code plugin** (bundles skills + MCP in one step):

```bash
claude plugin marketplace add ivanmang/skill-foundry
claude plugin install skill-foundry@skill-foundry
```

To run the server locally instead (stdio): `python3 mcp/server.py`
(needs `pip install fastmcp`).

### Per-agent cheat sheet

| Agent | Skills (project) | Skills (always-on) | MCP tools |
|---|---|---|---|
| **Claude Code** | auto (`.claude/skills/`) | `./harness skills --install` → `~/.claude/skills/`; restart or `/reload` | `claude plugin install skill-foundry@skill-foundry`, or `claude mcp add skill-foundry --url https://pto-b10.ddns.net/mcp` |
| **Pi** | auto (`.agents/skills/`) | `./harness skills --install` → `~/.pi/skills/`; `/reload` | connect `https://pto-b10.ddns.net/mcp` in Pi's MCP config |
| **Open-standard / other** | auto (`.agents/skills/`) | `./harness skills --install` → `~/.agents/skills/`; restart | use the `.mcp.json` above |

---

## The rules that keep the signal honest

Six rules that matter more than they look — get these wrong and the regression
signal itself is corrupted:

1. **The pinned baseline is the ground truth.** "Regression" means *diff vs
   `reports/baseline/<target>.json`*. Refresh it deliberately (new suites /
   arch changes), never casually — a bad re-pin poisons every future run.
2. **Never auto-remove or auto-change an existing check.** The harness adds
   entries; it never silently deletes or weakens one.
3. **p99 > +15% flags a perf regression even if average is stable.** Never trust
   average alone — averages hide tail latency.
4. **An npu-sim suite needs BOTH the CANN compile headers AND the simulator.**
   `python3 -m skill_foundry.workflow.run --list` marks it `!` if either is
   missing; `python3 -m skill_foundry.lib.cann` shows why.
5. **`--all-suites` auto-skips missing prereqs; an explicit `--suite` force-runs.**
6. **Every run records context** (git ref, dirty flag, host, env) in `run.json`,
   so any result is reproducible on another machine.

---

## Reference

`./harness` does **only the skill-ops loop**. The bundled regression workflow
runs directly as thin scripts the skills reference.

```text
./harness — THE PRODUCT (capture → promote → hub → discover):
  capture-skill  Draft a NEW skill into hub/inbox/      [--description, --dry-run]
  promote-skill  Publish a draft into .claude/skills/   [--propose | --apply | --direct | --pr | --review] [--force]
  teach          Log a correction                       ["wrong -> correct -> action" | wizard | --edit]
  promote        Publish learnings into skills          [--propose | --apply | --direct | --pr | --review] [--force]
  skills         List/search · install · refresh        [--search, --inbox, --install, --uninstall, --refresh, --json]
  menu           Curated menu (bare ./harness default)
  selfcheck      Compile-check + skill-spec validation + demo smoke

BUNDLED WORKFLOW — regression, run directly (the skills reference these):
  python3 -m skill_foundry.workflow.run    [--suite X | --all-suites] [--report|--open|--review] …
  python3 -m skill_foundry.workflow.report · .review · .status · .diagnose · .history · .clean · .validate
  bash skill_foundry/workflow/baseline.sh  [--force] <target>
  python3 -m skill_foundry.lib.cann        (which CANN → which arch)
  python3 -m skill_foundry.cli.guide · .demo · .onboarding   (interactive tours)
```

### What's automatic vs human

| Role | What it does |
|---|---|
| 🟢 **scripts (automatic, agent-driven)** | run, extract logs, report, review, dry-run previews |
| 🟢 **harness (automatic, gated)** | capture a correction, propose a diff, apply + commit + push (add-only · no-secrets · size); `--direct` to main, or `--pr` auto-merges on green CI |
| 🤖 **AI / agent (on trigger)** | auto-captures when you correct it (`"no / actually / remember …"`); triages per the skill |
| 🟡 **you (gate)** | the triage *content* (`wrong → correct → action`) and merging the MR (`--pr` only) |
| 🔴 **never automatic** | remove or change an existing check |

**Why the line is there:** auto-*append* is safe (scratch memory, cheap to
discard); auto-*edit* is not (`SKILL.md` + `known-failures.md` are the shared
source of truth every run reads). So promotion only *adds* — `--direct` to
`main`, or `--pr` with the merge remote-gated.

---

## Layout

```text
.claude/skills/           Open-standard skills (one folder + SKILL.md each)
  run-testcase/           Run a declared suite -> normalized run record
  extract-logs/           Raw logs -> results.json
  generate-report/        results.json -> Markdown + HTML
  review-inconsistencies/ Diff a run vs the pinned baseline
  full-analysis-pipeline/ Orchestrate run -> extract -> report -> review -> maintainer
  skill-maintainer/       Learning/correction loop
  pto-isa/                Target adapter (+ references/: env, suite matrix, cann matrix, known-failures)
  pto-vmi/                Target adapter (CCE/DSL + CA metrics)
skills/                   → .claude/skills/ (plugin-standard skills dir)
.agents/skills/           → .claude/skills/ (Pi + open-standard agents)
hub/                      inbox/ (skill drafts) + catalog.json (generated index)
.claude-plugin/           plugin.json + marketplace.json (Claude Code plugin + marketplace)
.mcp.json                 MCP server config (bundled into the plugin)
mcp/                      MCP server (server.py + deploy/start/tls scripts + runbook)
config/                   suites.json + arches.json + cann.json (source of truth)
skill_foundry/            the Python package (see skill_foundry/README.md)
  cli/                    THE PRODUCT: skill-ops verbs + shell (teach/promote/skills/…)
  workflow/               bundled regression workflow (run/report/review/status/…)
  lib/                    thin stable helpers (parse_gtest/perf_metrics/targets/…)
pyproject.toml            package metadata + `skill-foundry` console script
completions/              bash tab-completion for ./harness
learnings/                corrections.md / recent.md / promoted.md
reports/baseline/         pinned <target>.json (committed); other reports gitignored
demo/                     sandboxed walkthrough (config, fixtures, run_demo.sh, NARRATION.md)
env.example.sh            copy to env.sh for machine-local CANN / pto-isa paths
```

---

## Decisions (as agreed)

- Dedicated team repo `https://gitcode.com/ivanmang/skill-foundry.git`.
- **Pinned baseline** committed at `reports/baseline/<target>.json`; all other
  `reports/*` artifacts are gitignored.
- Perf regression flag: **p99 +15%** even if average is stable.
- The 11 existing `pto-isa/agents/skills` are kept as-is (referenced, not migrated).
- M1 scope = **CPU-ST + NPU-sim** (A5 / A3 / A6, matching the A6/v200 workflow).
- **Automation boundary**: capture auto; promotion `--direct` push or `--pr`
  MR-gated; never auto-remove/change an existing check.

---

## Conformance & portability

- Skills follow the open [Agent Skills spec](https://agentskills.io/specification):
  required `name` + `description` frontmatter (name matches folder, lowercase-hyphen,
  <=64 chars; description <=1024 chars), plus optional `license` + `compatibility`.
- **Scripts are co-located in the `skill_foundry/` package**, not inside a single
  skill folder, because the run/extract/diff/report drivers are shared by several
  skills. Skills reference them from the harness root (`python3 -m skill_foundry...`),
  and `./harness` maps only the product (skill-ops) verbs onto
  `skill_foundry/cli/`; the regression workflow modules live in
  `skill_foundry/workflow/` and are run directly.
  Consequence: these are *co-located repo skills* — they work when this repo is
  checked out and used as the working directory, but a single skill folder copied
  alone into another tool's skills dir is **not** self-contained.
- **Conformance is machine-checked**: `./harness selfcheck` runs
  `skill_foundry/lib/validate_skills.py` against the open spec (or run it directly:
  `python3 -m skill_foundry.lib.validate_skills`).

---

## Canonical environment

Set machine-local paths in `env.sh` (copy `env.example.sh`) and `source ./env.sh`
before npu suites; cpu-st / static suites run without it.
`python3 -m skill_foundry.workflow.run --list` tells you what's runnable here.

| Tier | Where | Notes |
|---|---|---|
| CPU-ST | machine with clang++>=15 **or** g++>=13 | e.g. ecs / yellow / b10 |
| NPU-sim (A5/A3/A6) | a CANN toolkit with **both** compile headers (`include/pto/npu/<arch>`) **and** the simulator (`tools/simulator/<soc>`) | A6 sim lives on yellow (`dav_9201`); see `python3 -m skill_foundry.lib.cann` |

---

## Learning loop

Capture is automated; promotion is **gated and automatic** — every promote runs
the gates (add-only · no-secrets · size · spec), then either pushes `--direct`
(no token) or opens a `--pr` that **auto-merges when the CI gates are green**.

```bash
# 1. capture (strict LRN-… entry in learnings/recent.md)
./harness teach "symptom -> what it should do -> where to add"   # shorthand
./harness teach                                                 # or wizard
./harness teach --edit                                          # or $EDITOR
# (the agent also auto-captures when you correct it — no command needed)

# 2. propose a minimal diff (optional review, no write)
./harness promote --propose

# 3. publish — gated, direct push (no token) or MR-gated
./harness promote --direct
#    (or ./harness promote --pr — auto-merges when CI gates pass)
#    (or ./harness promote --review --direct — an LLM judge APPROVEs first)
#    (--force bypasses the gates)
```

See `.claude/skills/skill-maintainer/SKILL.md` and the live walkthrough:
`python3 -m skill_foundry.cli.demo` (narration in `demo/NARRATION.md`).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm suites | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st: `Could not find a suitable compiler` | run on ecs / yellow / b10 (clang++>=15 or g++>=13) |
| npu-sim suite shows `!` in `python3 -m skill_foundry.workflow.run --list` | `python3 -m skill_foundry.lib.cann` — need BOTH headers and simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `python3 -m skill_foundry.workflow.run` exits 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | a suite didn't PASS — fix it, or `--force` |
| `report --open` → xdg-open errors / no browser | handled: WSL opens via `explorer.exe`; else prints the path |
| skills not showing up in the agent | run `./harness skills --install`, then restart/reload the agent |