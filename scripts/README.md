# Scripts

Everything is reachable through one entry point at the repo root:

```bash
./harness help
```

`./harness` maps verbs onto the files below. Prefer it over invoking scripts
directly.

## User-facing commands (via `./harness`)

| Verb | Script | Purpose |
|---|---|---|
| `run` | `run_suite.py` | Run suites → `run.json` + logs |
| `report` | `build_report.py` | `run.json` → Markdown + HTML |
| `review` | `diff_runs.py` | Diff a run vs the pinned baseline |
| `teach` | `teach` | Log a correction (wizard / shorthand / editor) |
| `promote` | `promote_recent.py` | Propose or apply learnings into skills |
| `baseline` | `make_baseline.sh` | Re-pin `reports/baseline/<target>.json` |
| `history` | `history.py` | List recent runs |
| `clean` | `clean.py` | Remove run dirs (keeps baseline) |
| `open` | `open_report.py` | Open a run's report.html |
| `validate` | `validate.py` | Check suites/arches/cann configs |
| `status` | `status.py` | One-glance dashboard (env, suites, baseline, learnings, last run) |
| `diagnose` | `diagnose.py` | Check this machine + print exact fixes |
| `targets` | `targets_cli.py` | List configured targets (name, label, repo, suites) |
| `capture-skill` | `capture_skill.py` | Draft a NEW skill into `skills/inbox/` |
| `promote-skill` | `promote_skill.py` | Promote a draft into `.claude/skills/` (+ MR) |
| `skills` | `skills_cli.py` | List/search skills · `--install`/`--uninstall` · `--refresh` |
| `onboarding` | `onboarding.py` | Guided first-run setup |
| `tui` | `tui.py` | Full-screen dashboard (interactive) |
| `menu` | `menu.py` | Curated interactive menu (bare `./harness` default) |
| `demo` | `demo_tour.py` | Interactive step-by-step sandboxed walkthrough (`--straight` = `demo/run_demo.sh`) |
| `guide` | `guide.py` | Interactive step-by-step tour |
| `list` | `run_suite.py --list` | List suites + arches |
| `cann` | `detect_cann.py` | Which CANN supports which arch |
| `selfcheck` | `selfcheck` | Compile-check + skill-spec validation + demo smoke |

## Internals (imported / used by the commands above — not for direct use)

- `_runs.py` — locate latest/list runs (used by report/review/history/clean/open).
- `capabilities.py` — runtime capability checks (compiler/CANN/simulator/device/MPI) for auto-enabling suites.
- `complete.py` — completion candidates (used by `completions/harness.bash`).
- `parse_gtest.py` — log → normalized results (used by `run_suite.py`).
- `log_correction.py` — strict `LRN-…` writer (used by `teach` and `session_digest.py`).
- `session_digest.py` — draft pending learnings from a `run.json`.
- `demo_tour.py` — interactive, step-by-step demo driver (reuses `guide.py` menus).
- `validate_skills.py` — checks every SKILL.md against the open Agent Skills spec (used by selfcheck).
- `status.py` / `diagnose.py` / `tui.py` — status dashboard, env health check, and full-screen dashboard (share `capabilities` + `_runs`).
- `perf_metrics.py` — per-case timing (p50/p99/max) + CAModel metrics (EX/IPC/vf_real/dual/stalls, vmi-dashboard schema).
- `targets.py` / `targets_cli.py` — the target registry + `./harness targets` listing (used by run/guide/status/diagnose/onboarding).
- `capture_skill.py` / `promote_skill.py` / `skills_cli.py` — draft, promote, and
  browse skills (skills_cli also subsumes `install_skills.py` via `--install`).
- `onboarding.py` / `menu.py` — guided first-run setup and the bare-`./harness` menu (reuse `guide.py` helpers).
- `wrap.py` — wraps a verb and offers a context-aware "What next?" menu (type-a-command / full menu / shell).
- `_browser.py` — cross-platform browser opener (WSL explorer.exe → xdg-open/open/start → print path).
- `_term.py` — shared ANSI colors + `c()`/`mark()`/`fmt_dur()` (imported by the CLI scripts).

## Conventions

- Exit codes: `0` success, `1` ran-but-not-clean, `2` usage error.
- Errors go to stderr; machine-readable output is JSON where `--json` is offered.

## Extras

- `./harness run --tui` — live per-suite spinner + pass/fail line (auto-falls back
  to quiet when stdout isn't a TTY).
- `./harness run --suite X --testcase T [--filter G]` — run a single testcase / gtest
  filter instead of the whole suite (maps to `-t`/`-g` for npu, `--testcase`/
  `--gtest_filter` for cpu).
- `./harness list --format markdown|html` — suite catalog for docs/dashboards.
- `./harness promote --pr` — apply + branch + commit + push + merge-request URL.
- `./harness report` / `./harness review` — default to the latest run.
- `./harness report --open` — generate and open in the browser.
- `./harness history [--limit N] [--json]` — recent runs table.
- `./harness clean [--dry-run] [--keep N]` — purge run dirs, keeps baseline.
- `./harness validate` — sanity-check suites/arches/cann configs.
- `make check` — run the self-check locally.
- `./harness list` — shows auto-detected availability: `✓` runnable, `!` missing prereqs, `—` disabled.
- `./harness demo` — interactive step-by-step walkthrough (run / next / previous / jump / explain / quit); `--straight` runs it non-interactively.
- `./harness run --dry-run` — preview what would run (no run.json); `--parallel` runs independent suites concurrently.
- `capabilities.py` caches CANN scans in `.cache/cann-lanes.json` (5-min TTL) for instant status/list.
- `--all-suites` auto-skips non-runnable suites and prints why (compiler/CANN/simulator/device/MPI).
- Tab completion: `source completions/harness.bash` (also completes `--suite`/`--testcase` values).