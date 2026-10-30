#!/usr/bin/env python3
"""Guard the `skills` CLI surface documented in README.md / dispatch.py.

Regressions here are easy (the verb was once rewritten and dropped
--install/--uninstall); these tests pin the user-facing flags.
"""

from __future__ import annotations

import subprocess
import unittest

from skill_foundry.paths import ROOT


def _help_args() -> str:
    r = subprocess.run(
        ["python3", "-m", "skill_foundry.cli.skills", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    return (r.stdout or "") + " " + (r.stderr or "")


class SkillsCliSurfaceTest(unittest.TestCase):
    def test_discovery_flags_present(self):
        help_text = _help_args()
        for flag in ("--search", "--category", "--origin", "--entry", "--inbox", "--check", "--json"):
            self.assertIn(flag, help_text, f"missing {flag}")

    def test_install_uninstall_flags_present(self):
        # README.md + dispatch.py document these; they must stay implemented.
        help_text = _help_args()
        self.assertIn("--install", help_text)
        self.assertIn("--uninstall", help_text)


if __name__ == "__main__":
    unittest.main()