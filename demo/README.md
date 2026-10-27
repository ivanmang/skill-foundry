# Demo

A self-contained, non-destructive live demo of the regression harness.

- **No hardware / compiler / CANN needed** — it drives the *real* harness
  scripts against a mock gtest runner.
- Shows both halves: **use** the harness (run → report → review) and
  **improve** it (correction → promotion → better triage next run).

## Run it

```bash
./demo/run_demo.sh            # straight through
PAUSE=1 ./demo/run_demo.sh    # pause between scenes (for presenting)
```

Presenter talking points: [`NARRATION.md`](NARRATION.md).

## What it does

1. Runs `demo/config/demo-suites.json` through `scripts/run_suite.py`
   (real driver) → `reports/demo-live-<ts>/run.json` + raw log.
2. `scripts/build_report.py` renders `report.md`/`report.html` (1 FAIL).
3. `scripts/diff_runs.py` diffs against `demo/baseline/demo-baseline.json`
   → flags a PASS→FAIL regression.
4. Simulates the learning loop in a `/tmp` sandbox: log a correction, promote a
   `known-failures` entry, show the git-style diff, then re-render the *same*
   run.json with `--known` → the failure is now annotated as **known**.

Run artifacts land under the gitignored `reports/` dir; the loop sandbox is in
`/tmp` — nothing in the tracked repo is touched.