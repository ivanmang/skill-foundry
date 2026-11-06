#!/usr/bin/env python3
"""`./harness metrics` — product-loop telemetry and judge calibration."""

from __future__ import annotations

import argparse
import sys

from skill_foundry.lib import metrics  # noqa: E402


def _render(s: dict) -> str:
    lines = ["product-loop telemetry:"]
    for ev, n in sorted(s["events"].items()):
        lines.append(f"  {ev:<14} {n}")
    jv = s["judge_verdicts"]
    if jv:
        total = sum(jv.values())
        lines.append("judge verdicts:")
        for v, n in sorted(jv.items()):
            lines.append(f"  {v:<8} {n} ({n / total * 100:.0f}%)")
    if s["calibrated"]:
        lines.append(
            f"judge agreement: {s['judge_agreement_pct']}% "
            f"({s['calibrated']} calibrated)"
        )
    else:
        lines.append("judge agreement: n/a (no calibrated verdicts yet)")
    if s.get("uncalibrated"):
        lines.append(
            f"uncalibrated verdicts: {s['uncalibrated']} "
            f"— list: ./harness metrics --pending"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Show product-loop telemetry and judge calibration."
    )
    ap.add_argument(
        "--calibrate",
        metavar="EVENT_ID",
        help="Record a human outcome for a judge event, then exit.",
    )
    ap.add_argument(
        "--outcome",
        choices=["approve", "reject"],
        help="Human outcome (requires --calibrate).",
    )
    ap.add_argument(
        "--pending",
        action="store_true",
        help="List uncalibrated judge events, then exit.",
    )
    args = ap.parse_args(argv)

    if args.calibrate:
        if not args.outcome:
            print("--calibrate requires --outcome approve|reject", file=sys.stderr)
            return 2
        metrics.record("calibrate", ref=args.calibrate, outcome=args.outcome)
        print(f"recorded {args.outcome} for judge event {args.calibrate}")
        return 0

    if args.pending:
        unc = metrics.uncalibrated()
        if not unc:
            print("no uncalibrated judge events.")
            return 0
        for j in unc:
            ctx = j.get("entries") or j.get("name") or ""
            print(f"  {j['event_id']}  {j.get('verdict', '?'):<8}  {j.get('ts', '')}  {ctx}")
        print(
            "\ncalibrate: ./harness metrics --calibrate <event_id> "
            "--outcome approve|reject"
        )
        return 0

    print(_render(metrics.summarize()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
