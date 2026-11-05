#!/usr/bin/env python3
"""Guard the `skills` CLI surface documented in README.md / dispatch.py.

Regressions here are easy (the verb was once rewritten and dropped
--install/--uninstall); these tests pin the user-facing flags.
"""

from __future__ import annotations

import argparse
import subprocess
import unittest

from skill_foundry.paths import ROOT
from skill_foundry.lib import install_skills, validate_skills


def _help_args() -> str:
    r = subprocess.run(
        ["python3", "-m", "skill_foundry.cli.skills", "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (r.stdout or "") + " " + (r.stderr or "")


class SkillsCliSurfaceTest(unittest.TestCase):
    def test_discovery_flags_present(self):
        help_text = _help_args()
        for flag in (
            "--search",
            "--category",
            "--origin",
            "--entry",
            "--inbox",
            "--check",
            "--json",
            "--dry-run",
            "--mine",
        ):
            self.assertIn(flag, help_text, f"missing {flag}")

    def test_install_uninstall_flags_present(self):
        # README.md + dispatch.py document these; they must stay implemented.
        help_text = _help_args()
        self.assertIn("--install", help_text)
        self.assertIn("--uninstall", help_text)


class InstallSelectionTest(unittest.TestCase):
    def _args(self, **kw):
        defaults = {
            "origin": None,
            "category": None,
            "entry": False,
            "name": None,
            "maturity": None,
            "owner": None,
        }
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_scope_core_selects_native_only(self):
        dirs = install_skills.select_dirs(self._args(origin="native"))
        self.assertTrue(dirs)
        for d in dirs:
            fm, _ = validate_skills.parse_frontmatter(
                (d / "SKILL.md").read_text(encoding="utf-8")
            )
            self.assertEqual((fm.get("origin") or "").strip(), "native")

    def test_entry_selects_entry_points_only(self):
        dirs = install_skills.select_dirs(self._args(entry=True))
        self.assertTrue(dirs)
        for d in dirs:
            fm, _ = validate_skills.parse_frontmatter(
                (d / "SKILL.md").read_text(encoding="utf-8")
            )
            self.assertEqual((fm.get("entry") or "").strip().lower(), "true")

    def test_name_selects_single_skill(self):
        dirs = install_skills.select_dirs(self._args(name=["pto-isa"]))
        self.assertEqual([d.name for d in dirs], ["pto-isa"])


if __name__ == "__main__":
    unittest.main()
