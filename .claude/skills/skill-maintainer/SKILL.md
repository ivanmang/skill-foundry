---
name: skill-maintainer
description: >
  Review regression results and user corrections, then propose or apply minimal,
  reviewable updates to the harness skills. Use when asked to update the skills,
  remember a correction, or review learnings/recent.md and promote reusable
  patterns.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git.
---

# Skill Maintainer

The learning loop. **Capture is automated; promotion is a reviewable,
git-tracked edit.** This skill never rewrites skills blindly.

## Scripts

| Action | Command |
|---|---|
| Log a correction (capture) | `./scripts/teach` (wizard) · `./scripts/teach "… → … → …"` (shorthand) · `./scripts/teach --edit` (editor) |
| Draft from a run (auto-capture) | `python3 scripts/session_digest.py --run reports/<id>/run.json [--apply]` |
| Propose promotion (diff, no write) | `python3 scripts/promote_recent.py --propose` |
| Apply promotion | `python3 scripts/promote_recent.py --apply [--branch feat/learnings-<date>]` |

## Modes

| Mode | Behavior | When |
|---|---|---|
| Propose | `promote_recent.py --propose` prints a diff, no file change | default |
| Apply (small) | `--apply` writes the edit, moves the entry to promoted.md | high-confidence, small change |
| Manual | User explicitly asks to update a skill | sensitive changes |

## Flow

1. **Capture** — whenever corrected, run `scripts/teach` (wizard, or
   `teach "…"` shorthand), or `session_digest.py` after a run. Never
   freeform-edit `learnings/recent.md`.
2. **Propose** — `promote_recent.py --propose` renders a minimal diff per
   pending entry into the right skill / known-failures file.
3. **Apply** — `--apply` writes it, marks the entry promoted, logs to
   `corrections.md`, and (with `--branch`) commits for a PR.
4. **Verify** — re-run a representative case to confirm the improvement.

## Auto-capture triggers

Log to `learnings/recent.md` via `scripts/teach` when any of these happen
(promotion stays reviewed). When the user says "remember …" or corrects you,
run it automatically and reply with the LRN id:

- The user corrects you ("no / wrong / actually / don't / remember …").
- A suite fails and the cause is reusable or repeats.
- Review flags a gap (missing check, wrong threshold, un-triaged failure).
- An external tool/API or command behaves unexpectedly.

## Promotion rules

- Promote only corrections that are reusable **or** occurred more than once.
- Never remove an existing check without strong evidence.
- Keep `description` frontmatter stable unless trigger conditions genuinely change.

## Gotchas

- No secrets / credentials / sensitive internal data inside skills.
- Small, reviewable diffs beat sweeping rewrites.