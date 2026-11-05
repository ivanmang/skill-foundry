#!/usr/bin/env python3
"""Unit tests for the regression diff logic (`skill_foundry/workflow/review.py`)."""

from __future__ import annotations

import unittest

from skill_foundry.workflow.review import diff, pct, stats


def _record(suites: list[dict]) -> dict:
    return {"target": "t", "suites": suites}


def _suite(name: str, pairs: list[tuple]) -> dict:
    return {
        "name": name,
        "results": {"cases": [
            {"name": n, "status": s, "duration_s": d} for n, s, d in pairs
        ]},
    }


class ReviewTest(unittest.TestCase):
    def test_stats_p99_and_avg(self):
        s = stats([{"duration_s": float(i)} for i in range(1, 101)])
        self.assertEqual(s["n"], 100)
        self.assertEqual(s["p99"], 99.0)
        self.assertAlmostEqual(s["avg"], 50.5)

    def test_pct(self):
        self.assertEqual(pct(115, 100), 15.0)
        self.assertIsNone(pct(100, 0))
        self.assertIsNone(pct(None, 100))

    def test_pass_to_fail_regression(self):
        d = diff(
            _record([_suite("s", [("a", "FAIL", 1.0)])]),
            _record([_suite("s", [("a", "PASS", 1.0)])]),
        )
        self.assertEqual(d["regressions"], [{"suite": "s", "name": "a", "before": "PASS", "after": "FAIL"}])

    def test_fail_to_pass_fix(self):
        d = diff(
            _record([_suite("s", [("a", "PASS", 1.0)])]),
            _record([_suite("s", [("a", "FAIL", 1.0)])]),
        )
        self.assertEqual(d["fixes"], [{"suite": "s", "name": "a", "before": "FAIL", "after": "PASS"}])

    def test_p99_perf_flag_even_when_avg_stable(self):
        # p99 doubles (+100%) while avg is comparable — must still flag.
        new_pairs = [("a", "PASS", 1.0), ("b", "PASS", 2.0)] * 50
        base_pairs = [("a", "PASS", 0.5), ("b", "PASS", 1.0)] * 50
        d = diff(_record([_suite("s", new_pairs)]), _record([_suite("s", base_pairs)]))
        self.assertTrue(any(p["metric"] == "p99" for p in d["perf_flags"]))


if __name__ == "__main__":
    unittest.main()