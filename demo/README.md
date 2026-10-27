# Demo

A self-contained, non-destructive live demo of the regression harness.

- **No hardware / compiler / CANN needed** — it drives the *real* harness
  scripts against a mock gtest runner.
- Shows both halves: **use** the harness (run → report → review) and
  **improve** it (auto-capture → auto-propose → apply → triage improves).

## Run it

```bash
./demo/run_demo.sh            # straight through
PAUSE=1 ./demo/run_demo.sh    # pause between scenes (for presenting)
```

Presenter talking points: [`NARRATION.md`](NARRATION.md).

## What it does

1. Runs `demo/config/demo-suites.json` through the real `scripts/run_suite.py`
   → `reports/demo-live-<ts>/run.json` + raw log.
2. `scripts/build_report.py` renders `report.md`/`report.html` (1 FAIL).
3. `scripts/diff_runs.py` diffs against `demo/baseline/demo-baseline.json`
   → flags a PASS→FAIL regression.
4. The (now scripted) learning loop, in a `/tmp` sandbox:
   - `scripts/log_correction.py` auto-captures the correction as a strict
     `LRN-…` entry in `learnings/recent.md`.
   - `scripts/session_digest.py` drafts the same entry straight from run.json.
   - `scripts/promote_recent.py --propose` turns it into a reviewable diff,
     `--apply` writes it into `known-failures.md` and moves the entry to
     `promoted.md` + `corrections.md`.
   - Re-render the *same* run.json with `--known` → the failure is now
     annotated as **known**.

Run artifacts land under the gitignored `reports/` dir; the loop sandbox is in
`/tmp` — nothing in the tracked repo is touched.