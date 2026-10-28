#!/usr/bin/env bash
# Regenerate the pinned baseline from a fresh full run and stage it for commit.
#
# Run on the canonical machine (CPU-ST: clang++>=15/g++>=13; NPU-sim: CANN sim).
# The harness intentionally keeps ALL other report artifacts gitignored; only
# reports/baseline/<target>.json is committed.
#
# Safety: refuses to pin a baseline if ANY suite did not PASS, unless --force.
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FORCE=0
TARGET="pto-isa"
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -*) echo "unknown flag: $arg" >&2; exit 2 ;;
    *) TARGET="$arg" ;;
  esac
done

STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="baseline-${STAMP}"

echo "Regenerating pinned baseline for target '${TARGET}' (run ${RUN_ID})..."
python3 "$HARNESS_DIR/scripts/run_suite.py" --target "$TARGET" --all-suites --run-id "$RUN_ID"

SRC="$HARNESS_DIR/reports/$RUN_ID/run.json"
DST="$HARNESS_DIR/reports/baseline/${TARGET}.json"

BAD_SUITES="$(python3 - "$SRC" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
bad = [s["name"] for s in data.get("suites", []) if s.get("status") != "PASS"]
print("\n".join(bad))
PY
)"

if [[ -n "$BAD_SUITES" ]]; then
  echo ""
  echo "ERROR: refusing to pin a baseline — these suites did not PASS:" >&2
  echo "$BAD_SUITES" | sed 's/^/  - /' >&2
  if [[ "$FORCE" != "1" ]]; then
    echo "Fix the failures, or re-run with --force to pin anyway." >&2
    exit 1
  fi
  echo "(--force given: pinning the failing baseline anyway.)" >&2
fi

mkdir -p "$(dirname "$DST")"
cp "$SRC" "$DST"
echo "Wrote $DST"

cat <<EOF

Committed baseline points at $DST.

Review, then commit:
  git -C "$HARNESS_DIR" add reports/baseline/${TARGET}.json
  git -C "$HARNESS_DIR" commit -m "chore: pin $TARGET regression baseline ($STAMP)"
EOF