# Promoted

Entries from `recent.md` that have been reviewed and applied to a skill (or
deliberately rejected with a reason).

- LRN-20261030-001 — skill-maintainer — Cross-skill references to external skills must be by name or skill: URI, declared in the plugin external manifest, with essential facts inlined.

- LRN-20261030-002 — skill-maintainer — category is required by hub discovery; keep it in YAML frontmatter and regenerate the catalog after skill changes.

- LRN-20261030-003 — skill-maintainer — gitcode is Gitee-style: POST api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls?access_token=<token> with {title,head,base}
- LRN-20261103-001 — pto-isa — The FP4 E2M1→E4M3 LUT dispatch guard was A5-only; pair A6 with A5 in tcvt_common.hpp:2915 and :3259 (fixed by pto-isa 7c0141eb).
- LRN-20261103-002 — pto-isa — The 7-arg copy_gm_to_ubuf is A5-only; use pto_copy_gm_to_ubuf_align_v2 on A6.
- LRN-20261103-003 — pto-isa — A6 ST testcases are separate copies under tests/npu/a6/..., registered in ALL_TESTCASES, with per-test acl init/reset and tests/common/test_common.h.
- LRN-20261105-002 — pto-isa — camodel_v100.json esl_top_thread_cnt is root-owned read-only; only in-place sudo edit (32→64) works, CWD/env override ignored.
- LRN-20261105-003 — pto-isa — ScheTop.cpp:126 thrId<s_thrCnt SIGABRT is deterministic per data-movement case (tload_mix #65), not concurrency.
- LRN-20261105-007 — pto-isa — source setenv.bash before sim runs (non-login SSH has no ASCEND_HOME_PATH).
- LRN-20261105-008 — pto-isa — known-failure baseline cannot use the PASS-only path; pin via direct copy + force-like step.
- LRN-20261105-009 — pto-isa — reconcile git divergence with reset → cherry-pick → push, never force-push a diverged main.
- LRN-20261105-011 — pto-isa — ScheTop repro needs a full no-timeout binary run; tload_mix looks green under timeout only because it stops before case 65.
- LRN-20261105-012 — pto-isa — ScheTop root cause: esl_top_thread_cnt 32→64 via sudo sed on both sim-dir copies.
- LRN-20261105-016 — pto-isa — must source setenv.bash on ecs non-login SSH before run_st.py.
- LRN-20261105-017 — pto-isa — TMOVTest.case_nz2nd_3 flaky: numeric/nondeterminism; triage backlog, not camodel.
