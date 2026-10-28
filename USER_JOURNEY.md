# PTO Regression Harness — User Journey

From first clone to a self-improving regression loop, end to end. Every command
below is real; the mock demo lets you experience the whole journey in ~2 minutes
without hardware.

> **Looking for the full reference?** See [docs/HANDBOOK.md](docs/HANDBOOK.md)
> (canonical) — this page is the narrative walkthrough.

---

## The 30-second version

The harness turns *"run the regression"* from a repeated instruction into:

- **Skills** (`.claude/skills/`) that tell any agent *how* to run/triage/report.
- **Scripts** behind a **single entry point** (`./harness …`) that do the
  run → extract → report → review.
- A **pinned baseline** (`reports/baseline/baseline.json`) so "regression" =
  *diff vs baseline*.
- A **learning loop** (`./harness teach` to capture, `./harness promote` to
  promote) that turns corrections into skills.

Two loops, always:

```text
USE      run → extract → report → review (diff vs baseline)
IMPROVE  capture → propose → apply → MR → next run is smarter
```

And a simple rule of thumb for who does what:

- 🟢 **harness does** — run, extract, report, review, capture, propose.
- 🟡 **you / a reviewer do** — the triage judgment (`teach`), merging the MR
  (`promote --pr`).

And six rules that keep the regression signal honest:

1. The pinned baseline is the **ground truth** — "regression" = diff vs it;
   refresh only deliberately (new suites / arch changes), never casually.
2. Never auto-remove or auto-change an existing check — the harness only adds.
3. p99 > +15% flags a perf regression even if the average is stable.
4. npu-sim needs BOTH compile headers AND the simulator (see `./harness list` / `cann`).
5. `--all-suites` auto-skips missing prereqs; an explicit `--suite` force-runs.
6. Every run records context (git ref, dirty flag, host, env) → reproducible.

---

## Personas

| Role | Typical activity |
|---|---|
| **Developer** | Runs regressions, reads reports, triages failures |
| **Reviewer** | Approves proposed skill changes (MR merge) |
| **Maintainer** | Curates `learnings/`, refreshes the baseline |

You'll usually wear the first hat, sometimes the last two.

---

## Step 0 — One-time setup

```bash
git clone git@gitcode.com:ivanmang/regression-harness.git
cd regression-harness

# one command sets up env.sh, picks a CANN, and verifies pto-isa (interactive)
./harness onboarding
#   or do it by hand:  cp env.example.sh env.sh && source ./env.sh

# see everything the harness can do
./harness help
./harness status        # one-glance dashboard
./harness demo          # interactive walkthrough (no hardware needed)
./harness guide         # interactive tour of the real flow
./harness cann          # which installed CANN supports which arch

# optional: tab-completion
source completions/harness.bash   # add to ~/.bashrc
```

Requirements are only `python3` + `git` for the harness itself. The *targets*
have their own needs — and `./harness list` auto-detects them on any machine:

| Suite | Needs |
|---|---|
| `cpu-st` | clang++>=15 **or** g++>=13 (run on ecs / yellow / b10, not the blue laptop) |
| `npu-sim-a5/a3` | a CANN toolkit with the matching **simulator** AND compile **headers** |
| `npu-sim-a6` | yellow (`dav_9201`); needs a CANN with **both** A6 headers and the A6 sim |
| `npu-hw-a5` | a real A5 device (`npu-smi` must succeed) + ASCEND_HOME_PATH |
| `costmodel-st` | ASCEND_HOME_PATH |
| `comm-st` | ASCEND_HOME_PATH + `mpirun` |

---

## Step 1 — Try it in 2 minutes (no hardware)

```bash
./harness demo                # interactive, step-by-step (arrow keys + Enter)
./harness demo --straight     # straight through (CI / a quick skim)
./harness guide --demo        # same interactive tour via the guide entry
PAUSE=1 ./demo/run_demo.sh    # scene-by-scene with a pause (for presenting)
```

This runs the **real** harness scripts against a mock gtest runner and walks the
entire journey (run → report → review → correct → promote → re-run) in 8 steps.
Everything happens in `/tmp` + the gitignored `reports/`, so the repo stays clean.

Each step is a **framed block** that makes the workflow self-explanatory:

```text
════════════════════════════════════════════════════════════════════
  STEP 1 / 8   ·   Use — run the suite
════════════════════════════════════════════════════════════════════

  progress  [░░░░░░░░░░░░░░░░░░░░░░]  0/8
  steps     ▶run  ·report  ·review  ·teach  ·propose  ·apply  ·rerun  ·takeaway

  What this step does
    One command runs the demo suite through the REAL run_suite.py → run.json.

  Who does what
    ▸ command   python3 scripts/run_suite.py --target demo --all-suites
    🟢 harness  runs the suite and normalizes the log into run.json
    🟡 you       nothing — press Enter to run

  Your move  ·  ↑/↓ choose  ·  Enter confirm  ·  1–6 jump  ·  q quit
   [▶] ▶  run this step & continue
       ⏭  skip to the next step
       ⏮  go back one step
       🗺  jump to any step
       🛈  explain this step
       ✕  quit demo
```

`run this step & continue` runs the step *and* advances to the next, so holding
Enter walks the whole journey; `skip` / `back` / `jump` / `explain` give control.
The first three steps are **USE**, the next four are **IMPROVE** — and the
"Who does what" box marks where a human is needed (teach = your triage call,
apply = a reviewer merges the MR).

The interactive `./harness guide` (without `--demo`) walks the **real** pto-isa
flow the same way: env check → choose suites → run → report → review → teach →
promote. Its interactive menus — **demo/real**, **suite**, **testcase**, **gtest
filter**, **CANN package**, and **output mode** — use arrow keys (`↑`/`↓` +
Enter, highlighted selection; fall back to numbered prompts when piped). When
`ASCEND_HOME_PATH` isn't set, the CANN picker lists each installed package and
which arches it can compile (headers) vs simulate.

---

## Step 2 — First real run: pin the baseline

On a canonical machine (see the table in Step 0):

```bash
./harness baseline pto-isa
# runs all enabled (and runnable) suites, copies the result to
# reports/baseline/baseline.json
# (refuses to pin if any suite did not PASS — use --force to override)

git add reports/baseline/baseline.json
git commit -m "chore: pin pto-isa regression baseline"
git push
```

From now on, every run is compared against this **pinned** baseline. Refresh it
only deliberately (new suites, arch changes), never casually.

---

## Step 3 — Everyday: run a regression

```bash
./harness list                                # what can I run on THIS machine? (auto-detected)

./harness run --all-suites --quiet            # everything runnable, summary only
./harness run --all-suites --tui              # live spinner + per-suite pass/fail
./harness run --all-suites --json             # machine-readable summary
./harness run --all-suites --parallel         # independent suites concurrently
./harness run --suite cpu-st                  # one suite (force, even if prereqs missing)
./harness run --suite npu-sim-a5 --testcase tpartargmax        # one testcase
./harness run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'  # one gtest case

# one testcase (raw pto-isa runner)
python3 tests/script/run_st.py -r sim -v a5 -t tadd -g 'TADDTest.case_*'
```

`run` requires an explicit `--suite` or `--all-suites` — a bare `./harness run`
prints the enabled suites and exits 2 (no accidental full run). `--all-suites`
auto-skips suites whose prerequisites aren't present on this machine (compiler /
CANN / simulator / device / MPI) and prints why; an explicit `--suite`
force-runs regardless.

`./harness list` shows the same auto-detection inline: `[✓]` = enabled and
runnable, `[!]` = enabled but missing prereqs (the reason is printed), `[ ]` =
disabled. Use it as the first thing on any new machine.

Each run produces, under `reports/<run-id>/`:

```text
run.json        # metadata (git ref, dirty, host, env) + normalized results
<suite>.log     # raw runner output
report.md/.html # generated report (see Step 4)
```

The driver records **context** (repo commit, host, CANN/ASCEND path) so any
result is reproducible — a FAIL on one machine can be re-investigated elsewhere.
Exit codes: **0** clean, **1** ran-with-failures, **2** usage.

---

## Step 4 — Read the report

```bash
./harness report             # latest run
./harness report --open      # latest run, in the browser
# explicit:
./harness report --run reports/<run-id>/run.json \
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
./harness review              # latest run vs baseline
./harness review --run reports/<run-id>/run.json   # a specific run
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

If it's in the corpus → done, it was already flagged known. If not — or if you
correct the agent's triage — go to Step 7 and teach it.

---

## Step 7 — Teach it (the learning loop)

You found something the harness didn't know. Capture it, propose the fix, and
promote it — capture is automatic, promotion is reviewed.

> Most of the time you don't type a command at all: the skills tell the agent
> to log it automatically when you correct it ("remember …", "no, that's
> wrong", "actually …"). The agent replies with the `LRN-…` id it logged.

### 7a. Capture (automatic, append-only)

```bash
# shorthand — one string, split on " -> " (or " → ") into wrong / correct / action
./harness teach "device vcvt round-field mismatch -> known pattern, annotate it -> promote to known-failures"

# interactive wizard — no flags to remember
./harness teach

# editor — opens $EDITOR with a prefilled template
./harness teach --edit
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

This step is **your judgment** — the harness logs what you tell it, it can't
decide the correct triage for you.

### 7b. Propose (auto-draft a diff, no write)

```bash
./harness promote --propose
```

It renders a **reviewable git-style diff** into the right place (a new
`known-failures.md` entry, or a `## Gotchas` bullet in the target skill), and
skips duplicates / entries already present in the target file. Nothing is
written yet.

### 7c. Apply + MR (scripted, human-gated)

```bash
./harness promote --pr     # apply + branch + commit + push + MR (merge request) URL
```

One command finishes the loop: it writes the edit, marks the entry
`promoted` in `recent.md`, appends a summary to `promoted.md`, and logs a dated
block in `corrections.md`. It then commits on a `feat/learnings-<date>` branch,
pushes, and prints the merge-request URL. **A reviewer merges** — the harness
never self-merges. This is the other place a human is required.

---

## Step 8 — Next run is smarter

Re-run the *same* `run.json` through the report with the improved corpus:

```bash
./harness report --run reports/<run-id>/run.json \
  --known .claude/skills/pto-isa/references/known-failures.md \
  --out reports/<run-id>/report
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
| On push/PR | `.gitcode/workflows/selfcheck.yml` runs `./harness selfcheck` |
| Weekly / on demand | reviewer merges `feat/learnings-*` MRs |
| After suite changes | `./harness baseline pto-isa` to re-pin the baseline |
| After a correction | re-run one representative case to verify it improved triage |
| Housekeeping | `./harness clean --keep 3` / `./harness history` / `make check` |

---

## Command quick reference

| Goal | Command |
|---|---|
| Interactive walkthrough (no hardware) | `./harness demo` (or `--straight`; `--demo` in `guide`) |
| Interactive tour (real flow) | `./harness guide` |
| One-glance dashboard | `./harness status` (or `./harness tui`) |
| Diagnose this machine | `./harness diagnose [--strict]` |
| Guided setup | `./harness onboarding` |
| List suites + arches + availability | `./harness list [--format markdown\|html]` |
| Which CANN supports which arch | `./harness cann [--scan] [--json]` |
| Pin / refresh baseline | `./harness baseline [--force] pto-isa` |
| Run all suites | `./harness run --all-suites [--quiet\|--tui\|--json\|--parallel]` |
| Run one suite | `./harness run --suite cpu-st` |
| Run one testcase | `./harness run --suite npu-sim-a5 --testcase tpartargmax` |
| Run a gtest filter | `./harness run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'` |
| Report | `./harness report [--open]` (default: latest run) |
| Diff vs baseline | `./harness review` (default: latest run) |
| List recent runs | `./harness history` |
| Clean run dirs | `./harness clean [--dry-run] [--keep N]` |
| Open report.html | `./harness open [<run-id>]` |
| Validate config | `./harness validate` |
| Capture correction | `./harness teach "… -> … -> …"` (or wizard) |
| Propose promotion | `./harness promote --propose` |
| Apply + MR | `./harness promote --pr` |
| Self-check | `./harness selfcheck` |

---

## Automation boundaries

| Step | Automation |
|---|---|
| Capture a correction (`recent.md`, append-only) | 🟢 automatic |
| Draft promotion (diff, no write) | 🟢 automatic |
| Apply + commit + push + MR | 🟡 scripted, MR-gated |
| Remove / change an existing check | 🔴 never automatic |

Capture is triggered by `./harness teach` or by the agent reacting to your
corrections; until a note is promoted it changes nothing in the skills.

This mirrors the industry norm: like Claude Code auto-writing memory but not
auto-editing your `CLAUDE.md`, the harness auto-logs but only *proposes* edits.

**Why the line is drawn there:** auto-append is cheap and safe — `recent.md` is
the harness's own scratch memory, append-only and trivially revertible.
Auto-edit is expensive and risky — `SKILL.md` + `known-failures.md` are the
team's shared source of truth that every future run reads. The worst failure
mode isn't a bad memory entry; it's a wrong "known failure" that silently
annotates a real regression as known and hides it. So the machine may grow its
memory freely, but shared knowledge only changes when a human merges the MR.

---

## Hygiene rules

- Promote only corrections that are **reusable** or occurred **more than once**.
- Never remove an existing check without strong evidence.
- Keep `description` frontmatter stable unless triggers genuinely change.
- No secrets / credentials / sensitive data in skills or learnings.
- Small, reviewable diffs beat sweeping rewrites.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st `Could not find a suitable compiler` | run on ecs / yellow / b10 (clang++>=15 or g++>=13) |
| npu-sim suite shows `!` in `./harness list` | `./harness cann` — the chosen CANN must have both headers and the simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `./harness run` exits 2 | pass `--suite <name>` or `--all-suites` |
| `./harness baseline` refuses to pin | a suite didn't PASS — fix it, or `--force` |
| `./harness list demo` says unknown target | demo uses its own config: `./harness list --target demo --config demo/config/demo-suites.json --arches demo/config/demo-arches.json` |