# Architecture — roles & interaction

This is the canonical description of how the **user**, **agent**, **harness**,
**MCP server**, and **thin scripts** fit together. It reflects the current shape:
the harness is *only* the skill-ops loop; the regression workflow is separate.

---

## 0. The system in one picture

```text
                    ┌───────────── natural language (intent + corrections) ───────────┐
                    ▼                                                                  │
             ┌─────────────┐      ┌───────────────────────────────────────────┐  ┌─────┴──────┐
             │    USER     │ ───▶ │              AGENT (conductor)             │  │   USER     │
             │  (oracle)   │      │  reads skills, decides what/where/how      │  │ (reviewer)  │
             └─────────────┘      └──────────────┬─────────────────────────────┘  └────────────┘
                                                 │
                          ┌──────────────────────┴───────────────────────────────┐
                          │                                                       │
                          ▼                                                       ▼
            ┌────────────────────────────┐                 ┌─────────────────────────────┐
            │      HARNESS (./harness)    │                 │        MCP SERVER           │
            │  ONLY the skill-ops loop:   │                 │  the same loop as 5 tools   │
            │  capture·promote·teach·skills│                │  (b10 gateway, no compute)   │
            └────────────┬───────────────┘                 └──────────────┬──────────────┘
                         │                                                │
                         └─────── both write the SAME skills / learnings ──┘
                                               │
                                      git (source of truth)
                                               │
            ┌──────────────────────────────────┴────────────────────────────────────┐
            │                 THE BUNDLED REGRESSION WORKFLOW (not the harness)      │
            │                    directly-runnable thin scripts                      │
            │   python3 -m skill_foundry.workflow.run · report · review · status …    │
            │   python3 -m skill_foundry.lib.parse_gtest · perf_metrics · cann        │
            │   (run by the AGENT per the skills — never through ./harness)           │
            └─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. The four actors (plus the scripts)

| | **USER** | **AGENT** | **HARNESS** | **MCP SERVER** |
|---|---|---|---|---|
| **Is** | the human | the AI (Claude Code / Pi / Cowork / any MCP client) | tiny CLI — **the skill-ops loop only** | a thin tool-call API over that loop |
| **Owns** | nothing in the repo — intent only | conversation + delegation + judgment | capture → promote → hub → discover mechanics | connectivity |
| **Decides** | what to do · triage *judgment* · `--pr` merge · re-pin baseline | which skill · real command · `wrong→correct→action` *content* | nothing (add-only) | nothing (delegates 1:1) |
| **Never** | — | hand-roll the regression (follows skills) | run regression · remove/change a check | hold state · drift from `./harness` |

A fifth actor is implicit: the **thin scripts** (`skill_foundry/workflow/` +
`skill_foundry/lib/`) — the deterministic *measurement* layer the agent runs
directly, guided by the skills.

---

## 2. Physical structure (file = actor interface)

```text
skill-foundry/
├── AGENTS.md                         ─▶ AGENT contract: "harness = skills loop ONLY"
├── .claude/skills/*/SKILL.md         ─▶ AGENT knowledge (pure, self-contained)
│     run-testcase · extract-logs · generate-report · review-inconsistencies
│     full-analysis-pipeline · skill-maintainer · pto-isa · pto-vmi
├── .agents/skills ↗                  ─▶ same skills for Pi / open agents
│
├── harness                           ─▶ HARNESS entry → python -m skill_foundry
├── .mcp.json                         ─▶ MCP config for agents
│
├── skill_foundry/
│   ├── __main__.py + dispatch.py      ─▶ router (9 verbs, product only)
│   ├── cli/                           ─▶ THE PRODUCT + shell
│   │     capture.py · promote_skill.py · teach.py · promote.py · skills.py
│   │     menu.py · wrap.py · complete.py · selfcheck.sh
│   ├── workflow/                      ─▶ BUNDLED regression (thin runnable scripts + tours)
│   │     run.py · report.py · review.py · baseline.sh · status.py
│   │     diagnose.py · history.py · clean.py · validate.py
│   │     demo.py · guide.py · onboarding.py   (tours, runnable — NOT harness verbs)
│   └── lib/                           ─▶ thin stable helpers
│         parse_gtest.py · perf_metrics.py · targets.py · cann.py · capabilities.py ·
│         ui.py · term.py · gates.py · reviewer.py …
│
├── config/                           ─▶ source of truth (suites · arches · cann)
├── reports/ · learnings/ · hub/      ─▶ state (runs+baseline / captures / drafts)
└── mcp/server.py                     ─▶ MCP SERVER (5 tools)
```

---

## 3. Responsibility matrix

```text
                         USER          AGENT          HARNESS       MCP SERVER    THIN SCRIPTS
────────────────────────────────────────────────────────────────────────────────────────────
intent ("run the tests")    ●
pick skill + plan                         ●
run the test command                                                    (agent runs)  ●
normalize logs → schema                                                              ●
diff vs baseline (arithmetic)                                                        ●
read logs + explain                       ●
triage (judgment)                         ●
capture a lesson (teach)                  ●              ●              ●
promote → push / PR                       ●              ●              ●
merge PR (--pr only)        ● gate
re-pin baseline             ● deliberate                                 ●
remove/change a check                   (never)        (never)        (never)
```

---

## 4. End-to-end process

### Phase A — Setup (once)
| # | Actor | Action |
|---|---|---|
| 1 | **User** | *"set this up"* (or `python3 -m skill_foundry.workflow.onboarding`) |
| 2 | **Agent** | reads skills → runs setup steps |
| 3 | **Agent** | runs `python3 -m skill_foundry.workflow.status` / `.lib.cann` to detect env |
| 4 | **User** | pins the baseline (`bash skill_foundry/workflow/baseline.sh pto-isa`) — deliberate |

### Phase B — USE loop (regression; agent drives thin scripts)
| # | Actor | Action |
|---|---|---|
| 1 | **User** | *"run the full regression"* |
| 2 | **Agent** | reads `run-testcase` + `pto-isa` skills |
| 3 | **Agent** | runs the **thin script**: `python3 -m skill_foundry.workflow.run --all-suites --report --open --review` |
| 4 | **scripts** | run suites · normalize (`lib/parse_gtest`) · render report · set-diff + p99 vs baseline |
| 5 | **Agent** | reads report + log · classifies · explains |
| 6 | **User** | reads the summary |

### Phase C — IMPROVE loop (the product; harness + MCP)
| # | Actor | Action |
|---|---|---|
| 1 | **User** | *"that vcvt thing is a known issue"* — **or the agent spots it** |
| 2 | **Agent** | `./harness teach "… → … → …"` (or MCP `teach(...)`) |
| 3 | **Harness** | appends `LRN-…` to `learnings/recent.md` |
| 4 | **Agent** | `./harness promote --pr` (or MCP `promote()`) |
| 5 | **Harness** | edits `SKILL.md`/`known-failures.md`, commits, pushes a `feat/learnings-<date>` branch, opens a PR |
| 6 | **User** | merges the PR |
| 7 | **everyone** | next run reads the improved skill → smarter |

---

## 5. The transports (split by concern)

| | **HARNESS (shell)** | **MCP SERVER** | **THIN SCRIPTS** |
|---|---|---|---|
| Agent calls | `./harness <skill-loop verb>` | `skills_list/load`, `capture_skill`, `teach`, `promote` | `python3 -m skill_foundry.workflow.*`, `lib.*` |
| For | the **product** (skills loop) | the product, as typed remote tools | the **bundled regression workflow** |
| Where | local / any checkout | b10 gateway (local only now) | local / ecs / anywhere with the repo |

The 5 MCP tools map 1:1 to harness verbs:

```text
skills_list    → ./harness skills --json
skills_load    → read SKILL.md + references
capture_skill  → ./harness capture-skill …
teach          → ./harness teach …
promote        → ./harness promote --<mode>   (default pr)
```

---

## 6. The measure/judge split

```text
MEASURE (thin scripts — code)         JUDGE (agent + skills — intelligence)
────────────────────────────          ────────────────────────────────────
exact pass/fail counts                what does this failure mean
stable run.json schema                compile / camodel / soc / numeric?
set-diff vs baseline                  known or new?
p99 > +15% arithmetic                 what should we capture?
known-failure string match            how to explain it to the user
reproducibility (git/host/env)        what to do next
```

The measurement lives in `workflow/` + `lib/` scripts; the harness only captures
and promotes the knowledge that measurement produces.

---

## 7. The automation boundary

```text
🟢 automatic                            🟡 human (rare)               🔴 never
─────────────────────────────────────────┼─────────────────────────────┼─────────────────────────
agent: run regression scripts             USER: triage judgment         ANYONE:
       capture (teach)                     review + merge the PR (--pr)   remove/change
harness: gates + LLM review + promote      re-pin the baseline           an existing check
```

---

## 8. One-paragraph summary

**The user speaks intent and corrections. The agent — guided by self-contained
skills — decides what to do and runs the regression through thin scripts while
using the harness solely for the skill-ops loop (capture → promote → hub →
discover). The harness is a tiny, add-only knowledge engine; the MCP server is
that loop exposed as five typed tools; the regression workflow is a separate,
directly-runnable set of scripts the skills reference as knowledge.** Skills are
the knowledge, git is the source of truth, and the only human gates are triage
judgment, the `--pr` merge, and a deliberate baseline re-pin.


## tilelangGym adapter

Third bundled target (alongside `pto-isa` / `pto-vmi`). Encodes SoftLib/ST
improve-loop **compliance** as static gate suites + Agent Skills:

- Motif ladder / Done-bar / TRACE / PRC / forced PR9 → `skill_foundry.lib.tilelanggym_gate`
- Knowledge cards → `hub/tilelanggym/`
- Skills → `.claude/skills/tilelanggym-*`
- Full opencode hours stay outside the foundry runner (`opencode-full` disabled)

See [TILELANGGYM.md](TILELANGGYM.md).
