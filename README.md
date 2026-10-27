# Regression Harness

A shared, self-improving harness of **Agent Skills** for benchmark and regression
testing, built to the open Agent Skills specification (`SKILL.md`).

First target: **pto-isa** regression (CPU simulator ST + NPU simulator ST).

Teams in scope (later): pto-vmi (CCE / DSL), costmodel, comm, and any new target
that can be expressed as a suite matrix.

> **New here?** Start with the [User Journey](USER_JOURNEY.md), run
> `./harness guide` for an interactive tour, or jump straight to the
> 2-minute sandboxed demo: `./harness demo`.
> One entry point for everything: `./harness help`.

---

## Use it

`./harness` is the single entry point:

```text
./harness run       Run suites            [--suite X | --all-suites] [--quiet | --tui | --json] [--testcase T | --filter G]
./harness report    run.json → MD + HTML  [--run, --known, --out]
./harness review    diff vs baseline      [--run, --baseline, --out]
./harness teach     log a correction      ["wrong -> correct -> action" | wizard | --edit]
./harness promote   learnings → skills    [--propose | --apply | --pr]
./harness baseline  re-pin baseline.json  [--force] [target]
./harness demo      2-minute walkthrough
./harness list      suites + arches       [--target, --format text|markdown|html]
./harness cann      which CANN → which arch  [--home, --scan, --json]
./harness selfcheck compile-check + demo smoke
./harness help      show this            ./harness version
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
./harness review --run reports/<id>/run.json       # diff vs the pinned baseline
./harness baseline pto-isa                         # re-pin the baseline (refuses if any suite FAILs)

source completions/harness.bash                    # tab-completion (add to ~/.bashrc)
```

- `run` requires an explicit `--suite` **or** `--all-suites`; a bare `run` prints
  the enabled suites and exits 2.
- Exit codes: **0** clean, **1** ran-with-failures, **2** usage error.

### Guided tour

```bash
./harness guide           # interactive step-by-step tour of the real flow
./harness guide --demo    # sandboxed demo tour (no hardware)
```

The guide walks you through env check → choose suites → run → report → review →
teach → promote, asking before each step.

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
  pto-isa/                Target adapter: pto-isa commands, suites, gotchas
config/                   suites.json + arches.json (source of truth)
scripts/                  drivers (see scripts/README.md: user verbs vs internals)
completions/              bash tab-completion for ./harness
learnings/                corrections.md / recent.md / promoted.md
reports/baseline/         pinned baseline.json (committed); other reports gitignored
env.example.sh            copy to env.sh for machine-local CANN / pto-isa paths
```

## Decisions (as agreed)

- Dedicated team repo `https://gitcode.com/ivanmang/regression-harness.git`.
- **Pinned baseline** committed at `reports/baseline/baseline.json`; all other
  `reports/*` artifacts are gitignored.
- Perf regression flag: **p99 +15%** even if average is stable.
- The 11 existing `pto-isa/agents/skills` are kept as-is (referenced, not migrated).
- M1 scope = **CPU-ST + NPU-sim** (A5 / A3 / A6, matching the A6/v200 workflow).

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
- If individual portability is ever needed, promote the shared drivers into a
  dedicated skill's `scripts/` folder (or a `harness-runner` skill).

## Canonical environment

Set machine-local paths in `env.sh` (copy `env.example.sh`) and
`source ./env.sh` before npu suites; cpu-st / static suites run without it.

| Tier | Where | Notes |
|---|---|---|
| CPU-ST | machine with clang++>=15 **or** g++>=13 | e.g. ecs / yellow / b10 |
| NPU-sim (A5/A3/A6) | CANN toolkit with simulator `tools/simulator/<soc>` | A6 sim lives on yellow (`dav_9201`) |

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
`./harness demo` (narration in `demo/NARRATION.md`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm suites | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st: `Could not find a suitable compiler` | run on ecs / yellow / b10 (needs clang++>=15 or g++>=13) |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `./harness run` returns exit 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | some suite did not PASS — fix it, or use `--force` |