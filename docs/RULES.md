# skill-foundry — Rules & shared reference

This is the **single source of truth** for the content repeated across the
docs. Edit it here; the other documents (README, HANDBOOK, USER_JOURNEY,
CONTRIBUTING) link to it instead of copy-pasting.

---

## The six rules

1. **The pinned baseline is the ground truth.** "Regression" means *diff vs
   `reports/baseline/<target>.json`*. Refresh it only deliberately (new suites /
   arch changes), never casually — a bad re-pin poisons every future run.
2. **Never auto-remove or auto-change an existing check.** The harness adds
   entries; it never silently deletes or weakens one.
3. **p99 > +15% flags a perf regression even if average is stable.** Never trust
   average alone — averages hide tail latency.
4. **An npu-sim suite needs BOTH the CANN compile headers AND the simulator.**
   `python3 -m skill_foundry.workflow.run --list` marks it `!` if either is
   missing; `python3 -m skill_foundry.lib.cann` shows why.
5. **`--all-suites` auto-skips missing prereqs; an explicit `--suite` force-runs.**
6. **Every run records context** (git ref, dirty flag, host, env) in `run.json`,
   so any result is reproducible on another machine.

---

## Automation boundary (who does what)

| Role | What it does |
|---|---|
| 🟢 **thin scripts (automatic, agent-driven)** | run suites, extract logs, report, review, dry-run previews |
| 🟢 **harness (automatic, gated + LLM-reviewed)** | capture a correction, propose a diff, apply + commit + push on a branch, open a PR |
| 🤖 **AI / agent (automatic, on trigger)** | auto-captures a correction when you correct it (`"no / actually / remember …"`) and replies with the `LRN-…` id; triages per the skill |
| 🟡 **you (gate)** | the triage *content* (`wrong → correct → action`) and **merging the PR** (branch protection) |
| 🔴 **never automatic** | remove or change an existing check |

**Why the line is drawn there:** auto-*append* is safe — `learnings/recent.md`
is the harness's own scratch memory. Auto-*edit* is not — `SKILL.md` +
`known-failures.md` are the team's shared source of truth. So promotion runs the
gates and an LLM judge first, then `--pr` applies + pushes + opens a PR that a
human merges after CI is green. A wrong auto-edit (e.g. a bad "known failure")
would hide real regressions.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ASCEND_HOME_PATH not set` on npu/costmodel/comm | `cp env.example.sh env.sh && source ./env.sh` |
| cpu-st: `Could not find a suitable compiler` | run on ecs / yellow / b10 (clang++>=15 or g++>=13) |
| npu-sim suite shows `!` in `--list` | `python3 -m skill_foundry.lib.cann` — need BOTH headers and simulator |
| `target repo not found` | `export PTO_ISA_REPO=~/pto-isa` |
| bare `python3 -m skill_foundry.workflow.run` exits 2 | pass `--suite <name>` or `--all-suites` |
| `baseline` refuses to pin | a suite didn't PASS — fix it, or `--force` |
| `report --open` → xdg-open errors / no browser | handled: WSL opens via `explorer.exe`; else prints the path |
| skills not showing up in the agent | `./harness skills --install`, then restart/reload the agent |
| `--pr` printed a PR-new URL instead of creating it | set `export GH_TOKEN=<github token>` (or `gh auth login`) in `env.sh` |
| Not sure what's wrong | `python3 -m skill_foundry.workflow.diagnose` |
| `run --list demo` says unknown target | demo uses its own config: `python3 -m skill_foundry.workflow.run --list --target demo --config demo/config/demo-suites.json --arches demo/config/demo-arches.json` |