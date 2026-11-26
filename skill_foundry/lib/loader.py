"""Load a skill's SKILL.md from the canonical sources (published → drafts).

Shared by the two agent-agnostic channels so they resolve a skill identically:
  - mcp/server.py::skills_load      (any MCP-capable agent)
  - skill_foundry.cli.skills::load_skill  (`./harness skills load <name>` — shell agents)

Returns (body, [reference filenames]) or None; callers attach their own telemetry
(`metrics.skill_load(via=...)`) so `via` stays correct per channel.
"""

from __future__ import annotations

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

LIVE = HARNESS / ".claude" / "skills"
INBOX = HARNESS / "hub" / "inbox"


def skill_body(name: str) -> tuple[str, list[str]] | None:
    """Return (body, [reference filenames]) for `name`, published first then drafts.

    Returns None when the skill exists in neither source.
    """
    for base in (LIVE, INBOX):
        p = base / name / "SKILL.md"
        if p.exists():
            refs = [
                f.relative_to(p.parent).as_posix()
                for f in p.parent.rglob("*")
                if f.is_file() and f.name != "SKILL.md"
            ]
            return p.read_text(encoding="utf-8", errors="replace"), refs
    return None


def render_loaded(body: str, refs: list[str]) -> str:
    """The canonical load payload (body + references section), shared by both channels."""
    ref_block = "\n".join(f"- {r}" for r in refs) or "- (none)"
    return f"{body.rstrip()}\n\n# references\n{ref_block}"