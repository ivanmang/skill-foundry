# Demo narration

Run `./demo/run_demo.sh` (or `PAUSE=1 ./demo/run_demo.sh` to step through).
Everything below is what you say *while* each scene prints — no heavy setup,
no hardware, works on any machine.

## The one-line pitch

> We turned "run the regression" into a shared skill + scripts + a pinned
> baseline. When we use it, it runs the suite, normalizes logs, renders a
> report, and diffs against a baseline. When we *correct* it, the correction is
> logged and promoted back into the skills — so next run, triage is faster and
> the report already flags known failures.

## Scene 0 — What this is

- "This is a mock gtest runner, but the harness scripts are the real ones — the
  same `run_suite.py`, `parse_gtest.py`, `build_report.py`, and `diff_runs.py`
  we use for pto-isa."
- "Two halves: **use** it, and **improve** it."

## Scene 1 — Use: run

- "One command runs the suite and produces a normalized `run.json` plus the raw
  log — extraction already happened."
- Point out: `run_suite.py` records the repo git ref, dirty flag, host, and env
  snapshot, so every result is reproducible.

## Scene 2 — Use: report

- "The report picks up one failing case: `VecOpTest.case_vcvt_bf16fp16_128x128`."
- "Right now the harness doesn't know *why* — it's just a failure."

## Scene 3 — Use: review vs baseline

- "Diffing against the pinned baseline flags the same case as a **regression**
  (PASS → FAIL). Avg and p99 are both tracked; p99 +15% trips a perf flag even
  when avg is flat."

## Scene 4 — Improve: auto-capture → auto-propose → apply

- "Now the important part. A person says: *that's a known vcvt round-field
  issue, not a new bug.*"
- "Capture is automatic: `log_correction.py` writes a strict `LRN-…` entry to
  `recent.md` — one command, no freeform editing. `session_digest.py` can even
  draft the same entry straight from the run's failures."
- "`promote_recent.py --propose` turns that pending entry into a **reviewable
  git-style diff** into the right file — no write yet. Then `--apply` writes it
  and moves the entry to `promoted.md` + `corrections.md`."
- "Watch the mechanical effect: known-failure signatures go 0 → 1, and
  re-rendering the *same* run.json now annotates the failure as **known**."
- Key line: "The agent didn't get smarter — the *harness* did. That's the
  self-improving loop."

## Scene 5 — Takeaway

- "Capture is automated; promotion is always a reviewed diff — mirroring how
  Claude Code auto-writes memory but doesn't auto-edit your CLAUDE.md."
- "Same flow, real target: `pto-isa` with `config/suites.json` + `arches.json`
  for CPU-ST and NPU-sim A5/A3/A6. A `gitcode` workflow can surface pending
  learnings nightly."
- "Small, git-tracked, reviewable improvements — no auto-rewriting, no black box."

## Anticipated Q&A

- **"Why not just a CI script?"** CI runs tests; this captures *how we triage*,
  *what we learned*, and *how to present it* — the part agents (and people)
  keep re-deriving. It sits on top of the existing `.gitcode` CI, doesn't replace it.
- **"Is the learning manual?"** Capture is automated (`log_correction.py` /
  `session_digest.py`); promotion is a scripted *proposal* that a human approves
  and a git PR commits — reviewable, revertable.
- **"What's auto vs gated?"** Append-only capture: auto. Editing shared skills:
  proposed automatically, applied on approval — never auto-rewritten, never
  removing an existing check silently.
- **"Does it need the A6 sim?"** No. The demo is mock; the real pto-isa NPU-sim
  A6 target runs on yellow (`dav_9201`), CPU-ST on any box with clang++≥15/g++≥13.