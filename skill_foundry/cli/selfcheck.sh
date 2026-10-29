#!/usr/bin/env bash
# Self-check: compile-check the package and run the demo as a smoke test.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$HARNESS"

echo "== py_compile =="
python3 -m py_compile skill_foundry/cli/*.py skill_foundry/lib/*.py mcp/*.py

echo "== bash syntax =="
bash -n harness skill_foundry/workflow/baseline.sh skill_foundry/cli/selfcheck.sh demo/run_demo.sh completions/harness.bash

echo "== skill spec conformance =="
python3 -m skill_foundry.lib.validate_skills

echo "== demo smoke =="
rm -rf reports/demo-live-*
if ./demo/run_demo.sh >/dev/null 2>&1; then
  echo "demo: PASS"
else
  echo "demo: FAIL" >&2
  exit 1
fi

rm -rf reports/demo-live-*
echo "selfcheck: OK"