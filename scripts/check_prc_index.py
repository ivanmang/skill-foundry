#!/usr/bin/env python3
"""SoftLib / ST PRC checklist gate (skill-foundry tilelangGym).

Index is the Agent SoT: a broken link, orphan card, or status drift
silently drops a checkpoint while reports still claim "all ready cards
reviewed". These invariants must be machine-checked.

Usage:
  python3 scripts/check_prc_index.py
  python3 scripts/check_prc_index.py --knowledge hub/tilelanggym/perf-review-knowledge
"""
from __future__ import annotations

import argparse
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE = ROOT / "hub" / "tilelanggym" / "perf-review-knowledge"

ROW = re.compile(
    r"\|\s*(PRC-[A-Z]+-\d{3})\s*\|[^|]*\|[^|]*\|([^|]+)\|\s*(\w+)\s*\|"
)
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SUMMARY = re.compile(
    r"统计：(\d+)\s*条（ready\s+(\d+)\s*/\s*draft\s+(\d+)）。"
)
REQUIRED_SECTIONS = (
    "## 知识点",
    "## 错误写法",
    "## 正确写法",
    "## 识别方法",
    "## 证据要求",
    "## 参考",
)
VALID_ROW_STATUS = ("ready", "draft", "needs-measure")
VALID_INDEX_STATUS = ("ready", "pending")


def _knowledge() -> Path:
    return Path(os.environ.get("TILELANGGYM_PRC", str(DEFAULT_KNOWLEDGE))).expanduser().resolve()


# deferred import for env override
import os  # noqa: E402


def parse_rows(knowledge: Path):
    index = knowledge / "perf-review-checklist.md"
    text = index.read_text(encoding="utf-8")
    out = []
    for cid, cell, status in ROW.findall(text):
        m = LINK.search(cell.strip())
        if not m:
            raise AssertionError(f"{cid}: knowledge-file cell has no markdown link: {cell!r}")
        rel = m.group(1).strip()
        out.append((cid, rel, status))
    return out


class SoftLibPrcChecklist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.KNOWLEDGE = _knowledge()
        cls.INDEX = cls.KNOWLEDGE / "perf-review-checklist.md"

    def test_index_exists(self):
        self.assertTrue(self.INDEX.is_file(), f"missing index SoT: {self.INDEX}")

    def test_index_declares_valid_status(self):
        head = self.INDEX.read_text(encoding="utf-8")
        declared = re.search(r"^status:\s*(\S+)\s*$", head, re.M)
        self.assertIsNotNone(declared, "index missing `status:` header")
        self.assertIn(declared.group(1), VALID_INDEX_STATUS)

    def test_every_row_resolves_to_a_knowledge_file(self):
        for cid, rel, _ in parse_rows(self.KNOWLEDGE):
            path = (self.KNOWLEDGE / rel).resolve()
            self.assertTrue(path.is_file(), f"{cid} broken link: {rel} → {path}")
            self.assertTrue(
                str(path).startswith(str(self.KNOWLEDGE.resolve())),
                f"{cid} link escapes knowledge root: {rel}",
            )

    def test_no_orphan_knowledge_files(self):
        linked = {(self.KNOWLEDGE / rel).resolve() for _, rel, _ in parse_rows(self.KNOWLEDGE)}
        on_disk = {p.resolve() for p in self.KNOWLEDGE.rglob("PRC-*.md")}
        on_disk = {p for p in on_disk if p.name != "PRC_TEMPLATE.md"}
        orphans = on_disk - linked
        self.assertEqual(
            orphans,
            set(),
            "orphan PRC cards not in checklist (silent skip risk): "
            + ", ".join(sorted(str(p.relative_to(self.KNOWLEDGE)) for p in orphans)),
        )

    def test_id_and_status_agree_with_front_matter(self):
        for cid, rel, status in parse_rows(self.KNOWLEDGE):
            text = (self.KNOWLEDGE / rel).read_text(encoding="utf-8")
            fid = re.search(r"^id:\s*(\S+)", text, re.M)
            fstatus = re.search(r"^status:\s*(\S+)", text, re.M)
            self.assertIsNotNone(fid, f"{rel} missing front matter id")
            self.assertIsNotNone(fstatus, f"{rel} missing front matter status")
            self.assertEqual(fid.group(1), cid, f"{rel} id ≠ checklist")
            self.assertEqual(fstatus.group(1), status, f"{rel} status ≠ checklist")
            self.assertIn(status, VALID_ROW_STATUS, f"{cid} illegal status")

    def test_ids_are_unique(self):
        ids = [cid for cid, _, _ in parse_rows(self.KNOWLEDGE)]
        dupes = [cid for cid, n in Counter(ids).items() if n > 1]
        self.assertEqual(dupes, [], f"duplicate PRC ids: {dupes}")

    def test_summary_line_matches_counts(self):
        rows = parse_rows(self.KNOWLEDGE)
        ready = sum(1 for *_, s in rows if s == "ready")
        draft = sum(1 for *_, s in rows if s == "draft")
        text = self.INDEX.read_text(encoding="utf-8")
        m = SUMMARY.search(text)
        self.assertIsNotNone(m, "missing 统计：N 条（ready X / draft Y）。 line")
        self.assertEqual(int(m.group(1)), len(rows))
        self.assertEqual(int(m.group(2)), ready)
        self.assertEqual(int(m.group(3)), draft)

    def test_knowledge_files_carry_all_six_sections(self):
        for cid, rel, _ in parse_rows(self.KNOWLEDGE):
            text = (self.KNOWLEDGE / rel).read_text(encoding="utf-8")
            for section in REQUIRED_SECTIONS:
                self.assertIn(section, text, f"{cid} missing section {section}")

    def test_no_empty_category_dirs(self):
        empty = []
        for d in sorted(p for p in self.KNOWLEDGE.iterdir() if p.is_dir()):
            prc = list(d.glob("PRC-*.md"))
            if not prc:
                empty.append(d.name)
        self.assertEqual(empty, [], f"empty category dirs (remove until first card): {empty}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PRC checklist orphan/link gate")
    ap.add_argument("--knowledge", default=None, help="Override TILELANGGYM_PRC / default hub path")
    args = ap.parse_args(argv)
    if args.knowledge:
        os.environ["TILELANGGYM_PRC"] = args.knowledge
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SoftLibPrcChecklist)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
