#!/usr/bin/env python3
"""harness-mcp — expose the skill-ops platform to any MCP-capable agent.

Tools:
  status          one-glance dashboard (JSON)
  skills_list     list/search skills (published + drafts)
  skills_load     return a skill's SKILL.md (+ note where references live)
  capture_skill   draft a NEW skill into skills/inbox/
  teach           log a correction (a lesson about an existing skill)
  promote         propose / apply / pr (learnings or a named skill draft)
  workflow_run    run the bundled regression workflow (or --dry-run)

The server wraps the same `./harness` CLI (subprocess) so behavior is identical
to the command line. Read-only tools could run anywhere; state-changing tools
(capture/teach/promote/run) need a checkout of the repo on the host.

Dependency:
  pip install fastmcp          # or: uv pip install fastmcp

Run (local / stdio):
  python mcp/server.py                          # stdio (attach to an agent directly)
  fastmcp run mcp/server.py                     # FastMCP CLI (stdio)

Run (hosted on b10, HTTP):
  fastmcp run mcp/server.py --transport http --host 0.0.0.0 --port 8000
  # agents connect to  http://<b10>:8000/mcp  (SSE/streamable HTTP)
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
LIVE = HARNESS / ".claude" / "skills"
INBOX = HARNESS / "skills" / "inbox"

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover
    print("fastmcp is required — install it: pip install fastmcp", file=sys.stderr)
    raise SystemExit(1)

mcp = FastMCP("harness-mcp")

# Compute-host proxy: when set, workflow.run/status run over SSH on that host
# (e.g. b10 hosts the MCP server; ecs has the CANN toolchain + simulators).
COMPUTE_HOST = os.environ.get("MCP_COMPUTE_HOST", "")      # SSH alias, e.g. "ecs"
COMPUTE_PATH = os.environ.get("MCP_COMPUTE_PATH", "~/skill-foundry")


def _remote_run(*argv: str, timeout: int = 3600) -> str:
    """Run `./harness <argv>` on COMPUTE_HOST via SSH (skill-foundry checkout)."""
    if not COMPUTE_HOST:
        return "error: MCP_COMPUTE_HOST not set — no compute host configured"
    cmd = f"cd {shlex.quote(COMPUTE_PATH)} && source ./env.sh 2>/dev/null; ./harness {shlex.join(argv)}"
    try:
        r = subprocess.run(
            ["ssh", COMPUTE_HOST, cmd], capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"error: remote harness command timed out after {timeout}s: {' '.join(argv)}"
    except FileNotFoundError:
        return "error: ssh not found on this host"
    out = (r.stdout or "").rstrip()
    if r.stderr:
        out = (out + "\n" + r.stderr.rstrip()) if out else r.stderr.rstrip()
    return out


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
def status() -> str:
    """One-glance dashboard: env, per-target suites, baseline, learnings, last run."""
    return _run("status", "--json")


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
    """Draft a NEW skill into skills/inbox/<name>/SKILL.md (promote it later)."""
    return _run("capture-skill", name, "--description", description, "--body", body)


@mcp.tool()
def teach(wrong: str, correct: str, action: str) -> str:
    """Log a correction (a lesson about an existing skill) as a pending LRN entry."""
    return _run("teach", "--wrong", wrong, "--correct", correct, "--action", action)


@mcp.tool()
def promote(mode: str = "propose", skill_name: str = "") -> str:
    """Promote pending learnings (or a named skill draft) into skills.

    mode: 'propose' (diff, no write) | 'apply' (write locally) |
          'direct' (commit + push to origin/main over SSH, no MR/token) |
          'pr' (branch + push + create the MR, needs GITCODE_TOKEN/glab).
    Give skill_name to promote that skills/inbox/ draft; otherwise promotes learnings.
    """
    if mode not in ("propose", "apply", "direct", "pr"):
        return "error: mode must be propose | apply | direct | pr"
    if skill_name:
        return _run("promote-skill", skill_name, f"--{mode}")
    return _run("promote", f"--{mode}")


@mcp.tool()
def workflow_status() -> str:
    """Compute host's dashboard (env, suites, baseline, learnings, last run)."""
    if COMPUTE_HOST:
        return _remote_run("status", "--json")
    return _run("status", "--json")


@mcp.tool()
def workflow_run(target: str = "pto-isa", suite: str = "", all_suites: bool = False,
                 testcase: str = "", filter: str = "", dry_run: bool = False) -> str:
    """Run the bundled regression workflow on the compute host (or locally)."""
    args = ["run", "--target", target]
    if all_suites:
        args.append("--all-suites")
    elif suite:
        args += ["--suite", suite]
    if testcase:
        args += ["--testcase", testcase]
    if filter:
        args += ["--filter", filter]
    args.append("--dry-run" if dry_run else "--quiet")
    if COMPUTE_HOST:
        return _remote_run(*args)
    return _run(*args)


if __name__ == "__main__":
    mcp.run()