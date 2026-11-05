# Corrections Log

Append-only log of changes made to skills. Each entry: date, skill affected,
what changed, and why.

```markdown
## <date> — <skill-name>
- Context: <run-id or trigger>
- Wrong: <what the flow previously did>
- Correct: <what it should do now>
- Action: <precise edit applied>
- Promoted from: recent.md
```

## 2026-10-30 — skill-maintainer
- Promoted: LRN-20261030-001
- Action: Reference external skills by name or skill: URI and declare them in the plugin external manifest (skills.json); inline the few essential facts (e.g. arch alias mapping) instead of relative sibling links.

## 2026-10-30 — skill-maintainer
- Promoted: LRN-20261030-002
- Action: Keep category in YAML frontmatter (hub discovery depends on it) and run harness skills --refresh after adding or changing skills.

## 2026-10-30 — skill-maintainer
- Promoted: LRN-20261030-003
- Action: Auto-create the PR via the gitcode v5 API using GITCODE_TOKEN from env.sh (promote --pr); see references/mr-automation.md for the options

## 2026-11-05 — pto-isa
- Promoted: LRN-20261105-002, -003, -007, -008, -009, -011, -012, -016, -017
- Action: documented camodel_v100.json esl_top_thread_cnt override + ScheTop.cpp:126 crash (merge of -002/-003/-011/-012) and TMOVTest nz2nd_3 flaky (-017) in known-failures.md; setenv.bash sourcing (-007/-016) in env.md; baseline known-failure pin + git reconciliation (-008/-009) in workflow docs.

## 2026-11-05 — pto-isa
- Promoted: LRN-20261105-001, -004, -005, -006, -010, -013, -014, -015
- Action: parse_gtest (-001/-010) already in code + tested, marked promoted; CA-metrics facts (-004/-005/-006/-013/-014/-015) inlined as references/ca-metrics.md (clock 5 GHz, SIMT byte/lane widths, MTE3 ×128/5.5) and linked from SKILL.md.

## 2026-11-05 — pto-isa
- Promoted: LRN-20261105-019, -020 (merged into one env.md note); Rejected: LRN-20261105-018 (duplicate of existing rules + cann-matrix).
- Action: added ecs temp-file inode-exhaustion note (TMPDIR=~/tmp + df -i) to references/env.md; --all-suites/A6 skip already documented — no change.
