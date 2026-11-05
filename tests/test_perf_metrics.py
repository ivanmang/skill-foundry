#!/usr/bin/env python3
"""Unit tests for the CA metrics extractor (`skill_foundry/lib/perf_metrics.py`)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skill_foundry.lib.perf_metrics import _classify, duration_stats, parse_ca_dump


class PerfMetricsTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(_classify("RVECEX", "RV_VCVT_F32_F16"), ("ex", "ex_cast"))
        self.assertEqual(_classify("RVECEX", "RV_VCMAX"), ("ex", "ex_reduce"))
        self.assertEqual(_classify("MTE2", "COPY"), ("dma", "mte2"))
        self.assertEqual(_classify("SCALAR", "ANY"), ("scalar", "addr_loop"))

    def test_duration_stats_empty(self):
        self.assertEqual(
            duration_stats([]),
            {
                "cases": 0,
                "min": None,
                "p50": None,
                "p99": None,
                "max": None,
                "mean": None,
            },
        )

    def test_duration_stats(self):
        d = duration_stats(
            [{"duration_s": 1.0}, {"duration_s": 2.0}, {"duration_s": 3.0}]
        )
        self.assertEqual(d["cases"], 3)
        self.assertEqual(d["min"], 1.0)
        self.assertEqual(d["mean"], 2.0)
        self.assertEqual(d["p99"], 3.0)

    def test_parse_ca_dump(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "core0.veccore0.instr_log.dump"
            p.write_text(
                "[info] [10] (PC: 0x1000) RVECEX : (Binary: 0x1) (ID: 1) RV_VCVT_F32_F16\n"
                "[info] [20] (PC: 0x1001) RVECEX : (Binary: 0x1) (ID: 2) RV_VCMAX\n"
                "vf_real_execute_time: 100\n"
                "instr_num: 0x8\n",
                encoding="utf-8",
            )
            m = parse_ca_dump(p)
            self.assertIsNotNone(m)
            self.assertEqual(m["total_records"], 2)
            self.assertEqual(m["category_counts"].get("ex"), 2)
            self.assertEqual(m["timing"]["vf_real"], 100)
            self.assertEqual(m["timing"]["instr_num"], 8)


if __name__ == "__main__":
    unittest.main()
