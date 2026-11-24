# Importing Skills

`./harness import` brings skills from an external source — a git repo, an agent
skills directory, or a knowledge library — into the skill-foundry corpus,
through the same gated, human-merged path as a hand-written skill.

It is the **front half of the capture loop**: it *discovers* candidates,
*checks relevance* (semantic scope + corpus-aware dedupe), and *drafts* them
into `hub/inbox/`. The existing `promote-skill` gate then publishes them
unchanged.

## Prerequisites

Two judge commands (each reads a payload on stdin, prints a verdict) and a PR
token, so the loop can run unattended:

```bash
export IMPORT_REVIEWER='…'   # scope + relevance, one call per candidate
# export SKILL_REVIEWER='…'  # promotion APPROVE/HOLD/REJECT (required for --pr)
export GH_TOKEN='…'          # so --pr can open the PR automatically
```

Without `IMPORT_REVIEWER`, `--scan` falls back to a lexical scope check;
without `SKILL_REVIEWER`, `--pr` fails closed.

## Quick start

```bash
# 1. register the source
./harness import --add skills-library --type knowledge-library --path ~/skills-library

# 2. review what's in scope / relevant
./harness import skills-library --scan

# 3. produce drafts for the relevant candidates
./harness import skills-library --draft

# 4. check the drafts against the spec
./harness import skills-library --validate

# 4b. (optional) record the candidates you've decided against — they stay dropped
./harness import skills-library --reject <name> [<name> …]

# 5. publish (gated + LLM-reviewed → PR; a human merges)
./harness import skills-library --pr

# 6. later: refresh snapshots after the source changes
./harness import skills-library --sync
```

Steps 2–5 chain in one command:
`./harness import skills-library --scan --draft --validate --pr` — stages run in
order and stop at the first error (a single flag still works alone).

## What it does, stage by stage

| command | what happens |
|---|---|
| `--list` | prints the registered sources (same as bare `./harness import`). |
| `--add` | writes an entry to `config/imports.json`. For a `knowledge-library` it also creates a mapping stub `config/imports/<name>.json` (edit its `skills` list before scanning). |
| `--remove` | deregisters a source — registry entry only; never deletes drafts, skills, or the manifest. |
| `--scan` | discovers candidates, runs the **relevance gate**, and writes `hub/imports/<source>/manifest.json` (fingerprints + verdicts). Writes only that manifest — not drafts or skills. |
| `--draft` | for each `relevant` candidate, snapshots the source into `hub/inbox/<name>/` and synthesizes a router `SKILL.md`. Reuses the last `--scan` verdicts (`--rescan` to re-judge); skips already-published skills. |
| `--reject <name> [--undo]` | records a human "skip this one" decision in the manifest; `--draft`/`--sync` then skip it. `--undo` restores. |
| `--validate` | runs `validate_skills --strict` (spec + repo metadata) on the produced drafts. |
| `--apply` / `--pr` | runs the mechanical gates + the builtin and `SKILL_REVIEWER` judges, then copies drafts into `.claude/skills/` (`--apply` = local; `--pr` = + commit, push, open a PR). |
| `--sync` | re-fingerprints the source, diffs against the manifest, and refreshes drifted *draft* snapshots (`unchanged / changed / added / removed`). Once a skill is promoted its draft is consumed, so later drift is reported as `changed (no draft)` and is **not** auto-applied to `.claude/skills/`. |

## Source types

A source declares a `type` (the adapter) — one of three shapes, none of which is
specific to any particular library:

| type | the source looks like | discovery |
|---|---|---|
| `knowledge-library` | no `SKILL.md`; a mapping manifest groups its leaves into skills | one candidate per mapping entry |
| `agent-skills` | `<name>/SKILL.md` folders (Claude / Anthropic spec) | one candidate per `SKILL.md` folder |
| `local-dir` | an agent user skills dir (`~/.pi/skills/`, `~/.claude/skills/`) | one candidate per `SKILL.md` folder |

Location is `--path <dir>` (local) or `--git <url>` (cloned into a gitignored
cache at `.cache/imports/<name>` on first use; `--sync` does `git pull --ff-only`).

## Import modes

`mode` controls how content moves, and is orthogonal to `type`:

| mode | behaviour |
|---|---|
| `vendor` (default) | copy the source into the draft; inject missing provenance frontmatter |
| `passthrough` | copy as-is (trust the source's frontmatter) |
| `reference` | write a pointer stub only — content stays at the source location |

## The relevance gate (`--scan`)

For each candidate, the engine checks:

1. **completeness** — name/description/category present, files resolved, `entry_file` present (else `irrelevant`).
2. **self-containment** — no machine paths (`/home/ /root/ /Users/`) (else `hold`).
3. **dedupe** — Jaccard + description similarity against the *published corpus* (authoritative for `duplicate`/`extend`).
4. **scope** — semantic: the `IMPORT_REVIEWER` judge answers `IN_SCOPE`/`OUT_OF_SCOPE` against the declared `scope_hint` (authoritative). With no judge configured, a lexical word-overlap fallback applies.

Verdicts and what they mean:

| verdict | meaning | action |
|---|---|---|
| `relevant` | in-scope, no meaningful overlap | draft it |
| `extend` | overlaps an existing skill | merge into it (`./harness teach`), don't fork |
| `duplicate` | already covered | skip |
| `irrelevant` | out of scope (judge said `OUT_OF_SCOPE`) | skip |
| `hold` | self-containment issue, or the LLM disagreed with a deterministic `relevant` | a human decides |

A human decision to drop a candidate is recorded with `--reject <name>` — that
mark lives in the manifest (not in the verdict), survives re-scans, and is
cleared only with `--reject <name> --undo`.

The LLM relevance verdict is **advisory**: it can escalate a deterministic
`relevant` to `hold` for human review, but never silently overrides the
deterministic dedupe (which has the actual skill list).

## What a draft contains

For `vendor` mode, each `relevant` candidate becomes a draft under
`hub/inbox/<name>/`. The shape depends on the source type:

`knowledge-library` — a synthesized router + snapshots:

```text
hub/inbox/<name>/
├── SKILL.md          # thin router: frontmatter + file table + "start here"
└── references/       # source snapshots, preserving the source's relative tree
    └── …
```

`agent-skills` / `local-dir` — a flat copy of the source folder (the original
`SKILL.md` and its content, no `references/`).

The `SKILL.md` frontmatter carries provenance either way: `origin`/`owner`
(from the source config), `maturity`, `license` (auto-detected, e.g.
`Apache-2.0`), and `metadata.source`/`location`/`fingerprint`.

## Publishing is gated and human-merged

`--pr` runs, in order: the spec gate, the secrets scan, the builtin review
(dangling refs, placeholders, contradictions), and the `SKILL_REVIEWER` judge —
then copies the skills into `.claude/skills/`, commits on a branch, and opens a
PR. **A human merges.** Non-interactive sessions fail closed without
`SKILL_REVIEWER`. `--apply` is the same gate, minus the commit/PR.

If the reviewer does not approve, the command exits `1` (nothing is promoted).
`--pr` leaves you on the new `feat/import-<src>-<ts>` branch — the skills stay
committed there until the PR merges (`git checkout main` to go back).

## Judges

Two env vars, each a command that reads the payload on stdin and prints a
verdict (see `scripts/import-reviewer.py` for an opencode/cannbot reference):

```bash
export IMPORT_REVIEWER='python3 <repo>/scripts/import-reviewer.py'
export SKILL_REVIEWER='python3 <repo>/scripts/import-reviewer.py "Strict skill reviewer. Reply exactly one word: APPROVE, HOLD, or REJECT."'
```

## Files it reads and writes

| path | read / written |
|---|---|
| `config/imports.json` + `config/imports/<source>.json` | source registry + mapping (authored) |
| `hub/imports/<source>/manifest.json` | import record — fingerprints, verdicts, actions (generated) |
| `hub/inbox/<name>/` | drafts awaiting promotion |
| `.claude/skills/<name>/` | the published skills (after `--pr` merges) |

## Example

Importing the skills-library reference layer produced 12 candidates. The
relevance gate kept the 5 genuinely-new formula/run skills, flagged 3 as
`extend` (already covered by `npu-*` skills), and routed 3 to `hold` (LLM
claimed overlap) for a human decision — which dropped them in favour of the
existing `npu-op-burst` / `npu-single-opcode-rate` / `tilelanggym-st-*` skills
(now recordable with `./harness import skills-library --reject <name>`).
