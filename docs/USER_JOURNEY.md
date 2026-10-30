# skill-foundry — User Journey

From first clone to a self-improving regression loop, end to end. Every command
below is real; the mock demo lets you experience the whole journey in ~2 minutes
without hardware.

> **Looking for the full reference?** See [docs/HANDBOOK.md](docs/HANDBOOK.md)
> (canonical) — this page is the narrative walkthrough.

---

## The 30-second version

The harness turns *"run the regression"* from a repeated instruction into:

- **Skills** (`.claude/skills/`) that tell any agent *how* to run/triage/report.
- **Thin scripts** (`python3 -m skill_foundry.workflow.*`) that do the
  run → extract → report → review (run directly, guided by the skills).
- A **pinned baseline** (`reports/baseline/<target>.json`) so "regression" =
  *diff vs baseline*.
- A **learning loop** (`./harness teach` to capture, `./harness promote` to
  promote) that turns corrections into skills.

Two loops, always:

```text
USE      run → extract → report → review (diff vs baseline)
IMPROVE  capture → propose → gate + LLM review → apply → push (--direct) or MR (--pr)
```

And a simple rule of thumb for who does what:

- 🟢 **the scripts do** — run, extract, report, review (driven by the agent).
- 🟢 **harness does** — capture, propose, gate, LLM-review, then promote (the skill-ops loop).
- 🟡 **you / a reviewer do** — the triage judgment (`teach`); and with `--pr`,
  you only touch red CI MRs (green ones auto-merge).

And six rules that keep the regression signal honest:

1. The pinned baseline is the **ground truth** — "regression" = diff vs it;
   refresh only deliberately (new suites / arch changes), never casually.
2. Never auto-remove or auto-change an existing check — the harness only adds.
3. p99 > +15% flags a perf regression even if the average is stable.
4. npu-sim needs BOTH compile headers AND the simulator (see `python3 -m skill_foundry.workflow.run --list` / `cann`).
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
git clone git@gitcode.com:ivanmang/skill-foundry.git
cd skill-foundry

# one command sets up env.sh, picks a CANN, and verifies pto-isa (interactive)
python3 -m skill_foundry.workflow.onboarding
#   or do it by hand:  cp env.example.sh env.sh && source ./env.sh

# see everything the harness can do
./harness help
python3 -m skill_foundry.workflow.status        # one-glance dashboard
python3 -m skill_foundry.workflow.demo          # interactive walkthrough (no hardware needed)
python3 -m skill_foundry.workflow.guide         # interactive tour of the real flow
python3 -m skill_foundry.lib.cann          # which installed CANN supports which arch

# optional: tab-completion
source completions/harness.bash   # add to ~/.bashrc
```

Requirements are only `python3` + `git` for the harness itself. The *targets*
have their own needs — and `python3 -m skill_foundry.workflow.run --list` auto-detects them on any machine:

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
python3 -m skill_foundry.workflow.demo                # interactive, step-by-step (arrow keys + Enter)
python3 -m skill_foundry.workflow.demo --straight     # straight through (CI / a quick skim)
python3 -m skill_foundry.workflow.guide --demo        # same interactive tour via the guide entry
PAUSE=1 ./demo/run_demo.sh    # scene-by-scene with a pause (for presenting)
```

This runs the **real** workflow scripts against a mock gtest runner and walks the
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
    One command runs the demo suite through the REAL run.py → run.json.

  Who does what
    ▸ command   python3 -m skill_foundry.workflow.run --target demo --all-suites
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
apply auto-creates the MR; merge = you on the remote).

The interactive `python3 -m skill_foundry.workflow.guide` (without `--demo`) walks the **real** pto-isa
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
bash skill_foundry/workflow/baseline.sh pto-isa   # or: bash skill_foundry/workflow/baseline.sh <target>
# runs all enabled (and runnable) suites, copies the result to
# reports/baseline/<target>.json
# (refuses to pin if any suite did not PASS — use --force to override)

git add reports/baseline/pto-isa.json
git commit -m "chore: pin pto-isa regression baseline"
git push
```

From now on, every run is compared against this **pinned** baseline. Refresh it
only deliberately (new suites, arch changes), never casually.

---

## Step 3 — Everyday: run a regression

```bash
python3 -m skill_foundry.workflow.run --list                                # what can I run on THIS machine? (auto-detected)

python3 -m skill_foundry.workflow.run --all-suites --report --open --review   # the whole USE loop: run + report + review, one command
python3 -m skill_foundry.workflow.run --all-suites --quiet            # everything runnable, summary only
python3 -m skill_foundry.workflow.run --all-suites --tui              # live spinner + per-suite pass/fail
python3 -m skill_foundry.workflow.run --all-suites --json             # machine-readable summary
python3 -m skill_foundry.workflow.run --all-suites --parallel         # independent suites concurrently
python3 -m skill_foundry.workflow.run --suite cpu-st                  # one suite (force, even if prereqs missing)
python3 -m skill_foundry.workflow.run --suite npu-sim-a5 --testcase tpartargmax        # one testcase
python3 -m skill_foundry.workflow.run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'  # one gtest case

# one testcase (raw pto-isa runner)
python3 tests/script/run_st.py -r sim -v a5 -t tadd -g 'TADDTest.case_*'
```

`run` requires an explicit `--suite` or `--all-suites` — a bare `python3 -m skill_foundry.workflow.run`
prints the enabled suites and exits 2 (no accidental full run). `--all-suites`
auto-skips suites whose prerequisites aren't present on this machine (compiler /
CANN / simulator / device / MPI) and prints why; an explicit `--suite`
force-runs regardless.

`python3 -m skill_foundry.workflow.run --list` shows the same auto-detection inline: `[✓]` = enabled and
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
Exit codes: **0** clean, **1** ran-with-failures, **2** usage. In an interactive
terminal, every verb ends with a guided **"What next?"** menu (context-aware
suggestions + "type a command" + `q` for the shell).

---

## Step 4 — Read the report

(`python3 -m skill_foundry.workflow.run --all-suites --report` already renders this right after the run;
running `report` standalone below is for re-rendering a past `run.json`.)

```bash
python3 -m skill_foundry.workflow.report             # latest run
python3 -m skill_foundry.workflow.report --open      # latest run, in the browser
# explicit:
python3 -m skill_foundry.workflow.report --run reports/<run-id>/run.json \
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

(`python3 -m skill_foundry.workflow.run --all-suites --review` diffs automatically after the run;
running `review` standalone below is for re-checking a past run.)

```bash
python3 -m skill_foundry.workflow.review              # latest run vs baseline
python3 -m skill_foundry.workflow.review --run reports/<run-id>/run.json   # a specific run
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
promote it — capture is automatic; promotion is **gated and LLM-reviewed by
default** before anything is written.

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

### 7c. Publish (gated + LLM-reviewed, then automatic)

```bash
./harness promote --direct    # gates → LLM judge APPROVEs → push straight to main
./harness promote --pr        # …or MR: gates → CI → auto-merges when green
./harness promote --no-review # skip the judge (mechanical gates still run)
./harness promote --force     # bypass the gates (human override)
```

Every publish runs the **mechanical gates** (add-only — never removes/changes an
existing check · no-secrets · size cap · spec) and then an **LLM judge** before
writing anything. The judge is `SKILL_REVIEWER` (a command that reads the diff on
stdin and replies `APPROVE` / `HOLD` / `REJECT`); if it isn't set, you confirm
interactively — and in a non-interactive session it **fails closed** rather than
merging unreviewed.

`--direct` commits on the current branch and pushes `origin HEAD` (SSH key, no
token). `--pr` commits on a `feat/learnings-<date>` branch, pushes, creates the
MR (via `glab` or the GitCode API with `GITCODE_TOKEN`/`GITLAB_TOKEN`), and
requests **auto-merge when the CI gates pass** — a clean promotion lands without
you, and you only see it if the gates are red.

---

## Step 8 — Next run is smarter

Re-run the *same* `run.json` through the report with the improved corpus:

```bash
python3 -m skill_foundry.workflow.report --run reports/<run-id>/run.json \
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
| Weekly / on demand | with `--pr`, green MRs auto-merge (CI gates); only red ones need you · `--direct` lands on `main` after the LLM judge |
| After suite changes | `bash skill_foundry/workflow/baseline.sh <target>` to re-pin the baseline |
| After a correction | re-run one representative case to verify it improved triage |
| Housekeeping | `python3 -m skill_foundry.workflow.clean --keep 3` / `python3 -m skill_foundry.workflow.history` / `make check` |

---

## Command quick reference

| Goal | Command |
|---|---|
| Interactive walkthrough (no hardware) | `python3 -m skill_foundry.workflow.demo` (or `--straight`; `--demo` in `guide`) |
| Interactive tour (real flow) | `python3 -m skill_foundry.workflow.guide` |
| One-glance dashboard | `python3 -m skill_foundry.workflow.status` |
| Diagnose this machine | `python3 -m skill_foundry.workflow.diagnose [--strict]` |
| Guided setup | `python3 -m skill_foundry.workflow.onboarding` |
| List suites + arches + availability | `python3 -m skill_foundry.workflow.run --list [--format markdown\|html]` |
| Which CANN supports which arch | `python3 -m skill_foundry.lib.cann [--scan] [--json]` |
| Pin / refresh baseline | `bash skill_foundry/workflow/baseline.sh [--force] <target>` |
| Run all suites | `python3 -m skill_foundry.workflow.run --all-suites [--quiet\|--tui\|--json\|--parallel]` |
| Run + report + review | `python3 -m skill_foundry.workflow.run --all-suites --report --open --review` |
| Run one suite | `python3 -m skill_foundry.workflow.run --suite cpu-st` |
| Run one testcase | `python3 -m skill_foundry.workflow.run --suite npu-sim-a5 --testcase tpartargmax` |
| Run a gtest filter | `python3 -m skill_foundry.workflow.run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'` |
| Report | `python3 -m skill_foundry.workflow.report [--open]` (default: latest run) |
| Diff vs baseline | `python3 -m skill_foundry.workflow.review` (default: latest run) |
| List recent runs | `python3 -m skill_foundry.workflow.history` |
| Clean run dirs | `python3 -m skill_foundry.workflow.clean [--dry-run] [--keep N]` |
| Validate config | `python3 -m skill_foundry.workflow.validate` |
| Capture correction | `./harness teach "… -> … -> …"` (or wizard) |
| Propose promotion (diff, no write) | `./harness promote --propose` |
| Publish (gated + LLM-reviewed) | `./harness promote --direct` (or `--pr`; `--no-review` skips the judge, `--force` bypasses the gates) |
| Self-check | `./harness selfcheck` |

---

## Automation boundaries

| Step | Automation | Who |
|---|---|---|
| Run / extract / report / review / dry-run | 🟢 automatic | scripts (agent-driven) |
| Capture a correction (`recent.md`, append-only) | 🟢 automatic | harness **or** the AI (when you correct it) |
| Draft promotion (diff, no write) | 🟢 automatic | harness |
| Mechanical gates (add-only · no-secrets · size · spec) | 🟢 automatic | harness |
| **LLM review** (judge must APPROVE) | 🟢 automatic | `SKILL_REVIEWER` (or you, interactively) |
| Apply + commit + push (`--direct`) / create the MR (`--pr`) | 🟢 automatic | harness |
| **Merge the MR** (`--pr`) | 🟢 auto-merge on green CI; you only on red | CI / you |
| Remove / change an existing check | 🔴 never automatic | — |

Capture is triggered by `./harness teach` or by the agent reacting to your
corrections (`"no / actually / remember …"`) and replying with the `LRN-…` id;
until a note is promoted it changes nothing in the skills.

This mirrors the industry norm: like Claude Code auto-writing memory but not
auto-editing your `CLAUDE.md`, the harness auto-logs but only *proposes* edits.

**Why the line is drawn there:** auto-append is cheap and safe — `recent.md` is
the harness's own scratch memory, append-only and trivially revertible.
Auto-edit is expensive and risky — `SKILL.md` + `known-failures.md` are the
team's shared source of truth that every future run reads. The worst failure
mode isn't a bad memory entry; it's a wrong "known failure" that silently
annotates a real regression as known and hides it. So the machine may grow its
memory freely, but shared knowledge changes only after the gates and an LLM
judge APPROVE — `--direct` to `main`, or `--pr` auto-merged when CI is green.

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
| npu-sim suite shows `!` in `python3 -m skill_foundry.workflow.run --list` | `python3 -m skill_foundry.lib.cann` — the chosen CANN must have both headers and the simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `python3 -m skill_foundry.workflow.run` exits 2 | pass `--suite <name>` or `--all-suites` |
| `bash skill_foundry/workflow/baseline.sh` refuses to pin | a suite didn't PASS — fix it, or `--force` |
| `python3 -m skill_foundry.workflow.run --list demo` says unknown target | demo uses its own config: `python3 -m skill_foundry.workflow.run --list --target demo --config demo/config/demo-suites.json --arches demo/config/demo-arches.json` |