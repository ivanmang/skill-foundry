# AGENTS.md

This is a **skill harness** (skill-ops platform) — agents and humans capture
reusable knowledge as Skills during work, and it flows through an MR-gated
promote step into a shared hub every teammate's agent can use. Regression is
the first bundled workflow.
platform. You (the agent) are the conductor; `./harness` is the tool; the user
is the only human gate.

## Your workflow

1. **Read the skills first** — they are your instruction set, under
   `.claude/skills/` (also reachable via `.agents/skills/`). Start with
   the target adapter (`pto-isa` / `pto-vmi`) and the pipeline skills
   (`run-testcase` → `extract-logs` → `generate-report` →
   `review-inconsistencies`).
2. **Drive everything through `./harness`** — never hand-edit test results or
   re-implement the pipeline.
3. **Capture every reusable lesson** with `./harness teach` automatically when
   any of these happen:
   - the user corrects you (`"no / wrong / actually / don't / remember …"`)
   - a suite fails and the cause is reusable or repeats
   - review flags a gap (missing check, wrong threshold, un-triaged failure)
   - an external tool / command behaves unexpectedly
   Reply with the `LRN-…` id you logged.
   For a **brand-new skill** (not a lesson about an existing one), draft it with
   `./harness capture-skill <name>`, then promote it.
4. **Promote captured lessons** with `./harness promote --pr` (learnings) or
   `./harness promote-skill <name> --pr` (new skills) — auto-applies, commits,
   pushes, and **creates the MR**. The merge is gated on the remote (branch
   protection); **never self-merge**.
5. **Never remove or change an existing check** — the harness only adds.

## Capture vs promote

- Capture is **automatic and continuous** — log lessons as they surface during
  development; nothing changes until promoted.
- Promotion is **automatic to the MR** — `--pr` does the apply/commit/push/create;
  the human merge is the gate.
- Draft from a run's failures with `session_digest.py --run <run.json> --apply`.

## Key commands

```bash
./harness status                    # is the machine ready? (auto-detected)
./harness run --all-suites --dry-run / --quiet / --parallel
./harness run --suite <s> --testcase <t> --filter <g>
./harness report --open             # per-case metrics + log links
./harness review                    # diff vs the pinned baseline
./harness teach "wrong -> correct -> action"
./harness promote --propose | --direct | --pr
./harness capture-skill <name>           # draft a NEW skill
./harness promote-skill <name> --direct  # publish it (direct push, no token)
./harness promote-skill <name> --pr      # publish it (MR-gated)
./harness skills [--search q] [--inbox]  # discover skills
./harness demo                      # sandboxed walkthrough (no hardware)
./harness help [verb]
```

## Layout

- `.claude/skills/` — the skills (read them first)
- `config/` — targets (`suites.json`), arches, CANN matrix (source of truth)
- `learnings/recent.md` — captured pending lessons
- `reports/baseline/<target>.json` — pinned baseline (regression = diff vs it)
- `docs/` — handbook, metrics reference, story

## Rules

- Exit codes: `0` clean · `1` ran-with-failures · `2` usage.
- `--all-suites` auto-skips suites whose prereqs are missing; an explicit
  `--suite` force-runs.
- npu-sim needs BOTH compile headers AND the simulator; p99 +15% flags a perf
  regression even if average is stable.
- The baseline is the ground truth — refresh it only deliberately.