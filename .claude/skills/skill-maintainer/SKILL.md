---
name: skill-maintainer
description: >
  Review regression results and user corrections, then propose or apply minimal,
  reviewable updates to the skills: capture lessons as LRN entries and promote
  them (gated + LLM-reviewed) into the shared corpus. Use when asked to update
  the skills, remember a correction, or review learnings/recent.md and promote
  reusable patterns.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. Portable — the ./harness CLI is an optional accelerator, not a requirement.
category: regression
origin: native
---

# Skill Maintainer

The learning loop. **Capture is automatic; promotion is a gated, LLM-reviewed,
git-tracked edit.** This skill never rewrites skills blindly, and it works with
or without the harness.

## The loop (portable — no harness needed)

### 1. Capture — append a strict `LRN-…` entry

Whenever corrected, append an entry to `learnings/recent.md` in exactly this
format (id = `LRN-YYYYMMDD-NNN`):

```markdown
## LRN-20261027-003
- category: correction
- context: reports/<run-id>
- skill: pto-isa
- wrong: <what happened / what the current flow missed>
- correct: <what should happen instead>
- action: <which skill or known-failures file to update + proposed edit>
- status: pending
```

### 2. Propose — render a minimal diff

Decide the target file from `action`:
- mentions "known-failure(s)"/"triage corpus" → `.claude/skills/<skill>/references/known-failures.md`
- otherwise → the matching `.claude/skills/<skill>/SKILL.md`'s `## Gotchas`

Show the exact diff (add-only — never modify/remove an existing line).

### 3. Gate + review — before applying

- **Mechanical gates**: the diff must be **add-only** (no removed/modified lines),
  contain **no secrets**, and stay **small**.
- **LLM judge**: have a reviewer (an LLM, or the user) read the diff and reply
  APPROVE / HOLD / REJECT. Only APPROVE proceeds. In automation, point the judge
  at the diff via `SKILL_REVIEWER`.

### 4. Apply + publish — git-tracked

Mark the entry `status: promoted`, append a line to `learnings/promoted.md`,
commit on the current branch (or a `feat/learnings-<date>` branch), and
`git push`. For an MR: create it with **merge-when-pipeline-succeeds** so a
green CI gates run auto-merges it.

## Accelerator (optional — if skill-foundry is checked out)

The same loop as one command each (gates + LLM judge are built in):

```bash
./harness teach "wrong -> correct -> action"   # capture (wizard / shorthand / --edit)
./harness promote --propose                    # diff, no write
./harness promote --direct                     # gates → LLM APPROVE → push main
./harness promote --pr                         # gates → CI → auto-merge MR
./harness promote --no-review                  # skip the judge (gates still run)
./harness promote --force                      # bypass the gates
python3 -m skill_foundry.lib.session_digest --run reports/<id>/run.json --apply   # draft from a run
```

## Auto-capture triggers

Log an `LRN-…` entry (and reply with its id) when any of these happen:

- The user corrects you ("no / wrong / actually / don't / remember …").
- A suite fails and the cause is reusable or repeats.
- Review flags a gap (missing check, wrong threshold, un-triaged failure).
- An external tool/API or command behaves unexpectedly.

## Promotion rules

- Promote only corrections that are reusable **or** occurred more than once.
- Never remove an existing check without strong evidence.
- Keep `description` frontmatter stable unless trigger conditions genuinely change.
- No secrets / credentials / sensitive internal data inside skills.
- Small, reviewable diffs beat sweeping rewrites.

## Gotchas

- Reference external skills by name or skill: URI and declare them in the plugin external manifest (skills.json); inline the few essential facts (e.g. arch alias mapping) instead of relative sibling links. (was: Relative links to external cannbot-skills/TTK skills (e.g. ../npu-arch/SKILL.md, ../ttk-env-check/SKILL.md, skills/ascendc-whitebox-design/...) dangled because those skills are not vendored in this repo.) — `2026-10-30 skills audit`
- Keep category in YAML frontmatter (hub discovery depends on it) and run harness skills --refresh after adding or changing skills. (was: category: knowledge sat in the body (after closing ---) instead of frontmatter; 5 tilelanggym-* skills had no category; hub/catalog.json was stale.) — `2026-10-30 skills audit`
