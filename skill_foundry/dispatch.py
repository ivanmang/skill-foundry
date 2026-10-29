"""Verb dispatch: map `./harness <verb>` onto a module `main()` — in-process.

This is the single place that knows which module implements which verb, so the
CLI (`__main__`), the wrap loop, and the menu all share it without re-spawning
a Python process per verb.
"""

from __future__ import annotations

import importlib
import subprocess
import sys

from skill_foundry.paths import ROOT, version as _version

# python verbs: verb -> (module, argv prefix to inject)
VERB_MODULES: dict[str, tuple[str, list[str] | None]] = {
    # ── THE PRODUCT — the skill-ops loop (capture → promote → hub → discover) ──
    "capture-skill": ("skill_foundry.cli.capture", None),
    "promote-skill": ("skill_foundry.cli.promote_skill", None),
    "teach": ("skill_foundry.cli.teach", None),
    "promote": ("skill_foundry.cli.promote", None),
    "skills": ("skill_foundry.cli.skills", None),

    # ── BUNDLED WORKFLOW — regression (run → report → review) + readiness ──
    "run": ("skill_foundry.workflow.run", None),
    "list": ("skill_foundry.workflow.run", ["--list"]),
    "report": ("skill_foundry.workflow.report", None),
    "review": ("skill_foundry.workflow.review", None),
    "status": ("skill_foundry.workflow.status", None),
    "diagnose": ("skill_foundry.workflow.diagnose", None),
    "history": ("skill_foundry.workflow.history", None),
    "clean": ("skill_foundry.workflow.clean", None),
    "validate": ("skill_foundry.workflow.validate", None),
    "cann": ("skill_foundry.lib.cann", None),

    # ── INTERACTIVE / SHELL ──
    "menu": ("skill_foundry.cli.menu", None),
    "guide": ("skill_foundry.cli.guide", None),
    "demo": ("skill_foundry.cli.demo", None),
    "onboarding": ("skill_foundry.cli.onboarding", None),

    # ── internal ──
    "complete": ("skill_foundry.cli.complete", None),
    "__complete": ("skill_foundry.cli.complete", None),
}

# shell verbs (kept as bash for process-boundary reasons)
SHELL_VERBS: dict[str, str] = {
    "baseline": "skill_foundry/workflow/baseline.sh",
    "selfcheck": "skill_foundry/cli/selfcheck.sh",
}

# Verbs that manage their own terminal and must not be wrapped by the
# "What next?" loop (run straight through).
NON_WRAP = {
    "menu", "help", "-h", "--help",
    "version", "--version", "-V", "__complete", "selfcheck",
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
            capture_output=True, text=True,
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

THE PRODUCT — capture & publish skills (the loop):
  capture-skill  Draft a NEW skill into hub/inbox/  [--description, --dry-run]
  promote-skill  Promote a draft into .claude/skills/  [--propose | --apply | --pr | --direct]
  teach     Log a correction (a lesson about an existing skill)  ["wrong -> correct -> action" | wizard | --edit]
  promote   Promote learnings into skills        [--propose | --apply | --pr | --direct]
  skills    List/search skills · install into agents · refresh the catalog  [--search, --inbox, --install, --uninstall, --refresh, --json]

BUNDLED WORKFLOW — regression (run → report → review), driven by the skills:
  run       Run a declared suite               [--suite | --all-suites] [--testcase] [--filter] [--quiet|--tui|--json] [--dry-run] [--parallel] [--report|--open|--review]
  report    Render a run to Markdown + HTML    [--run (default: latest), --known, --out, --open]
  review    Diff a run vs the pinned baseline  [--run (default: latest), --baseline, --out]

SETUP:
  onboarding  Guided first-run setup
  status      One-glance dashboard (all targets)  [--json, --target]
  diagnose    Check env + print exact fixes    [--json, --strict]
  cann        Which CANN supports which arch   [--home, --scan, --json]

INTERACTIVE:
  guide     Interactive step-by-step tour      [--demo]
  demo      Sandboxed walkthrough (interactive) [--straight]
  menu      Curated interactive menu (bare ./harness default)

BASELINE & HOUSEKEEPING:
  baseline  Re-pin reports/baseline/<target>.json  [--force] [target]
  history   List recent runs                   [--limit N, --json]
  clean     Remove run dirs (keeps baseline)   [--dry-run, --keep N]
  validate  Check suites/arches/cann configs
  list      List suites + arches               [--target, --format text|markdown|html]
  selfcheck Compile-check + skill-spec validation + demo smoke

  help      Show this help — or: ./harness help <verb> for examples
  version   Show the harness version           [--short]

Examples:
  ./harness capture-skill code-review          # draft a new skill
  ./harness skills --search review             # discover skills
  ./harness status
  ./harness run --all-suites --dry-run      # preview before the real run
  ./harness run --suite npu-sim-a5 --testcase tpartargmax
  ./harness report --open                  # latest run, in the browser
  ./harness review                         # latest run vs baseline
  ./harness teach "vcvt mismatch -> annotate as known -> add to known-failures"
  ./harness demo                           # no hardware needed
"""


VERB_HELP: dict[str, str] = {
    "run": """\
./harness run — run a declared suite
  --suite <name>   one suite (force-runs even if prereqs are missing)
  --all-suites     every enabled suite that is runnable here (auto-skips the rest)
  --target <t>     target key in config/suites.json (default pto-isa)
  --testcase <t>   one testcase (e.g. tpartargmax); --filter <g> a gtest filter
  --quiet          summary only   --tui live spinner   --json machine output
  --dry-run        print what WOULD run and exit (no run.json)
  --parallel       run independent suites concurrently (implies per-suite quiet)
  --report         render report.md/.html after the run (auto-annotates known failures)
  --open           like --report + open the HTML in a browser
  --review         diff vs the pinned baseline after the run

Examples:
  ./harness run --all-suites --dry-run
  ./harness run --all-suites --quiet
  ./harness run --all-suites --report --open --review   # the whole USE loop, one command
  ./harness run --suite npu-sim-a5 --testcase tpartargmax
  ./harness run --suite cpu-st --testcase tadd --filter 'TADDTest.case_*'
""",
    "report": """\
./harness report — render run.json -> report.md/.html
  --run <path>   run.json (default latest run)
  --known <file> known-failures.md to annotate known failures
  --out <base>   output base path (default <run>/report)
  --open         open the HTML in the browser

Examples:
  ./harness report
  ./harness report --open
  ./harness report --run reports/<id>/run.json --known .claude/skills/pto-isa/references/known-failures.md
""",
    "review": """\
./harness review — diff a run vs the pinned baseline
  --run <path>      run.json (default latest run)
  --baseline <path> baseline.json (default: reports/baseline/<target>.json for the run's target)

Example: ./harness review
""",
    "teach": """\
./harness teach — log a correction (append-only)
  "wrong -> correct -> action"  one-line shorthand
  (no args)                     interactive wizard
  --edit                        open $EDITOR with a template

Example: ./harness teach "vcvt mismatch -> known pattern, annotate -> promote to known-failures"
""",
    "promote": """\
./harness promote — promote pending learnings into skills
  --propose   print a reviewable diff (no write)
  --apply     write the edits locally
  --direct    commit + push to origin/main over SSH (NO MR, NO token)
  --pr        branch + push + AUTO-CREATE the MR (glab / GITCODE_TOKEN)

Example: ./harness promote --direct    # then teammates git pull
""",
    "capture-skill": """\
./harness capture-skill <name> [--description "…"] [--dry-run]
Draft a NEW skill into hub/inbox/<name>/SKILL.md (wizard / editor for the body).
Example: ./harness capture-skill code-review --description "Review PRs against house style"
""",
    "promote-skill": """\
./harness promote-skill [<name>] [--propose | --apply | --direct | --pr]
Promote a draft from hub/inbox/ into .claude/skills/.
  --direct  commit + push to origin/main over SSH (no MR, no token)
  --pr      branch + push + auto-MR (glab / GITCODE_TOKEN)
Example: ./harness promote-skill code-review --direct
""",
    "skills": """\
./harness skills [--search <q>] [--inbox] [--install | --uninstall] [--refresh] [--json]
List/search skills (published .claude/skills/ + drafts hub/inbox/).
  --refresh   regenerate hub/catalog.json
  --install   symlink skills into each detected agent's user dir
  --uninstall remove the harness skill symlinks
Examples: ./harness skills --search review      ./harness skills --install
""",
    "status": """\
./harness status — one-glance dashboard (env, per-target suites, baseline, learnings, last run)
  --target <t>  show only one target
  --json        machine output
Example: ./harness status
""",
    "diagnose": """\
./harness diagnose — check this machine and print the exact fix for each issue
  --json    machine output
  --strict  exit 1 if any issue (for CI)
Example: ./harness diagnose
""",
    "demo": """\
./harness demo — interactive sandboxed walkthrough (no hardware)
  --straight  run straight through (CI / presenting)
Example: ./harness demo
""",
    "guide": """\
./harness guide — interactive tour of the real pto-isa flow (env -> choose -> run -> report -> review -> teach -> promote)
  --demo  jump straight to the sandboxed demo
Example: ./harness guide
""",
    "baseline": """\
./harness baseline [--force] <target> — run all enabled (runnable) suites and re-pin reports/baseline/<target>.json
Refuses unless every suite PASSes (use --force to override).
Example: ./harness baseline pto-isa
""",
    "list": """\
./harness list — list suites + arches with auto-detected availability
  --target <t>  --format text|markdown|html
Example: ./harness list
""",
    "cann": """\
./harness cann — which installed CANN supports which arch (headers vs simulator)
  --home <path>  --scan  --json
Example: ./harness cann
""",
    "onboarding": """\
./harness onboarding — guided first-run setup (detect env, write env.sh, pick CANN, verify pto-isa)
Example: ./harness onboarding
""",
}