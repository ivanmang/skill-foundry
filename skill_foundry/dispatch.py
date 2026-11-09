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

from skill_foundry import verbs as verb_registry
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
    "learnings": ("skill_foundry.cli.learnings", None),
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
    print(verb_registry.usage_text(), file=file or sys.stdout, end="")


def verb_help(verb: str) -> None:
    print(
        verb_registry.VERB_HELP.get(
            verb, "no detailed help for '%s' — run ./harness help" % verb
        )
    )


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
