# skill-foundry — Handbook

The canonical reference. This one document is the source of truth for how to
use the harness and why it's shaped the way it is. (README is the short index;
docs/USER_JOURNEY.md is the narrative walkthrough.)

---

## What this is

A shared, self-improving skill-foundry built on open **Agent Skills**
(`SKILL.md`). One entry point — `./harness help` — points at the two loops:
**run → report → review** (the USE loop, thin scripts) and **teach → promote → PR**
(the IMPROVE loop, the harness).

```text
USE      python3 -m skill_foundry.workflow.run → report → review   (diff vs pinned baseline)
IMPROVE  ./harness teach → promote --pr                 (corrections → skills via a reviewed PR)
```

---

## The rules that keep the signal honest

Six rules that matter more than they look. Canonical text: [RULES.md](RULES.md);
the one-line version: baseline is ground truth · never auto-remove/change a check
· p99 +15% flags a perf regression even if avg is stable · npu-sim needs BOTH
headers AND simulator · `--all-suites` auto-skips missing prereqs · every run
records context in `run.json`.

See [metrics.md](metrics.md) for the performance-metric schema
(modeled on the vmi-dashboard: EX/IPC/vf_real/dual/stalls) and the exact
regression thresholds.

---

## Automation boundary (who does what)

See [RULES.md](RULES.md#automation-boundary-who-does-what) for the canonical
table + rationale. Summary: scripts + harness are automatic and gated; you own
the triage content and the PR merge; removing/changing an existing check is
never automatic.

On the report side: gtest-style case timing (p50/p99/max) is always captured;
per-suite CA metrics (EX/IPC/vf_real/dual/stalls, modeled on the vmi-dashboard)
are recorded when a CAModel instruction dump is present. See
[metrics.md](metrics.md).

---

## Getting started

```bash
git clone git@github.com:ivanmang/skill-foundry.git
cd skill-foundry

python3 -m skill_foundry.workflow.onboarding   # guided: detect env, write env.sh, pick CANN, verify pto-isa
python3 -m skill_foundry.workflow.status       # one-glance dashboard — is this machine ready?
python3 -m skill_foundry.workflow.demo         # 2-minute walkthrough, no hardware
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
  `~/.agents/skills/`); `--uninstall` removes them. `--dry-run` previews the
  links, and `--mine` shows what each agent currently sees vs the hub.
  Restart/reload.

---

## Command reference

The full CLI surface is generated from `skill_foundry/verbs.py` — see
[CLI.md](CLI.md) for the canonical table (harness verbs + bundled workflow
commands; never hand-edited).

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

Then: `python3 -m skill_foundry.workflow.status`, `python3 -m skill_foundry.workflow.run --list --target your-target`, `python3 -m skill_foundry.workflow.guide`
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
./harness promote --apply             # 8. write locally (gates + LLM judge APPROVE first)
./harness promote --pr                 #    …or publish: branch + push + open a PR (a human merges)
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
- **CI** — `.github/workflows/ci.yml` runs on push/PR (`selfcheck` + `lint` +
  `typecheck` + `package`); `.github/workflows/secret-scan.yml` runs gitleaks;
  `.github/workflows/mirror-to-gitcode.yml` mirrors `main` + tags to GitCode.

---

## Learning loop, in detail

- **Capture** (`./harness teach`, or the agent auto-captures when you correct
  it) appends a strict `LRN-…` entry to `learnings/recent.md` with
  `status: pending`.
- **Propose** (`./harness promote --propose`) renders a git-style diff into the
  right file — `known-failures.md` (if the entry says "known-failure"/"triage
  corpus") or a skill's `## Gotchas` — and **writes nothing**. Duplicates and
  already-present entries are skipped (marked `rejected`).
- **Apply** (`./harness promote --apply`) runs the gates (add-only · no-secrets
  · size) and the review (built-in judge + LLM judge `SKILL_REVIEWER`), writes
  the edit, flips the entry to `promoted`, appends a summary to
  `promoted.md` + an audit block to `corrections.md`. `--pr` instead commits on
  a `feat/learnings-<date>` branch, pushes, and **auto-creates the PR** (GitHub
  `gh pr create` / `GH_TOKEN`, or GitCode v5 API) — a human merges it after CI is green.

Files: `learnings/recent.md` (pending log) · `promoted.md` (promoted log) ·
`corrections.md` (audit trail). Skills + `known-failures.md` are the shared
corpus that changes only through the gates + review (a green-CI `--pr`).

---

## The demo and the guide

- **`python3 -m skill_foundry.workflow.demo`** — drives the *real* harness drivers against a mock gtest runner
  in 8 framed steps (progress bar, step map, a "Who does what" box, and a
  `run & continue / skip / back / jump / explain / quit` menu). No hardware.
- **`python3 -m skill_foundry.workflow.guide`** — the same journey against a real target (pto-isa /
  pto-vmi): target picker → env check → CANN picker → suite/testcase/filter
  menus → run → report → review →
  teach → promote.

---

## Glossary

- **Baseline** — the pinned `reports/baseline/<target>.json`; the reference a run is diffed against (per target; cross-target diffs are refused).
- **PR (pull request)** — the gated step for `--pr`: the gates + an LLM judge run, then a human merges it after CI is green.
- **LRN-…** — a learning entry id (`LRN-YYYYMMDD-NNN`) in `learnings/recent.md`.
- **Known failure** — a failure already triaged and recorded in `known-failures.md`; the report annotates it instead of re-triaging.
- **soc / march** — the hardware's SoC name (`Ascend910B1`, `dav_9201`, `v926`) and the compile arch (`dav-920r1-vec`).
- **headers vs simulator** — a CANN can compile for an arch (has `include/pto/npu/<arch>`) yet lack its simulator (`tools/simulator/<soc>`), or vice versa.
- **Runnable** — a suite whose prerequisites (compiler / CANN headers+simulator / device / MPI) are all present.
- **p99** — the 99th-percentile latency; the perf-regression threshold is +15% on p99, not on the mean.

---

## Troubleshooting

See [RULES.md](RULES.md#troubleshooting) for the canonical table.


## tilelangGym SoftLib/ST gates

1. Point `TILELANGGYM_PACK` at a closed explore pack (or use the demo fixture).
2. `python3 -m skill_foundry.workflow.run --target tilelangGym --suite sv567-1xg-clean`
3. On FAIL: read Motif/Done-bar/PRC miss → `./harness teach` → promote into `tilelanggym-*` skills.
4. Do not paste dig el/cyc into Motif seeds; live SoT bands come from tip packs at review time.
