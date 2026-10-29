# The `skill_foundry/` package

Everything is reachable through one entry point at the repo root:

```bash
./harness help
```

`./harness` maps each verb onto a module below. Prefer it over invoking the
modules directly.

## `cli/` — one module per `./harness` verb

| Verb | Module | Purpose |
|---|---|---|
| `run` | `cli/run.py` | Run suites → `run.json` + logs |
| `report` | `cli/report.py` | `run.json` → Markdown + HTML |
| `review` | `cli/review.py` | Diff a run vs the pinned baseline |
| `teach` | `cli/teach.py` | Log a correction (wizard / shorthand / editor) |
| `promote` | `cli/promote.py` | Propose / apply / direct / pr learnings into skills |
| `baseline` | `cli/baseline.sh` | Re-pin `reports/baseline/<target>.json` |
| `history` | `cli/history.py` | List recent runs |
| `clean` | `cli/clean.py` | Remove run dirs (keeps baseline) |
| `validate` | `cli/validate.py` | Check suites/arches/cann configs |
| `status` | `cli/status.py` | One-glance dashboard (env, suites, baseline, learnings, last run) |
| `diagnose` | `cli/diagnose.py` | Check this machine + print exact fixes |
| `capture-skill` | `cli/capture.py` | Draft a NEW skill into `hub/inbox/` |
| `promote-skill` | `cli/promote_skill.py` | Promote a draft into `.claude/skills/` (+ MR / direct) |
| `skills` | `cli/skills.py` | List/search skills · `--install`/`--uninstall` · `--refresh` |
| `onboarding` | `cli/onboarding.py` | Guided first-run setup |
| `tui` | `cli/tui.py` | Full-screen dashboard (interactive) |
| `menu` | `cli/menu.py` | Curated interactive menu (bare `./harness` default) |
| `demo` | `cli/demo.py` | Interactive step-by-step sandboxed walkthrough |
| `guide` | `cli/guide.py` | Interactive step-by-step tour |
| `list` | `cli/run.py --list` | List suites + arches |
| `cann` | `lib/cann.py` | Which CANN supports which arch |
| `selfcheck` | `cli/selfcheck.sh` | Compile-check + skill-spec validation + demo smoke |
| `__complete` | `cli/complete.py` | Completion candidates (for `completions/harness.bash`) |
| (wrapper) | `cli/wrap.py` | "What next?" menu after each typed verb |

## `lib/` — shared internals (imported, also runnable on their own)

- `runs.py` — locate latest/list runs (used by report/review/history/clean).
- `term.py` — ANSI colors + `c()`/`mark()`/`fmt_dur()`.
- `browser.py` — cross-platform browser opener.
- `capabilities.py` — runtime capability checks (compiler/CANN/simulator/device/MPI).
- `cann.py` — CANN detection (headers vs simulator per arch); also the `cann` verb.
- `targets.py` — the target registry (labels, repo env/clone, testcase dirs, arches).
- `parse_gtest.py` — log → normalized results (used by `cli/run.py`; also `extract-logs`).
- `perf_metrics.py` — per-case timing (p50/p99/max) + CAModel metrics (EX/IPC/vf_real/dual/stalls).
- `log_correction.py` — strict `LRN-…` writer (used by `teach` and `session_digest.py`).
- `session_digest.py` — draft pending learnings from a `run.json`.
- `validate_skills.py` — check every SKILL.md against the open Agent Skills spec.
- `install_skills.py` — symlink skills into agent user dirs (via `skills --install`).

## Conventions

- Exit codes: `0` success, `1` ran-but-not-clean, `2` usage error.
- Errors go to stderr; machine-readable output is JSON where `--json` is offered.
- Repo locations come from `skill_foundry/paths.py` (single source of truth);
  modules import `ROOT` from there instead of recomputing it from `__file__`.
- Run via `./harness` (or `python3 -m skill_foundry`) — a single in-process
  dispatcher (`skill_foundry/__main__.py` + `skill_foundry/dispatch.py`) maps each
  verb onto a module's `main()` with no per-verb subprocess and no per-module
  `sys.path` hacks.
- Optional: `pip install -e .` (setuptools>=64, pip>=21.3) adds the
  `skill-foundry` console script, so the same CLI works from any directory.

## Extras

- `./harness run --tui` — live per-suite spinner + pass/fail line.
- `./harness run --suite X --testcase T [--filter G]` — single testcase / gtest filter.
- `./harness list --format markdown|html` — suite catalog for docs/dashboards.
- `./harness promote --direct` — apply + commit + push to origin/main (no MR, no token);
  `--pr` keeps the MR-gated path.
- `./harness report` / `./harness review` — default to the latest run.
- `make check` — run the self-check locally.