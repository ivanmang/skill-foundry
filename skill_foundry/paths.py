"""Single source of truth for repository paths.

Every module imports `ROOT` (or a derived constant) from here instead of
recomputing the repo root from `__file__`. This is the only place that knows
where the checkout lives.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG = ROOT / "config"
SKILLS = ROOT / ".claude" / "skills"
HUB = ROOT / "hub"
INBOX = HUB / "inbox"
LEARNINGS = ROOT / "learnings"
REPORTS = ROOT / "reports"
BASELINES = REPORTS / "baseline"
MCP = ROOT / "mcp"
DEMO = ROOT / "demo"
VERSION_FILE = ROOT / "VERSION"

CANN_CONFIG = CONFIG / "cann.json"
SUITES_CONFIG = CONFIG / "suites.json"
ARCHES_CONFIG = CONFIG / "arches.json"


def version() -> str:
    """Return the harness version from the VERSION file (falls back to 0.0.0)."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
