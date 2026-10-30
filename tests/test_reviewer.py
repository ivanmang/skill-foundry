#!/usr/bin/env python3
"""Tests for the built-in deterministic promotion judge (reviewer)."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from skill_foundry.lib import reviewer


class BuiltinReviewTest(unittest.TestCase):
    def _review(self, added, target=""):
        # explicit empty skill universe so tests never depend on the real repo
        return reviewer.builtin_review(
            "", target_content=target, added_text=added,
            local_skills=set(), externals=set(),
        )

    def test_clean_addition_approves(self):
        v, rs = self._review("- add a reusable gotcha about buffer sizing")
        self.assertEqual(v, "approve")
        self.assertEqual(rs, [])

    def test_dangling_skill_reference_rejects(self):
        v, rs = self._review("see skill:totally-unknown-skill for the fix")
        self.assertEqual(v, "reject")
        self.assertTrue(any("totally-unknown-skill" in r for r in rs))

    def test_secret_rejects(self):
        v, rs = self._review("use token ghp_" + "A" * 24)
        self.assertEqual(v, "reject")
        self.assertTrue(any("secret" in r for r in rs))

    def test_placeholder_holds(self):
        v, rs = self._review("- TODO: verify this claim later")
        self.assertEqual(v, "hold")
        self.assertTrue(any("TODO" in r.upper() for r in rs))

    def test_contradiction_rejects(self):
        existing = "- never hardcode the device count in tiling expressions\n"
        added = "- hardcode the device count in tiling expressions\n"
        v, rs = self._review(added, target=existing)
        self.assertEqual(v, "reject")
        self.assertTrue(any("contradict" in r for r in rs))

    def test_near_duplicate_holds(self):
        existing = "- always set the device count from the platform api\n"
        added = "- always set the device count from the platform api\n"
        v, rs = self._review(added, target=existing)
        self.assertEqual(v, "hold")
        self.assertTrue(any("near-duplicate" in r for r in rs))


class ApproveIntegrationTest(unittest.TestCase):
    def test_reject_without_any_llm_reviewer(self):
        # no SKILL_REVIEWER, no TTY -> the builtin judge alone REJECTs
        saved = os.environ.get("SKILL_REVIEWER")
        os.environ.pop("SKILL_REVIEWER", None)
        try:
            self.assertFalse(reviewer.approve("+ see skill:totally-unknown-skill\n"))
        finally:
            if saved is not None:
                os.environ["SKILL_REVIEWER"] = saved

    def test_clean_diff_without_llm_fails_closed(self):
        # SKILL_REVIEWER is mandatory: even a clean diff must not auto-approve
        # when there is no LLM judge and no interactive terminal.
        saved = os.environ.get("SKILL_REVIEWER")
        os.environ.pop("SKILL_REVIEWER", None)
        try:
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                self.assertFalse(reviewer.approve("+ - add a useful gotcha about buffer sizing\n"))
        finally:
            if saved is not None:
                os.environ["SKILL_REVIEWER"] = saved


if __name__ == "__main__":
    unittest.main()