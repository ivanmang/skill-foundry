# Corrections Log

Append-only log of changes made to skills. Each entry: date, skill affected,
what changed, and why.

```markdown
## <date> — <skill-name>
- Context: <run-id or trigger>
- Wrong: <what the flow previously did>
- Correct: <what it should do now>
- Action: <precise edit applied>
- Promoted from: recent.md
```

## 2026-10-30 — skill-maintainer
- Promoted: LRN-20261030-001
- Action: Reference external skills by name or skill: URI and declare them in the plugin external manifest (skills.json); inline the few essential facts (e.g. arch alias mapping) instead of relative sibling links.

## 2026-10-30 — skill-maintainer
- Promoted: LRN-20261030-002
- Action: Keep category in YAML frontmatter (hub discovery depends on it) and run harness skills --refresh after adding or changing skills.
