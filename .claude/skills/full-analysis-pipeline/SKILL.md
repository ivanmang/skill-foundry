---
name: full-analysis-pipeline
description: >
  Orchestrate the full regression flow end to end: run-testcase -> extract-logs
  -> generate-report -> review-inconsistencies, then hand off to
  skill-maintainer when corrections or reusable patterns surface. Use when asked
  to run the full analysis pipeline or a complete regression analysis.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. Each stage is portable; the accelerator path needs the skill-foundry checkout.
category: regression
entry: true
stages: run-testcase, extract-logs, generate-report, review-inconsistencies, skill-maintainer
origin: native
---

# Full Analysis Pipeline

One entry point for the whole flow. Each stage delegates to its own skill; this
skill is the wiring and the handoff.

## Steps

1. **Run** — `run-testcase` for the target's suites (real pto-isa commands, or
   the accelerator `python3 -m skill_foundry.workflow.run --all-suites`).
2. **Extract** — `extract-logs` (bundled parser) into a `results` object.
3. **Report** — `generate-report` to `report.md` (+ `report.html`).
4. **Review** — `review-inconsistencies` against the pinned baseline.
5. **Handoff** — if the review surfaced (a) a user correction, (b) a repeated
   failure pattern, or (c) a missing check, log it with `skill-maintainer`.

## Pipeline contract

- Each stage reads the previous stage's files; do not recompute from scratch.
- A failed suite does **not** abort the pipeline; it is recorded and reported.
- The pipeline is idempotent: re-running the same run overwrites that run's artifacts.

## Handoff to maintainer

Log a correction and promote it (see `skill-maintainer` for the full loop):

```markdown
## LRN-20261027-003
- Context: <run-id>
- Wrong: <what the current flow missed>
- Correct: <what should happen instead>
- Action: <which skill to update + proposed edit>
```

## Output

- `run.json`, `report.md`, `report.html`
- a `learnings/recent.md` entry (when applicable)