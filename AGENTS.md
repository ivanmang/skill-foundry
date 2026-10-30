# AGENTS.md

This is **skill-foundry** — a skill-ops platform. The harness (`./harness`) does
**only the skill-ops loop** (capture → promote → hub → discover). Everything else
— including the bundled regression workflow — is **knowledge in the skills**,
executed via thin scripts the skills reference. You (the agent) are the
conductor; the user is the only human gate. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for the full roles & interaction model.

## Your workflow

1. **Read the skills first** — they are your instruction set, under
   `.claude/skills/` (also reachable via `.agents/skills/`). They are
   self-contained knowledge: each one tells you *what to run* and *how to
   triage*, using real test commands and thin helper scripts
   (`python3 -m skill_foundry.workflow.*`, `skill_foundry.lib.*`).
2. **Use `./harness` ONLY for the skill-ops loop** — `capture-skill`,
   `promote-skill`, `teach`, `promote`, `skills`. Never route the regression
   workflow through the harness; run its scripts directly per the skills.
3. **Capture every reusable lesson** with `./harness teach` automatically when
   any of these happen:
   - the user corrects you (`"no / wrong / actually / don't / remember …"`)
   - a suite fails and the cause is reusable or repeats
   - review flags a gap (missing check, wrong threshold, un-triaged failure)
   - an external tool / command behaves unexpectedly
   Reply with the `LRN-…` id you logged.
   For a **brand-new skill** (not a lesson about an existing one), draft it with
   `./harness capture-skill <name>`, then promote it.
4. **Promote captured lessons** with `./harness promote --pr` (learnings) or
   `./harness promote-skill <name> --pr` (new skills). Publication is **strict
   and controlled**: the mechanical gates (add-only · no-secrets · size · spec)
   always run, then an LLM judge (`SKILL_REVIEWER`) must APPROVE before anything
   is written — in a non-interactive session you need `SKILL_REVIEWER` set, or it
   fails closed. Review cannot be skipped and the gates cannot be bypassed. The
   only publish path is `--pr`, which opens an MR a human merges; **never
   self-merge**.
5. **Never remove or change an existing check** — the harness only adds.

## Capture vs promote

- Capture is **automatic and continuous** — log lessons as they surface;
  nothing changes until promoted.
- Publication is **gated + LLM-reviewed, then human-merged** — `--pr` opens an
  MR; a human merges it after CI is green (no auto-merge, no direct push).
- Draft from a run's failures with
  `python3 -m skill_foundry.lib.session_digest --run <run.json> --apply`.

## Key commands

```bash
# THE PRODUCT — the skill-ops loop (the only harness verbs)
./harness capture-skill <name>           # draft a NEW skill
./harness teach "wrong -> correct -> action"
./harness promote --pr                   # publish learnings (open an MR)
./harness promote-skill <name> --pr      # publish a draft (open an MR)
./harness skills [--search q] [--category c] [--origin o] [--entry] [--check]  # discover skills (map: docs/SKILLS_INDEX.md)

# BUNDLED WORKFLOW — run these thin scripts directly (per the skills)
python3 -m skill_foundry.workflow.run --all-suites --report --open --review
python3 -m skill_foundry.workflow.status   # readiness
python3 -m skill_foundry.lib.cann          # CANN/arch detection
```

## Layout

- `.claude/skills/` — the knowledge (read them first; they are the workflow)
- `docs/SKILLS_INDEX.md` — auto-generated entry points + category map (route tasks here)
- `config/externals.json` — declared external skills (cannbot-skills / ttk / …)
- `skill_foundry/workflow/` — thin, runnable regression scripts the skills call
- `skill_foundry/lib/` — thin stable helpers (parse/diff/perf/targets)
- `skill_foundry/cli/` — the harness: the skill-ops loop + shell
- `hub/` — skill drafts; `learnings/` — captured lessons
- `reports/baseline/<target>.json` — pinned baseline (regression = diff vs it)
- `.githooks/` — pre-push gate; enable `make hooks`, run `make push-check`

## Rules

- Exit codes: `0` clean · `1` ran-with-failures · `2` usage.
- npu-sim needs BOTH compile headers AND the simulator; p99 +15% flags a perf
  regression even if average is stable.
- The baseline is the ground truth — refresh it only deliberately.
## tilelangGym target (SoftLib/ST)

- Skills: `tilelanggym-st-explore`, `tilelanggym-softlib-simt`, `tilelanggym-st-report`,
  `tilelanggym-semantics-gate`, `tilelanggym-vmi-gmap`.
- **USE (gate):** set `TILELANGGYM_PACK` to a closed pack (fixture under
  `demo/fixtures/tilelanggym-pack-ok` for smoke), then
  `python3 -m skill_foundry.workflow.run --target tilelangGym --suite sv567-1xg-clean`
  (and `sv567-nx1-outer`). Validates Motif ladder, Done-bar, TRACE, PRC, PR9, RESULT schema.
- **IMPROVE:** teach Motif/Done-bar/PRC misses via `./harness teach` → promote into the
  tilelanggym-* skills; do not paste dig el/cyc into Motif seeds.
- Full multi-hour opencode clean regress stays **out of band** (`opencode-full` suite
  `enabled:false`).
