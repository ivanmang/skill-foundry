#!/usr/bin/env python3
"""Target registry — the shared source of truth for configured targets.

Each target lives in `config/suites.json` under `targets.<name>` and declares:
  label         human-readable name
  repo_env      env var pointing at the checkout (fallback repo_default)
  repo_default  default checkout path
  env_setup     shell setup run before each suite
  testcase_dirs per-suite testcase directory (for the guide's dropdowns)
  arches        optional per-target arches file (default config/arches.json)
  suites        the suite list

Scripts that need to be target-aware (guide/status/diagnose/onboarding/run_suite)
read from here instead of hardcoding a target name.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

CONFIG = HARNESS / "config" / "suites.json"
DEFAULT_ARCHES = HARNESS / "config" / "arches.json"
BASELINES_DIR = HARNESS / "reports" / "baseline"


def baseline_path(target_name: str) -> Path:
    """Per-target pinned baseline: reports/baseline/<target>.json."""
    return BASELINES_DIR / f"{target_name}.json"


def load_config(path: Path | None = None) -> dict:
    return json.loads((path or CONFIG).read_text(encoding="utf-8"))


def list_targets(cfg: dict | None = None) -> list[str]:
    cfg = cfg or load_config()
    return list(cfg.get("targets", {}).keys())


def get_target(name: str, cfg: dict | None = None) -> dict | None:
    cfg = cfg or load_config()
    return cfg.get("targets", {}).get(name)


def default_target(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    return cfg.get("default_target") or (
        list_targets(cfg)[0] if list_targets(cfg) else "pto-isa"
    )


def resolve_repo(target: dict) -> Path:
    env_name = target.get("repo_env") or "PTO_ISA_REPO"
    raw = os.environ.get(env_name) or target.get("repo_default") or "~/pto-isa"
    return Path(raw).expanduser().resolve()


def testcase_dirs(target: dict) -> dict:
    return target.get("testcase_dirs", {})


def target_arches_path(target: dict) -> Path:
    raw = target.get("arches")
    if raw:
        return (HARNESS / raw) if not Path(raw).is_absolute() else Path(raw)
    return DEFAULT_ARCHES


def load_arches(target: dict) -> dict:
    return load_config(target_arches_path(target))


def target_label(target: dict) -> str:
    return target.get("label") or target.get("name") or ""
