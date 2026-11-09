# Contributing to skill-foundry

skill-foundry is a **skill-ops platform**: agents and humans capture reusable
knowledge as [Agent Skills](https://agentskills.io) (`SKILL.md`), and it flows
through a reviewed promote step into a shared hub every teammate's agent can use.

## The two loops

```text
USE      run → report → review     (thin scripts · diff vs pinned baseline)
IMPROVE  teach → promote --pr      (corrections → skills via a reviewed PR)
```

## Development setup

```bash
git clone git@github.com:ivanmang/skill-foundry.git
cd skill-foundry
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
make check          # full self-check: compile + spec + unit + demo + tilelangGym
```

The canonical merge gate is `./skill_foundry/cli/selfcheck.sh`; CI runs it on
every PR. `ruff` is a blocking gate over the product code (`skill_foundry/`,
`mcp/`, `tests/`, `scripts/`).

## Submitting a change

1. **Open an issue first** for new skills, new targets, or behavior changes.
   Trivial doc fixes and bug fixes can go straight to a PR.
2. Branch from `main`, make your change, and open a **pull request on GitHub**
   (GitCode is a read-only mirror — never open a PR there).
3. CI must be green (`selfcheck` + `lint` + `package`).
4. A human merges; **never self-merge**.

PRs include a description in the
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) shape.

## Skills

- Follow the open [Agent Skills spec](https://agentskills.io/specification):
  required `name` + `description` frontmatter, name matches the folder,
  lowercase-hyphen, ≤64 chars; description ≤1024 chars.
- skill-foundry adds discovery fields: `category`, `origin`, `owner`,
  `maturity` (all required to pass the promote gate).
- Conformance is machine-checked: `python3 -m skill_foundry.lib.validate_skills --strict`.

## Rules

See [docs/RULES.md](docs/RULES.md) for the canonical six rules and the automation
boundary. Contribution specifics:

- **Exit codes:** `0` clean · `1` ran-with-failures · `2` usage.
- **Secrets never touch git** — tokens go in the gitignored `env.sh`.

## Automation boundary

See [docs/RULES.md](docs/RULES.md#automation-boundary-who-does-what) for the
canonical who-does-what table.

## Git reconciliation

If a checkout diverges from `origin/main` (unpushed baseline, duplicated
local fix, or drifted commits), reconcile cleanly rather than force-pushing:

```bash
git fetch origin
# 1. reset to the shared upstream, keeping any wanted commit(s) aside first
#    (e.g. a baseline pin):  git cherry-pick <baseline-sha>  AFTER the reset
# 2. hard-reset the branch to origin/main
# 3. cherry-pick the wanted commit(s) back on top
# 4. push, then fast-forward any other local clones
```

Never force-push a diverged `main` — reset → cherry-pick → push keeps history
linear and every clone able to fast-forward.
