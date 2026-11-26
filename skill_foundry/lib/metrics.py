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
import os
import time
import uuid
from pathlib import Path
from typing import Any

from skill_foundry.paths import ROOT  # noqa: E402

# Overridable so tests/CI can redirect telemetry away from the real store
# (SKILL_FOUNDRY_METRICS=<path>). Defaults to the gitignored operational store.
METRICS_FILE = Path(
    os.environ.get("SKILL_FOUNDRY_METRICS") or ROOT / ".cache" / "metrics.jsonl"
)


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


def uncalibrated() -> list[dict[str, Any]]:
    """Judge events with no human `calibrate` outcome yet."""
    evs = events()
    calib = {str(e.get("ref")) for e in evs if e["event"] == "calibrate"}
    return [
        e
        for e in evs
        if e["event"] == "judge"
        and isinstance(e.get("verdict"), str)
        and str(e.get("event_id")) not in calib
    ]


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
        "uncalibrated": sum(
            1
            for e in evs
            if e["event"] == "judge"
            and str(e.get("event_id"))
            not in {str(c.get("ref")) for c in evs if c["event"] == "calibrate"}
        ),
        "judge_agreement_pct": (
            round(agree / len(outcomes) * 100.0, 1) if outcomes else None
        ),
    }


# ── Agent-agnostic skill telemetry ─────────────────────────────────────────
#
# These answer "which skills did the agent use / search for and miss" for ANY
# agent (pi / Claude Code / Cowork / any MCP client), because they are recorded
# at the two shared in-process boundaries rather than from a transcript:
#   - mcp/server.py::skills_load / skills_list   (any MCP-capable agent)
#   - skill_foundry.cli.skills (./harness skills --search — shell agents)
#
# They are deliberately NOT transcript-derived — transcript formats are
# agent-specific (pi's .jsonl is not Claude Code's or Cowork's).


def skill_load(skill: str, via: str = "mcp", found: bool = True) -> str | None:
    """Record a skill load (agent read a SKILL.md via the canonical channel).

    `found=False` marks a load-miss: the agent asked for a skill that does not
    exist — a direct missing-skill (gap) signal.
    """
    return record("skill.load", skill=skill, via=via, found=found)


def skill_search(query: str, via: str = "cli", hits: int | None = None) -> str | None:
    """Record a skill search; `hits == 0` is a missing-skill (gap) signal."""
    fields: dict[str, Any] = {"query": query, "via": via}
    if hits is not None:
        fields["hits"] = hits
    return record("skill.search", **fields)


# Attribution taxonomy for human interventions (why a task step needed a human).
# These are telemetry tags on `intervention` events — NOT fields on LRN entries,
# so the learnings format + promote logic stay untouched.
ATTRIBUTIONS = (
    "missing_skill",  # no skill covered this
    "wrong_skill",  # skill exists but wrong/outdated
    "not_followed",  # skill correct but agent skipped it
    "env_changed",  # tool/env/CANN/simulator changed
    "new_knowledge",  # nothing was wrong; genuinely new fact
)


def intervention(
    attribution: str,
    skill: str | None = None,
    note: str | None = None,
    lrn: str | None = None,
) -> str | None:
    """Record a human intervention with its attribution (why the step needed a human)."""
    if attribution not in ATTRIBUTIONS:
        return None
    fields: dict[str, Any] = {"attribution": attribution}
    if skill:
        fields["skill"] = skill
    if note:
        fields["note"] = note
    if lrn:
        fields["lrn"] = lrn
    return record("intervention", **fields)


def skill_health() -> dict[str, Any]:
    """Aggregate skill telemetry: loads, searches, interventions, daily trend."""
    evs = events()
    loads: dict[str, int] = {}
    load_misses: list[str] = []
    searches: dict[str, dict[str, Any]] = {}
    by_attribution: dict[str, int] = {}
    by_skill: dict[str, int] = {}
    trend: dict[str, dict[str, int]] = {}
    for e in evs:
        ev = e.get("event")
        ts = str(e.get("ts") or "")
        day = ts[:10] or "?"
        d = trend.setdefault(day, {})
        if ev == "skill.load":
            sk = str(e.get("skill") or "?")
            if e.get("found") is False:
                load_misses.append(sk)
            loads[sk] = loads.get(sk, 0) + 1
            d["loads"] = d.get("loads", 0) + 1
        elif ev == "skill.search":
            q = str(e.get("query") or "").strip()
            if q:
                cur = searches.setdefault(q, {"count": 0, "zero_hit": 0})
                cur["count"] += 1
                if e.get("hits") == 0:
                    cur["zero_hit"] += 1
            d["searches"] = d.get("searches", 0) + 1
        elif ev == "intervention":
            a = str(e.get("attribution") or "new_knowledge")
            sk = str(e.get("skill") or "?")
            by_attribution[a] = by_attribution.get(a, 0) + 1
            by_skill[sk] = by_skill.get(sk, 0) + 1
            d["interventions"] = d.get("interventions", 0) + 1
        elif ev == "capture":
            d["captures"] = d.get("captures", 0) + 1
        elif ev in ("promote", "promote_skill"):
            d["promotes"] = d.get("promotes", 0) + 1
    missing = [q for q, s in searches.items() if s["zero_hit"] > 0]
    return {
        "skill_loads": loads,
        "skill_load_misses": load_misses,
        "skill_searches": searches,
        "missing_skill_queries": missing,
        "interventions": {
            "total": sum(by_attribution.values()),
            "by_attribution": by_attribution,
            "by_skill": by_skill,
        },
        "trend": {"by_day": trend},
    }
