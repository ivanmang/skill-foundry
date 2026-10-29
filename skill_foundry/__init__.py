"""skill-foundry — skill-ops platform (CLI + bundled regression workflow).

Importing this package makes `skill_foundry` resolvable; `paths.py` is the
single source of truth for repo locations.
"""

from __future__ import annotations

from skill_foundry.paths import ROOT  # noqa: F401  (re-exported for convenience)

__version__ = "0.6.0"
