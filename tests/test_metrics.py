#!/usr/bin/env python3
"""Unit tests for product-loop telemetry + judge calibration (lib/metrics.py)."""

from __future__ import annotations

import json
import unittest

from skill_foundry.lib import metrics


class MetricsTest(unittest.TestCase):
    def _write(self, events: list[dict]) -> None:
        metrics.METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        metrics.METRICS_FILE.write_text(
            "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
        )

    def tearDown(self) -> None:
        metrics.METRICS_FILE.unlink(missing_ok=True)

    def test_summarize_agreement(self):
        self._write(
            [
                {"ts": "t", "event": "judge", "event_id": "a", "verdict": "approve"},
                {"ts": "t", "event": "judge", "event_id": "b", "verdict": "reject"},
                {"ts": "t", "event": "calibrate", "ref": "a", "outcome": "approve"},
                {"ts": "t", "event": "calibrate", "ref": "b", "outcome": "approve"},
            ]
        )
        s = metrics.summarize()
        # judge a: approve==approve → agree; judge b: reject vs approve → disagree
        self.assertEqual(s["calibrated"], 2)
        self.assertEqual(s["judge_agreement_pct"], 50.0)
        self.assertEqual(s["uncalibrated"], 0)

    def test_uncalibrated(self):
        self._write(
            [
                {"ts": "t", "event": "judge", "event_id": "a", "verdict": "approve"},
                {"ts": "t", "event": "judge", "event_id": "b", "verdict": "reject"},
                {"ts": "t", "event": "calibrate", "ref": "a", "outcome": "approve"},
            ]
        )
        self.assertEqual([e["event_id"] for e in metrics.uncalibrated()], ["b"])
        self.assertEqual(metrics.summarize()["uncalibrated"], 1)

    def test_agreement_none_when_no_calibration(self):
        self._write(
            [{"ts": "t", "event": "judge", "event_id": "a", "verdict": "approve"}]
        )
        s = metrics.summarize()
        self.assertIsNone(s["judge_agreement_pct"])
        self.assertEqual(s["uncalibrated"], 1)


if __name__ == "__main__":
    unittest.main()
