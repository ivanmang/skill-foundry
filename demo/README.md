# Demo

A self-contained, non-destructive live demo of the skill-foundry.

- **No hardware / compiler / CANN needed** — it drives the *real* harness
  scripts against a mock gtest runner.
- Shows both halves: **use** the harness (run → report → review) and
  **improve** it (auto-capture → auto-propose → apply → triage improves).

## Run it

```bash
./harness demo                # interactive, step-by-step (arrow keys + Enter)
./harness demo --straight     # straight through (CI / quick skim)
PAUSE=1 ./demo/run_demo.sh    # scene-by-scene with a pause (for presenting)
```

Presenter talking points: [`NARRATION.md`](NARRATION.md).

### Interactive controls

After each step the tour offers a menu (arrow keys + Enter):

- **run this step** — execute the real harness command and show its output
- **next / previous step** — move without running
- **jump to a step** — open the step map and pick any scene
- **explain more** — a short "why it matters" for the step
- **quit** — stop; artifacts remain under `reports/demo-live-<ts>/` and `/tmp`

## What it does

1. Runs `demo/config/demo-suites.json` through the real `skill_foundry/cli/run.py`
   → `reports/demo-live-<ts>/run.json` + raw log.
2. `skill_foundry/cli/report.py` renders `report.md`/`report.html` (1 FAIL).
3. `skill_foundry/cli/review.py` diffs against `demo/baseline/demo-baseline.json`
   → flags a PASS→FAIL regression.
4. The (now scripted) learning loop, in a `/tmp` sandbox:
   - `skill_foundry/cli/teach.py` auto-captures the correction as a strict
     `LRN-…` entry in `learnings/recent.md`.
   - `skill_foundry/lib/session_digest.py` drafts the same entry straight from run.json.
   - `skill_foundry/cli/promote.py --propose` turns it into a reviewable diff,
     `--apply` writes it into `known-failures.md`, marks the entry `promoted`
     in `recent.md`, and appends a summary to `promoted.md` + an audit block to
     `corrections.md`.
   - Re-render the *same* run.json with `--known` → the failure is now
     annotated as **known**.

Run artifacts land under the gitignored `reports/` dir; the loop sandbox is in
`/tmp` — nothing in the tracked repo is touched.