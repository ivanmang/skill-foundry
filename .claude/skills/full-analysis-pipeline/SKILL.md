---
name: full-analysis-pipeline
description: >
  Orchestrate the full regression flow end to end: run-testcase -> extract-logs
  -> generate-report -> review-inconsistencies, then hand off to
  skill-maintainer when corrections or reusable patterns surface. Use when asked
  to run the full analysis pipeline or a complete regression analysis.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. Delegates to the run/extract/report/review skills.
---

# Full Analysis Pipeline

One entry point for the whole flow. Each stage delegates to its own skill; this
skill is the wiring and the handoff.

## Steps

1. **Run** — `run-testcase` for the target's enabled suites
   (`./harness run --all-suites`, or a narrow `--suite`/`--testcase`).
2. **Extract** — confirm `run.json` contains per-suite `results` (the driver
   does this automatically; re-run `extract-logs` only if a parse failed).
3. **Report** — `generate-report` to `report.md` + `report.html`.
4. **Review** — `review-inconsistencies` against the pinned baseline.
5. **Handoff** — if the review surfaced (a) a user correction, (b) a repeated
   failure pattern, or (c) a missing check, log it with `./harness teach "…"`
   and hand to `skill-maintainer`.

## Pipeline contract

- Each stage reads the previous stage's files; do not recompute from scratch.
- A failed suite does **not** abort the pipeline; it is recorded and reported.
- The pipeline is idempotent: re-running with the same run-id overwrites that
  run's artifacts.

## Handoff to maintainer

Log with `./harness teach "wrong -> correct -> action"` (it writes the strict
`LRN-…` entry automatically), then hand to `skill-maintainer` to promote.
`skill-maintainer` runs `./harness promote --pr`, which auto-applies, commits,
pushes, and creates the MR — the human merges it on the remote.

```markdown
## LRN-20261027-003
- Context: <run-id>
- Wrong: <what the current flow missed>
- Correct: <what should happen instead>
- Action: <which skill to update + proposed edit>
```

## Output

- `reports/<run-id>/run.json`, `report.md`, `report.html`
- `learnings/recent.md` entry (when applicable)
