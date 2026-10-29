#!/usr/bin/env bash
# Start the skill-foundry MCP server in the background (no systemd needed).
# Used by @reboot cron and manual restarts. Idempotent — replaces any running
# instance via the pid file.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DIR/env.sh" 2>/dev/null || true
cd "$DIR"

# stop any existing instance (avoid 'can't register with selector' port clash)
if [[ -f "$DIR/mcp.pid" ]]; then
  kill "$(cat "$DIR/mcp.pid")" 2>/dev/null || true
  sleep 1
fi

nohup "$DIR/.venv-mcp/bin/fastmcp" run mcp/server.py \
  --transport http --host 127.0.0.1 --port "${MCP_PORT:-8000}" \
  >> "$DIR/mcp.log" 2>&1 &
echo $! > "$DIR/mcp.pid"
echo "started skill-foundry MCP (pid $(cat "$DIR/mcp.pid")) — log: $DIR/mcp.log"