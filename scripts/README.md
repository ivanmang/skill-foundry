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
| `demo` | `demo/run_demo.sh` | Sandboxed walkthrough |
| `list` | `run_suite.py --list` | List suites + arches |
| `selfcheck` | `selfcheck` | Compile-check + demo smoke |

## Internals (imported / used by the commands above — not for direct use)

- `parse_gtest.py` — log → normalized results (used by `run_suite.py`).
- `log_correction.py` — strict `LRN-…` writer (used by `teach` and `session_digest.py`).
- `session_digest.py` — draft pending learnings from a `run.json`.

## Conventions

- Exit codes: `0` success, `1` ran-but-not-clean, `2` usage error.
- Errors go to stderr; machine-readable output is JSON where `--json` is offered.