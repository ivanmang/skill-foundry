# Vision

skill-foundry is a **skill-ops platform**: agents and humans capture reusable
knowledge as **Skills** during work, and it flows — through a promote step
(a reviewed `--pr` PR) — into a shared hub every teammate's agent can
discover and use.

Regression testing is the **first bundled workflow**, not the product. The
product is the loop:

```text
CAPTURE  (ambient, during any work)   agent corrects you → ./harness teach / capture-skill
CURATE   (reviewable)                  promote --propose → promote --pr (open a PR; a human merges)
HUB      (shared)                      git repo + hub/catalog.json + MCP server
CONSUME  (every teammate's agent)      discover via skills / MCP, load SKILL.md on demand
```

## What stays

- **Agent Skills** (`SKILL.md`) as the unit — open standard, interoperable.
- The **learning loop** (`teach → promote → PR`) — already proven by regression.
- The **automation boundary** — capture is automatic; promotion is automatic
  (`--pr` PR); the **merge is human-gated** (a human merges the PR).
- The **CLI** (`./harness`) and capability detection.

## What changes

- **Reframe** — from "regression harness" to "skill-foundry" (a skill-ops
  platform). Regression (`config/suites.json` targets + report/review/diff)
  becomes a bundled workflow, one domain among many.
- **Generalize capture** — knowledge can become a *learning* (`teach`) or a
  *new skill* (`capture-skill`), not just a regression triage note.
- **Add a hub** — `hub/catalog.json` + `./harness skills` for discovery.
- **Add hosting** — an MCP server (`mcp/server.py`) as the live interface, with git as
  the source of truth. Exposes `skills_list` / `skills_load` / `capture_skill` /
  `teach` / `promote` over stdio or HTTP. Hosting runbook: `mcp/b10-deploy.md`.

## The two kinds of capture

| Verb | Produces | Promoted into |
|---|---|---|
| `./harness teach "wrong → correct → action"` | a `LRN-…` entry in `learnings/recent.md` | `known-failures.md` or a skill's `## Gotchas` |
| `./harness capture-skill <name>` | a draft in `hub/inbox/<name>/SKILL.md` | `.claude/skills/<name>/` |

Both promote through the same `--pr` PR-gated path —
and only ever *add*; shared knowledge is never auto-removed or auto-changed.
