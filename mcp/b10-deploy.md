# Deploy skill-foundry MCP on b10

b10 (`pto-b10.ddns.net`) is the public gateway; **ecs** (`115.175.35.144`) is the
compute host with CANN 9.1.0 + A5/A3 simulators. The MCP server lives on b10 and
SSHs to ecs for `workflow_run` / `workflow_status`. Skills/learnings/git live in
the b10 checkout; the MR-gate (`GITCODE_TOKEN`) is centralized on b10.

## Topology

```text
agent (any machine) ── https://pto-b10.ddns.net/mcp ──▶ b10 (gateway)
                                                        │  mcp/server.py (FastMCP)
                                                        │  skill-foundry clone
                                                        │  GITCODE_TOKEN (auto-MR)
                                                        └── ssh ecs ──▶ ./harness run/status
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

The script prompts for: `GITCODE_TOKEN`, compute-host SSH alias (default `ecs`),
compute checkout path (default `~/skill-foundry`). It writes `env.sh` (mode 600),
launches the server in the background via `nohup` (pid in `mcp.pid`, log in
`mcp.log`), and self-verifies. If b10 has passwordless sudo, it installs a
systemd unit instead (see [Persistence](#persistence)).

> On ecs, the checkout must be at `~/skill-foundry` (or set `MCP_COMPUTE_PATH`
> to where it actually is). And b10 must be able to `ssh ecs` non-interactively
> (same key the daily-refresh already uses).

## Manual steps (what deploy.sh does)

```bash
git clone git@gitcode.com:ivanmang/skill-foundry.git ~/skill-foundry
cd ~/skill-foundry
python3 -m venv .venv-mcp && source .venv-mcp/bin/activate
pip install -r mcp/requirements.txt

cat > env.sh <<'EOF'
export GITCODE_TOKEN="glpat-…"
export MCP_COMPUTE_HOST="ecs"
export MCP_COMPUTE_PATH="~/skill-foundry"
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
| `status` | b10 local | hub state: skills, learnings, catalog, git |
| `skills_list` / `skills_load` | b10 local | discovery is live |
| `capture_skill` / `teach` / `promote` | b10 local | writes the b10 clone; `promote --pr` uses `GITCODE_TOKEN` → auto-MR |
| `workflow_status` | **ecs** | the compute host's env/suites/baseline/last-run |
| `workflow_run` | **ecs** | runs the regression workflow where the toolchain is |

## Ops

```bash
pgrep -f 'mcp/server[.]py'                  # is it running?
tail -f ~/skill-foundry/mcp.log              # logs
bash ~/skill-foundry/mcp/start.sh            # restart
crontab -l                                   # the @reboot entry
```

To update the server after a new release: `cd ~/skill-foundry && git pull` then
`bash mcp/start.sh`.