# Deploy skill-foundry MCP on b10

b10 (`pto-b10.ddns.net`) is the public gateway. The MCP server lives on b10 and
exposes **only the skill-ops loop** (skills list/load, capture, teach, promote).
The bundled regression workflow is *not* in the harness — teammates run it on
their own machines via the thin scripts (see `.claude/skills/`). Skills /
learnings / git live in the b10 checkout; the MR-gate (`GITCODE_TOKEN`) is
centralized on b10.

## Topology

```text
agent (any machine) ── https://pto-b10.ddns.net/mcp ──▶ b10 (gateway)
                                                        │  mcp/server.py (FastMCP)
                                                        │  skill-foundry clone
                                                        │  GITCODE_TOKEN (auto-MR, --pr)
```

## Quick start (on b10)

```bash
scp mcp/deploy.sh b10:~/          # from your laptop
ssh b10
bash ~/deploy.sh                   # clone + venv + env.sh + systemd + verify
```

Or if you already have the checkout on b10:

```bash
ssh b10 'bash ~/skill-foundry/mcp/deploy.sh'
```

The script prompts for `GITCODE_TOKEN`. It writes `env.sh` (mode 600),
launches the server in the background via `nohup` (pid in `mcp.pid`, log in
`mcp.log`), and self-verifies. If b10 has passwordless sudo, it installs a
systemd unit instead (see [Persistence](#persistence)).

## Manual steps (what deploy.sh does)

```bash
git clone https://github.com/ivanmang/skill-foundry.git ~/skill-foundry
cd ~/skill-foundry
python3 -m venv .venv-mcp && source .venv-mcp/bin/activate
pip install -r mcp/requirements.txt

cat > env.sh <<'EOF'
export GITCODE_TOKEN="glpat-…"
EOF
chmod 600 env.sh

sudo tee /etc/systemd/system/skill-foundry-mcp.service >/dev/null <<'EOF'
[Unit]
Description=skill-foundry MCP server
After=network.target
[Service]
User=ivanmang
WorkingDirectory=/home/ivanmang/skill-foundry
EnvironmentFile=/home/ivanmang/skill-foundry/env.sh
ExecStart=/home/ivanmang/skill-foundry/.venv-mcp/bin/fastmcp run mcp/server.py --transport http --host 127.0.0.1 --port 8000
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && sudo systemctl enable --now skill-foundry-mcp
curl -fsS http://127.0.0.1:8000/mcp
```

## Security & HTTPS (REQUIRED)

Put a reverse proxy with **auth + TLS** in front — never expose `127.0.0.1:8000`.
Caddy is the simplest: it auto-provisions a Let's Encrypt cert.

```bash
sudo bash mcp/tls-setup.sh                    # installs caddy + writes the config
# prompts for the auth password; caddy hash-password generates the hash
```

The config (`mcp/Caddyfile`) does:

```caddyfile
pto-b10.ddns.net {
    basicauth { team <bcrypt-hash> }
    reverse_proxy 127.0.0.1:8000
}
```

Requires ports 80/443 forwarded to b10 and the DDNS record resolving. For a
bearer-token auth instead of basic auth, swap the `basicauth` block for a header
check. `GITCODE_TOKEN` stays in b10's `env.sh` (mode 600), never in laptops or
the repo.

## Persistence

Deployed without sudo via **cron `@reboot`** + `mcp/start.sh`:

```bash
# installed on b10:
@reboot sleep 15 && /home/ivanmang/skill-foundry/mcp/start.sh

# manual restart / logs:
bash ~/skill-foundry/mcp/start.sh
tail -f ~/skill-foundry/mcp.log
```

If you prefer systemd and have passwordless sudo, the unit is in the Manual
steps section; or run `sudo bash mcp/deploy.sh` (it auto-detects sudo).

## Teammates' agent config

```json
{
  "mcpServers": {
    "skill-foundry": { "url": "https://pto-b10.ddns.net/mcp" }
  }
}
```

(Add any auth header your proxy requires.)

## Tools (what they see)

| Tool | Where it runs | Notes |
|---|---|---|
| `skills_list` / `skills_load` | b10 local | discovery is live |
| `capture_skill` / `teach` / `promote` | b10 local | writes the b10 clone; `promote` defaults to `mode=direct` (SSH push to `main`, no token); `mode=pr` uses `GITCODE_TOKEN` → auto-MR |

## Ops

```bash
pgrep -f 'mcp/server[.]py'                  # is it running?
tail -f ~/skill-foundry/mcp.log              # logs
bash ~/skill-foundry/mcp/start.sh            # restart
crontab -l                                   # the @reboot entry
```

To update the server after a new release: `cd ~/skill-foundry && git pull` then
`bash mcp/start.sh`.