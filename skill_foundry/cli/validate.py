#!/usr/bin/env python3
"""Validate the harness config files (suites.json / arches.json / cann.json).

Usage:
  ./harness validate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2]
CONFIG = HARNESS / "config"


def load(name: str) -> dict:
    p = CONFIG / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{name}: invalid JSON — {e}")


def main(argv: list[str] | None = None) -> int:
    errors: list[str] = []

    suites = load("suites.json")
    arches = load("arches.json")
    cann = load("cann.json")

    targets = suites.get("targets", {})
    if not isinstance(targets, dict) or not targets:
        errors.append("suites.json: 'targets' is empty or not an object")

    for target, cfg in targets.items():
        for i, s in enumerate(cfg.get("suites", [])):
            label = f"suites.json:{target}.suites[{i}]"
            if not s.get("name"):
                errors.append(f"{label}: missing 'name'")
            if not s.get("mode"):
                errors.append(f"{label}: missing 'mode'")
            if not isinstance(s.get("command"), list) or not s.get("command"):
                errors.append(f"{label}: 'command' must be a non-empty list")
            if not isinstance(s.get("timeout_s", 0), int):
                errors.append(f"{label}: 'timeout_s' must be an int")
            arch = s.get("arch")
            if arch and arch not in arches:
                errors.append(f"{label}: arch '{arch}' not in arches.json")

    for name, a in arches.items():
        if not isinstance(a, dict) or not a.get("soc"):
            errors.append(f"arches.json:{name}: missing 'soc'")

    if not isinstance(cann.get("soc_to_arch"), dict):
        errors.append("cann.json: 'soc_to_arch' must be an object")

    if errors:
        print("Config validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        return 1

    print(f"✓ config OK — {len(targets)} target(s), {len(arches)} arch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())