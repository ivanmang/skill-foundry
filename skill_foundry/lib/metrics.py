#!/usr/bin/env python3
"""Product-loop telemetry — capture / promote / judge counters and calibration.

Operational telemetry (distinct from the *perf* metrics in `docs/metrics.md`).
Appended as JSONL to `.cache/metrics.jsonl` (gitignored — operational, not
shared knowledge). Each line is `{"ts": ..., "event": ..., "event_id": ...}`.

Events:
  capture        a correction was logged (teach / auto-capture)
  promote        learnings applied into a skill
  promote_skill  a draft skill was published
  judge          a promotion review verdict (approve | hold | reject)
  calibrate      a human's final call on a judge event (approve | reject)

Judge calibration: a `judge` event records `event_id`; a later `calibrate`
event links `ref=<event_id>` with the human outcome. Agreement = the fraction
of calibrated judges where `(verdict == approve) == (outcome == approve)`.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from skill_foundry.paths import ROOT  # noqa: E402

METRICS_FILE = ROOT / ".cache" / "metrics.jsonl"


def _ensure_dir() -> None:
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)


def record(event: str, **fields: Any) -> str | None:
    """Append one event. Returns its `event_id`, or None if the write failed."""
    _ensure_dir()
    event_id = str(fields.pop("event_id", "") or uuid.uuid4().hex[:12])
    line: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event": event,
        "event_id": event_id,
        **fields,
    }
    try:
        with METRICS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return event_id
    except Exception:
        return None


def events() -> list[dict[str, Any]]:
    """Read all recorded events (oldest first)."""
    if not METRICS_FILE.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in METRICS_FILE.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def summarize() -> dict[str, Any]:
    """Counts per event + judge verdict distribution + calibration agreement."""
    evs = events()
    counts: dict[str, int] = {}
    judge: dict[str, int] = {}
    judges: dict[str, str] = {}
    outcomes: list[tuple[str, str]] = []
    for e in evs:
        counts[e["event"]] = counts.get(e["event"], 0) + 1
        if e["event"] == "judge" and isinstance(e.get("verdict"), str):
            judge[e["verdict"]] = judge.get(e["verdict"], 0) + 1
            judges[str(e.get("event_id", ""))] = e["verdict"]
    for e in evs:
        if e["event"] == "calibrate":
            ref = str(e.get("ref", ""))
            verdict = judges.get(ref)
            outcome = e.get("outcome")
            if verdict and outcome in ("approve", "reject"):
                outcomes.append((verdict, outcome))
    agree = sum(1 for v, o in outcomes if (v == "approve") == (o == "approve"))
    return {
        "events": counts,
        "judge_verdicts": judge,
        "calibrated": len(outcomes),
        "judge_agreement_pct": round(agree / len(outcomes) * 100.0, 1)
        if outcomes
        else None,
    }
