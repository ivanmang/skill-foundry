# skill-foundry — Handbook

The canonical reference. This one document is the source of truth for how to
use the harness and why it's shaped the way it is. (README is the short index;
USER_JOURNEY is the narrative walkthrough.)

---

## What this is

A shared, self-improving skill-foundry built on open **Agent Skills**
(`SKILL.md`). One entry point — `./harness` — wraps **run → report → review**
(the USE loop) and **teach → promote → MR** (the IMPROVE loop), against a
pinned baseline that makes "regression" a mechanical diff.

```text
USE      python3 -m skill_foundry.workflow.run → report → review   (diff vs pinned baseline)
IMPROVE  ./harness teach → promote --direct | --pr    (corrections become skills)
```

---

## The rules that keep the signal honest

Six rules that matter more than they look:

1. **The pinned baseline is the ground truth.** "Regression" = *diff vs
   `reports/baseline/<target>.json`*. Refresh it only deliberately (new suites /
   arch changes), never casually.
2. **Never auto-remove or auto-change an existing check.** The harness adds; it
   never silently deletes or weakens a check.
3. **p99 > +15% flags a perf regression even if average is stable.** Never trust
   average alone.
4. **An npu-sim suite needs BOTH the CANN compile headers AND the simulator.**
   `python3 -m skill_foundry.workflow.run --list` marks it `!` if either is missing; `python3 -m skill_foundry.lib.cann` shows why.
5. **`--all-suites` auto-skips missing prereqs; an explicit `--suite` force-runs.**
6. **Every run records context** (git ref, dirty flag, host, env) in `run.json`,
   so any result is reproducible on another machine.

See [docs/metrics.md](docs/metrics.md) for the performance-metric schema
(modeled on the vmi-dashboard: EX/IPC/vf_real/dual/stalls) and the exact
regression thresholds.

---

## Automation boundary (who does what)

| Role | What it does |
|---|---|
| 🟢 **harness (automatic)** | run, extract logs, report, review, capture a correction, propose a diff, apply + commit + push + create the MR, dry-run previews |
| 🤖 **AI / agent (automatic, on trigger)** | auto-captures a correction when you correct it (`"no / actually / remember …"`) and replies with the `LRN-…` id; triages per the skill |
| 🟡 **you (remote gate)** | the triage *content* (`wrong → correct → action`) and **merging the MR on the remote** (branch protection) |
| 🔴 **never automatic** | remove or change an existing check |

**Why the line is drawn there:** auto-*append* is safe — `learnings/recent.md`
is the harness's own scratch memory. Auto-*edit* is not — `SKILL.md` +
`known-failures.md` are the team's shared source of truth. So `--pr`
auto-applies + pushes + creates the MR, but the **merge stays remote-gated**
(branch protection). Same line Claude Code draws: it auto-writes its memory but
never auto-edits your `CLAUDE.md`. A wrong auto-edit (e.g. a bad "known
failure") would hide real regressions.

On the report side: gtest-style case timing (p50/p99/max) is always captured;
per-suite CA metrics (EX/IPC/vf_real/dual/stalls, modeled on the vmi-dashboard)
are recorded when a CAModel instruction dump is present. See
[docs/metrics.md](docs/metrics.md).

---

## Getting started

```bash
git clone git@gitcode.com:ivanmang/skill-foundry.git
cd skill-foundry

python3 -m skill_foundry.cli.onboarding   # guided: detect env, write env.sh, pick CANN, verify pto-isa
python3 -m skill_foundry.workflow.status       # one-glance dashboard — is this machine ready?
python3 -m skill_foundry.cli.demo         # 2-minute walkthrough, no hardware
python3 -m skill_foundry.workflow.run --all-suites --dry-run   # preview before the real run
python3 -m skill_foundry.workflow.run --all-suites --quiet     # the real run
python3 -m skill_foundry.workflow.report --open                # read the result
```

The harness itself needs only `python3` + `git`. Targets need more — and
`python3 -m skill_foundry.workflow.run --list` / `python3 -m skill_foundry.workflow.status` auto-detect exactly what on any machine.

### Agent setup (skills discoverability)

Skills live in one canonical place (`.claude/skills/`) and are reachable by any
Agent-Skills-compatible agent:

- **Project-level** — Claude Code reads `.claude/skills/`; Pi and open-standard
  agents read `.agents/skills/` (a symlink to the same skills). Zero setup.
- **Always-on** — `./harness skills --install` links each skill into the
  installed agents' user dirs (`~/.claude/skills/`, `~/.pi/skills/`,
  `~/.agents/skills/`); `--uninstall` removes them. Restart/reload.

---

## Command reference

| Command | Purpose |
|---|---|
| `python3 -m skill_foundry.workflow.status` | one-glance dashboard (env, suites, baseline, learnings, last run) |
| `python3 -m skill_foundry.workflow.diagnose` | check this machine + print the exact fix for each issue |
| `python3 -m skill_foundry.cli.onboarding` | guided first-run setup |
| `./harness menu` | curated interactive menu (also the bare `./harness` default) |
| `python3 -m skill_foundry.workflow.run` | run suites (`--all-suites`, `--suite X`, `--testcase`, `--filter`, `--quiet`, `--tui`, `--json`, `--dry-run`, `--parallel`) |
| `python3 -m skill_foundry.workflow.report` | run.json → `report.md`/`.html` (`--open`, `--known`) |
| `python3 -m skill_foundry.workflow.review` | diff a run vs the pinned baseline (p99 + CA metrics) |
| `./harness capture-skill` | draft a NEW skill into `hub/inbox/` |
| `./harness promote-skill` | promote a draft into `.claude/skills/` (`--propose`/`--apply`/`--direct`/`--pr`) |
| `./harness skills` | list/search skills · `--install` / `--uninstall` into agents · `--refresh` the catalog |
| `./harness teach` | log a correction (append-only) |
| `./harness promote` | pending learnings → skills (`--propose` / `--apply` / `--direct` / `--pr`) |
| `bash skill_foundry/workflow/baseline.sh` | re-pin `reports/baseline/<target>.json` (per target) |
| `python3 -m skill_foundry.workflow.run --list` | suites + arches with auto-detected availability |
| `python3 -m skill_foundry.lib.cann` | which CANN supports which arch (headers vs simulator) |
| `python3 -m skill_foundry.cli.guide` | interactive tour of the real flow |
| `python3 -m skill_foundry.cli.demo` | interactive sandboxed walkthrough |
| `python3 -m skill_foundry.workflow.history` / `clean` / `validate` | housekeeping |
| `./harness selfcheck` | compile-check + skill-spec validation + demo smoke |
| `./harness help [verb]` · `./harness version` | this help / per-verb examples / version |

Run `./harness help <verb>` for any verb's detailed examples.

In an interactive terminal, every verb finishes with a guided **"What next?"**
menu: the natural next step for what you just ran (arrow keys), a **"type a
command"** option to enter any `./harness …` yourself, the full verb menu, or
`q` to return to the shell. Piped/CI invocations skip it.

---

## How to add a target

A target is one declarative block in `config/suites.json` under `targets.<name>`
plus (optionally) one adapter skill. Nothing in run/report/review/learn needs to
change — they already read the target from the run record.

```jsonc
{
  "name": "your-target",
  "label": "Your target (…)",
  "repo_env": "YOUR_TARGET_REPO",          // env var for the checkout
  "repo_default": "~/your-target",
  "repo_clone": "git@gitcode.com:org/your-target.git",
  "env_setup": "source \"$ASCEND_HOME_PATH/set_env.sh\"",
  "testcase_dirs": {                        // for the guide's dropdowns
    "suite-name": "path/to/testcases"
  },
  "suites": [
    {
      "name": "suite-name",
      "mode": "cpu" | "npu-sim" | "npu" | "costmodel" | "comm" | "static",
      "arch": "a5",                             // per config/arches.json
      "runner": "cpu" | "run_st" | "generic",   // generic: use {testcase}/{filter} in command
      "testcase_kind": "dir" | "file",           // guide dropdown: dirs (default) or .py case files
      "perf_copy": [                            // optional: copy newest CA dumps into the run dir
        "build/msprof_res/{testcase_stem}/OPPROF_*/dump"
      ],
      "enabled": true,
      "milestone": "M1",
      "command": ["python3", "run.py", "{testcase}"],
      "timeout_s": 7200,
      "description": "…"
    }
  ]
}
```

Then: `python3 -m skill_foundry.workflow.status`, `python3 -m skill_foundry.workflow.run --list --target your-target`, `python3 -m skill_foundry.cli.guide`
(pick the target), `python3 -m skill_foundry.workflow.run --target your-target --all-suites --dry-run`.
`runner` defaults are derived from `mode` (cpu → `--testcase`/`--gtest_filter`,
npu-sim/npu/comm → `-t`/`-g`); `generic` lets the `command` template use
`{testcase}`/`{filter}`/`{repo}`/`{arch}`/`{soc}` placeholders directly, for
arbitrary runners. `testcase_kind: "file"` makes the guide list `.py` case files
instead of subdirectories; `perf_copy` globs copy the newest
`core0.veccore0.*` CAModel dumps into the run dir so `perf_metrics` can compute
EX/IPC/dual/stalls (vmi-dashboard schema).

---

## The daily flow, end to end

```bash
python3 -m skill_foundry.workflow.status                       # 1. is everything ready?
python3 -m skill_foundry.workflow.run --all-suites --dry-run   # 2. what will this do?
python3 -m skill_foundry.workflow.run --all-suites --report --open --review   # 3. run + report + review (one command)
#   (report/review also run standalone: python3 -m skill_foundry.workflow.report / python3 -m skill_foundry.workflow.review)

# if something new failed and you triaged it:
./harness teach "symptom -> correct -> action"   # 6. capture (auto, append-only)
./harness promote --propose            # 7. review the proposed diff (no write, optional)
./harness promote --direct             # 8. apply + commit + push to origin/main (no MR, no token)
./harness promote --pr                 #    …or MR-gated (human merges; needs GITCODE_TOKEN/glab)
```

Exit codes: `0` clean, `1` ran-with-failures, `2` usage.

---

## Performance & CI

- **`--parallel`** — run independent suites concurrently (npu-sim A5/A3/A6 in
  parallel) with `python3 -m skill_foundry.workflow.run --all-suites --parallel`. Implies per-suite quiet;
  the summary still prints once all finish.
- **Capability cache** — `capabilities.py` caches CANN header/simulator scans in
  `.cache/cann-lanes.json` (5-min TTL), so `status`/`list`/`dry-run` are instant
  on slow mounts.
- **CI** — `.gitcode/workflows/selfcheck.yml` runs on push/PR;
  `promote-learnings.yml` surfaces pending learnings nightly;
  `dashboard.yml` renders `status --json` + `diagnose --strict` on a schedule.

---

## Learning loop, in detail

- **Capture** (`./harness teach`, or the agent auto-captures when you correct
  it) appends a strict `LRN-…` entry to `learnings/recent.md` with
  `status: pending`.
- **Propose** (`./harness promote --propose`) renders a git-style diff into the
  right file — `known-failures.md` (if the entry says "known-failure"/"triage
  corpus") or a skill's `## Gotchas` — and **writes nothing**. Duplicates and
  already-present entries are skipped (marked `rejected`).
- **Apply** (`./harness promote --direct`) writes the edit, flips the entry to
  `promoted`, appends a summary to `promoted.md` + an audit block to
  `corrections.md`, commits on the current branch, and pushes `origin HEAD`
  (SSH key — no token). `--pr` instead commits on `feat/learnings-<date>`,
  pushes, and **auto-creates the MR** (via `glab` or the GitCode API with
  `GITCODE_TOKEN`/`GITLAB_TOKEN`; otherwise it prints the MR-new URL). **You
  merge it on the remote** — branch protection is the gate.

Files: `learnings/recent.md` (pending log) · `promoted.md` (promoted log) ·
`corrections.md` (audit trail). Skills + `known-failures.md` are the shared
corpus that changes only through a promotion (`--direct` push or a merged MR).

---

## The demo and the guide

- **`python3 -m skill_foundry.cli.demo`** — drives the *real* harness drivers against a mock gtest runner
  in 8 framed steps (progress bar, step map, a "Who does what" box, and a
  `run & continue / skip / back / jump / explain / quit` menu). No hardware.
- **`python3 -m skill_foundry.cli.guide`** — the same journey against a real target (pto-isa /
  pto-vmi): target picker → env check → CANN picker → suite/testcase/filter
  menus → run → report → review →
  teach → promote.

---

## Glossary

- **Baseline** — the pinned `reports/baseline/<target>.json`; the reference a run is diffed against (per target; cross-target diffs are refused).
- **MR (merge request)** — the remote-gated step; merging it applies a learning to shared skills.
- **LRN-…** — a learning entry id (`LRN-YYYYMMDD-NNN`) in `learnings/recent.md`.
- **Known failure** — a failure already triaged and recorded in `known-failures.md`; the report annotates it instead of re-triaging.
- **soc / march** — the hardware's SoC name (`Ascend910B1`, `dav_9201`, `v926`) and the compile arch (`dav-920r1-vec`).
- **headers vs simulator** — a CANN can compile for an arch (has `include/pto/npu/<arch>`) yet lack its simulator (`tools/simulator/<soc>`), or vice versa.
- **Runnable** — a suite whose prerequisites (compiler / CANN headers+simulator / device / MPI) are all present.
- **p99** — the 99th-percentile latency; the perf-regression threshold is +15% on p99, not on the mean.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st `Could not find a suitable compiler` | clang++>=15 or g++>=13 (ecs / yellow / b10) |
| npu-sim suite shows `!` in `python3 -m skill_foundry.workflow.run --list` | `python3 -m skill_foundry.lib.cann` — need BOTH headers and simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `python3 -m skill_foundry.workflow.run` exits 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | a suite didn't PASS — fix it, or `--force` |
| Not sure what's wrong | `python3 -m skill_foundry.workflow.diagnose` |
| `report --open` prints xdg-open errors / no browser | handle automatically: on WSL it opens via `explorer.exe` (host browser), else prints the file path (+ Windows path on WSL) |
