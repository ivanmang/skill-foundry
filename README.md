# Regression Harness

A shared, self-improving harness of **Agent Skills** for benchmark and regression
testing, built to the open Agent Skills specification (`SKILL.md`).

First target: **pto-isa** regression (CPU simulator ST + NPU simulator ST).

Teams in scope (later): pto-vmi (CCE / DSL), costmodel, comm, and any new target
that can be expressed as a suite matrix.

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

After a run, a user correction is logged to `learnings/recent.md`. The
`skill-maintainer` skill reviews recent entries and **proposes** (default) or
**applies** (small, high-confidence) minimal edits to the relevant `SKILL.md`,
then commits to git so the whole team benefits.

See `.claude/skills/skill-maintainer/SKILL.md`.