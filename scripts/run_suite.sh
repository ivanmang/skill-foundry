#!/usr/bin/env bash
# Thin wrapper over scripts/run_suite.py.
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$HARNESS_DIR/scripts/run_suite.py" "$@"