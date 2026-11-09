"""Single source of truth for the ./harness CLI surface.

`dispatch.py` builds `./harness help` and per-verb `./harness help <verb>` from
this module; `docs/CLI.md` is generated from the same data (see
`skill_foundry.cli.skills` refresh / check). Keeping the registry here means the
help text, the README reference, and the generated docs can never drift.

Do NOT hand-edit `TEXT_USAGE` / `VERB_HELP` in dispatch.py — add or edit verbs
here instead.
"""

from __future__ import annotations

# (verb, one-line summary, flags hint) — rendered in ./harness help, in order.
PRODUCT_VERBS: list[tuple[str, str, str]] = [
    (
        "capture-skill",
        "Draft a NEW skill into hub/inbox/",
        "[--description, --body, --dry-run]",
    ),
    (
        "promote-skill",
        "Publish a draft into .claude/skills/",
        "[--propose | --apply | --pr]",
    ),
    (
        "teach",
        "Log a correction (a lesson)",
        '["wrong -> correct -> action" | wizard | --edit]',
    ),
    (
        "learn",
        "Log + promote in one step",
        '["wrong -> correct -> action" | --apply (default) | --propose | --pr]',
    ),
    (
        "capture-session",
        "Draft learnings from a pi session",
        "[--session X.jsonl | --apply]",
    ),
    ("promote", "Publish learnings into skills", "[--propose | --apply | --pr]"),
    (
        "skills",
        "List/search skills · install · refresh",
        "[--search, --category, --origin, --owner, --maturity, --scope, --entry, "
        "--name, --inbox, --install, --uninstall, --dry-run, --mine, --refresh, "
        "--check, --json]",
    ),
    ("learnings", "List captured learnings", "[status (default) | rotate]"),
    (
        "metrics",
        "Show product-loop telemetry",
        "[--calibrate EVENT_ID --outcome approve|reject | --pending]",
    ),
]

# (verb, one-line summary) — shell verbs, rendered after the product verbs.
SHELL_VERBS_HELP: list[tuple[str, str]] = [
    ("menu", "Curated menu (bare ./harness default)"),
    (
        "selfcheck",
        "Compile + spec + reference integrity + index freshness + demo smoke",
    ),
]

# Detailed per-verb help (`./harness help <verb>`).
VERB_HELP: dict[str, str] = {
    "capture-skill": """\
./harness capture-skill <name> [--description "…"] [--body "…"] [--dry-run]
Draft a NEW skill into hub/inbox/<name>/SKILL.md (wizard / editor for the body).
Example: ./harness capture-skill code-review --description "Review PRs against house style"
""",
    "promote-skill": """\
./harness promote-skill [<name>] [--propose | --apply | --pr]
Publish a draft from hub/inbox/ into .claude/skills/ (gated + LLM-reviewed; a human merges the PR).
Example: ./harness promote-skill code-review --pr
""",
    "teach": """\
./harness teach — log a correction (append-only)
  "wrong -> correct -> action"  one-line shorthand
  (no args)                     interactive wizard
  --edit                        open $EDITOR with a template

Example: ./harness teach "vcvt mismatch -> known pattern, annotate -> promote to known-failures"
""",
    "learn": """\
./harness learn — log a correction and promote it in one step
  "wrong -> correct -> action"  shorthand (logged, then promoted)
  --apply                       apply locally (default, no commit/push)
  --propose                     stop after printing the reviewable diff
  --pr                          push a branch + open a PR (a human merges)

Example: ./harness learn "vcvt mismatch -> annotate as known -> add to known-failures" --pr
""",
    "capture-session": """\
./harness capture-session [--session X.jsonl | --apply]
Draft learnings from a pi session log into learnings/recent.md.
Example: ./harness capture-session --session ~/.pi/agent/sessions/foo.jsonl --apply
""",
    "promote": """\
./harness promote — publish pending learnings into skills (gated + LLM-reviewed)
  --propose  print a reviewable diff (no write)
  --apply    write the edits locally (no commit)
  --pr       branch + push + open a PR (a human merges)

Review and the mechanical gates are MANDATORY: there is no --no-review,
no --force, and no --direct. Publish only via --pr, which opens a PR.

Examples:
  ./harness promote --propose   # review the diff first
  ./harness promote --pr        # apply + push a branch + open a PR
""",
    "skills": """\
./harness skills [--search <q>] [--category <c>] [--origin <o>] [--scope core|all] [--entry] [--inbox] [--install | --uninstall] [--dry-run] [--mine] [--refresh] [--check] [--json]
List/search skills (published .claude/skills/ + drafts hub/inbox/).
  --search    filter by name/description/category substring
  --category  filter by exact category
  --origin    filter by exact origin (native | cannbot)
  --owner     filter by exact owner (skill-foundry | cannbot)
  --maturity  filter by maturity (ready | draft | deprecated)
  --name      only this skill (repeatable; --install/--uninstall)
  --scope     preset: 'core' = the owned (origin: native) skills
  --entry     entry points only
  --refresh   rewrite hub/catalog.json + docs/SKILLS_INDEX.md + README count + docs/CLI.md
  --check     fail if catalog/index/README count/CLI.md are stale (no writes)
  --install   symlink skills into each detected agent's user dir (respects filters)
  --uninstall remove the harness skill symlinks (respects filters)
  --dry-run   with --install/--uninstall: show what would change (no writes)
  --mine      show what each detected agent can see vs the hub
Examples: ./harness skills --search review      ./harness skills --install --scope core      ./harness skills --mine
""",
    "learnings": """\
./harness learnings [status | rotate]
Manage the learnings ledger (learnings/recent.md).
  status  print pending/promoted/rejected counts (default)
  rotate  archive recent.md and start a fresh one (refuses if pending remain)

Example: ./harness learnings status
""",
    "metrics": """\
./harness metrics [--calibrate EVENT_ID --outcome approve|reject] [--pending]
Show product-loop telemetry; calibrate a reviewer judge event after the fact.
  --pending  list uncalibrated judge events

Example: ./harness metrics --calibrate c7839ad8f58b --outcome approve
""",
    "selfcheck": """\
./harness selfcheck — compile + skill-spec + reference integrity + index freshness + demo smoke.
Example: ./harness selfcheck
""",
}

# The bundled regression workflow — thin scripts, run directly (not harness verbs).
BUNDLED_WORKFLOW: list[tuple[str, str, str]] = [
    ("run", "run suites", "[--suite X | --all-suites] [--report|--open|--review] …"),
    ("report", "run.json → report.md/.html", "[--open] [--known]"),
    ("review", "diff a run vs the pinned baseline", "[--run reports/<id>/run.json]"),
    ("status", "one-glance readiness dashboard", "[--target X] [--json]"),
    ("diagnose", "check this machine + print the exact fix", "[--strict]"),
    ("onboarding", "guided first-run setup", ""),
    ("demo", "interactive sandboxed walkthrough (no hardware)", "[--straight]"),
    ("guide", "interactive tour of the real flow", ""),
    ("history", "list recent runs", ""),
    ("clean", "clean run dirs", "[--dry-run] [--keep N]"),
    ("validate", "validate config", ""),
    ("cann", "which CANN supports which arch", "[--scan] [--json]"),
    ("baseline.sh", "re-pin reports/baseline/<target>.json", "[--force] <target>"),
]


def usage_text() -> str:
    """Render the `./harness help` body from the registry above."""
    lines = [
        "usage: ./harness <command> [args]",
        "",
        "THE PRODUCT — the skill-ops loop (capture → promote → hub → discover):",
    ]
    for name, summary, flags in PRODUCT_VERBS:
        lines.append(f"  {name:<15} {summary:<38} {flags}".rstrip())
    lines += [
        "",
        "SHELL:",
    ]
    for name, summary in SHELL_VERBS_HELP:
        lines.append(f"  {name:<15} {summary}")
    lines += [
        "",
        "  help           Show this help — or: ./harness help <verb>",
        "  version        Show the harness version                [--short]",
        "",
        "The bundled regression workflow (run → report → review, capability detection,",
        "baseline, readiness) is NOT part of the harness. It lives as directly-runnable",
        "thin scripts that the skills reference as knowledge:",
        "",
        "  python3 -m skill_foundry.workflow.run [--all-suites | --suite X …]",
        "  python3 -m skill_foundry.workflow.report · .workflow.review · .workflow.status",
        "  python3 -m skill_foundry.lib.cann   (CANN/arch detection)",
        "",
        "See .claude/skills/ for the full, self-contained workflow knowledge.",
        "",
        "Examples:",
        "  ./harness capture-skill code-review",
        '  ./harness teach "vcvt mismatch -> annotate as known -> add to known-failures"',
        "  ./harness promote --pr            # publish learnings (open a PR, human merges)",
        "  ./harness skills --search review  # discover skills",
    ]
    return "\n".join(lines) + "\n"


def _cell(text: str) -> str:
    """Escape pipe characters so they don't break a Markdown table cell."""
    return text.replace("|", "\\|")


def cli_markdown() -> str:
    """Render docs/CLI.md from the registry (single source for the README ref)."""
    lines = [
        "# CLI Reference",
        "",
        "_Auto-generated from `skill_foundry/verbs.py` — edit that file, then run "
        "`./harness skills --refresh` (or `./harness selfcheck` to detect staleness)._",
        "",
        "## `./harness` — the skill-ops loop (capture → promote → hub → discover)",
        "",
        "| Verb | Purpose | Flags |",
        "|---|---|---|",
    ]
    for name, summary, flags in PRODUCT_VERBS:
        lines.append(f"| `{name}` | {_cell(summary)} | {_cell(flags)} |")
    for name, summary in SHELL_VERBS_HELP:
        lines.append(f"| `{name}` | {_cell(summary)} | |")
    lines += [
        "| `help` | Show this help — or `./harness help <verb>` | |",
        "| `version` | Show the harness version | `--short` |",
        "",
        "## Bundled regression workflow — run directly (the skills reference these)",
        "",
        "| Command | Purpose | Flags |",
        "|---|---|---|",
    ]
    for name, summary, flags in BUNDLED_WORKFLOW:
        if name == "baseline.sh":
            cmd = "`bash skill_foundry/workflow/baseline.sh`"
        elif name == "cann":
            cmd = f"`python3 -m skill_foundry.lib.{name}`"
        else:
            cmd = f"`python3 -m skill_foundry.workflow.{name}`"
        lines.append(f"| {cmd} | {_cell(summary)} | {_cell(flags)} |")
    lines += [
        "",
        "Run `./harness help <verb>` for a verb's detailed examples.",
    ]
    return "\n".join(lines) + "\n"
