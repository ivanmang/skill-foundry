#!/usr/bin/env bash
# Deploy the skill-foundry MCP server on b10 (public gateway) with ecs as the
# compute host. Run ON b10:
#
#   bash mcp/deploy.sh              # from inside a checkout, or:
#   scp mcp/deploy.sh b10:~/ && ssh b10 'bash ~/deploy.sh'
set -euo pipefail

REPO_URL="git@gitcode.com:ivanmang/skill-foundry.git"
INSTALL_DIR="${1:-$HOME/skill-foundry}"
VENV="$INSTALL_DIR/.venv-mcp"
SYSTEMD_UNIT=/etc/systemd/system/skill-foundry-mcp.service
PORT="${PORT:-8000}"

say() { printf '\n  \033[1m%s\033[0m\n' "$*"; }

say "1/6 · prerequisites"
for c in git python3 ssh curl; do
  command -v "$c" >/dev/null || { echo "  ✗ missing $c — install it first" >&2; exit 1; }
done
echo "  ✓ git, python3, ssh, curl present"

say "2/6 · checkout"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "  ✓ $INSTALL_DIR exists — pulling latest"
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

say "3/6 · venv + deps"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -U pip
"$VENV/bin/pip" install -q -r "$INSTALL_DIR/mcp/requirements.txt"
echo "  ✓ installed fastmcp into $VENV"

say "4/6 · environment"
TOKEN="${GITCODE_TOKEN:-}"
if [[ -z "$TOKEN" && -t 0 ]]; then
  read -rsp "GITCODE_TOKEN (glpat-…; Enter to skip — auto-MR disabled): " TOKEN || true; echo
fi
CHOST="${MCP_COMPUTE_HOST:-ecs}"
CPATH="${MCP_COMPUTE_PATH:-~/skill-foundry}"
umask 077
{
  [[ -n "$TOKEN" ]] && echo "export GITCODE_TOKEN=\"$TOKEN\""
  echo "export MCP_COMPUTE_HOST=\"$CHOST\""
  echo "export MCP_COMPUTE_PATH=\"$CPATH\""
} > "$INSTALL_DIR/env.sh"
chmod 600 "$INSTALL_DIR/env.sh"
if [[ -z "$TOKEN" ]]; then
  echo "  ⚠ no GITCODE_TOKEN — discovery/capture/teach/run work; promote --pr (auto-MR) is disabled until you add it to $INSTALL_DIR/env.sh"
else
  echo "  ✓ wrote $INSTALL_DIR/env.sh (600, with GITCODE_TOKEN)"
fi

say "5/6 · launch"
if sudo -n true 2>/dev/null; then
  sudo tee "$SYSTEMD_UNIT" >/dev/null <<EOF
[Unit]
Description=skill-foundry MCP server (b10 gateway, ecs compute)
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/env.sh
ExecStart=$VENV/bin/fastmcp run mcp/server.py --transport http --host 127.0.0.1 --port $PORT
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now skill-foundry-mcp
  echo "  ✓ enabled skill-foundry-mcp on 127.0.0.1:$PORT"
else
  # no passwordless sudo: run as a nohup background process
  cd "$INSTALL_DIR"
  nohup "$VENV/bin/fastmcp" run mcp/server.py --transport http --host 127.0.0.1 --port "$PORT" \
    >> "$INSTALL_DIR/mcp.log" 2>&1 &
  echo $! > "$INSTALL_DIR/mcp.pid"
  echo "  ✓ launched via nohup (pid $(cat "$INSTALL_DIR/mcp.pid")); log: $INSTALL_DIR/mcp.log"
  echo "  (to make it a persistent service, run the systemd block from mcp/b10-deploy.md with your sudo password)"
fi

say "6/6 · verify"
sleep 2
if curl -fsS "http://127.0.0.1:$PORT/mcp" >/dev/null; then
  echo "  ✓ MCP endpoint responding"
else
  echo "  ✗ endpoint not responding — inspect: journalctl -u skill-foundry-mcp -n 50"
fi
echo
echo "  Next: reverse-proxy + auth/TLS (nginx/caddy) in front of 127.0.0.1:$PORT"
echo "  Agent config:"
echo '  { "mcpServers": { "skill-foundry": { "url": "https://pto-b10.ddns.net/mcp" } } }'
echo
echo "  Verify compute proxy:"
echo "    curl -H 'Authorization: Bearer <t>' https://pto-b10.ddns.net/mcp  (workflow_status tool)"