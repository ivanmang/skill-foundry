# Vision

The harness is a **skill-ops platform**: agents and humans capture reusable
knowledge as **Skills** during work, and it flows — through an MR-gated promote
step — into a shared hub every teammate's agent can discover and use.

Regression testing is the **first bundled workflow**, not the product. The
product is the loop:

```text
CAPTURE  (ambient, during any work)   agent corrects you → ./harness teach / capture-skill
CURATE   (MR-gated)                    promote --propose → promote --pr (apply + push + create MR)
HUB      (shared)                      git repo + hub/catalog.json + MCP server
CONSUME  (every teammate's agent)      discover via skills / MCP, load SKILL.md on demand
```

## What stays

- **Agent Skills** (`SKILL.md`) as the unit — open standard, interoperable.
- The **learning loop** (`teach → promote → MR`) — already proven by regression.
- The **automation boundary** — capture is automatic; promotion is automatic to
  the MR; the **merge is human-gated** (branch protection).
- The **CLI** (`./harness`) and capability detection.

## What changes

- **Reframe** — from "regression harness" to "skill-foundry" (a skill-ops
  platform). Regression (`config/suites.json` targets + report/review/diff)
  becomes a bundled workflow, one domain among many.
- **Generalize capture** — knowledge can become a *learning* (`teach`) or a
  *new skill* (`capture-skill`), not just a regression triage note.
- **Add a hub** — `hub/catalog.json` + `./harness skills` for discovery.
- **Add hosting** — an MCP server (`mcp/server.py`) as the live interface, with git as
  the source of truth. Exposes status / skills.list/search/load / capture / teach /
  promote / workflow.run over stdio or HTTP. Hosting runbook: `mcp/b10-deploy.md`.

## The two kinds of capture

| Verb | Produces | Promoted into |
|---|---|---|
| `./harness teach "wrong → correct → action"` | a `LRN-…` entry in `learnings/recent.md` | `known-failures.md` or a skill's `## Gotchas` |
| `./harness capture-skill <name>` | a draft in `hub/inbox/<name>/SKILL.md` | `.claude/skills/<name>/` |

Both promote through the same MR-gated path, so shared knowledge only changes
when a human merges.
