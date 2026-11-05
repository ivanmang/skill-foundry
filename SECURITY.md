# Security Policy

## Reporting a vulnerability

**Do not open a public issue.** Report privately to the maintainer
(`ivanmang`) — via email if you have it, or a private GitHub Security Advisory
(**Security → Report a vulnerability** on the repo).

Please include: a description, steps to reproduce, affected component
(harness / MCP server / a specific skill / CI workflows), and any suggested fix.
You'll get an acknowledgement, and a fix + disclosure once confirmed.

## Scope

- The harness CLI, `skill_foundry/` package, MCP server, and CI workflows.
- Credential handling (tokens, deploy keys) and the `promote` no-secrets gate.
- Anything that could let a promotion bypass the add-only / size / spec / LLM-judge gates.

## Out of scope

- The bundled skill corpus (`.claude/skills/`) is *content* — imported skills and
  illustrative examples; report issues against the relevant upstream instead.

## Credential hygiene

- Tokens (`GH_TOKEN`, `GITCODE_TOKEN`, `GITLAB_TOKEN`) and the mirror deploy key
  belong in the gitignored `env.sh` / GitHub Actions secrets — **never committed**.
- The `promote`/`promote-skill` no-secrets gate rejects committed credentials.
- The CI mirror uses a dedicated SSH deploy key (`GITCODE_DEPLOY_KEY`), never a
  personal account key.
