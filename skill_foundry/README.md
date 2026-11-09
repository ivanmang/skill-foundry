# The `skill_foundry/` package

Everything is reachable through one entry point at the repo root:

```bash
./harness help
```

`./harness` maps each verb onto a module below. Prefer it over invoking the
modules directly. The package is split by *purpose*, not by file type:

- **`cli/`** — the product (skill-ops) + the CLI shell.
- **`workflow/`** — the bundled regression workflow (the first example domain).
- **`lib/`** — thin, stable helpers shared by both.

---

## `cli/` — THE PRODUCT: capture → promote → hub → discover

| Verb | Module | Purpose |
|---|---|---|
| `capture-skill` | `cli/capture.py` | Draft a NEW skill into `hub/inbox/` |
| `promote-skill` | `cli/promote_skill.py` | Promote a draft into `.claude/skills/` (`--pr`) |
| `teach` | `cli/teach.py` | Log a correction (wizard / shorthand / editor) |
| `promote` | `cli/promote.py` | Promote learnings into skills (`--propose`/`--apply`/`--pr`) |
| `skills` | `cli/skills.py` | List/search skills · `--install`/`--uninstall` · `--refresh` |

The CLI shell (interactive UX, not domain logic):

- `cli/menu.py` — curated menu (bare `./harness` default)
- `cli/wrap.py` — "What next?" menu after each typed verb
- `cli/complete.py` — completion candidates (for `completions/harness.bash`)
- `cli/selfcheck.sh` — compile-check + skill-spec validation + demo smoke
- `lib/ui.py` — shared arrow-key menus / prompts / pickers (`banner`, `ask`,
  `select_menu`, `choose_cann`, …)

---

## `workflow/` — BUNDLED WORKFLOW: regression (run → report → review)

The regression workflow is a *consumer* of the platform, not the platform. Its
drivers live here as **directly-runnable thin scripts** (not `./harness` verbs);
the skills hold the workflow knowledge and reference these:

| Script | Module | Purpose |
|---|---|---|
| `run` | `workflow/run.py` | Run suites → `run.json` + logs |
| `list` | `workflow/run.py --list` | List suites + arches with availability |
| `report` | `workflow/report.py` | `run.json` → Markdown + HTML |
| `review` | `workflow/review.py` | Diff a run vs the pinned baseline |
| `baseline` | `workflow/baseline.sh` | Re-pin `reports/baseline/<target>.json` |
| `status` | `workflow/status.py` | One-glance dashboard (env, suites, baseline, learnings, last run) |
| `diagnose` | `workflow/diagnose.py` | Check this machine + print exact fixes |
| `history` | `workflow/history.py` | List recent runs |
| `clean` | `workflow/clean.py` | Remove run dirs (keeps baseline) |
| `validate` | `workflow/validate.py` | Check suites/arches/cann configs |
| `guide` | `workflow/guide.py` | Interactive tour of the real flow (runnable script) |
| `demo` | `workflow/demo.py` | Interactive sandboxed walkthrough, no hardware |
| `onboarding` | `workflow/onboarding.py` | Guided first-run setup |

The *knowledge* for this workflow lives in the skills
(`run-testcase`, `extract-logs`, `generate-report`, `review-inconsistencies`,
`full-analysis-pipeline`) — the modules here are the thin tools those skills
call.

---

## `lib/` — thin, stable helpers (shared, also runnable standalone)

- `runs.py` — locate latest/list runs.
- `term.py` — ANSI colors + `c()`/`mark()`/`fmt_dur()`.
- `browser.py` — cross-platform browser opener.
- `capabilities.py` — runtime capability checks (compiler/CANN/simulator/device/MPI).
- `cann.py` — CANN detection (headers vs simulator per arch); also the `cann` verb.
- `targets.py` — the target registry (labels, repo env/clone, testcase dirs, arches).
- `parse_gtest.py` — log → normalized results (used by `workflow/run.py`; also `extract-logs`).
- `perf_metrics.py` — per-case timing (p50/p99/max) + CAModel metrics (EX/IPC/vf_real/dual/stalls).
- `log_correction.py` — strict `LRN-…` writer (used by `teach` and `session_digest.py`).
- `session_digest.py` — draft pending learnings from a `run.json`.
- `validate_skills.py` — check every SKILL.md against the open Agent Skills spec.
- `install_skills.py` — symlink skills into agent user dirs (via `skills --install`).

---

## Conventions

- Exit codes: `0` success, `1` ran-but-not-clean, `2` usage error.
- Errors go to stderr; machine-readable output is JSON where `--json` is offered.
- Repo locations come from `skill_foundry/paths.py` (single source of truth).
- Run via `./harness` (or `python3 -m skill_foundry`) — a single in-process
  dispatcher (`skill_foundry/__main__.py` + `skill_foundry/dispatch.py`) maps each
  verb onto a module's `main()` with no per-verb subprocess.
- Optional: `pip install -e .` (setuptools>=64, pip>=21.3) adds the
  `skill-foundry` console script.

## Extras

- `python3 -m skill_foundry.workflow.run --all-suites --report --open --review` — the whole USE loop, one command.
- `python3 -m skill_foundry.workflow.run --suite X --testcase T [--filter G]` — single testcase / gtest filter.
- `./harness promote --pr` — branch + push + auto-create the PR (via `gh`/`GH_TOKEN`); a human merges.
- `make check` — run the self-check locally.