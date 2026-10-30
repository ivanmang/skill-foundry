# Demo

A self-contained, non-destructive live demo of skill-foundry. **No hardware,
compiler, or CANN needed** — it drives the *real* workflow scripts against a
mock gtest runner, so every step is the actual code you'd run on pto-isa.

It shows both halves:

- **USE** — the bundled regression workflow (`run → report → review` via the
  thin scripts).
- **IMPROVE** — the skill-ops loop (`capture → propose → gates → apply`).

## Run it

```bash
python3 -m skill_foundry.cli.demo             # interactive, step-by-step (arrow keys + Enter)
python3 -m skill_foundry.cli.demo --straight  # straight through (CI / quick skim)
PAUSE=1 ./demo/run_demo.sh                    # scene-by-scene with a pause (presenting)
```

Presenter talking points: [`NARRATION.md`](NARRATION.md).

### Interactive controls

After each step the tour offers a menu (arrow keys + Enter):

- **run this step** — execute the real workflow command and show its output
- **next / previous step** — move without running
- **jump to a step** — open the step map and pick any scene
- **explain more** — a short "why it matters" for the step
- **quit** — stop; artifacts remain under `reports/demo-live-<ts>/` and `/tmp`

## What it does (8 steps)

1. **run** — `demo/config/demo-suites.json` through the real
   `python3 -m skill_foundry.workflow.run` → `reports/demo-live-<ts>/run.json`
   + raw log (the mock suite fails one case on purpose).
2. **report** — `python3 -m skill_foundry.workflow.report` renders
   `report.md` / `report.html` (1 FAIL).
3. **review** — `python3 -m skill_foundry.workflow.review` diffs against
   `demo/baseline/demo-baseline.json` → flags a PASS→FAIL regression.
4. **teach** — `python3 -m skill_foundry.cli.teach` captures the correction as a
   strict `LRN-…` entry in `learnings/recent.md`.
5. **propose** — `python3 -m skill_foundry.cli.promote --propose` renders the
   reviewable diff (no write).
6. **apply** — `python3 -m skill_foundry.cli.promote --apply --no-review` writes
   it into `known-failures.md`, marks the entry `promoted`, and appends to
   `promoted.md` + `corrections.md`. (`--no-review` keeps the demo scripted and
   non-interactive; a *real* promote would run the LLM judge by default.)
7. **rerun** — re-render the *same* `run.json` with `--known` → the failure is
   now annotated **known**.
8. **takeaway** — the agent didn't get smarter, the harness did.

Run artifacts land under the gitignored `reports/` dir; the loop sandbox is in
`/tmp` — nothing in the tracked repo is touched.
