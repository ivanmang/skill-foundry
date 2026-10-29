# Skill Harness

A **skill-ops platform** built on open Agent Skills (`SKILL.md`): agents and
humans capture reusable knowledge as Skills during work, and it flows — through
an MR-gated promote step — into a shared hub every teammate's agent can
discover and use.

The first bundled workflow is **regression** (`run → report → review` on the
`pto-isa` and `pto-vmi` targets), but the product is the loop:
**capture → promote → hub → discover**. See [the Vision](docs/VISION.md) for
the architecture, [AGENTS.md](AGENTS.md) for the agent-facing contract.

> **New here?** Start with the [Handbook](docs/HANDBOOK.md) (the canonical
> reference), the [User Journey](USER_JOURNEY.md), or read
> [the Story](docs/STORY.md) — then run `./harness onboarding` and
> `./harness demo`.
> One entry point for everything: `./harness help`.

Legend: 🟢 automatic · 🟡 human · 🔴 never automatic · `✓ / ! / ·` runnable / missing / disabled.

---

## The two loops

```text
USE      ./harness run → report → review   (diff vs pinned baseline)
IMPROVE  ./harness teach → promote --pr    (corrections become skills)
```

- **USE** — run suites, extract logs, render reports, and diff against the
  pinned baseline. Exit codes: `0` clean, `1` ran-with-failures, `2` usage.
- **IMPROVE** — capture a correction (append-only), propose a diff (no write),
  then apply + open an MR — gated on human review. Capture is automatic;
  promotion is always reviewed.

See both loops live in ~2 minutes: `./harness demo`.

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
   `./harness list` marks it `!` if either is missing; `./harness cann` shows why.
5. **`--all-suites` auto-skips missing prereqs; an explicit `--suite` force-runs.**
   Safe-by-default, with an explicit override.
6. **Every run records context** (git ref, dirty flag, host, env) in `run.json`,
   so any result is reproducible on another machine.

---

## Getting started

```bash
git clone git@gitcode.com:ivanmang/regression-harness.git
cd regression-harness

./harness onboarding            # 1. guided setup: env.sh, CANN, pto-isa
./harness status                # 2. one-glance dashboard — is this machine ready?
./harness demo                  # 3. interactive walkthrough (no hardware needed)
./harness run --all-suites --dry-run   # 4. preview what will run
./harness run --all-suites --quiet     # 5. run everything runnable
./harness report --open          # 6. open the report in your browser
./harness review                 # 7. diff vs the pinned baseline
```

`./harness baseline <target>` pins the baseline on the canonical machine (see
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

---

## Use it

`./harness` is the single entry point:

```text
./harness run       Run suites            [--suite X | --all-suites] [--quiet | --tui | --json] [--dry-run] [--parallel] [--testcase T | --filter G]
./harness report    run.json → MD + HTML  [--run (default latest), --known, --out, --open]
./harness review    diff vs baseline      [--run (default latest), --baseline, --out]
./harness teach     log a correction      ["wrong -> correct -> action" | wizard | --edit]
./harness promote   learnings → skills    [--propose | --apply | --pr]
./harness capture-skill  draft a new skill   [--description, --dry-run]
./harness promote-skill  draft → skills     [--propose | --apply | --pr]
./harness skills    list/search skills    [--search, --inbox, --refresh, --json]
./harness baseline  re-pin baseline <target>.json  [--force] [target]
./harness history   recent runs           [--limit, --json]
./harness clean     remove run dirs       [--dry-run, --keep N]
./harness validate  check config files
./harness status    one-glance dashboard (all targets)  [--json, --target]
./harness diagnose  check env + fixes      [--json, --strict]
./harness skills    list/search skills    [--search, --inbox, --install, --uninstall, --refresh, --json]
./harness onboarding  guided first-run setup
./harness tui       full-screen dashboard (interactive)
./harness menu      curated menu (bare ./harness default)
./harness list      suites + arches       [--target, --format text|markdown|html]
./harness cann      which CANN → which arch  [--home, --scan, --json]
./harness guide     interactive tour of the real flow  [--demo]
./harness demo      interactive sandboxed walkthrough  [--straight]
./harness selfcheck compile-check + skill-spec validation + demo smoke
./harness help      show this — ./harness help <verb> for examples
./harness version   show the harness version   [--short]
```

Quick start:

```bash
./harness list                                     # what can I run?
./harness run --all-suites --quiet                 # run everything, summary only
./harness run --suite cpu-st                       # one suite
./harness run --suite npu-sim-a5 --testcase tpartargmax       # one testcase
./harness run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'   # one gtest case
./harness report --run reports/<id>/run.json \
  --known .claude/skills/pto-isa/references/known-failures.md --out reports/<id>/report
./harness report --open                 # latest run → browser
./harness review                         # latest run vs baseline
./harness history                        # recent runs
./harness clean --keep 3                 # purge old runs, keep 3 (keeps the baseline)
make check                               # run the self-check

source completions/harness.bash          # tab-completion (add to ~/.bashrc)
```

- `run` requires an explicit `--suite` **or** `--all-suites`; a bare `run` prints
  the enabled suites and exits 2.
- `./harness list` auto-detects availability per environment: `[✓]` = enabled
  and runnable, `[!]` = enabled but missing prereqs (with the reason), `[ ]` =
  disabled. `--all-suites` runs only the runnable ones and prints why the rest
  were skipped; an explicit `--suite` force-runs regardless.
- Exit codes: **0** clean, **1** ran-with-failures, **2** usage error.
- In an interactive terminal, every verb ends with a guided **"What next?"** menu —
  the natural next step for what you just ran, a **"type a command"** option, the
  full verb menu, or `q` to return to the shell. Skipped automatically when piped / in CI.
- Reports include a summary table, failures (annotated **known**), per-case
  **timing** (min/p50/p99/max), and — when a CAModel dump is present — a
  **Performance (CA metrics)** table (EX/IPC/vf_real/dual/stalls, modeled on the
  vmi-dashboard). See [docs/metrics.md](docs/metrics.md).

### What's automatic vs human

Four roles, shown on every demo step and applying to the real flow:

| Role | What it does |
|---|---|
| 🟢 **harness (automatic)** | run, extract logs, report, review, capture a correction, propose a diff, apply + commit + push + create the MR, dry-run previews |
| 🤖 **AI / agent (automatic, on trigger)** | auto-captures a correction when you correct it (`"no / actually / remember …"`) and replies with the `LRN-…` id; triages per the skill |
| 🟡 **you (remote gate)** | the triage *content* (`wrong → correct → action`) and **merging the MR on the remote** (branch protection) |
| 🔴 **never automatic** | remove or change an existing check |

`./harness demo` shows this per step with a **"Who does what"** box
(command / harness / you). Capture and apply are automatic — `--pr`
auto-creates the MR; the **merge** is the gate, and it lives on the remote.

**Why the line is drawn there**: auto-*append* is safe — `learnings/recent.md`
is the harness's own scratch memory (append-only, cheap to discard). Auto-*edit*
is not — `SKILL.md` + `known-failures.md` are the team's shared source of truth
every future run reads. So the harness auto-applies and auto-opens the MR, but
the **merge stays remote-gated** (branch protection). Same line Claude Code draws:
it auto-writes its memory but never auto-edits your `CLAUDE.md`. A machine that
silently rewrites shared knowledge turns its own mistakes into everyone's blind
spots — e.g. a wrong "known failure" would annotate real regressions as known and
hide them.

### Guided tour

```bash
./harness guide           # interactive step-by-step tour of the real flow
./harness demo            # interactive sandboxed demo (no hardware, step-by-step)
./harness demo --straight # demo straight through (for presenting / CI)
```

The guide walks you through env check → choose suites → run → report → review →
teach → promote, asking before each step. Interactive menus — the **demo/real**
choice, **suite**, **testcase**, **gtest filter**, **CANN package**, and
**output mode** — use arrow keys (`↑`/`↓` + Enter, highlighted selection; `q` to
skip) and fall back to numbered prompts when piped. If `ASCEND_HOME_PATH` is
unset, the CANN picker lists each installed package with which arches it can
compile vs simulate.

The demo (`./harness demo`) drives the **real** harness scripts against a mock
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
skills/                   inbox/ (skill drafts) + catalog.json (generated index)
mcp/                      MCP server (server.py + b10 deploy runbook)
config/                   suites.json + arches.json + cann.json (source of truth)
scripts/                  drivers (see scripts/README.md: user verbs vs internals)
completions/              bash tab-completion for ./harness
learnings/                corrections.md / recent.md / promoted.md
reports/baseline/         pinned <target>.json (committed); other reports gitignored
demo/                     sandboxed walkthrough (config, fixtures, run_demo.sh, NARRATION.md)
env.example.sh            copy to env.sh for machine-local CANN / pto-isa paths
```

## Decisions (as agreed)

- Dedicated team repo `https://gitcode.com/ivanmang/regression-harness.git`.
- **Pinned baseline** committed at `reports/baseline/<target>.json`; all other
  `reports/*` artifacts are gitignored.
- Perf regression flag: **p99 +15%** even if average is stable.
- The 11 existing `pto-isa/agents/skills` are kept as-is (referenced, not migrated).
- M1 scope = **CPU-ST + NPU-sim** (A5 / A3 / A6, matching the A6/v200 workflow).
- **Automation boundary**: capture auto, promotion propose/apply + MR-gated,
  never auto-remove/change an existing check.

## Conformance & portability

- Skills follow the open [Agent Skills spec](https://agentskills.io/specification):
  required `name` + `description` frontmatter (name matches folder, lowercase-hyphen,
  <=64 chars; description <=1024 chars), plus optional `license` + `compatibility`.
- **Scripts are deliberately co-located at the repo root** (`scripts/`), not inside a
  single skill folder, because the run/extract/diff/report drivers are shared by
  several skills. Skills reference them from the harness root (`./scripts/...`).
  Consequence: these are *co-located repo skills* — they work when this repo is
  checked out and used as the working directory, but a single skill folder copied
  alone into another tool's skills dir is **not** self-contained.
- **Conformance is machine-checked**: `./harness selfcheck` runs
  `scripts/validate_skills.py` against the open spec (or run it directly:
  `python3 scripts/validate_skills.py`).

## Canonical environment

Set machine-local paths in `env.sh` (copy `env.example.sh`) and
`source ./env.sh` before npu suites; cpu-st / static suites run without it.
`./harness list` tells you exactly what's runnable on the current machine.

| Tier | Where | Notes |
|---|---|---|
| CPU-ST | machine with clang++>=15 **or** g++>=13 | e.g. ecs / yellow / b10 |
| NPU-sim (A5/A3/A6) | a CANN toolkit with **both** compile headers (`include/pto/npu/<arch>`) **and** the simulator (`tools/simulator/<soc>`) | A6 sim lives on yellow (`dav_9201`); see `./harness cann` for which installed CANN covers which arch |

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

# 3. apply + commit + push + auto-create the MR — you merge it on the remote
./harness promote --pr
```

`--pr` auto-creates the MR via `glab` or the GitCode API (`GITCODE_TOKEN` /
`GITLAB_TOKEN`); otherwise it prints the MR-new URL for you to click. Set branch
protection on the repo so the merge itself is the review gate.

`.gitcode/workflows/promote-learnings.yml` surfaces pending learnings nightly;
`.gitcode/workflows/selfcheck.yml` runs `./harness selfcheck` on push/PR.

See `.claude/skills/skill-maintainer/SKILL.md` and run the live walkthrough:
`./harness demo` (interactive; narration in `demo/NARRATION.md`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm suites | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st: `Could not find a suitable compiler` | run on ecs / yellow / b10 (needs clang++>=15 or g++>=13) |
| npu-sim suite shows `!` in `./harness list` | `./harness cann` — the chosen CANN must have both headers and the simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `./harness run` returns exit 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | some suite did not PASS — fix it, or use `--force` |
| `report --open` → xdg-open errors / no browser | handled: WSL opens via `explorer.exe`; otherwise prints the path (+ Windows path on WSL) |