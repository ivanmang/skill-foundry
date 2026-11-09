# CLI Reference

_Auto-generated from `skill_foundry/verbs.py` — edit that file, then run `./harness skills --refresh` (or `./harness selfcheck` to detect staleness)._

## `./harness` — the skill-ops loop (capture → promote → hub → discover)

| Verb | Purpose | Flags |
|---|---|---|
| `capture-skill` | Draft a NEW skill into hub/inbox/ | [--description, --body, --dry-run] |
| `promote-skill` | Publish a draft into .claude/skills/ | [--propose \| --apply \| --pr] |
| `teach` | Log a correction (a lesson) | ["wrong -> correct -> action" \| wizard \| --edit] |
| `learn` | Log + promote in one step | ["wrong -> correct -> action" \| --apply (default) \| --propose \| --pr] |
| `capture-session` | Draft learnings from a pi session | [--session X.jsonl \| --apply] |
| `promote` | Publish learnings into skills | [--propose \| --apply \| --pr] |
| `skills` | List/search skills · install · refresh | [--search, --category, --origin, --owner, --maturity, --scope, --entry, --name, --inbox, --install, --uninstall, --dry-run, --mine, --refresh, --check, --json] |
| `learnings` | List captured learnings | [status (default) \| rotate] |
| `metrics` | Show product-loop telemetry | [--calibrate EVENT_ID --outcome approve\|reject \| --pending] |
| `menu` | Curated menu (bare ./harness default) | |
| `selfcheck` | Compile + spec + reference integrity + index freshness + demo smoke | |
| `help` | Show this help — or `./harness help <verb>` | |
| `version` | Show the harness version | `--short` |

## Bundled regression workflow — run directly (the skills reference these)

| Command | Purpose | Flags |
|---|---|---|
| `python3 -m skill_foundry.workflow.run` | run suites | [--suite X \| --all-suites] [--report\|--open\|--review] … |
| `python3 -m skill_foundry.workflow.report` | run.json → report.md/.html | [--open] [--known] |
| `python3 -m skill_foundry.workflow.review` | diff a run vs the pinned baseline | [--run reports/<id>/run.json] |
| `python3 -m skill_foundry.workflow.status` | one-glance readiness dashboard | [--target X] [--json] |
| `python3 -m skill_foundry.workflow.diagnose` | check this machine + print the exact fix | [--strict] |
| `python3 -m skill_foundry.workflow.onboarding` | guided first-run setup |  |
| `python3 -m skill_foundry.workflow.demo` | interactive sandboxed walkthrough (no hardware) | [--straight] |
| `python3 -m skill_foundry.workflow.guide` | interactive tour of the real flow |  |
| `python3 -m skill_foundry.workflow.history` | list recent runs |  |
| `python3 -m skill_foundry.workflow.clean` | clean run dirs | [--dry-run] [--keep N] |
| `python3 -m skill_foundry.workflow.validate` | validate config |  |
| `python3 -m skill_foundry.lib.cann` | which CANN supports which arch | [--scan] [--json] |
| `bash skill_foundry/workflow/baseline.sh` | re-pin reports/baseline/<target>.json | [--force] <target> |

Run `./harness help <verb>` for a verb's detailed examples.
