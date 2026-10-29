# skill-foundry

A **skill-ops platform** built on open Agent Skills (`SKILL.md`): agents and
humans capture reusable knowledge as Skills during work, and it flows — through
a promote step (`--direct` push or `--pr` MR) — into a shared hub every
teammate's agent can discover and use.

The first bundled workflow is **regression** (`run → report → review` on the
`pto-isa` and `pto-vmi` targets), but the product is the loop:
**capture → promote → hub → discover**. See [the Vision](docs/VISION.md) for
the product framing, [the Architecture](docs/ARCHITECTURE.md) for the
user/agent/harness/MCP roles & interaction, and [AGENTS.md](AGENTS.md) for the
agent-facing contract.

> **New here?** Start with the [Handbook](docs/HANDBOOK.md) (the canonical
> reference) or the [User Journey](USER_JOURNEY.md) — then run
> `python3 -m skill_foundry.cli.onboarding` and `python3 -m skill_foundry.cli.demo`.
> One entry point for everything: `./harness help`.

Legend: 🟢 automatic · 🟡 human · 🔴 never automatic · `✓ / ! / ·` runnable / missing / disabled.

---

## The two loops

```text
USE      run → report → review   (python3 -m skill_foundry.workflow.* · diff vs pinned baseline)
IMPROVE  ./harness teach → promote --direct | --pr    (corrections become skills)
```

- **USE** — run suites, extract logs, render reports, and diff against the
  pinned baseline. Exit codes: `0` clean, `1` ran-with-failures, `2` usage.
- **IMPROVE** — capture a correction (append-only), propose a diff (no write),
  then apply + commit + push — `--direct` to `origin/main` (no token), or `--pr`
  for an MR-gated review. Capture is automatic; with `--pr` the merge is reviewed.

See both loops live in ~2 minutes: `python3 -m skill_foundry.cli.demo`.

---

## The rules that keep the signal honest

Six rules that matter more than they look — get these wrong and the regression
signal itself is corrupted:

1. **The pinned baseline is the ground truth.** "Regression" means *diff vs
   `reports/baseline/<target>.json`*. Refresh it only deliberately (new suites /
   arch changes), never casually — a bad re-pin poisons every future run.
2. **Never auto-remove or auto-change an existing check.** The harness adds
   entries; it never silently deletes or weakens one. Removing a check is how
   regressions start leaking through.
3. **p99 > +15% flags a perf regression even if average is stable.** Never trust
   average alone — averages hide tail latency.
4. **An npu-sim suite needs BOTH the CANN compile headers AND the simulator.**
   `python3 -m skill_foundry.workflow.run --list` marks it `!` if either is missing; `python3 -m skill_foundry.lib.cann` shows why.
5. **`--all-suites` auto-skips missing prereqs; an explicit `--suite` force-runs.**
   Safe-by-default, with an explicit override.
6. **Every run records context** (git ref, dirty flag, host, env) in `run.json`,
   so any result is reproducible on another machine.

---

## Getting started

```bash
git clone git@gitcode.com:ivanmang/skill-foundry.git
cd skill-foundry

python3 -m skill_foundry.cli.onboarding            # 1. guided setup: env.sh, CANN, pto-isa
python3 -m skill_foundry.workflow.status                # 2. one-glance dashboard — is this machine ready?
python3 -m skill_foundry.cli.demo                  # 3. interactive walkthrough (no hardware needed)
python3 -m skill_foundry.workflow.run --all-suites --dry-run   # 4. preview what will run
python3 -m skill_foundry.workflow.run --all-suites --quiet     # 5. run everything runnable
# steps 5–7 in one command:
#   python3 -m skill_foundry.workflow.run --all-suites --report --open --review
python3 -m skill_foundry.workflow.report --open          # 6. open the report in your browser (standalone)
python3 -m skill_foundry.workflow.review                 # 7. diff vs the pinned baseline (standalone)
```

`bash skill_foundry/workflow/baseline.sh <target>` pins the baseline on the canonical machine (see
[Canonical environment](#canonical-environment)); it refuses unless every suite
PASSes (`--force` overrides).

---

## Agent setup (skills discoverability)

Skills live in one canonical place — `.claude/skills/` — and are reachable by
any Agent-Skills-compatible agent two ways:

- **Project-level** (work in the repo, zero setup): Claude Code reads
  `.claude/skills/`; Pi and open-standard agents read `.agents/skills/` (a
  symlink to the same skills).
- **Always-on** (regardless of cwd): one command to link into each installed
  agent's user dir — `./harness skills --install` (auto-detects Claude Code / Pi /
  open-standard; `--uninstall` to remove). Then restart/reload the agent.

### MCP server

Any MCP-capable agent can also talk to the harness directly, no shell required:
`mcp/server.py` exposes `status`, `skills.list/search/load`, `capture-skills`,
`teach`, `promote`, and `workflow.run` over stdio or HTTP. Hosting + runbook:
[mcp/b10-deploy.md](mcp/b10-deploy.md).

### Plugin & marketplace

This repo is also a **Claude Code plugin** and a **marketplace** — teammates
install the skills + MCP server in one step:

```bash
claude plugin marketplace add ivanmang/skill-foundry
claude plugin install skill-foundry@skill-foundry
```

Files: `.claude-plugin/plugin.json` (manifest), `.claude-plugin/marketplace.json`
(catalog), `.mcp.json` (MCP server), `skills/` (the skills).

---

## Use it

`./harness` is the single entry point — and it does **only the skill-ops loop**.
The bundled regression workflow runs directly as thin scripts (the skills hold
the knowledge).

```text
./harness — THE PRODUCT (capture → promote → hub → discover):
  capture-skill  Draft a NEW skill into hub/inbox/      [--description, --dry-run]
  promote-skill  Publish a draft into .claude/skills/   [--propose | --apply | --direct | --pr]
  teach          Log a correction                       ["wrong -> correct -> action" | wizard | --edit]
  promote        Publish learnings into skills          [--propose | --apply | --direct | --pr]
  skills         List/search · install · refresh        [--search, --inbox, --install, --uninstall, --refresh, --json]
  menu           Curated menu (bare ./harness default)
  selfcheck      Compile-check + skill-spec validation + demo smoke
  help / version

BUNDLED WORKFLOW — regression, run directly (the skills reference these):
  python3 -m skill_foundry.workflow.run    [--suite X | --all-suites] [--report|--open|--review] …
  python3 -m skill_foundry.workflow.report · .review · .status · .diagnose · .history · .clean · .validate
  bash skill_foundry/workflow/baseline.sh  [--force] <target>
  python3 -m skill_foundry.lib.cann        (which CANN → which arch)
  python3 -m skill_foundry.cli.guide · .demo · .onboarding   (interactive tours)
```

Optional install — makes the CLI available anywhere as `skill-foundry`
(`./harness` already works with no install):

```bash
pip install -e .        # needs setuptools>=64, pip>=21.3
skill-foundry version
```

Quick start:

```bash
./harness skills                                    # what skills exist?
./harness capture-skill code-review                 # draft a new skill
./harness teach "symptom -> correct -> action"      # log a correction
./harness promote --direct                          # publish learnings (push to main)

# the bundled regression workflow (see .claude/skills/ for full knowledge):
python3 -m skill_foundry.workflow.run --all-suites --report --open --review
```
### What's automatic vs human

Four roles, shown on every demo step and applying to the real flow:

| Role | What it does |
|---|---|
| 🟢 **harness (automatic)** | run, extract logs, report, review, capture a correction, propose a diff, apply + commit + push (`--direct` to main, or `--pr` creates the MR), dry-run previews |
| 🤖 **AI / agent (automatic, on trigger)** | auto-captures a correction when you correct it (`"no / actually / remember …"`) and replies with the `LRN-…` id; triages per the skill |
| 🟡 **you (remote gate)** | the triage *content* (`wrong → correct → action`) and **merging the MR on the remote** (branch protection) |
| 🔴 **never automatic** | remove or change an existing check |

`python3 -m skill_foundry.cli.demo` shows this per step with a **"Who does what"** box
(command / harness / you). Capture and apply are automatic — `--direct` pushes
straight to `origin/main` (no token); `--pr` auto-creates the MR and the
**merge** is the gate on the remote.

**Why the line is drawn there**: auto-*append* is safe — `learnings/recent.md`
is the harness's own scratch memory (append-only, cheap to discard). Auto-*edit*
is not — `SKILL.md` + `known-failures.md` are the team's shared source of truth
every future run reads. So the harness auto-applies and pushes — `--direct`
straight to `main` (fast, tokenless) or `--pr` with the **merge remote-gated**
(branch protection). Either way it only *adds*; it never removes or changes an
existing check. Same line Claude Code draws:
it auto-writes its memory but never auto-edits your `CLAUDE.md`. A machine that
silently rewrites shared knowledge turns its own mistakes into everyone's blind
spots — e.g. a wrong "known failure" would annotate real regressions as known and
hide them.

### Guided tour

```bash
python3 -m skill_foundry.cli.guide           # interactive step-by-step tour of the real flow
python3 -m skill_foundry.cli.demo            # interactive sandboxed demo (no hardware, step-by-step)
python3 -m skill_foundry.cli.demo --straight # demo straight through (for presenting / CI)
```

The guide walks you through env check → choose suites → run → report → review →
teach → promote, asking before each step. Interactive menus — the **demo/real**
choice, **suite**, **testcase**, **gtest filter**, **CANN package**, and
**output mode** — use arrow keys (`↑`/`↓` + Enter, highlighted selection; `q` to
skip) and fall back to numbered prompts when piped. If `ASCEND_HOME_PATH` is
unset, the CANN picker lists each installed package with which arches it can
compile vs simulate.

The demo (`python3 -m skill_foundry.cli.demo`) drives the **real** harness scripts against a mock
gtest runner, one step at a time. Each step is a framed block with a progress
bar, a step map (`✓` done · `▶` current · `·` upcoming), a **"Who does what"**
box, and a menu: **run & continue / skip / back / jump / explain / quit**.

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

## Decisions (as agreed)

- Dedicated team repo `https://gitcode.com/ivanmang/skill-foundry.git`.
- **Pinned baseline** committed at `reports/baseline/<target>.json`; all other
  `reports/*` artifacts are gitignored.
- Perf regression flag: **p99 +15%** even if average is stable.
- The 11 existing `pto-isa/agents/skills` are kept as-is (referenced, not migrated).
- M1 scope = **CPU-ST + NPU-sim** (A5 / A3 / A6, matching the A6/v200 workflow).
- **Automation boundary**: capture auto, promotion propose/apply + `--direct`
  push or `--pr` MR-gated, never auto-remove/change an existing check.

## Conformance & portability

- Skills follow the open [Agent Skills spec](https://agentskills.io/specification):
  required `name` + `description` frontmatter (name matches folder, lowercase-hyphen,
  <=64 chars; description <=1024 chars), plus optional `license` + `compatibility`.
- **Scripts are co-located in the `skill_foundry/` package**, not inside a single
  skill folder, because the run/extract/diff/report drivers are shared by several
  skills. Skills reference them from the harness root (`python3 -m skill_foundry...`),
  and the `./harness` entry point maps each verb onto its module in
  `skill_foundry/cli/` (product) or `skill_foundry/workflow/` (regression).
  Consequence: these are *co-located repo skills* — they work when this repo is
  checked out and used as the working directory, but a single skill folder copied
  alone into another tool's skills dir is **not** self-contained.
- **Conformance is machine-checked**: `./harness selfcheck` runs
  `skill_foundry/lib/validate_skills.py` against the open spec (or run it directly:
  `python3 -m skill_foundry.lib.validate_skills`).

## Canonical environment

Set machine-local paths in `env.sh` (copy `env.example.sh`) and
`source ./env.sh` before npu suites; cpu-st / static suites run without it.
`python3 -m skill_foundry.workflow.run --list` tells you exactly what's runnable on the current machine.

| Tier | Where | Notes |
|---|---|---|
| CPU-ST | machine with clang++>=15 **or** g++>=13 | e.g. ecs / yellow / b10 |
| NPU-sim (A5/A3/A6) | a CANN toolkit with **both** compile headers (`include/pto/npu/<arch>`) **and** the simulator (`tools/simulator/<soc>`) | A6 sim lives on yellow (`dav_9201`); see `python3 -m skill_foundry.lib.cann` for which installed CANN covers which arch |

See `.claude/skills/pto-isa/references/env.md` for the arch/soc/env table.

## Learning loop

Capture is automated; promotion is automated to the MR, and the **merge is
remote-gated** (branch protection).

```bash
# 1. capture (strict LRN-… entry in learnings/recent.md)
./harness teach "symptom -> what it should do -> where to add"   # shorthand
./harness teach                                                 # or wizard
./harness teach --edit                                          # or $EDITOR
# (the agent also auto-captures when you correct it — no command needed)

# 2. propose a minimal diff (optional review, no write)
./harness promote --propose

# 3. apply + commit + push to origin/main directly — no MR, no token
./harness promote --direct
#    (or MR-gated: ./harness promote --pr — needs GITCODE_TOKEN/glab)
```

`--pr` auto-creates the MR via `glab` or the GitCode API (`GITCODE_TOKEN` /
`GITLAB_TOKEN`); otherwise it prints the MR-new URL for you to click. Set branch
protection on the repo so the merge itself is the review gate.

`.gitcode/workflows/promote-learnings.yml` surfaces pending learnings nightly;
`.gitcode/workflows/selfcheck.yml` runs `./harness selfcheck` on push/PR.

See `.claude/skills/skill-maintainer/SKILL.md` and run the live walkthrough:
`python3 -m skill_foundry.cli.demo` (interactive; narration in `demo/NARRATION.md`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm suites | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st: `Could not find a suitable compiler` | run on ecs / yellow / b10 (needs clang++>=15 or g++>=13) |
| npu-sim suite shows `!` in `python3 -m skill_foundry.workflow.run --list` | `python3 -m skill_foundry.lib.cann` — the chosen CANN must have both headers and the simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `python3 -m skill_foundry.workflow.run` returns exit 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | some suite did not PASS — fix it, or use `--force` |
| `report --open` → xdg-open errors / no browser | handled: WSL opens via `explorer.exe`; otherwise prints the path (+ Windows path on WSL) |