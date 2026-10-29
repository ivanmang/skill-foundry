#!/usr/bin/env bash
# HTTPS reverse proxy (caddy) in front of the skill-foundry MCP server.
# REQUIRES sudo (installs caddy + binds 80/443). Run ON b10:
#
#   sudo bash mcp/tls-setup.sh [domain] [username]
set -euo pipefail

DOMAIN="${1:-pto-b10.ddns.net}"
AUTH_USER="${2:-team}"
UPSTREAM="127.0.0.1:8000"

if ! command -v caddy >/dev/null; then
  echo "→ installing caddy (apt)…"
  apt-get update -y
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

# generate a password hash if not provided
HASH="${MCP_AUTH_HASH:-}"
if [[ -z "$HASH" ]]; then
  read -rsp "password for '$AUTH_USER': " PW; echo
  HASH="$(caddy hash-password --plaintext "$PW")"
fi

cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    basicauth {
        $AUTH_USER $HASH
    }
    reverse_proxy $UPSTREAM
}
EOF

systemctl enable --now caddy
systemctl reload caddy
echo
echo "✓ caddy serving https://$DOMAIN → $UPSTREAM"
echo "  (ports 80/443 must be forwarded to b10; DDNS must resolve $DOMAIN)"
echo "  agent config: { \"mcpServers\": { \"skill-foundry\": { \"url\": \"https://$DOMAIN/mcp\" } } }"