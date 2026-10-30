#!/usr/bin/env python3
"""harness-mcp — expose the skill-ops loop to any MCP-capable agent.

Tools:
  skills_list     list/search skills (published + drafts)
  skills_load     return a skill's SKILL.md (+ note where references live)
  capture_skill   draft a NEW skill into hub/inbox/
  teach           log a correction (a lesson about an existing skill)
  promote         direct | pr | propose | apply (learnings or a named skill draft)

First-class tools: each calls the `skill_foundry` library **in-process** (via the
shared dispatcher) — no shelling out to `./harness`. Behavior is identical to the
CLI because it's the same code path.

Dependency:
  pip install fastmcp          # or: uv pip install fastmcp

Run (local / stdio):
  python3 mcp/server.py                          # stdio (attach to an agent directly)
  fastmcp run mcp/server.py                     # FastMCP CLI (stdio)

Run (hosted on b10, HTTP):
  fastmcp run mcp/server.py --transport http --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
LIVE = HARNESS / ".claude" / "skills"
INBOX = HARNESS / "hub" / "inbox"

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover
    print("fastmcp is required — install it: pip install fastmcp", file=sys.stderr)
    raise SystemExit(1)

sys.path.insert(0, str(HARNESS))  # in case the server is launched from a cwd other than the repo
from skill_foundry import dispatch  # noqa: E402

mcp = FastMCP("harness-mcp")


def _run(*argv: str) -> str:
    """Dispatch a verb in-process and return its combined stdout+stderr."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            dispatch.dispatch(argv[0], list(argv[1:]))
    except Exception as exc:  # pragma: no cover - defensive
        print(f"error: {exc}", file=buf)
    return buf.getvalue().rstrip()


@mcp.tool()
def skills_list(search: str = "", inbox: bool = False) -> str:
    """List/search skills. Set inbox=true for pending drafts only."""
    args = ["skills", "--json"]
    if inbox:
        args.append("--inbox")
    if search:
        args += ["--search", search]
    return _run(*args)


@mcp.tool()
def skills_load(name: str) -> str:
    """Return a skill's SKILL.md (published first, then inbox drafts)."""
    for base in (LIVE, INBOX):
        p = base / name / "SKILL.md"
        if p.exists():
            refs = [f.relative_to(p.parent).as_posix() for f in p.parent.rglob("*")
                    if f.is_file() and f.name != "SKILL.md"]
            body = p.read_text(encoding="utf-8")
            return f"{body}\n\n# references\n" + ("\n".join(f"- {r}" for r in refs) or "- (none)")
    return f"skill '{name}' not found"


@mcp.tool()
def capture_skill(name: str, description: str, body: str = "") -> str:
    """Draft a NEW skill into hub/inbox/<name>/SKILL.md (promote it later)."""
    return _run("capture-skill", name, "--description", description, "--body", body)


@mcp.tool()
def teach(wrong: str, correct: str, action: str) -> str:
    """Log a correction (a lesson about an existing skill) as a pending LRN entry."""
    return _run("teach", "--wrong", wrong, "--correct", correct, "--action", action)


@mcp.tool()
def promote(mode: str = "pr", skill_name: str = "") -> str:
    """Promote pending learnings (or a named skill draft) into skills.

    mode: 'pr' (default — branch + push + auto-create the PR; a human merges) |
          'propose' (diff, no write) | 'apply' (write locally).
    Give skill_name to promote that hub/inbox/ draft; otherwise promotes learnings.
    Review is mandatory: gates + built-in judge + LLM judge (SKILL_REVIEWER) run first,
    and nothing is applied unless it APPROVEs.
    """
    if mode not in ("propose", "apply", "pr"):
        return "error: mode must be propose | apply | pr"
    args = [f"--{mode}"]
    if skill_name:
        return _run("promote-skill", skill_name, *args)
    return _run("promote", *args)


if __name__ == "__main__":
    mcp.run()