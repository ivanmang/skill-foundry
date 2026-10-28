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
| `baseline` | `make_baseline.sh` | Re-pin `reports/baseline/baseline.json` |
| `history` | `history.py` | List recent runs |
| `clean` | `clean.py` | Remove run dirs (keeps baseline) |
| `open` | `open_report.py` | Open a run's report.html |
| `validate` | `validate.py` | Check suites/arches/cann configs |
| `demo` | `demo/run_demo.sh` | Sandboxed walkthrough |
| `guide` | `guide.py` | Interactive step-by-step tour |
| `list` | `run_suite.py --list` | List suites + arches |
| `cann` | `detect_cann.py` | Which CANN supports which arch |
| `selfcheck` | `selfcheck` | Compile-check + demo smoke |

## Internals (imported / used by the commands above — not for direct use)

- `_runs.py` — locate latest/list runs (used by report/review/history/clean/open).
- `capabilities.py` — runtime capability checks (compiler/CANN/simulator/device/MPI) for auto-enabling suites.
- `complete.py` — completion candidates (used by `completions/harness.bash`).
- `parse_gtest.py` — log → normalized results (used by `run_suite.py`).
- `log_correction.py` — strict `LRN-…` writer (used by `teach` and `session_digest.py`).
- `session_digest.py` — draft pending learnings from a `run.json`.
- `demo_tour.py` — interactive, step-by-step demo driver (reuses `guide.py` menus).

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
- `--all-suites` auto-skips non-runnable suites and prints why (compiler/CANN/simulator/device/MPI).
- Tab completion: `source completions/harness.bash` (also completes `--suite`/`--testcase` values).