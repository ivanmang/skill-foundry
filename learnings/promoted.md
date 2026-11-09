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
- LRN-20261105-001 — pto-isa — parse_gtest must accumulate per-binary gtest summaries and count `run binary failed … died with` as a FAIL (already in code + tested).
- LRN-20261105-004 — pto-isa — ca clock is 5 GHz (core_period 200 ps); GB/s = B/cyc × 5.
- LRN-20261105-005 — pto-isa — SIMT [type:] codes are bytes/lane (1=B8,2=B16,4=B32,5=B64); type:2 = 64 B/instr.
- LRN-20261105-006 — pto-isa — MTE3 write bytes unlogged; estimate mte3_busy × 128 / 5.5.
- LRN-20261105-010 — pto-isa — parse_gtest overwrite/crash bug (dup of -001); covered by added tests + docs.
- LRN-20261105-013 — pto-isa — MTE3 ×128 calibration factor 5.3–6.4 (use /5.5); MTE2 read bytes from XT descriptor low 16 bits.
- LRN-20261105-014 — pto-isa — SIMT type width = bytes/lane; type:2 is exact 64 B/instr.
- LRN-20261105-015 — pto-isa — ca clock 5 GHz constant (dup of -004).
- LRN-20261105-019 — pto-isa — ecs temp-file failures: /tmp on root FS; set TMPDIR=~/tmp so temp files land on /home (merged with -020).
- LRN-20261105-020 — pto-isa — root cause is `/` inode exhaustion (df -i 6553600/6553600), not block-full; diagnose with df -i.
- LRN-20261105-018 — pto-isa — REJECTED (duplicate): --all-suites auto-skip is already the documented rule; A6=dav_9201 headers-first already in cann-matrix.md.
- LRN-20261106-001 — pto-isa — run.json is written only at completion; don't trust the newest run.json until pgrep DONE + EXITCODE line present.
- LRN-20261106-002 — pto-isa — a full --all-suites regression can exceed 16h; plan a long window or re-poll.
- LRN-20261106-003 — pto-isa — npu-sim-a6 auto-skip is an expected env limitation, not a regression.
- LRN-20261106-004 — pto-isa — the nohup wrapper appends EXITCODE only on process exit; check it together with pgrep DONE.
- LRN-20261106-005 — pto-isa — log line-growth over ~60s confirms liveness on long sim runs.
- 2026-11-09 batch (20) — pto-isa — OAT/license wording + year, trailing newline, oat-check, CMakeLists.txt plural, header-filename match, squash+force-push, A6 TLOAD/TSTORE->pto_copy_align_v2, TCvt.hpp wrapper, cpu-st /tmp env, baseline drift, disk cleanup, extract-filters-from-log, capture dedupe limitation. → references/porting-and-compliance.md.
