#!/usr/bin/env python3
"""Print tab-completion candidates (internal — used by completions/harness.bash)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402

TESTCASE_DIRS = {
    "cpu-st": "tests/cpu/st/testcase",
    "npu-sim-a3": "tests/npu/a2a3/src/st/testcase",
    "npu-hw-a3": "tests/npu/a2a3/src/st/testcase",
    "npu-sim-a5": "tests/npu/a5/src/st/testcase",
    "npu-hw-a5": "tests/npu/a5/src/st/testcase",
    "npu-sim-a6": "tests/npu/a6/src/st/testcase",
    "npu-hw-a6": "tests/npu/a6/src/st/testcase",
}


def suites() -> None:
    try:
        cfg = json.loads((HARNESS / "config" / "suites.json").read_text(encoding="utf-8"))
    except Exception:
        return
    for t in cfg.get("targets", {}).values():
        for s in t.get("suites", []):
            print(s.get("name", ""))


def arches() -> None:
    try:
        cfg = json.loads((HARNESS / "config" / "arches.json").read_text(encoding="utf-8"))
    except Exception:
        return
    for name in cfg:
        print(name)


def testcases(suite: str) -> None:
    repo = Path(os.environ.get("PTO_ISA_REPO", "~/pto-isa")).expanduser()
    rel = TESTCASE_DIRS.get(suite)
    d = repo / rel if rel else None
    if not d or not d.exists():
        return
    for p in sorted(d.iterdir()):
        if p.is_dir():
            print(p.name)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "suites":
        suites()
    elif cmd == "arches":
        arches()
    elif cmd == "testcases":
        testcases(args[1] if len(args) > 1 else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())