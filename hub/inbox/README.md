# hub/inbox — pending skill drafts

Each subdirectory holds a **new skill draft** waiting to be promoted:

```text
hub/inbox/
└── my-skill/
    └── SKILL.md     # valid frontmatter (name/description) + instructions
```

Drafts are created with `./harness capture-skill <name>` and promoted into
`.claude/skills/` with `./harness promote-skill <name> --pr` (a human merges the
PR). Until promoted, they are visible in `./harness skills` (marked `draft`) but
not distributed as live skills.

Regression triage learnings use a separate path: `learnings/recent.md` (see
`./harness teach`).