# Regression Harness

A shared, self-improving **regression harness** built on open Agent Skills
(`SKILL.md`), wrapping a single entry point (`./harness`) around run → extract →
report → review, plus a learning loop that promotes corrections back into the
skills.

First target: **pto-isa** (CPU simulator ST + NPU simulator ST). Later targets:
pto-vmi (CCE / DSL), costmodel, comm, and any target expressible as a suite
matrix.

> **New here?** Start with the [Handbook](docs/HANDBOOK.md) (the canonical
> reference) or the [User Journey](USER_JOURNEY.md), then run
> `./harness onboarding` and `./harness demo`. One entry point for everything:
> `./harness help`.

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
   `reports/baseline/baseline.json`*. Refresh it only deliberately (new suites /
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

`./harness baseline pto-isa` pins the baseline on the canonical machine (see
[Canonical environment](#canonical-environment)); it refuses unless every suite
PASSes (`--force` overrides).

---

## Use it

`./harness` is the single entry point:

```text
./harness run       Run suites            [--suite X | --all-suites] [--quiet | --tui | --json] [--dry-run] [--parallel] [--testcase T | --filter G]
./harness report    run.json → MD + HTML  [--run (default latest), --known, --out, --open]
./harness review    diff vs baseline      [--run (default latest), --baseline, --out]
./harness teach     log a correction      ["wrong -> correct -> action" | wizard | --edit]
./harness promote   learnings → skills    [--propose | --apply | --pr]
./harness baseline  re-pin baseline.json  [--force] [target]
./harness history   recent runs           [--limit, --json]
./harness clean     remove run dirs       [--dry-run, --keep N]
./harness open      open report.html      [run-id (default latest)]
./harness validate  check config files
./harness status    one-glance dashboard   [--json]
./harness diagnose  check env + fixes      [--json, --strict]
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

### What's automatic vs human

Every step of the interactive demo labels the three roles; the same boundary
applies to the real flow:

| Role | Actions |
|---|---|
| 🟢 **harness (automatic)** | run, extract logs, report, review, capture a correction, propose a diff |
| 🟡 **you / a reviewer** | triage judgment (`teach`), merging the MR (`promote --pr`) |

`./harness demo` shows this per step with a **"Who does what"** box
(command / harness / you). Capture is automatic; promotion is PR-gated — the
harness auto-logs but only *proposes* edits.

**Why the line is drawn there**: auto-*append* is safe — `learnings/recent.md`
is the harness's own scratch memory (append-only, cheap to discard). Auto-*edit*
is not — `SKILL.md` + `known-failures.md` are the team's shared source of truth
every future run reads. This is the same line Claude Code draws: it auto-writes
its memory but never auto-edits your `CLAUDE.md`. A machine that silently
rewrites shared knowledge turns its own mistakes into everyone's blind spots —
e.g. a wrong "known failure" would annotate real regressions as known and hide
them.

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
config/                   suites.json + arches.json + cann.json (source of truth)
scripts/                  drivers (see scripts/README.md: user verbs vs internals)
completions/              bash tab-completion for ./harness
learnings/                corrections.md / recent.md / promoted.md
reports/baseline/         pinned baseline.json (committed); other reports gitignored
demo/                     sandboxed walkthrough (config, fixtures, run_demo.sh, NARRATION.md)
env.example.sh            copy to env.sh for machine-local CANN / pto-isa paths
```

## Decisions (as agreed)

- Dedicated team repo `https://gitcode.com/ivanmang/regression-harness.git`.
- **Pinned baseline** committed at `reports/baseline/baseline.json`; all other
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

Capture is automated; promotion is a reviewable, git-tracked edit.

```bash
# 1. capture (strict LRN-… entry in learnings/recent.md)
./harness teach "symptom -> what it should do -> where to add"   # shorthand
./harness teach                                                 # or wizard
./harness teach --edit                                          # or $EDITOR
# (the agent also auto-captures when you correct it — no command needed)

# 2. propose a minimal diff into the right skill / known-failures (no write)
./harness promote --propose

# 3. apply + push + open a merge request, all in one command
./harness promote --pr
```

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