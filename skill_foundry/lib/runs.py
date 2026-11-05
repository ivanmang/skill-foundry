#!/usr/bin/env python3
"""Shared helpers for locating recent runs (internal)."""

from __future__ import annotations

import json
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import state  # noqa: E402


def runs_dir() -> Path:
    return HARNESS / "reports"


def iter_runs(reports: Path | None = None) -> list[tuple[Path, dict]]:
    d = reports or runs_dir()
    if not d.exists():
        return []
    runs: list[tuple[Path, dict]] = []
    for p in d.glob("*/run.json"):
        try:
            data = state.migrate_run(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
        if not isinstance(data, dict) or not data.get("run_id"):
            continue
        runs.append((p, data))
    runs.sort(
        key=lambda t: (t[1].get("generated_at") or "", t[0].stat().st_mtime),
        reverse=True,
    )
    return runs


def latest_run(reports: Path | None = None) -> tuple[Path, dict] | None:
    runs = iter_runs(reports)
    return runs[0] if runs else None
