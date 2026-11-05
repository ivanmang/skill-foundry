"""Verb dispatch: map `./harness <verb>` onto a module `main()` — in-process.

The harness is DELIBERATELY SMALL — it exposes only the skill-ops loop
(capture → promote → hub → discover). Everything else (the bundled regression
workflow, capability detection, reporters, baseline, readiness checks) lives as
directly-runnable thin scripts under `skill_foundry/workflow/` and
`skill_foundry/lib/`, which the skills reference as knowledge.
"""

from __future__ import annotations

import importlib
import subprocess
import sys

from skill_foundry.paths import ROOT, version as _version

# ── THE PRODUCT — the skill-ops loop (this is all ./harness does) ──
VERB_MODULES: dict[str, tuple[str, list[str] | None]] = {
    "capture-skill": ("skill_foundry.cli.capture", None),
    "promote-skill": ("skill_foundry.cli.promote_skill", None),
    "teach": ("skill_foundry.cli.teach", None),
    "learn": ("skill_foundry.cli.learn", None),
    "capture-session": ("skill_foundry.cli.capture_session", None),
    "promote": ("skill_foundry.cli.promote", None),
    "skills": ("skill_foundry.cli.skills", None),
    "metrics": ("skill_foundry.cli.metrics", None),
    # shell
    "menu": ("skill_foundry.cli.menu", None),
    "complete": ("skill_foundry.cli.complete", None),
    "__complete": ("skill_foundry.cli.complete", None),
}

# shell verbs kept as bash (process boundary / housekeeping)
SHELL_VERBS: dict[str, str] = {
    "selfcheck": "skill_foundry/cli/selfcheck.sh",
}

NON_WRAP = {
    "menu",
    "help",
    "-h",
    "--help",
    "version",
    "--version",
    "-V",
    "__complete",
    "selfcheck",
}


def verbs() -> list[str]:
    """User-facing verb names (for menus + completion), sorted."""
    hidden = {"__complete", "complete"}
    return sorted(
        [k for k in VERB_MODULES if k not in hidden]
        + list(SHELL_VERBS)
        + ["help", "version"]
    )


def version(short: bool = False) -> str:
    """Return the harness version string (VERSION file + git describe)."""
    ver = _version()
    if short:
        return ver
    sha = "dev"
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
        )
        sha = out.stdout.strip() or "dev"
    except FileNotFoundError:
        pass
    return f"skill-foundry {ver} ({sha})"


def usage(file=None) -> None:
    print(TEXT_USAGE, file=file or sys.stdout, end="")


def verb_help(verb: str) -> None:
    print(VERB_HELP.get(verb, "no detailed help for '%s' — run ./harness help" % verb))


def dispatch(cmd: str, args: list[str]) -> int:
    """Run `cmd` with `args` and return its exit code (in-process where possible)."""
    if cmd in ("help", "-h", "--help"):
        if args and args[0] not in ("-h", "--help"):
            verb_help(args[0])
        else:
            usage()
        return 0
    if cmd in ("version", "--version", "-V"):
        print(version(short=(args[:1] == ["--short"])))
        return 0

    if cmd in VERB_MODULES:
        modname, prefix = VERB_MODULES[cmd]
        module = importlib.import_module(modname)
        call_args = list(prefix or []) + list(args)
        return int(module.main(call_args))

    if cmd in SHELL_VERBS:
        return subprocess.call([str(ROOT / SHELL_VERBS[cmd]), *args])

    print(f"unknown command: {cmd}", file=sys.stderr)
    usage(sys.stderr)
    return 2


TEXT_USAGE = """\
usage: ./harness <command> [args]

THE PRODUCT — the skill-ops loop (capture → promote → hub → discover):
  capture-skill  Draft a NEW skill into hub/inbox/       [--description, --dry-run]
  promote-skill  Publish a draft into .claude/skills/    [--propose | --apply | --pr]
  teach          Log a correction (a lesson)             ["wrong -> correct -> action" | wizard | --edit]
  learn          Log + promote (and --pr) in one step    ["wrong -> correct -> action" | --pr]
  capture-session Draft learnings from a pi session     [--session X.jsonl | --apply]
  promote        Publish learnings into skills           [--propose | --apply | --pr]
  skills         List/search skills · install · refresh  [--search, --category, --origin, --scope, --entry, --inbox, --install, --uninstall, --dry-run, --mine, --refresh, --check, --json]

SHELL:
  menu           Curated menu (bare ./harness default)
  selfcheck      Compile + spec + reference integrity + index freshness + demo smoke

  help           Show this help — or: ./harness help <verb>
  version        Show the harness version                [--short]

The bundled regression workflow (run → report → review, capability detection,
baseline, readiness) is NOT part of the harness. It lives as directly-runnable
thin scripts that the skills reference as knowledge:

  python3 -m skill_foundry.workflow.run [--all-suites | --suite X …]
  python3 -m skill_foundry.workflow.report · .workflow.review · .workflow.status
  python3 -m skill_foundry.lib.cann   (CANN/arch detection)

See .claude/skills/ for the full, self-contained workflow knowledge.

Examples:
  ./harness capture-skill code-review
  ./harness teach "vcvt mismatch -> annotate as known -> add to known-failures"
  ./harness promote --pr            # publish learnings (open an MR, human merges)
  ./harness skills --search review  # discover skills
"""


VERB_HELP: dict[str, str] = {
    "capture-skill": """\
./harness capture-skill <name> [--description "…"] [--dry-run]
Draft a NEW skill into hub/inbox/<name>/SKILL.md (wizard / editor for the body).
Example: ./harness capture-skill code-review --description "Review PRs against house style"
""",
    "promote-skill": """\
./harness promote-skill [<name>] [--propose | --apply | --pr]
Publish a draft from hub/inbox/ into .claude/skills/ (gated + LLM-reviewed; a human merges the MR).
Example: ./harness promote-skill code-review --pr
""",
    "teach": """\
./harness teach — log a correction (append-only)
  "wrong -> correct -> action"  one-line shorthand
  (no args)                     interactive wizard
  --edit                        open $EDITOR with a template

Example: ./harness teach "vcvt mismatch -> known pattern, annotate -> promote to known-failures"
""",
    "promote": """\
./harness promote — publish pending learnings into skills (gated + LLM-reviewed)
  --propose  print a reviewable diff (no write)
  --apply    write the edits locally (no commit)
  --pr       branch + push + open an MR (a human merges)

Review and the mechanical gates are MANDATORY: there is no --no-review,
no --force, and no --direct. Publish only via --pr, which opens an MR.

Examples:
  ./harness promote --propose   # review the diff first
  ./harness promote --pr        # apply + push a branch + open an MR
""",
    "skills": """\
./harness skills [--search <q>] [--category <c>] [--origin <o>] [--scope core|all] [--entry] [--inbox] [--install | --uninstall] [--dry-run] [--mine] [--refresh] [--check] [--json]
List/search skills (published .claude/skills/ + drafts hub/inbox/).
  --search    filter by name/description/category substring
  --category  filter by exact category
  --origin    filter by exact origin (native | cannbot)
  --scope     preset: 'core' = the owned (origin: native) skills
  --entry     entry points only
  --refresh   rewrite hub/catalog.json + docs/SKILLS_INDEX.md
  --check     fail if catalog/index are stale (no writes)
  --install   symlink skills into each detected agent's user dir (respects filters)
  --uninstall remove the harness skill symlinks (respects filters)
  --dry-run   with --install/--uninstall: show what would change (no writes)
  --mine      show what each detected agent can see vs the hub
Examples: ./harness skills --search review      ./harness skills --install --scope core      ./harness skills --mine
""",
    "selfcheck": """\
./harness selfcheck — compile + skill-spec + reference integrity + index freshness + demo smoke.
Example: ./harness selfcheck
""",
}
