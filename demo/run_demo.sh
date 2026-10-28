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

# Keep at most one demo-live run on disk (previous runs are gitignored anyway).
rm -rf "$HARNESS"/reports/demo-live-*

STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="demo-live-$STAMP"
RUN_DIR="$HARNESS/reports/$RUN_ID"
SANDBOX="$(mktemp -d /tmp/harness-demo.XXXXXX)"

DEMO_CONFIG="$HARNESS/demo/config/demo-suites.json"
DEMO_ARCHES="$HARNESS/demo/config/demo-arches.json"
BASELINE="$HARNESS/demo/baseline/demo-baseline.json"
KNOWN_BEFORE="$HARNESS/demo/fixtures/known-failures.before.md"

# Isolate the mock target as its own git repo (clean target_commit + dirty=false)
TARGET_REPO="$SANDBOX/target"
cp -R "$HARNESS/demo/mockrepo" "$TARGET_REPO"
git -C "$TARGET_REPO" init -q
git -C "$TARGET_REPO" -c user.name=demo -c user.email=demo@example.com add -A
git -C "$TARGET_REPO" -c user.name=demo -c user.email=demo@example.com commit -qm "chore: mock regression target"
export DEMO_REPO="$TARGET_REPO"

# Sandbox harness copy for the (non-destructive) learning loop
SB2="$SANDBOX/harness"
mkdir -p "$SB2/.claude/skills" "$SB2/learnings"
cp -R "$HARNESS/.claude/skills/pto-isa" "$SB2/.claude/skills/pto-isa"
cp "$KNOWN_BEFORE" "$SB2/.claude/skills/pto-isa/references/known-failures.md"
cp "$KNOWN_BEFORE" "$SB2/.claude/skills/pto-isa/references/known-failures.before.md"
cp "$HARNESS/learnings/recent.md" "$SB2/learnings/recent.md"
cp "$HARNESS/learnings/promoted.md" "$SB2/learnings/promoted.md"
cp "$HARNESS/learnings/corrections.md" "$SB2/learnings/corrections.md"

section() { printf '\n%s\n' "══════════════════════════════════════════════════════════════"; printf '  %s\n' "$*"; printf '%s\n' "──────────────────────────────────────────────────────────────"; }
pause() { if [[ "${PAUSE:-0}" == "1" ]]; then read -r -p "  ▶ Enter to continue..."; printf '\n'; fi; }

section "0 · What this is"
cat <<'EOF'
The harness turns "run the regression" from a repeated instruction into a
skill + scripts + a pinned baseline, and it gets BETTER each time you teach it
a correction. This demo shows both halves:
  1. USE it   — run → extract → report → review (all through shared drivers)
  2. IMPROVE it — auto-capture a correction → auto-propose a diff → apply → triage improves
EOF
pause

section "1 · USE — run the suite"
echo "  python3 scripts/run_suite.py --config demo/config/demo-suites.json \\"
echo "      --arches demo/config/demo-arches.json --target demo --all-suites --run-id $RUN_ID"
echo
python3 scripts/run_suite.py --config "$DEMO_CONFIG" --arches "$DEMO_ARCHES" \
  --target demo --all-suites --run-id "$RUN_ID" || true   # exit 1 is expected (mock suite fails on purpose)
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

section "4 · IMPROVE — auto-capture → auto-propose → apply"
echo "  (auto-capture) scripts/teach records the correction in strict format:"
./scripts/teach "device vcvt round-field mismatch in VecOpTest.case_vcvt_bf16fp16_128x128 -> known vcvt round-field pattern; annotate instead of re-triage -> promote vcvt round-field swap into known-failures" \
    --file "$SB2/learnings/recent.md"
echo
echo "  (auto-draft alternative) session_digest.py drafts pending entries from the run:"
python3 scripts/session_digest.py --run "$RUN_DIR/run.json" --file "$SB2/learnings/recent.md" || true
pause

echo "  (auto-propose) promote_recent.py turns the pending entry into a reviewable diff:"
python3 scripts/promote_recent.py --root "$SB2" --propose
pause

echo "  (apply) write the edit into the sandbox known-failures.md:"
python3 scripts/promote_recent.py --root "$SB2" --apply
echo
echo "  Mechanical effect — known-failure signatures go 0 → 1:"
printf '    before: %s known-failure signatures\n' "$(grep -Ec '^### .*vcvt' "$SB2/.claude/skills/pto-isa/references/known-failures.before.md" || true)"
printf '    after:  %s known-failure signatures\n' "$(grep -Ec '^### .*vcvt' "$SB2/.claude/skills/pto-isa/references/known-failures.md" || true)"
echo
echo "  learnings/ bookkeeping after apply (promoted + corrections):"
grep -F 'vcvt' "$SB2/learnings/promoted.md" || true
pause

echo "  Re-render the SAME run.json against the improved corpus:"
python3 scripts/build_report.py --run "$RUN_DIR/run.json" \
  --known "$SB2/.claude/skills/pto-isa/references/known-failures.md" --out "$RUN_DIR/report-known"
echo
echo "  Failure line AFTER learning (now annotated as known):"
grep -F 'VecOpTest.case_vcvt_bf16fp16_128x128' "$RUN_DIR/report-known.md" || true
pause

section "5 · Takeaway"
cat <<EOF
Run artifacts:  $RUN_DIR/run.json, report.md, report-known.md, demo-suite.log
Sandbox (loop): $SANDBOX

- USE:      run_suite.py → parse_gtest → build_report → diff_runs
- IMPROVE:  teach / session_digest.py (capture) →
            promote_recent.py --propose (draft diff) → --apply → annotated next report

The real targets (pto-isa, pto-vmi) use the same flow with config/suites.json.
EOF