---
name: skill-import
description: >
  Integrate external skills and knowledge libraries into the skill-foundry corpus:
  register a source, scan it for relevance, convert relevant units into drafts, then
  validate and promote them through the gated, LLM-reviewed publish loop, with
  fingerprint-based drift sync. Use when bringing in skills from another repo, an
  agent skills directory, or a self-contained knowledge library.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git. The ./harness CLI is the tool under management.
category: repo-ops
origin: native
maturity: ready
owner: skill-foundry
---

# Skill Import

Bring external skills into the corpus through the harness's `import` verb. The
verb is the **front half of the capture loop**: it discovers candidates, checks
relevance, and produces drafts under `hub/inbox/`; the existing `promote-skill`
gate (spec + secrets + `SKILL_REVIEWER`) then publishes them unchanged.
Relevance is checked at import time; validity is checked by the publish gates.

## When to use

- a user points at an external repo / skills directory and asks to "integrate" or
  "import" it
- a knowledge library (no `SKILL.md` files) should become discoverable skills
- imported snapshots need a refresh after the source changed

Not for capturing a correction about an existing skill — that is
`skill:skill-maintainer`.

## Source taxonomy

A source is declared in `config/imports.json` with a `type` (adapter) and a
`mode` (how content moves).

| type | what the source looks like | mode default |
|---|---|---|
| `knowledge-library` | no `SKILL.md`; a mapping manifest groups leaves → skills | `vendor` |
| `agent-skills` | `<name>/SKILL.md` folders (Claude / Anthropic spec) | `vendor` |
| `local-dir` | an agent user skills dir (`~/.pi/skills/`, `~/.claude/skills/`) | `vendor` (or `reference`) |

| mode | behaviour |
|---|---|
| `vendor` | copy content into the draft; inject missing provenance frontmatter |
| `passthrough` | copy as-is (trust the source frontmatter) |
| `reference` | pointer stub only — content stays at the source location |

## Procedure

```text
1. register   ./harness import --add <name> --type <t> --path <loc> [--origin o] [--owner o]
2. relevance  ./harness import <name> --scan
3. draft      ./harness import <name> --draft
4. validate   ./harness import <name> --validate
5. publish    ./harness import <name> --pr        # (--apply for local-only)
6. discover   ./harness skills --refresh && ./harness selfcheck
7. refresh    ./harness import <name> --sync
```

### 1. Register

- `knowledge-library` needs a mapping manifest. `--add` writes a stub at
  `config/imports/<name>.json` — edit its `skills` list (`name`, `category`,
  `entry`, `description`, `include`, `entry_file`) before scanning. `include`
  entries are directory (trailing `/`) / file / glob; resolved files skip
  `.git`, `.gitignore`, `__pycache__`, `*.pyc`.
- `agent-skills` / `local-dir` need no manifest — discovery is one candidate per
  `<name>/SKILL.md` folder.

### 2. Scan (relevance)

Deterministic checks (completeness → self-containment → dedupe) plus an optional
LLM judge (`IMPORT_REVIEWER`, same stdin contract as `SKILL_REVIEWER`). Verdicts:

| verdict | meaning | action |
|---|---|---|
| `relevant` | in-scope, no meaningful overlap | draft it |
| `extend` | overlaps an existing skill | merge into it (`./harness teach`), don't fork |
| `duplicate` | already covered | skip |
| `irrelevant` | out of scope | skip |
| `hold` | self-containment / ambiguity | a human decides |

### 3. Draft

Drafts only `relevant` candidates into `hub/inbox/<name>/` (a `references/`
snapshot for libraries). `--draft` is capture, so it does not hard-require
`IMPORT_REVIEWER` — it warns when the judge is absent. Re-running is idempotent
(existing drafts are skipped).

### 4. Validate

Runs the spec + repo-metadata gate on the produced drafts
(`validate_skills --strict`): `name` matches the folder, `description` present,
`category` / `origin` / `owner` set.

### 5. Publish

`--pr` runs the mechanical gates on every draft, then one `SKILL_REVIEWER`
review over the batch, copies drafts into `.claude/skills/`, commits on a
branch, and opens a PR a human merges. `--apply` is the local-only variant (no
commit). Non-interactive sessions fail closed without `SKILL_REVIEWER`.

### 6. Discover

After promotion (or after any draft), refresh the catalog/index so
`./harness skills --check` stays green.

### 7. Sync

Re-fingerprints the source and diffs against the manifest —
`unchanged / changed / added / removed`. Changed drafts are refreshed (snapshots
re-copied, stale files removed, `SKILL.md` fingerprint updated). New candidates
are reported, not auto-drafted.

## Accelerator

```bash
./harness import --add skills-library --type knowledge-library --path ~/skills-library
./harness import skills-library --scan        # per-candidate verdict
./harness import skills-library --draft       # → hub/inbox/<name>/
./harness import skills-library --validate    # spec + metadata
./harness import skills-library --pr          # gated + SKILL_REVIEWER → PR
./harness import skills-library --sync        # drift refresh
```

## Gotchas

- `origin` must be one of `native|cannbot|local|library`; add a new value to
  `validate_skills.KNOWN_ORIGINS` (add-only) before promoting a source that
  needs one.
- `hub/imports/<source>/manifest.json` is a generated record, not a hand-edited
  file — `--scan` / `--draft` / `--sync` rewrite it.
- `--remove` deregisters the registry entry only; it never deletes drafts,
  skills, or the manifest.
- `--pr` reads the actual `hub/inbox/` folders, not the manifest `action` field
  (which idempotent `--draft` re-runs overwrite).
- Don't route this workflow through other harness verbs; the publish gate is
  `promote-skill`'s, unchanged.

## Output

- `config/imports.json` + `config/imports/<source>.json` — the source registry.
- `hub/inbox/<name>/` — drafts (SKILL.md + `references/` snapshots) awaiting promotion.
- `hub/imports/<source>/manifest.json` — import record (fingerprints, verdicts, actions).
- `.claude/skills/<name>/` — the promoted skills (after the PR merges).
