#!/usr/bin/env python3
"""Tests for the import engine (skill_foundry.lib.importer + the import CLI).

These pin the deterministic parts: registry CRUD, include resolution,
fingerprinting, knowledge-library discovery, relevance (completeness /
self-containment / dedupe), frontmatter injection, manifest round-trip, and the
CLI surface.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skill_foundry.lib import importer, reviewer
from skill_foundry.paths import ROOT


def _write(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _source(tmp: Path, files: list[str]) -> Path:
    root = tmp / "src"
    for f in files:
        _write(root / f, f"# {f}\n\nbody\n")
    return root


def _candidate(
    name: str = "alpha",
    description: str = "desc",
    category: str = "cat",
    files: list[str] | None = None,
    entry_file: str = "",
) -> importer.Candidate:
    return importer.Candidate(
        name=name,
        description=description,
        category=category,
        entry=(name == "entry"),
        files=files or [],
        entry_file=entry_file,
    )


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = self.tmp / "imports.json"
        self.cfg.write_text(json.dumps({"version": 1, "sources": {}}), encoding="utf-8")
        self.patch = mock.patch("skill_foundry.paths.IMPORTS_CONFIG", self.cfg)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_add_list_remove_roundtrip(self):
        src = importer.add_source(
            "demo", "agent-skills", "/tmp/x", origin="cannbot", owner="cannbot"
        )
        self.assertEqual(src.name, "demo")
        self.assertEqual(importer.source_from_registry("demo").type, "agent-skills")
        importer.remove_source("demo")
        self.assertIsNone(importer.source_from_registry("demo"))

    def test_add_rejects_bad_name(self):
        with self.assertRaises(ValueError):
            importer.add_source("Bad_Name", "agent-skills", "/tmp/x")

    def test_add_rejects_unknown_type_and_mode(self):
        with self.assertRaises(ValueError):
            importer.add_source("a", "bogus", "/tmp/x")
        with self.assertRaises(ValueError):
            importer.add_source("a", "agent-skills", "/tmp/x", mode="bogus")

    def test_add_rejects_unknown_origin_and_duplicate(self):
        importer.add_source("dup", "agent-skills", "/tmp/x")
        with self.assertRaises(ValueError):
            importer.add_source("dup", "agent-skills", "/tmp/x")
        with self.assertRaises(ValueError):
            importer.add_source("b", "agent-skills", "/tmp/x", origin="nope")

    def test_add_accepts_git_url(self):
        src = importer.add_source("r", "agent-skills", "https://example.com/x.git")
        self.assertEqual(src.location, "https://example.com/x.git")
        self.assertEqual(src.type, "agent-skills")

    def test_is_git_url(self):
        self.assertTrue(importer._is_git_url("https://example.com/x.git"))
        self.assertTrue(importer._is_git_url("git@github.com:a/b.git"))
        self.assertFalse(importer._is_git_url("/tmp/x"))
        self.assertFalse(importer._is_git_url("~/x"))


class ResolveIncludeTest(unittest.TestCase):
    def setUp(self):
        self.root = _source(Path(tempfile.mkdtemp()), ["a/a.md", "a/b.md", "top.md"])

    def test_directory_include_is_recursive(self):
        rels = importer.resolve_includes(self.root, ["a/"])
        self.assertEqual(sorted(rels), ["a/a.md", "a/b.md"])

    def test_file_include(self):
        self.assertEqual(importer.resolve_includes(self.root, ["top.md"]), ["top.md"])

    def test_glob_include(self):
        rels = importer.resolve_includes(self.root, ["a/*.md"])
        self.assertEqual(sorted(rels), ["a/a.md", "a/b.md"])

    def test_build_artifacts_are_skipped(self):
        _write(self.root / "a/__pycache__/x.pyc", "")
        _write(self.root / "a/.gitignore", "")
        rels = importer.resolve_includes(self.root, ["a/"])
        self.assertEqual(sorted(rels), ["a/a.md", "a/b.md"])

    def test_include_escaping_root_is_skipped(self):
        _write(self.root.parent / "outside.txt", "secret\n")
        rels = importer.resolve_includes(self.root, ["../outside.txt"])
        self.assertEqual(rels, [])

    def test_symlink_to_outside_is_skipped(self):
        outside = _write(self.root.parent / "secret.txt", "secret\n")
        (self.root / "link.txt").symlink_to(outside)
        rels = importer.resolve_includes(self.root, ["link.txt"])
        self.assertEqual(rels, [])


class FingerprintTest(unittest.TestCase):
    def setUp(self):
        self.root = _source(Path(tempfile.mkdtemp()), ["a.md"])

    def test_stable_for_same_content(self):
        a = importer.fingerprint_files(self.root, ["a.md"])
        b = importer.fingerprint_files(self.root, ["a.md"])
        self.assertEqual(a, b)

    def test_changes_when_content_changes(self):
        before = importer.fingerprint_files(self.root, ["a.md"])
        _write(self.root / "a.md", "# a\n\nbody changed\n")
        after = importer.fingerprint_files(self.root, ["a.md"])
        self.assertNotEqual(before, after)


class DiscoverTest(unittest.TestCase):
    def test_knowledge_library_discover_builds_candidates(self):
        root = _source(Path(tempfile.mkdtemp()), ["a/a.md", "b.md"])
        mapping = {
            "skills": [
                {
                    "name": "alpha",
                    "description": "d1",
                    "category": "c1",
                    "entry": True,
                    "include": ["a/"],
                    "entry_file": "a/a.md",
                },
                {
                    "name": "beta",
                    "description": "d2",
                    "category": "c2",
                    "include": ["b.md"],
                },
            ]
        }
        src = importer.SourceConfig(
            name="lib", type="knowledge-library", location=str(root)
        )
        with mock.patch.object(importer, "load_mapping", return_value=mapping):
            cands = importer.KnowledgeLibraryAdapter().discover(src)
        self.assertEqual([c.name for c in cands], ["alpha", "beta"])
        alpha = cands[0]
        self.assertEqual(alpha.files, ["a/a.md"])
        self.assertEqual(alpha.entry_file, "a/a.md")
        self.assertTrue(alpha.entry)
        self.assertEqual(len(alpha.fingerprint), 64)


class RelevanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = importer.SourceConfig(
            name="lib", type="knowledge-library", location=str(self.tmp / "src")
        )
        (self.tmp / "src").mkdir(parents=True)

    def test_missing_description_is_irrelevant(self):
        c = _candidate(description="")
        verdict, reasons = importer.relevance(c, self.src, [])
        self.assertEqual(verdict, importer.IRRELEVANT)
        self.assertTrue(any("description" in r for r in reasons))

    def test_zero_files_is_irrelevant(self):
        c = _candidate(files=[])
        verdict, _ = importer.relevance(c, self.src, [])
        self.assertEqual(verdict, importer.IRRELEVANT)

    def test_entry_file_not_in_files_is_irrelevant(self):
        _write(self.tmp / "src" / "x.md")
        c = _candidate(files=["x.md"], entry_file="missing.md")
        verdict, _ = importer.relevance(c, self.src, [])
        self.assertEqual(verdict, importer.IRRELEVANT)

    def test_machine_path_is_hold(self):
        _write(self.tmp / "src" / "x.md", "see /home/alice/secret\n")
        c = _candidate(files=["x.md"])
        verdict, reasons = importer.relevance(c, self.src, [])
        self.assertEqual(verdict, importer.HOLD)
        self.assertTrue(any("/home/" in r for r in reasons))

    def test_duplicate_and_extend(self):
        _write(self.tmp / "src" / "x.md")
        dup = _candidate(name="stage-model", files=["x.md"])
        existing = [{"name": "stage-model", "description": "build a staged model"}]
        self.assertEqual(
            importer.relevance(dup, self.src, existing)[0], importer.DUPLICATE
        )
        overlap = _candidate(name="cce-run", files=["x.md"])
        existing = [{"name": "npu-cce-run", "description": "run CCE bodies"}]
        self.assertEqual(
            importer.relevance(overlap, self.src, existing)[0], importer.EXTEND
        )

    def test_substring_name_is_not_exact_duplicate(self):
        c = _candidate(name="cce-run")
        name, score = importer.closest_existing(
            c, [{"name": "npu-cce-run", "description": "y"}]
        )
        self.assertEqual(name, "npu-cce-run")
        self.assertLess(score, 1.0)

    def test_scope_check_lexical_uncertain_without_overlap(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "cooking recipes for dinner\n")
        c = _candidate(name="recipe", files=["x.md"])
        status, reason = importer.scope_check(c, src)
        self.assertEqual(status, "uncertain")
        self.assertIn("scope", reason)

    def test_scope_check_lexical_in_scope_with_overlap(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "a tilelang simt kernel on ascend\n")
        c = _candidate(name="kernel", files=["x.md"])
        self.assertEqual(importer.scope_check(c, src)[0], "in_scope")

    def test_scope_check_skips_without_hint(self):
        _write(self.tmp / "src" / "x.md", "anything\n")
        c = _candidate(files=["x.md"])
        self.assertEqual(importer.scope_check(c, self.src), ("in_scope", ""))

    def test_llm_verdicts_one_call_out_of_scope(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "anything\n")
        c = _candidate(files=["x.md"])
        with mock.patch.dict(
            os.environ, {"IMPORT_REVIEWER": "echo OUT_OF_SCOPE IRRELEVANT"}
        ):
            scope, rel, used = importer.llm_verdicts(c, src, [])
        self.assertEqual(scope, "out_of_scope")
        self.assertEqual(rel, "irrelevant")
        self.assertTrue(used)

    def test_llm_verdicts_one_call_in_scope(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "anything\n")
        c = _candidate(files=["x.md"])
        with mock.patch.dict(os.environ, {"IMPORT_REVIEWER": "echo IN_SCOPE RELEVANT"}):
            scope, rel, used = importer.llm_verdicts(c, src, [])
        self.assertEqual(scope, "in_scope")
        self.assertEqual(rel, "relevant")
        self.assertTrue(used)

    def test_assess_semantic_out_of_scope_rejects(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "anything\n")
        c = _candidate(files=["x.md"])
        with mock.patch.dict(
            os.environ, {"IMPORT_REVIEWER": "echo OUT_OF_SCOPE RELEVANT"}
        ):
            verdict, reasons, rel, used = importer.assess(c, src, [])
        self.assertEqual(verdict, importer.IRRELEVANT)
        self.assertTrue(any("out of scope" in r for r in reasons))
        self.assertTrue(used)

    def test_assess_advisory_duplicate_on_relevant_is_hold(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "a tilelang kernel\n")
        c = _candidate(files=["x.md"])
        with mock.patch.object(
            importer, "llm_verdicts", return_value=("in_scope", "duplicate", True)
        ):
            verdict, reasons, rel, used = importer.assess(c, src, [])
        self.assertEqual(verdict, importer.HOLD)
        self.assertEqual(rel, "duplicate")
        self.assertTrue(any("human review" in r for r in reasons))

    def test_assess_advisory_relevant_does_not_override_extend(self):
        src = importer.SourceConfig(
            name="lib",
            type="knowledge-library",
            location=str(self.tmp / "src"),
            scope_hint="ascend tilelang simt performance",
        )
        _write(self.tmp / "src" / "x.md", "cce run body\n")
        c = _candidate(name="cce-run", files=["x.md"])
        with mock.patch.object(
            importer, "llm_verdicts", return_value=("in_scope", "relevant", True)
        ):
            verdict, _, _, _ = importer.assess(
                c, src, [{"name": "npu-cce-run", "description": "run cce bodies"}]
            )
        self.assertEqual(verdict, importer.EXTEND)


class FrontmatterTest(unittest.TestCase):
    def test_split(self):
        text = "---\nname: a\ndescription: d\n---\n\n# Body\n"
        fm, body = importer._split_skill_md(text)
        self.assertIn("name: a", fm)
        self.assertIn("# Body", body)

    def test_inject_adds_only_missing(self):
        text = "---\nname: a\ndescription: d\n---\n\n# Body\n"
        out = importer._inject_frontmatter(
            text, {"category": "c", "origin": "library", "name": "IGNORED"}
        )
        self.assertIn("category: c", out)
        self.assertIn("origin: library", out)
        self.assertNotIn("name: IGNORED", out)
        self.assertIn("# Body", out)

    def test_inject_builds_frontmatter_when_absent(self):
        out = importer._inject_frontmatter("# Just body\n", {"category": "c"})
        self.assertTrue(out.startswith("---\ncategory: c\n---"))
        self.assertIn("# Just body", out)


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patch = mock.patch.object(importer, "IMPORTS_HUB", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_roundtrip(self):
        results = [{"name": "alpha", "verdict": "relevant", "fingerprint": "abc"}]
        importer.write_manifest("lib", results)
        self.assertEqual(importer.read_manifest("lib")["candidates"], results)

    def test_read_missing_returns_none(self):
        self.assertIsNone(importer.read_manifest("nope"))


class ReviewerThreadingTest(unittest.TestCase):
    def test_builtin_review_resolves_batch_names(self):
        verdict, reasons = reviewer.builtin_review(
            "", added_text="see skill:peer for details", local_skills={"peer"}
        )
        self.assertEqual(verdict, "approve")
        self.assertEqual(reasons, [])


class CliSurfaceTest(unittest.TestCase):
    def test_import_verb_flags_present(self):
        r = subprocess.run(
            ["python3", "-m", "skill_foundry.cli.import_skills", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        help_text = (r.stdout or "") + " " + (r.stderr or "")
        for flag in (
            "--add",
            "--remove",
            "--list",
            "--scan",
            "--draft",
            "--validate",
            "--apply",
            "--pr",
            "--sync",
            "--json",
        ):
            self.assertIn(flag, help_text, f"missing {flag}")


if __name__ == "__main__":
    unittest.main()
