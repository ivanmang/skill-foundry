---
name: skill-maintainer
description: >
  Review regression results and user corrections, then propose or apply minimal,
  reviewable updates to the harness skills. Use when asked to update the skills,
  remember a correction, or review learnings/recent.md and promote reusable
  patterns.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires git.
---

# Skill Maintainer

The learning loop. This harness does **not** auto-update; this skill makes
improvements deliberate, minimal, and git-tracked.

## Modes

| Mode | Behavior | When |
|---|---|---|
| Propose | Write a proposed edit + rationale, no file change | default for team harness |
| Apply (small) | Directly edit a skill for minor fixes | high-confidence, small change |
| Manual | User explicitly asks to update a skill | sensitive changes |

## Flow

1. Read `learnings/recent.md` and the latest run's review output.
2. Identify reusable patterns, missing checks, better steps, or outdated
   instructions.
3. **Propose** (default) a minimal edit:
   - prefer adding to an existing section (Gotchas / Checklists / Common
     Patterns) over rewriting a whole skill
   - never remove an existing check without strong evidence
4. On approval, apply and move the entry from `recent.md` to `promoted.md`.
5. Log the change in `learnings/corrections.md` with date, skill, and rationale.
6. Commit to git so the team benefits; use PRs for non-trivial changes.

## Correction log format

```markdown
## 2026-10-27 — review-inconsistencies
- Context: latency regression report for kernel A
- Wrong: only compared average latency
- Correct: also flag cases where p99 increased >15% even if average was stable
- Action: add p99 check to the inconsistency checklist
```

## Promotion rules

- Promote only corrections that are reusable **or** occurred more than once.
- Keep `description` frontmatter stable unless trigger conditions genuinely change.
- After updating a skill, re-run a representative case to verify the improvement.

## Gotchas

- No secrets / credentials / sensitive internal data inside skills.
- Small, reviewable diffs beat sweeping rewrites.
