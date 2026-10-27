#!/usr/bin/env bash
# Convenience alias — prefer `./harness run <args>`.
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$HARNESS_DIR/harness" run "$@"