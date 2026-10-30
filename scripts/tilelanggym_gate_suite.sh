#!/usr/bin/env bash
# Run tilelangGym pack gate from skill-foundry root (cwd-safe).
set -euo pipefail
SUITE="${1:?usage: tilelanggym_gate_suite.sh <sv567-1xg-clean|sv567-nx1-outer>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export TILELANGGYM_PACK="${TILELANGGYM_PACK:-$ROOT/demo/fixtures/tilelanggym-pack-ok}"
exec python3 -m skill_foundry.lib.tilelanggym_gate --suite "$SUITE" --pack "$TILELANGGYM_PACK"
