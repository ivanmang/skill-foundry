#!/usr/bin/env bash
# Self-check: compile-check the package, guard the portability copy, and run the
# demo as a smoke test.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$HARNESS"

echo "== py_compile =="
python3 -m py_compile skill_foundry/*.py skill_foundry/cli/*.py \
  skill_foundry/workflow/*.py skill_foundry/lib/*.py mcp/*.py

echo "== bash syntax =="
bash -n harness skill_foundry/workflow/baseline.sh skill_foundry/cli/selfcheck.sh \
  demo/run_demo.sh completions/harness.bash mcp/*.sh

echo "== skill spec conformance =="
python3 -m skill_foundry.lib.validate_skills

echo "== catalog + skills index fresh =="
./harness skills --check

echo "== unit tests (negative-path output below is expected; the line must end 'OK') =="
if [ -d tests ]; then python3 -m unittest discover -s tests -q 2>&1 | sed 's/^/  /'; fi

echo "== bundled parser in sync =="
diff -q skill_foundry/lib/parse_gtest.py .claude/skills/extract-logs/scripts/parse_gtest.py \
  || { echo "  ✗ extract-logs/scripts/parse_gtest.py drifted from lib/parse_gtest.py" >&2; exit 1; }

echo "== demo smoke =="
rm -rf reports/demo-live-*
if ./demo/run_demo.sh >/dev/null 2>&1; then
  echo "demo: PASS"
else
  echo "demo: FAIL" >&2
  exit 1
fi

rm -rf reports/demo-live-*

echo "== tilelangGym pack gate (fixture) =="
export TILELANGGYM_PACK="$HARNESS/demo/fixtures/tilelanggym-pack-ok"
bash "$HARNESS/scripts/tilelanggym_gate_suite.sh" sv567-1xg-clean
bash "$HARNESS/scripts/tilelanggym_gate_suite.sh" sv567-nx1-outer
python3 "$HARNESS/scripts/check_prc_index.py" --knowledge "$HARNESS/hub/tilelanggym/perf-review-knowledge"

echo "selfcheck: OK"
