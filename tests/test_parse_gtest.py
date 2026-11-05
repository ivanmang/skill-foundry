#!/usr/bin/env python3
"""Unit tests for the canonical log parser (`skill_foundry/lib/parse_gtest.py`)."""

from __future__ import annotations

import unittest

from skill_foundry.lib.parse_gtest import parse_text


class ParseGtestTest(unittest.TestCase):
    def test_gtest_summary_counts(self):
        r = parse_text(
            "[  PASSED  ] 5 tests.\n[  FAILED  ] 2 tests, listed below:\n", "s"
        )
        self.assertEqual(r["summary"]["passed"], 5)
        self.assertEqual(r["summary"]["failed"], 2)
        self.assertEqual(r["summary"]["status"], "FAIL")

    def test_run_cpu_per_case_lines(self):
        r = parse_text("[PASS] tadd (0.12s)\n[FAIL] tsub (1.2s)\n", "cpu-st")
        cases = {c["name"]: c for c in r["cases"]}
        self.assertEqual(cases["tadd"]["status"], "PASS")
        self.assertAlmostEqual(cases["tadd"]["duration_s"], 0.12)
        self.assertEqual(cases["tsub"]["status"], "FAIL")
        self.assertEqual(r["summary"]["passed"], 1)
        self.assertEqual(r["summary"]["failed"], 1)

    def test_gtest_run_ok_state_machine(self):
        r = parse_text(
            "[ RUN      ] A.B\n[       OK ] A.B (1 ms)\n"
            "[ RUN      ] C.D\n[  FAILED  ] C.D (2 ms)\n",
            "g",
        )
        cases = {c["name"]: c for c in r["cases"]}
        self.assertEqual(cases["A.B"]["status"], "PASS")
        self.assertEqual(cases["C.D"]["status"], "FAIL")

    def test_simdsl_launch_duration(self):
        r = parse_text("PASS case0_foo compile=0.014s launch=72.536s\n", "dsl-st")
        self.assertEqual(len(r["cases"]), 1)
        self.assertEqual(r["cases"][0]["name"], "case0_foo")
        self.assertEqual(r["cases"][0]["status"], "PASS")
        self.assertAlmostEqual(r["cases"][0]["duration_s"], 72.536)

    def test_binary_crash_counts_failure(self):
        r = parse_text(
            "run binary failed: ./tadd died with <Signals.SIGSEGV>\n", "cpu-st"
        )
        self.assertEqual(r["summary"]["failed"], 1)
        self.assertEqual(r["cases"][0]["name"], "tadd")
        self.assertEqual(r["cases"][0]["status"], "FAIL")

    def test_unknown_when_no_signal(self):
        r = parse_text("some unrelated noise\n", "s")
        self.assertEqual(r["summary"]["status"], "UNKNOWN")
        self.assertEqual(r["summary"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
