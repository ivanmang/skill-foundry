# Deploy harness-mcp on b10

b10 (`pto-b10.ddns.net:8022`) is the team's dashboard host — an always-on box
that already serves the vmi-dashboard. Hosting `harness-mcp` there gives every
teammate a single live endpoint for skills + workflows.

## 1. Get the repo + deps on b10

```bash
ssh b10
git clone git@gitcode.com:ivanmang/skill-foundry.git ~/skill-foundry
cd ~/skill-foundry
python3 -m venv .venv-mcp && source .venv-mcp/bin/activate
pip install -r mcp/requirements.txt
```

## 2. Configure the environment

```bash
cp env.example.sh env.sh
# edit: ASCEND_HOME_PATH (if b10 has CANN — usually NOT; see workflow note)
#       PTO_ISA_REPO / PTO_VMI_REPO (only if workflows run locally — usually NOT)

# the one secret that must live here, not on laptops:
export GITCODE_TOKEN="glpat-…"
```

## 3. Run the server (HTTP, for remote agents)

```bash
cd ~/skill-foundry
fastmcp run mcp/server.py --transport http --host 0.0.0.0 --port 8000
```

Verify: `curl http://127.0.0.1:8000/mcp` (and from a teammate's machine against
`http://pto-b10.ddns.net:<port>/mcp`, with the firewall allowing it).

For a long-running service:

```bash
# systemd unit /etc/systemd/system/harness-mcp.service
[Unit]
Description=harness-mcp
After=network.target
[Service]
User=ivanmang
WorkingDirectory=/home/ivanmang/skill-foundry
ExecStart=/home/ivanmang/skill-foundry/.venv-mcp/bin/fastmcp run mcp/server.py --transport http --host 0.0.0.0 --port 8000
Environment=GITCODE_TOKEN=glpat-…
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now harness-mcp
```

## 4. Point teammates' agents at it

Each agent's MCP config (e.g. Claude Desktop / Codex / Pi / Zed) adds:

```json
{
  "mcpServers": {
    "harness": { "url": "http://pto-b10.ddns.net:8000/mcp" }
  }
}
```

No clone, no `env.sh`, no token on the teammate's machine.

## 5. Security (REQUIRED)

- **Auth**: put the MCP server behind a reverse proxy (nginx/caddy) with a
  bearer token or mTLS. Do NOT expose the raw port to the internet.
- **Secrets**: `GITCODE_TOKEN` only in the b10 env file (`env.sh` is gitignored;
  systemd `Environment=` or an env file, never committed).
- **Network**: the sim host (ecs) is on a restricted network; b10 already SSHs
  to it for the daily dashboard refresh. Reuse that path for `workflow_run`.

## 6. workflow.run — b10 has no CANN

b10 is a dashboard box, not a compute box. So `workflow_run` on b10 should
**proxy to ecs**, not run locally. Two options:

1. Run the MCP server **on ecs** instead (ecs has CANN 9.1.0 + A5/A3 sims) and
   have b10 (or a reverse proxy) forward `/mcp` to it. This is the cleanest —
   then `workflow_run` executes where the toolchain is.
2. Keep the server on b10 and have it `ssh ecs './harness run …'` for
   `workflow_run` (add an `mcp/proxy.sh` wrapper if you take this route).

**Recommendation**: host the MCP server on **ecs** (it can run both skills and
workflows), and use b10 as the public reverse-proxy / TLS terminator in front of
it. That keeps compute next to the toolchain and b10 in its dashboard role.

## 7. Local (no server) alternative

Any agent can also attach directly over **stdio**:

```bash
python mcp/server.py          # or: fastmcp run mcp/server.py
```

```json
{ "mcpServers": { "harness": { "command": "python", "args": ["mcp/server.py"], "cwd": "/path/to/skill-foundry" } } }
```

This runs the server on the agent's machine (state-changing tools need the repo
+ env there).