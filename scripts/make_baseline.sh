#!/usr/bin/env bash
# Regenerate the pinned baseline from a fresh full run and stage it for commit.
#
# Run on the canonical machine (CPU-ST: clang++>=15/g++>=13; NPU-sim: CANN sim).
# The harness intentionally keeps ALL other report artifacts gitignored; only
# reports/baseline/baseline.json is committed.
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-pto-isa}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="baseline-${STAMP}"

echo "Regenerating pinned baseline for target '${TARGET}' (run ${RUN_ID})..."
python3 "$HARNESS_DIR/scripts/run_suite.py" --target "$TARGET" --all-suites --run-id "$RUN_ID"

SRC="$HARNESS_DIR/reports/$RUN_ID/run.json"
DST="$HARNESS_DIR/reports/baseline/baseline.json"

mkdir -p "$(dirname "$DST")"
cp "$SRC" "$DST"
echo "Wrote $DST"

cat <<EOF

Committed baseline points at $DST.

Review, then commit:
  git -C "$HARNESS_DIR" add reports/baseline/baseline.json
  git -C "$HARNESS_DIR" commit -m "chore: pin pto-isa regression baseline ($STAMP)"
EOF