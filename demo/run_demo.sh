#!/usr/bin/env bash
# Self-contained live demo of the regression harness.
#
# Runs the REAL harness scripts against a MOCK gtest runner, so it works on any
# machine (no CANN, no compiler requirements). Non-destructive: run artifacts go
# to the gitignored reports/ dir, the learning loop runs in a /tmp sandbox.
#
# Usage:
#   ./demo/run_demo.sh            # run straight through
#   PAUSE=1 ./demo/run_demo.sh    # pause between scenes (for presenting)
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HARNESS"

STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="demo-live-$STAMP"
RUN_DIR="$HARNESS/reports/$RUN_ID"
SANDBOX="$(mktemp -d /tmp/harness-demo.XXXXXX)"

# Isolate the mock target as its own git repo (clean target_commit + dirty=false)
TARGET_REPO="$SANDBOX/target"
cp -R "$HARNESS/demo/mockrepo" "$TARGET_REPO"
git -C "$TARGET_REPO" init -q
git -C "$TARGET_REPO" -c user.name=demo -c user.email=demo@example.com add -A
git -C "$TARGET_REPO" -c user.name=demo -c user.email=demo@example.com commit -qm "chore: mock regression target"
export DEMO_REPO="$TARGET_REPO"

DEMO_CONFIG="$HARNESS/demo/config/demo-suites.json"
DEMO_ARCHES="$HARNESS/demo/config/demo-arches.json"
BASELINE="$HARNESS/demo/baseline/demo-baseline.json"
KNOWN_BEFORE="$HARNESS/demo/fixtures/known-failures.before.md"

section() { printf '\n%s\n' "══════════════════════════════════════════════════════════════"; printf '  %s\n' "$*"; printf '%s\n' "──────────────────────────────────────────────────────────────"; }
pause() { if [[ "${PAUSE:-0}" == "1" ]]; then read -r -p "  ▶ Enter to continue..."; printf '\n'; fi; }

section "0 · What this is"
cat <<'EOF'
The harness turns "run the regression" from a repeated instruction into a
skill + scripts + a pinned baseline, and it gets BETTER each time you teach it
a correction. This demo shows both halves:
  1. USE it   — run → extract → report → review (all through shared drivers)
  2. IMPROVE it — log a correction, promote it, and watch triage improve
EOF
pause

section "1 · USE — run the suite"
echo "  ./scripts/run_suite.sh --config demo/config/demo-suites.json \\"
echo "      --arches demo/config/demo-arches.json --target demo --all-suites --run-id $RUN_ID"
echo
python3 scripts/run_suite.py --config "$DEMO_CONFIG" --arches "$DEMO_ARCHES" \
  --target demo --all-suites --run-id "$RUN_ID"
echo
echo "  ✔ produced $RUN_DIR/run.json  +  $RUN_DIR/demo-suite.log (normalized by extract-logs)"
pause

section "2 · USE — report (before learning)"
python3 scripts/build_report.py --run "$RUN_DIR/run.json" --out "$RUN_DIR/report"
echo
echo "  Failure as the harness sees it today (no triage knowledge):"
grep -F 'VecOpTest.case_vcvt_bf16fp16_128x128' "$RUN_DIR/report.md" || true
pause

section "3 · USE — review vs the pinned baseline"
python3 scripts/diff_runs.py --run "$RUN_DIR/run.json" --baseline "$BASELINE"
pause

section "4 · IMPROVE — the learning loop"
echo "  A human corrects the agent during triage:"
cat <<'EOF'
    "That vcvt round-field mismatch is a known failure, not a new bug.
     Promote it into the triage corpus so next time it's flagged automatically."
EOF
echo

# Simulate skill-maintainer: log the correction, then promote it.
mkdir -p "$SANDBOX"
cp "$KNOWN_BEFORE" "$SANDBOX/known-failures.before.md"
cp "$KNOWN_BEFORE" "$SANDBOX/known-failures.md"
cat >> "$SANDBOX/known-failures.md" <<'EOF'

### vcvt round-field swap (bf16->fp16)
- Symptoms: `device vcvt round-field mismatch`
- Cause: round-field semantics swapped in generated vcvt (round-to-nearest-even vs round-away)
- Fix: see pto-isa tools/ proof_vcvt_regression.sh + diff_vcvt_round.sh
EOF

echo "  learnings/recent.md entry the maintainer records:"
cat <<'EOF'
  ## <date> — pto-isa npu-sim
  - Context: VecOpTest.case_vcvt_bf16fp16_128x128 failed in review
  - Wrong: treated as a fresh regression
  - Correct: known vcvt round-field pattern -> annotate, don't re-triage
  - Action: promote 'vcvt round-field swap' into known-failures.md
EOF
echo
echo "  Promotion diff (this is the git-tracked improvement the team shares):"
diff -u "$SANDBOX/known-failures.before.md" "$SANDBOX/known-failures.md" || true
pause

echo "  Mechanical effect — signature known-count goes 0 → 1:"
printf '    before: %s known-failure signatures\n' "$(grep -Ec '^### .*vcvt' "$SANDBOX/known-failures.before.md" || true)"
printf '    after:  %s known-failure signatures\n' "$(grep -Ec '^### .*vcvt' "$SANDBOX/known-failures.md" || true)"
echo
echo "  Re-render the SAME run.json against the improved corpus:"
python3 scripts/build_report.py --run "$RUN_DIR/run.json" \
  --known "$SANDBOX/known-failures.md" --out "$RUN_DIR/report-known"
echo
echo "  Failure line AFTER learning (now annotated as known):"
grep -F 'VecOpTest.case_vcvt_bf16fp16_128x128' "$RUN_DIR/report-known.md" || true
pause

section "5 · Takeaway"
cat <<EOF
Run artifacts:  $RUN_DIR/run.json, report.md, report-known.md, demo-suite.log
Sandbox (loop): $SANDBOX

- USE:    ./scripts/run_suite.{sh,py} → parse_gtest → build_report → diff_runs
- IMPROVE: correction → learnings/recent.md → skill-maintainer promotes →
           known-failures.md (git diff) → next report annotates it automatically

The real pto-isa target uses the same flow with config/suites.json + arches.json.
EOF