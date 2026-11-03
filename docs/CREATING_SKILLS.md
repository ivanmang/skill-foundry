# Creating Skills — A Guide for New Users

This is the step-by-step guide for adding a **new** skill to skill-foundry.
It assumes you've cloned the repo and know the two loops at a high level. If
not, read [USER_JOURNEY.md](USER_JOURNEY.md) first.

**The one-sentence version:** every new skill goes
**author → propose → gate → `--pr` → refresh → selfcheck**, and the only
write to the shared corpus is a human-merged MR.

---

## Fast path — let your agent write it (recommended)

Most users never type a `SKILL.md` by hand: they describe the skill in plain
language, and their LLM agent authors it, fills the frontmatter, runs the
checks, and opens the MR. It's the same pipeline — the only difference is who
drafts the file. Your job reduces to **reviewing the diff and merging**.

```text
You (plain language to your agent):
  "Create a skill opt-verify: it runs a reference on the golden cases, diffs the
   kernel output against it, and fails on any mismatch > 1e-6. Tell me the exact
   command and where results are written."

Agent (deterministic steps, then you verify):
  1. ./harness skills --search verify              # dedupe — extend, don't fork
  2. write hub/inbox/opt-verify/SKILL.md            # full file, ALL frontmatter fields
      (name = folder · description = what+when · category · origin · owner · maturity)
  3. ./harness promote-skill --propose opt-verify   # optional: preview the copy
  4. ./harness promote-skill --pr opt-verify        # gates + LLM judge + MR
  5. ./harness skills --refresh && ./harness selfcheck

You:
  - review the MR diff
  - merge
```

The agent may skip `capture-skill` and author the file directly (it's just
Markdown) — `promote-skill` picks up any draft from `hub/inbox/`. That's cleaner
than the `capture-skill` path, which is for humans typing interactively and
leaves the frontmatter minimal. Sections §2–§6 below are the *reference* these
steps rest on — read them only when a draft needs correcting.

**What "done" means for the agent** (all machine-checkable):
- frontmatter complete — `name` matches the folder, `description` states what + when
- `category` / `origin` / `owner` / `maturity` set
- no dangling `skill:` refs · no secrets · no TODO/FIXME placeholders
- `promote-skill` gates pass (spec + no-secrets + review)
- after promotion: `validate_skills` clean + `selfcheck` green

---

## 0. Before you start — is this a *new* skill?

Decide which loop you're in. This decides the command.

| You want to… | Use | Command |
|---|---|---|
| Add a **new** skill (new domain/capability) | the *draft* path | `./harness capture-skill …` → `./harness promote-skill --pr` |
| Add knowledge to an **existing** skill (a gotcha, known failure, threshold) | the *learning* loop | `./harness teach …` → `./harness promote --pr` |
| Bring in a skill from **another repo** | vendor + index | copy/symlink its folder into `.claude/skills/` (e.g. `npx skills add`) → `./harness skills --refresh` |

This guide covers the first row (a new skill). The learning loop is
[USER_JOURNEY.md](USER_JOURNEY.md) §7. `config/externals.json` is *not* an
import path — it only declares external names so cross-skill references resolve.

> Before creating, check it doesn't already exist:
> `./harness skills --search <topic>`. Extend an existing skill instead of
> forking one.

---

## 1. What a skill actually is

A skill is a folder containing a `SKILL.md`, optionally with bundled files:

```text
my-skill/
├── SKILL.md          ← required: frontmatter + instructions
├── references/       ← optional: extra docs the skill reads
├── scripts/          ← optional: executable helpers
└── assets/           ← optional: templates, fixtures
```

Skills live canonically in `.claude/skills/`. (`.agents/skills/` symlinks to the
same place, so Pi and open-standard agents see them too.)

---

## 2. Draft the skill

```bash
./harness capture-skill my-skill \
  --description "What it does. Use when <trigger>."
```

- `--description` sets the routing text (what + when); if omitted, it's prompted for.
- `--body "…"` provides the instructions directly; if omitted, your `$EDITOR` opens for the body (in an interactive session).
- `--dry-run` prints the `SKILL.md` instead of writing.

This writes a **draft** into `hub/inbox/my-skill/SKILL.md` — nothing lands in
`.claude/skills/` yet. If you prefer to hand-write, you can create the folder in
`.claude/skills/` directly.

> **Heads-up:** `capture-skill` writes only a *minimal* frontmatter — `name`,
> `description`, `license`, and `metadata.status: draft`. Add `category`,
> `origin`, `owner`, and `maturity` yourself (below) before promoting, or the
> skill won't surface in category/owner discovery.

### The frontmatter

Fill every field. Use an existing native skill (e.g.
`.claude/skills/run-testcase/SKILL.md`) as a template.

```markdown
---
name: my-skill                 # MUST match the folder name (see rules below)
description: >
  <what the skill does>. Use when <trigger / routing condition>.
license: CANN Open Software License Agreement Version 2.0
compatibility: Requires python3 and git.
category: regression           # REQUIRED for hub discovery
origin: native                 # native | cannbot | local
maturity: ready                # ready | draft | deprecated
owner: skill-foundry           # or your team
---

# My Skill
```

### Frontmatter rules (enforced by `validate_skills.py`)

| Field | Required? | Rule |
|---|---|---|
| `name` | ✅ | lowercase-hyphen, `[a-z0-9-]` only, ≤64 chars, **no leading / trailing / consecutive hyphens**, **must match the folder name** |
| `description` | ✅ | ≤1024 chars; state **what it does** *and* **when to use it** (this is how the model routes to it) |
| `license` | optional | name or bundled license file |
| `compatibility` | optional | ≤500 chars |
| `category` | ⚠️ required by hub | optional per spec, but **missing = a warning and the skill won't surface in category discovery** |
| `origin` / `owner` / `maturity` | recommended | drives `--origin/--owner/--maturity` filters + catalog |
| `entry` | optional | `true` marks an entry-point skill (surfaced first in discovery) |
| `disable-model-invocation` | optional | `true` = only loadable via `/skill:name` |

---

## 3. Write the instructions body

Follow the house pattern — **portable first, accelerator second**, so the skill
works even outside this repo:

1. **`# <Title>`** — one line.
2. **`## Portable procedure`** — the real commands, env, and rules the skill
   teaches. Assume the reader has no skill-foundry checkout. Reference bundled
   files by relative path (`references/…`, `scripts/…`).
3. **`## Accelerator (optional — if skill-foundry is checked out)`** — the
   one-liner(s) that collapse the procedure (`python3 -m skill_foundry.…`).
4. **`## Gotchas`** — add-only bullets for tripwires and known failures.
   *(This is also the section `promote` appends to during the learning loop.)*
5. **`## Output`** — what the skill produces.

**Cross-references must resolve.** If you reference another skill, use a
`skill:<name>` URI, `../<name>/SKILL.md`, or `skills/<name>/` — and the name
must exist locally *or* be declared in `config/externals.json`. Unknown names
fail validation:

```markdown
See `skill:pto-isa` for the env and suite matrix.
```

---

## 4. Propose and validate (no write yet)

```bash
./harness promote-skill --propose my-skill   # preview: lists what would be copied — writes nothing
```

`--propose` shows which files will be copied (and that the draft gets removed),
but not the full diff — open `hub/inbox/my-skill/SKILL.md` to review the content.

You don't need a separate validation step for the draft: **`promote-skill`
re-runs the spec + no-secrets + review gates on the draft** (§5) before it
writes anything. Choose `--apply` for a local-only promote, or `--pr` to commit
+ open the MR.

After the skill is promoted (now in `.claude/skills/`), validate the *published*
corpus — this also checks cross-skill reference integrity, which needs the full
skill set present:

```bash
python3 -m skill_foundry.lib.validate_skills   # spec + reference integrity (published skills)
./harness selfcheck                            # + compile + index freshness + demo smoke
```

The spec checks are: `SKILL.md` present · valid frontmatter · `name` matches the
folder · name/description lengths + character rules · `category` present
(warning only) · every cross-skill reference resolves to a local skill or a
declared external (`config/externals.json`).

---

## 5. Publish — gated, LLM-reviewed, human-merged

```bash
./harness promote-skill --pr my-skill
```

`--pr` = copy into `.claude/skills/` + remove the draft + commit on a
`feat/skill-<name>-<date>` branch + push + **open an MR**. Before anything is
written, the harness runs the gates and the review:

| Gate | What it checks |
|---|---|
| spec | `validate_skill()` — valid frontmatter (name matches folder, description present, length caps) |
| no-secrets | token / private-key pattern scan |
| review — built-in judge | dangling cross-skill refs · secrets · TODO/FIXME placeholders · contradiction vs existing checks |
| review — LLM judge | `SKILL_REVIEWER` must reply `APPROVE`; without it you approve interactively, and non-interactive sessions **fail closed** |

(The add-only / size-cap gates belong to the *learning* loop, which edits an
existing skill line-by-line; copying a brand-new skill is already add-only.)

A **human merges the MR** after CI is green — that is the final, deliberate step.
For local-only iteration (no push), use `./harness promote-skill --apply`.

> **Recommended:** set `export GITCODE_TOKEN=<token>` (or `GITLAB_TOKEN`) in
> `env.sh` so `--pr` can auto-create the MR via the gitcode v5 API. Without it,
> the agent pushes the branch and prints a manual PR-new URL.

---

## 6. Index, verify, and make it discoverable

```bash
./harness skills --refresh     # regenerate hub/catalog.json + docs/SKILLS_INDEX.md
./harness skills --check       # fail if catalog/index are stale (no writes)
./harness selfcheck            # compile + spec + reference integrity + index + demo
./harness skills --mine        # does each installed agent actually see it?
```

To make it always-on in your own agents (any directory, not just inside the
repo):

```bash
./harness skills --install --name my-skill   # symlink just this one into ~/.claude/skills/, ~/.pi/skills/, ~/.agents/skills/
# narrower filters: --name (repeatable) · --category <c> · --entry · --origin · --owner · --maturity
# then restart the agent, or /reload (Pi / Claude Code)
```

---

## End-to-end, copy-paste

```bash
# 0. dedupe
./harness skills --search my-topic

# 1–2. draft
./harness capture-skill my-skill --description "…" --body "…"

# 3. validate (loop here until clean)
python3 -m skill_foundry.lib.validate_skills

# 4. publish
./harness promote-skill --pr my-skill

# 5. index + verify + install
./harness skills --refresh && ./harness selfcheck
./harness skills --install --name my-skill
```

## Checklist (all boxes before you open the MR)

- [ ] `name` matches the folder, lowercase-hyphen, ≤64 chars
- [ ] `description` says **what + when** (≤1024 chars)
- [ ] `category` + `origin` + `owner` + `maturity` set
- [ ] portable procedure *before* the accelerator section
- [ ] bundled files referenced by relative path
- [ ] no dangling cross-skill references (or declared in `externals.json`)
- [ ] `validate_skills` passes; `selfcheck` green
- [ ] no secrets; diff is small and add-only

## Common mistakes

| Symptom | Fix |
|---|---|
| Validation: `name … does not match parent directory` | rename the folder or the `name` field to match |
| Validation: `name … invalid` | no `_`, no capital letters, no `--`, no leading/trailing `-` |
| Warning: `category is missing` | add `category:` to frontmatter and re-`refresh` |
| `reference to unknown skill 'x'` | fix the link or declare `x` in `config/externals.json` |
| skill not showing up in the agent | `./harness skills --install --name my-skill`, then restart / `/reload` |
| `--pr` printed a PR-new URL instead of creating one | set `GITCODE_TOKEN` in `env.sh` |