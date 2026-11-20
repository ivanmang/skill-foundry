#!/usr/bin/env python3
"""LLM judge wrapper — read the payload on stdin, call opencode (cannbot), and
print only the assistant's final text. Usable as both IMPORT_REVIEWER and
SKILL_REVIEWER (the harness parses the verdict tokens from the output).

The optional positional arg is a review instruction prepended to the payload;
omit it when the payload already carries the instruction (IMPORT_REVIEWER).

Usage (machine-local; add to env.sh):
  export IMPORT_REVIEWER='python3 <repo>/scripts/import-reviewer.py'
  export SKILL_REVIEWER='python3 <repo>/scripts/import-reviewer.py "Strict skill
    reviewer. Reply exactly one word: APPROVE, HOLD, or REJECT."'
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

MODEL = os.environ.get("IMPORT_REVIEWER_MODEL", "cannbot/DeepSeek-V4-Pro")
MAX_ATTEMPTS = 4


def _judge(message: str) -> str:
    """One opencode call → the assistant's final text ('' if it emitted none)."""
    r = subprocess.run(
        ["opencode", "run", "--format", "json", "--model", MODEL, message],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "opencode judge failed")
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
    return "\n".join(parts).strip()


def main() -> int:
    instruction = " ".join(sys.argv[1:]).strip()
    payload = sys.stdin.read()
    if not payload.strip():
        return 2
    message = (instruction + "\n\n" + payload) if instruction else payload
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            time.sleep(1)
        try:
            out = _judge(message)
        except RuntimeError as exc:
            last_error = str(exc)
            continue
        if out:
            print(out)
            return 0
    print(last_error or "judge returned no verdict after retries", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
