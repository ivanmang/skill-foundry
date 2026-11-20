#!/usr/bin/env python3
"""LLM judge wrapper — read the payload on stdin, call opencode (cannbot), and
print only the assistant's final text. Usable as both IMPORT_REVIEWER and
SKILL_REVIEWER (the harness parses the verdict tokens from the output).

Usage (machine-local; add to env.sh):
  export IMPORT_REVIEWER='python3 <repo>/scripts/import-reviewer.py'
  export SKILL_REVIEWER='python3 <repo>/scripts/import-reviewer.py'
"""

from __future__ import annotations

import json
import subprocess
import sys

MODEL = "cannbot/DeepSeek-V4-Flash"


def main() -> int:
    payload = sys.stdin.read()
    if not payload.strip():
        return 2
    r = subprocess.run(
        ["opencode", "run", "--format", "json", "--model", MODEL, payload],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r.returncode != 0:
        print(r.stderr or "opencode judge failed", file=sys.stderr)
        return 1
    parts = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "text":
            part = ev.get("part") or {}
            if part.get("type") == "text" and part.get("text"):
                parts.append(part["text"])
    print("\n".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
