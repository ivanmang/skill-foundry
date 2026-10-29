#!/usr/bin/env python3
"""harness-mcp — expose the skill-ops loop to any MCP-capable agent.

Tools:
  skills_list     list/search skills (published + drafts)
  skills_load     return a skill's SKILL.md (+ note where references live)
  capture_skill   draft a NEW skill into hub/inbox/
  teach           log a correction (a lesson about an existing skill)
  promote         direct | pr | propose | apply (learnings or a named skill draft)

The server wraps the same `./harness` CLI (subprocess) so behavior is identical
to the command line. The harness is ONLY the skill-ops loop; the bundled
regression workflow lives as directly-runnable scripts under
skill_foundry/workflow/ that the skills reference — not here.

Dependency:
  pip install fastmcp          # or: uv pip install fastmcp

Run (local / stdio):
  python mcp/server.py                          # stdio (attach to an agent directly)
  fastmcp run mcp/server.py                     # FastMCP CLI (stdio)

Run (hosted on b10, HTTP):
  fastmcp run mcp/server.py --transport http --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import subprocess
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

mcp = FastMCP("harness-mcp")


def _run(*argv: str, timeout: int = 3600) -> str:
    """Run `./harness <argv>` and return combined stdout+stderr."""
    try:
        r = subprocess.run(
            [str(HARNESS / "harness"), *argv],
            cwd=HARNESS, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"error: harness command timed out after {timeout}s: {' '.join(argv)}"
    out = (r.stdout or "").rstrip()
    if r.stderr:
        out = (out + "\n" + r.stderr.rstrip()) if out else r.stderr.rstrip()
    return out


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
def promote(mode: str = "direct", skill_name: str = "", force: bool = False) -> str:
    """Promote pending learnings (or a named skill draft) into skills.

    mode: 'direct' (default — commit + push to origin/main over SSH, no MR/token) |
          'pr' (branch + push + create the MR, auto-merge on green) |
          'review' (gates + LLM judge; applies only on APPROVE) |
          'propose' (diff, no write) | 'apply' (write locally).
    Give skill_name to promote that hub/inbox/ draft; otherwise promotes learnings.
    Set force=true to bypass the gates (add-only · secrets · spec).
    """
    if mode not in ("propose", "apply", "direct", "pr", "review"):
        return "error: mode must be propose | apply | direct | pr | review"
    args = [f"--{mode}"]
    if force:
        args.append("--force")
    if skill_name:
        return _run("promote-skill", skill_name, *args)
    return _run("promote", *args)


if __name__ == "__main__":
    mcp.run()