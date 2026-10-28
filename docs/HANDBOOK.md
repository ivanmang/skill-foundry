# Regression Harness — Handbook

The canonical reference. This one document is the source of truth for how to
use the harness and why it's shaped the way it is. (README is the short index;
USER_JOURNEY is the narrative walkthrough.)

---

## What this is

A shared, self-improving regression harness built on open **Agent Skills**
(`SKILL.md`). One entry point — `./harness` — wraps **run → report → review**
(the USE loop) and **teach → promote → MR** (the IMPROVE loop), against a
pinned baseline that makes "regression" a mechanical diff.

> Want the human angle? Read [docs/STORY.md](STORY.md) — a short story about a
> developer, a pi agent, and the harness.

```text
USE      ./harness run → report → review   (diff vs pinned baseline)
IMPROVE  ./harness teach → promote --pr    (corrections become skills)
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
   `./harness list` marks it `!` if either is missing; `./harness cann` shows why.
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
git clone git@gitcode.com:ivanmang/regression-harness.git
cd regression-harness

./harness onboarding   # guided: detect env, write env.sh, pick CANN, verify pto-isa
./harness status       # one-glance dashboard — is this machine ready?
./harness demo         # 2-minute walkthrough, no hardware
./harness run --all-suites --dry-run   # preview before the real run
./harness run --all-suites --quiet     # the real run
./harness report --open                # read the result
```

The harness itself needs only `python3` + `git`. Targets need more — and
`./harness list` / `./harness status` auto-detect exactly what on any machine.

### Agent setup (skills discoverability)

Skills live in one canonical place (`.claude/skills/`) and are reachable by any
Agent-Skills-compatible agent:

- **Project-level** — Claude Code reads `.claude/skills/`; Pi and open-standard
  agents read `.agents/skills/` (a symlink to the same skills). Zero setup.
- **Always-on** — `./harness install-skills` links each skill into the
  installed agents' user dirs (`~/.claude/skills/`, `~/.pi/skills/`,
  `~/.agents/skills/`); `--dry-run` previews, `--uninstall` removes. Restart/reload.

---

## Command reference

| Command | Purpose |
|---|---|
| `./harness status` | one-glance dashboard (env, suites, baseline, learnings, last run) |
| `./harness targets` | list configured targets (name, label, repo, suites) |
| `./harness install-skills` | link skills into each agent's user dir (`.claude`/`.pi`/`.agents`) |
| `./harness diagnose` | check this machine + print the exact fix for each issue |
| `./harness onboarding` | guided first-run setup |
| `./harness tui` | full-screen dashboard (interactive) |
| `./harness menu` | curated interactive menu (also the bare `./harness` default) |
| `./harness run` | run suites (`--all-suites`, `--suite X`, `--testcase`, `--filter`, `--quiet`, `--tui`, `--json`, `--dry-run`, `--parallel`) |
| `./harness report` | run.json → `report.md`/`.html` (`--open`, `--known`) |
| `./harness review` | diff a run vs the pinned baseline (p99 + CA metrics) |
| `./harness teach` | log a correction (append-only) |
| `./harness promote` | pending learnings → skills (`--propose` / `--apply` / `--pr`) |
| `./harness baseline` | re-pin `reports/baseline/<target>.json` (per target) |
| `./harness list` | suites + arches with auto-detected availability |
| `./harness cann` | which CANN supports which arch (headers vs simulator) |
| `./harness guide` | interactive tour of the real flow |
| `./harness demo` | interactive sandboxed walkthrough |
| `./harness history` / `clean` / `open` / `validate` | housekeeping |
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

Then: `./harness status`, `./harness list --target your-target`, `./harness guide`
(pick the target), `./harness run --target your-target --all-suites --dry-run`.
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
./harness status                       # 1. is everything ready?
./harness run --all-suites --dry-run   # 2. what will this do?
./harness run --all-suites --quiet     # 3. do it (summary only)
./harness report --open                # 4. read failures (known ones annotated)
./harness review                       # 5. the regression signal (vs baseline)

# if something new failed and you triaged it:
./harness teach "symptom -> correct -> action"   # 6. capture (auto, append-only)
./harness promote --propose            # 7. review the proposed diff (no write)
./harness promote --pr                 # 8. apply + branch + push + MR (human merges)
```

Exit codes: `0` clean, `1` ran-with-failures, `2` usage.

---

## Performance & CI

- **`--parallel`** — run independent suites concurrently (npu-sim A5/A3/A6 in
  parallel) with `./harness run --all-suites --parallel`. Implies per-suite quiet;
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
- **Apply** (`./harness promote --pr`) writes the edit, flips the entry to
  `promoted`, appends a summary to `promoted.md` + an audit block to
  `corrections.md`, commits on `feat/learnings-<date>`, pushes, and **auto-creates
  the MR** (via `glab` or the GitCode API with `GITCODE_TOKEN`/`GITLAB_TOKEN`;
  otherwise it prints the MR-new URL). **You merge it on the remote** — branch
  protection is the gate.

Files: `learnings/recent.md` (pending log) · `promoted.md` (promoted log) ·
`corrections.md` (audit trail). Skills + `known-failures.md` are the shared
corpus that only changes via a merged MR.

---

## The demo and the guide

- **`./harness demo`** — drives the *real* scripts against a mock gtest runner
  in 8 framed steps (progress bar, step map, a "Who does what" box, and a
  `run & continue / skip / back / jump / explain / quit` menu). No hardware.
- **`./harness guide`** — the same journey against the real pto-isa repo: env
  check → CANN picker → suite/testcase/filter menus → run → report → review →
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
| npu-sim suite shows `!` in `./harness list` | `./harness cann` — need BOTH headers and simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `./harness run` exits 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | a suite didn't PASS — fix it, or `--force` |
| Not sure what's wrong | `./harness diagnose` |
| `report --open` prints xdg-open errors / no browser | handle automatically: on WSL it opens via `explorer.exe` (host browser), else prints the file path (+ Windows path on WSL) |
