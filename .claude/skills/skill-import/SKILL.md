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

Flags chain in order: `--scan --draft --validate --pr` runs the whole loop in
one go (stops at the first error). `--reject` and `--sync` stay standalone.

```text
1. register   ./harness import --add <name> --type <t> --path <loc> [--origin o] [--owner o]
2. relevance  ./harness import <name> --scan
3. draft      ./harness import <name> --draft      # reuses --scan verdicts; --rescan re-judges
4. drop       ./harness import <name> --reject <candidate> ...   # (optional) record rejected candidates
5. validate   ./harness import <name> --validate
6. publish    ./harness import <name> --pr        # (--apply for local-only)
7. discover   ./harness skills --refresh && ./harness selfcheck
8. refresh    ./harness import <name> --sync
```

Deregister with `./harness import --remove <name>` (registry entry only — it
leaves drafts, skills, and the manifest in place). `--list` prints the registry.

### 1. Register

- `knowledge-library` needs a mapping manifest. `--add` writes a stub at
  `config/imports/<name>.json` — edit its `skills` list (`name`, `category`,
  `entry`, `description`, `include`, `entry_file`) before scanning. `include`
  entries are directory (trailing `/`) / file / glob (`pathlib.glob` — use
  `**/*` to recurse); resolved files skip
  `.git`, `.gitignore`, `__pycache__`, `*.pyc`.
- `agent-skills` / `local-dir` need no manifest — discovery is one candidate per
  `<name>/SKILL.md` folder.

### 2. Scan (relevance)

Per candidate, in order: **completeness** (metadata/files present),
**self-containment** (no machine paths), **dedupe** against the published
corpus (Jaccard + description similarity — the authoritative owner of
`duplicate` / `extend`), and **scope** — judged semantically by
`IMPORT_REVIEWER` (`IN_SCOPE` / `OUT_OF_SCOPE`; one call also returns the
overall relevance word), with a lexical word-overlap fallback when no judge is
configured.

| verdict | meaning | action |
|---|---|---|
| `relevant` | in-scope, no meaningful overlap | draft it |
| `extend` | overlaps an existing skill (dedupe) | merge into it (`./harness teach`), don't fork |
| `duplicate` | already covered (dedupe) | skip |
| `irrelevant` | out of scope (`OUT_OF_SCOPE`) | skip |
| `hold` | self-containment, or the LLM disagreed with a deterministic `relevant` | a human decides |

The LLM relevance verdict is **advisory** — it escalates a deterministic
`relevant` to `hold` for human review, never silently overrides the dedupe.

### 3. Draft

Drafts only `relevant` candidates into `hub/inbox/<name>/` — a `references/`
snapshot for `knowledge-library`; a flat copy of the source folder for
`agent-skills`/`local-dir`. `--draft` is capture, so it does not hard-require
`IMPORT_REVIEWER` — it warns when the judge is absent. It **reuses the last
`--scan` verdicts** so the preview matches the draft; add `--rescan` to re-judge.
Re-running is idempotent (existing drafts and already-published skills are skipped).

### 4. Reject (optional)

`./harness import <name> --reject <candidate> [--undo]` records a human "skip
this one" decision in the manifest, so `--draft` and `--sync` keep skipping it
even though it looked `relevant`. `--undo` re-enables it. The decision survives
`--scan` / `--rescan` (a re-judge doesn't un-reject — you must `--undo`).

### 5. Validate

Runs the spec + repo-metadata gate on the produced drafts
(`validate_skills --strict`): `name` matches the folder, `description` present,
`category` / `origin` / `owner` set.

### 6. Publish

`--pr` runs the mechanical gates on every draft, then one `SKILL_REVIEWER`
review over the batch, copies drafts into `.claude/skills/`, commits on a
branch, and opens a PR a human merges. `--apply` is the local-only variant (no
commit). Non-interactive sessions fail closed without `SKILL_REVIEWER` — and
the command exits `1` when the reviewer doesn't approve. `--pr` leaves you on
the new `feat/import-<src>-<ts>` branch.

### 7. Discover

After promotion (or after any draft), refresh the catalog/index so
`./harness skills --check` stays green.

### 8. Sync

Re-fingerprints the source and diffs against the manifest —
`unchanged / changed / added / removed`. Changed *drafts* are refreshed
(snapshots re-copied, stale files removed, `SKILL.md` fingerprint updated). A
promoted skill's draft is consumed by promotion, so later drift reports
`changed (no draft)` rather than re-applying — update `.claude/skills/<name>/`
directly (or re-import under a new source). New candidates are reported, not
auto-drafted.

## Accelerator

```bash
./harness import --add skills-library --type knowledge-library --path ~/skills-library
./harness import skills-library --scan        # per-candidate verdict
./harness import skills-library --draft       # → hub/inbox/<name>/
./harness import skills-library --reject <candidate>   # (optional) record a drop
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
- `--reject` writes the decision into that manifest (not a separate file); it
  survives `--scan`/`--rescan` and is cleared only by `--reject <name> --undo`.
- `--remove` deregisters the registry entry only; it never deletes drafts,
  skills, or the manifest.
- `--pr` reads the actual `hub/inbox/` folders, not the manifest `action` field
  (which idempotent `--draft` re-runs overwrite).
- Don't route this workflow through other harness verbs; the publish gate is
  `promote-skill`'s, unchanged.

## Output

- `config/imports.json` + `config/imports/<source>.json` — the source registry.
- `hub/inbox/<name>/` — drafts awaiting promotion (a `references/` snapshot for
  `knowledge-library`; a flat copy of the source folder for `agent-skills`/`local-dir`).
- `hub/imports/<source>/manifest.json` — import record (fingerprints, verdicts, actions).
- `.claude/skills/<name>/` — the promoted skills (after the PR merges).
