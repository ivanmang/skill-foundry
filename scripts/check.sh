#!/usr/bin/env bash
# Lightweight push gate — fast enough for a pre-push hook.
#   skill spec + reference integrity · catalog/index freshness · unit tests
# The full smoke (demo + tilelangGym gates) lives in `make check` / selfcheck.sh.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HARNESS"

echo "== skill spec + reference integrity =="
python3 -m skill_foundry.lib.validate_skills --strict

echo "== catalog + skills index fresh =="
./harness skills --check

echo "== unit tests =="
if [ -d tests ]; then
  python3 -m unittest discover -s tests -q
else
  echo "(no tests/ dir — skipping)"
fi

echo "push gate: OK"