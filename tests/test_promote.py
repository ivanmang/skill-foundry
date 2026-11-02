#!/usr/bin/env python3
"""Regression tests for promote.py plan accumulation.

Guards the same-target clobber fix: multiple pending learnings that resolve to
the same target file (or section) must compose, not overwrite each other.
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from skill_foundry.cli import promote


def _entry(eid: str, skill: str, wrong: str, action: str) -> dict:
    return {
        "id": eid,
        "category": "correction",
        "context": "test",
        "skill": skill,
        "wrong": wrong,
        "correct": action,
        "action": action,
        "status": "pending",
    }


def _make_root() -> Path:
    root = Path(tempfile.mkdtemp())
    sk = root / ".claude" / "skills" / "foo"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "---\nname: foo\ndescription: test\n---\n\n# Foo\n\n## Gotchas\n\n- keep me\n",
        encoding="utf-8",
    )
    return root


class PlanEntriesTest(unittest.TestCase):
    def test_same_target_accumulates_not_clobbers(self):
        root = _make_root()
        e1 = _entry("LRN-20990101-001", "foo", "wrong-1", "add bullet one")
        e2 = _entry("LRN-20990101-002", "foo", "wrong-2", "add bullet two")
        plan, skipped = promote.plan_entries(root, [e1, e2])

        self.assertEqual(skipped, [])
        self.assertEqual(len(plan), 1)
        target, old, new, entries = plan[0]
        self.assertEqual(target.name, "SKILL.md")
        self.assertEqual([e["action"] for e in entries], ["add bullet one", "add bullet two"])
        self.assertIn("add bullet one", new)
        self.assertIn("add bullet two", new)
        self.assertIn("keep me", new)  # original content preserved

    def test_unmapped_entry_is_skipped(self):
        root = _make_root()
        e = _entry("LRN-20990101-001", "does-not-exist", "w", "a")
        plan, skipped = promote.plan_entries(root, [e])
        self.assertEqual(plan, [])
        self.assertEqual([x["id"] for x in skipped], ["LRN-20990101-001"])

    def test_known_failures_target_appends_both(self):
        root = _make_root()
        kf = root / ".claude" / "skills" / "pto-isa" / "references" / "known-failures.md"
        kf.parent.mkdir(parents=True)
        kf.write_text("# Known failures\n\n- old entry\n", encoding="utf-8")
        e1 = _entry("LRN-20990101-001", "pto-isa", "known-failure: symptom 1", "fix 1")
        e2 = _entry("LRN-20990101-002", "pto-isa", "triage corpus: symptom 2", "fix 2")
        plan, skipped = promote.plan_entries(root, [e1, e2])
        self.assertEqual(skipped, [])
        self.assertEqual(len(plan), 1)
        _, old, new, _ = plan[0]
        self.assertIn("symptom 1", new)
        self.assertIn("symptom 2", new)
        self.assertIn("old entry", new)


class ApplyAllTest(unittest.TestCase):
    def test_two_entries_same_skill_both_present_on_disk(self):
        root = _make_root()
        e1 = _entry("LRN-20990101-001", "foo", "wrong-1", "add bullet one")
        e2 = _entry("LRN-20990101-002", "foo", "wrong-2", "add bullet two")

        lp = root / "learnings" / "recent.md"
        lp.parent.mkdir(parents=True)
        lp.write_text(promote.serialize_entries([e1, e2]), encoding="utf-8")
        entries = promote.parse_entries(lp.read_text(encoding="utf-8"))
        pending = [e for e in entries if e.get("status") == "pending"]

        rc = promote.apply_all(
            root, lp, entries, pending,
            branch=None, push=False, review=False,
        )

        self.assertEqual(rc, 0)
        final = (root / ".claude" / "skills" / "foo" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("add bullet one", final)
        self.assertIn("add bullet two", final)
        self.assertIn("keep me", final)
        self.assertTrue(all(e["status"] == "promoted" for e in entries))


class DedupeTest(unittest.TestCase):
    def _root(self):
        root = Path(tempfile.mkdtemp())
        sk = root / ".claude" / "skills" / "foo"
        sk.mkdir(parents=True)
        (sk / "SKILL.md").write_text(
            "---\nname: foo\ndescription: d\ncategory: c\n---\n\n# Foo\n\n## Gotchas\n\n- keep me\n",
            encoding="utf-8",
        )
        return root

    def _e(self, eid, action, wrong="w"):
        return {
            "id": eid, "category": "correction", "context": "t", "skill": "foo",
            "wrong": wrong, "correct": action, "action": action, "status": "pending",
        }

    def test_short_value_substring_is_not_treated_as_present(self):
        # "y" is a substring of "ready" in the frontmatter; it must NOT dedupe.
        root = self._root()
        active, skipped = promote.dedupe_pending([self._e("LRN-1", "y")], root)
        self.assertEqual(skipped, {})
        self.assertEqual([x["id"] for x in active], ["LRN-1"])

    def test_exact_existing_bullet_is_deduped(self):
        root = self._root()
        e = self._e("LRN-1", "dup action", wrong="dup wrong")
        target = root / ".claude" / "skills" / "foo" / "SKILL.md"
        line = [ln for ln in promote.build_snippet(e, target).splitlines() if ln.strip()][0]
        target.write_text(target.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")
        active, skipped = promote.dedupe_pending([e], root)
        self.assertEqual(active, [])
        self.assertEqual(skipped["LRN-1"], "already present in .claude/skills/foo/SKILL.md")


class PrTokenWarningTest(unittest.TestCase):
    def test_pr_without_gitcode_token_warns_but_proceeds(self):
        saved = (os.environ.get("GITCODE_TOKEN"), os.environ.get("GITLAB_TOKEN"))
        os.environ.pop("GITCODE_TOKEN", None)
        os.environ.pop("GITLAB_TOKEN", None)
        tmp = Path(tempfile.mkdtemp())
        try:
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = promote.main(["--pr", "--root", str(tmp)])
            self.assertEqual(rc, 0)  # no learnings file -> 0; the token is only a warning
            self.assertIn("GITCODE_TOKEN", buf.getvalue())
        finally:
            if saved[0] is not None:
                os.environ["GITCODE_TOKEN"] = saved[0]
            if saved[1] is not None:
                os.environ["GITLAB_TOKEN"] = saved[1]


class BuildMrBodyTest(unittest.TestCase):
    def test_what_always_present(self):
        self.assertEqual(promote.build_mr_body("did X"), "## What\ndid X")

    def test_optional_sections(self):
        body = promote.build_mr_body("did X", why="because Y", testing="ran Z", notes="- note")
        self.assertIn("## What\ndid X", body)
        self.assertIn("\n\n## Why\nbecause Y", body)
        self.assertIn("\n\n## Testing\nran Z", body)
        self.assertIn("\n\n## Notes\n- note", body)


if __name__ == "__main__":
    unittest.main()