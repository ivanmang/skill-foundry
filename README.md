# Regression Harness

A shared, self-improving harness of **Agent Skills** for benchmark and regression
testing, built to the open Agent Skills specification (`SKILL.md`).

First target: **pto-isa** regression (CPU simulator ST + NPU simulator ST).

Teams in scope (later): pto-vmi (CCE / DSL), costmodel, comm, and any new target
that can be expressed as a suite matrix.

> **New here?** Start with the [User Journey](USER_JOURNEY.md), or run the
> 2-minute sandboxed walkthrough: `./demo/run_demo.sh`.

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
scripts/                  Zero-dependency Python + shell drivers
learnings/                corrections.md / recent.md / promoted.md
reports/baseline/         pinned baseline.json (committed); other reports gitignored
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

## Quickstart

```bash
# Run one suite (produces reports/<run-id>/run.json + raw log)
./scripts/run_suite.sh --target pto-isa --suite cpu-st

# Run all enabled M1 suites for pto-isa
./scripts/run_suite.sh --target pto-isa --all-suites

# Extract/normalize an existing log
python3 scripts/parse_gtest.py --log path/to/run.log --suite cpu-st --out results.json

# Compare a run against the pinned baseline
python3 scripts/diff_runs.py --run reports/<run-id>/run.json

# Generate a Markdown + HTML report
python3 scripts/build_report.py --run reports/<run-id>/run.json --out reports/<run-id>/report

# (Re)generate + commit the pinned baseline on the canonical machine
./scripts/make_baseline.sh
```

## Canonical environment

| Tier | Where | Notes |
|---|---|---|
| CPU-ST | machine with clang++>=15 **or** g++>=13 | e.g. ecs / yellow / b10 |
| NPU-sim (A5/A3/A6) | CANN toolkit with simulator `tools/simulator/<soc>` | A6 sim lives on yellow (`dav_9201`) |

See `.claude/skills/pto-isa/references/env.md` for the arch/soc/env table.

## Learning loop

Capture is automated; promotion is a reviewable, git-tracked edit.

```bash
# 1. capture a correction (strict LRN-… entry in learnings/recent.md)
python3 scripts/log_correction.py --category correction --context <run-id> \
  --skill pto-isa --wrong "…" --correct "…" --action "…"

# 1b. or auto-draft pending entries straight from a run
python3 scripts/session_digest.py --run reports/<run-id>/run.json [--apply]

# 2. propose a minimal diff into the right skill / known-failures (no write)
python3 scripts/promote_recent.py --propose

# 3. apply it (moves entry to promoted.md, logs to corrections.md)
python3 scripts/promote_recent.py --apply [--branch feat/learnings-<date>]
```

`.gitcode/workflows/promote-learnings.yml` surfaces pending learnings nightly.

See `.claude/skills/skill-maintainer/SKILL.md` and run the live walkthrough:
`./demo/run_demo.sh` (narration in `demo/NARRATION.md`).