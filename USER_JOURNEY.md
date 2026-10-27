# PTO Regression Harness — User Journey

From first clone to a self-improving regression loop, end to end. Every command
below is real; the mock demo lets you experience the whole journey in ~2 minutes
without hardware.

---

## The 30-second version

The harness turns *"run the regression"* from a repeated instruction into:

- **Skills** (`.claude/skills/`) that tell any agent *how* to run/triage/report.
- **Scripts** (`scripts/`) that actually do the run → extract → report → review.
- A **pinned baseline** (`reports/baseline/baseline.json`) so "regression" =
  *diff vs baseline*.
- A **learning loop** (`learnings/` + `log_correction.py` / `promote_recent.py`)
  that captures corrections and promotes them back into the skills.

Two loops, always:

```
USE     run → extract → report → review (diff vs baseline)
IMPROVE capture → propose → apply → PR → next run is smarter
```

---

## Personas

| Role | Typical activity |
|---|---|
| **Developer** | Runs regressions, reads reports, triages failures |
| **Reviewer** | Approves proposed skill changes (PR merge) |
| **Maintainer** | Curates `learnings/`, refreshes the baseline |

You'll usually wear the first hat, sometimes the last two.

---

## Step 0 — One-time setup

```bash
git clone git@gitcode.com:ivanmang/regression-harness.git
cd regression-harness

# optional: point at your pto-isa checkout (default ~/pto-isa)
export PTO_ISA_REPO=~/pto-isa
```

Requirements are only `python3` + `git` for the harness itself. The *targets*
have their own needs:

| Suite | Needs |
|---|---|
| `cpu-st` | clang++>=15 **or** g++>=13 (run on ecs / yellow / b10, not the blue laptop) |
| `npu-sim-a5/a3` | a CANN toolkit with the matching simulator |
| `npu-sim-a6` | yellow (`dav_9201`); pto-isa headers before CANN include |

---

## Step 1 — Try it in 2 minutes (no hardware)

```bash
./demo/run_demo.sh            # or PAUSE=1 ./demo/run_demo.sh to step through
```

This runs the **real** harness scripts against a mock gtest runner and walks the
entire journey (run → report → review → correct → promote → re-run). Everything
happens in `/tmp` + the gitignored `reports/`, so the repo stays clean.

---

## Step 2 — First real run: pin the baseline

On a canonical machine (see table above):

```bash
./scripts/make_baseline.sh pto-isa
# runs all enabled suites, copies the result to reports/baseline/baseline.json

git add reports/baseline/baseline.json
git commit -m "chore: pin pto-isa regression baseline"
git push
```

From now on, every run is compared against this **pinned** baseline. Refresh it
only deliberately (new suites, arch changes), never casually.

---

## Step 3 — Everyday: run a regression

```bash
# all enabled M1 suites (cpu-st + npu-sim a5/a3/a6)
./scripts/run_suite.sh --target pto-isa --all-suites

# one suite
./scripts/run_suite.sh --target pto-isa --suite cpu-st

# one testcase
python3 tests/script/run_st.py -r sim -v a5 -t tadd -g 'TADDTest.case_*'
```

Each run produces, under `reports/<run-id>/`:

```text
run.json        # metadata (git ref, dirty, host, env) + normalized results
<suite>.log     # raw runner output
report.md/.html # generated report (see Step 4)
```

The driver records **context** (repo commit, host, CANN/ASCEND path) so any
result is reproducible — a FAIL on one machine can be re-investigated elsewhere.

---

## Step 4 — Read the report

```bash
python3 scripts/build_report.py --run reports/<run-id>/run.json \
  --known .claude/skills/pto-isa/references/known-failures.md \
  --out reports/<run-id>/report
```

You get `report.md` + a self-contained `report.html`:

```text
| suite      | passed | failed | skipped | total | status | duration |
|------------|--------|--------|---------|-------|--------|----------|
| cpu-st     | 42     | 0      | 0       | 42    | PASS   | 1.20s    |
| npu-sim-a5 | 38     | 1      | 0       | 39    | FAIL   | 2m 10s   |

### Failures
- `npu-sim-a5/VecOpTest.case_vcvt_bf16fp16_128x128` — **known**: vcvt round-field swap
```

Failures already matched against the triage corpus are annotated **known**,
saving you the triage time.

---

## Step 5 — Review vs the baseline (the regression signal)

```bash
python3 scripts/diff_runs.py --run reports/<run-id>/run.json
```

```text
regressions: 1  fixes: 1  new: 3  removed: 0  perf_flags: 1

REGRESSIONS (PASS -> FAIL):
  npu-sim-a5/VecOpTest.case_vcvt_bf16fp16_128x128  (PASS -> FAIL)

PERF FLAGS (p99 > +15%):
  cpu-st: p99 1.00s -> 1.20s (+20%, avg +2%)
```

- **regression** = was PASS, now FAIL (the thing you must look at).
- **fix** = was FAIL, now PASS.
- **perf flag** = p99 rose >15% **even if avg is stable** — never report avg alone.

---

## Step 6 — Triage a failure

The `pto-isa` adapter skill drives this. In order:

1. Read the **first concrete error line** from `<suite>.log`.
2. Classify: compile / link / camodel / numeric-wrong / alignment / soc-mismatch
   / env-leak / timeout.
3. Check `.claude/skills/pto-isa/references/known-failures.md` first.

If it's in the corpus → done, it was already flagged known. If not → go to
Step 7 and teach it.

---

## Step 7 — Teach it (the learning loop)

You found something the harness didn't know. Capture it, propose the fix, and
promote it — capture is automatic, promotion is reviewed.

### 7a. Capture (automatic, append-only)

Use the friendly `teach` entry point (wizard, shorthand, or editor):

```bash
# shorthand — one string, split on " → " into wrong / correct / action
./scripts/teach "device vcvt round-field mismatch → known pattern, annotate it → promote to known-failures"

# interactive wizard — no flags to remember
./scripts/teach

# editor — opens $EDITOR with a prefilled template
./scripts/teach --edit

# or auto-draft pending entries straight from a run
python3 scripts/session_digest.py --run reports/<run-id>/run.json --apply
```

This appends a strict, parseable entry to `learnings/recent.md`:

```markdown
## LRN-20261027-003
- category: correction
- context: reports/<run-id>
- skill: pto-isa
- wrong: device vcvt round-field mismatch
- correct: known vcvt round-field pattern; annotate instead of re-triage
- action: promote vcvt round-field swap into known-failures
- status: pending
```

### 7b. Propose (auto-draft a diff, no write)

```bash
python3 scripts/promote_recent.py --propose
```

It renders a **reviewable git-style diff** into the right place (a new
`known-failures.md` entry, or a `## Gotchas` bullet in the target skill).

### 7c. Apply + PR (scripted, human-gated)

```bash
python3 scripts/promote_recent.py --apply --branch feat/learnings-20261027
git push -u origin feat/learnings-20261027
# open the PR; a reviewer merges
```

`--apply` writes the edit, moves the entry from `recent.md` → `promoted.md`,
logs it in `corrections.md`, and commits on the branch. Nothing is ever
auto-merged.

---

## Step 8 — Next run is smarter

Re-run the *same* `run.json` through the report with the improved corpus:

```bash
python3 scripts/build_report.py --run reports/<run-id>/run.json \
  --known .claude/skills/pto-isa/references/known-failures.md --out reports/<run-id>/report
```

The failure that was a raw FAIL is now:

```markdown
- `npu-sim-a5/VecOpTest.case_vcvt_bf16fp16_128x128` — **known**: vcvt round-field swap
```

The agent didn't get smarter — **the harness did**. That's the self-improving
loop, and every teammate gets it via git.

---

## Step 9 — Ongoing maintenance

| Cadence | Action |
|---|---|
| Nightly | `.gitcode/workflows/promote-learnings.yml` surfaces pending learnings |
| Weekly / on demand | reviewer merges `feat/learnings-*` PRs |
| After suite changes | `./scripts/make_baseline.sh pto-isa` to re-pin the baseline |
| After a correction | re-run one representative case to verify it improved triage |

---

## Command quick reference

| Goal | Command |
|---|---|
| Sandboxed walkthrough | `./demo/run_demo.sh` |
| Pin / refresh baseline | `./scripts/make_baseline.sh pto-isa` |
| Run all suites | `./scripts/run_suite.sh --target pto-isa --all-suites` |
| Run one suite | `./scripts/run_suite.sh --target pto-isa --suite cpu-st` |
| Report | `python3 scripts/build_report.py --run reports/<id>/run.json --known <kf> --out <base>` |
| Diff vs baseline | `python3 scripts/diff_runs.py --run reports/<id>/run.json` |
| Capture correction | `python3 scripts/log_correction.py …` |
| Auto-draft from run | `python3 scripts/session_digest.py --run reports/<id>/run.json --apply` |
| Propose promotion | `python3 scripts/promote_recent.py --propose` |
| Apply + branch | `python3 scripts/promote_recent.py --apply --branch feat/learnings-<date>` |

---

## Automation boundaries

| Step | Automation |
|---|---|
| Capture a correction (`recent.md`, append-only) | 🟢 automatic |
| Draft promotion (diff, no write) | 🟢 automatic |
| Apply + commit | 🟡 scripted, PR-gated |
| Remove / change an existing check | 🔴 never automatic |

This mirrors the industry norm: like Claude Code auto-writing memory but not
auto-editing your `CLAUDE.md`, the harness auto-logs but only *proposes* edits.

---

## Hygiene rules

- Promote only corrections that are **reusable** or occurred **more than once**.
- Never remove an existing check without strong evidence.
- Keep `description` frontmatter stable unless triggers genuinely change.
- No secrets / credentials / sensitive data in skills or learnings.
- Small, reviewable diffs beat sweeping rewrites.
