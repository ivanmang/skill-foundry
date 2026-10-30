#!/usr/bin/env python3
"""Regression tests for validate_skills.check_references (reference integrity)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skill_foundry.lib import validate_skills as vs


def _skill(root: Path, name: str, body: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: d\ncategory: c\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return d


class CheckReferencesTest(unittest.TestCase):
    def _root(self) -> Path:
        root = Path(tempfile.mkdtemp())
        _skill(root, "foo", "see skill:bar, ../baz/SKILL.md and skills/qux/ref.md")
        _skill(root, "bar", "local leaf")
        return root

    def test_local_and_declared_external_resolve(self):
        root = self._root()
        self.assertEqual(vs.check_references(root, {"baz", "qux"}), [])

    def test_unknown_references_are_reported(self):
        root = self._root()
        errs = vs.check_references(root, set())
        self.assertEqual(len(errs), 2)
        self.assertTrue(any("'baz'" in e for e in errs))
        self.assertTrue(any("'qux'" in e for e in errs))

    def test_path_false_positives_are_ignored(self):
        root = Path(tempfile.mkdtemp())
        _skill(root, "foo", "reads vendor/cannbot-skills/ops/ and npu_skills/pto-as/x")
        self.assertEqual(vs.check_references(root, set()), [])


if __name__ == "__main__":
    unittest.main()