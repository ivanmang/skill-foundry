# Recent — pending learnings

Strict, machine-parseable format. One entry per `## LRN-…` block; fields in
this exact order. `skill_foundry/lib/log_correction.py` and `skill_foundry/lib/session_digest.py`
write entries; `skill_foundry/cli/promote.py` parses and promotes them.

```markdown

## LRN-20261030-001
- id: LRN-20261030-001
- category: correction
- context: 2026-10-30 skills audit
- skill: skill-maintainer
- wrong: Relative links to external cannbot-skills/TTK skills (e.g. ../npu-arch/SKILL.md, ../ttk-env-check/SKILL.md, skills/ascendc-whitebox-design/...) dangled because those skills are not vendored in this repo.
- correct: Cross-skill references to external skills must be by name or skill: URI, declared in the plugin external manifest, with essential facts inlined.
- action: Reference external skills by name or skill: URI and declare them in the plugin external manifest (skills.json); inline the few essential facts (e.g. arch alias mapping) instead of relative sibling links.
- status: promoted

## LRN-20261030-002
- id: LRN-20261030-002
- category: knowledge_gap
- context: 2026-10-30 skills audit
- skill: skill-maintainer
- wrong: category: knowledge sat in the body (after closing ---) instead of frontmatter; 5 tilelanggym-* skills had no category; hub/catalog.json was stale.
- correct: category is required by hub discovery; keep it in YAML frontmatter and regenerate the catalog after skill changes.
- action: Keep category in YAML frontmatter (hub discovery depends on it) and run harness skills --refresh after adding or changing skills.
- status: promoted

## LRN-20261030-003
- id: LRN-20261030-003
- category: correction
- context: gitcode-mr-automation
- skill: skill-maintainer
- wrong: gitcode ignored GitLab push options and returned 404 on /api/v4, so promote --pr only pushed the branch and printed a manual PR URL
- correct: gitcode is Gitee-style: POST api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls?access_token=<token> with {title,head,base}
- action: Auto-create the PR via the gitcode v5 API using GITCODE_TOKEN from env.sh (promote --pr); see references/mr-automation.md for the options
- status: promoted

## LRN-20261103-001
- id: LRN-20261103-001
- category: correction
- context: 2026-11-03 A6 tcvt_fp4_lut port
- skill: pto-isa
- wrong: A6 device compile of tcvt_fp4_lut failed with tcvt_common.hpp:2883:21: no matching function for call to 'castData_2D_NoPostUpdate'
- correct: The FP4 E2M1→E4M3 LUT dispatch guard was A5-only, so A6 fell through to the generic implTCVT which has no FP4→FP8 castData overloads
- action: known-failures: pair A6 with A5 in the tcvt_common.hpp LUT/dispatch guards (#if defined(PTO_NPU_ARCH_A5) || defined(PTO_NPU_ARCH_A6)) at :2915 and :3259; fixed by pto-isa commit 7c0141eb
- status: promoted

## LRN-20261103-002
- id: LRN-20261103-002
- category: correction
- context: 2026-11-03 A6 tcvt_fp4_lut port
- skill: pto-isa
- wrong: A6 device compile failed with 'copy_gm_to_ubuf' does not support the given target feature on dav-920r1-vec
- correct: The 7-arg copy_gm_to_ubuf builtin is A5-only; A6 uses the 13-arg copy_gm_to_ubuf_align_v2
- action: known-failures: use pto_copy_gm_to_ubuf_align_v2 from arch_cce_intrinsic.hpp (forwards pre_allocation/non_eod_ctrl=false on A6) instead of copy_gm_to_ubuf when porting an A5 test kernel to A6
- status: promoted

## LRN-20261103-003
- id: LRN-20261103-003
- category: knowledge_gap
- context: 2026-11-03 A6 tcvt_fp4_lut port
- skill: pto-isa
- wrong: Assumed A6 reuses a5 ST test kernels via arch guards
- correct: A6 ST testcases are separate copies under tests/npu/a6/src/st/testcase/<name>/ registered in ALL_TESTCASES
- action: When porting an a5 testcase to A6, copy it into tests/npu/a6/src/st/testcase/<name>/ rather than arch-guarding the a5 kernel; register it in ALL_TESTCASES; use per-test aclInit/aclrtSetDevice/aclrtResetDevice/aclFinalize and tests/common/test_common.h
- status: promoted

## LRN-20261105-001
- id: LRN-20261105-001
- category: error
- context: skill-foundry parse_gtest.py normalizer
- skill: pto-isa
- wrong: Gtest counts were overwritten by the last binary in multi-binary runs and binary crashes were never counted
- correct: Accumulate passed/failed per per-binary gtest summary and add one failure for each `run binary failed: ... died with <Signals...>` match
- action: update skill_foundry/lib/parse_gtest.py and extract-logs skill copy
- status: promoted


## LRN-20261105-002
- id: LRN-20261105-002
- category: knowledge_gap
- context: camodel_v100.json esl_top_thread_cnt override
- skill: pto-isa
- wrong: CWD override of camodel_v100.json was ignored and the file is root-owned read-only
- correct: Camodel loads the config by hardcoded basename from the sim dir next to libpem_davinci.so; only sudo edit works
- action: document in references/known-failures.md and env doc
- status: promoted


## LRN-20261105-003
- id: LRN-20261105-003
- category: error
- context: npu-sim-a5 ScheTop crash attribution
- skill: pto-isa
- wrong: ScheTop.cpp:126 `thrId < s_thrCnt` looked load-induced and tload_mix appeared to pass in isolation due to timeout
- correct: Crash is deterministic per data-movement testcase, e.g. tload_mix case #65 NCHW2FZ4D_int8_t, not concurrency
- action: update references/known-failures.md with signature and exact crashing cases
- status: promoted


## LRN-20261105-004
- id: LRN-20261105-004
- category: feature
- context: camodel clock for UB GB/s
- skill: pto-isa
- wrong: UB bandwidth needed camodel frequency
- correct: Core period is 200 ps in Ascend950pr_9599_model.toml so clock is 5 GHz; GB/s = B/cyc times 5
- action: record in ca_instr_analysis.py docs
- status: promoted


## LRN-20261105-005
- id: LRN-20261105-005
- category: correction
- context: SIMT type:2 exact width
- skill: pto-isa
- wrong: type:2 width was previously estimated near 48 B uncertain
- correct: `[type:]` codes encode bytes/lane: 1=B8 2=B16 4=B32 5=B64; with 32-lane execMask type:2 is exact 64 B per instruction
- action: document in ca_instr_analysis.py
- status: promoted


## LRN-20261105-006
- id: LRN-20261105-006
- category: knowledge_gap
- context: MTE3 DMA write bytes
- skill: pto-isa
- wrong: UB-to-GM output store missing from core0.veccore0.instr_log.dump caused bandwidth undercount
- correct: MTE3 MOV_SRC_TO_DST is issued at teardown by host and unlogged; estimate as mte3_busy times 128 divided by calibrated 5.5 factor
- action: document fallback in ca_instr_analysis.py and build_tilelang_report.py
- status: promoted


## LRN-20261105-007
- id: LRN-20261105-007
- category: error
- context: CANN simulator env
- skill: pto-isa
- wrong: npu-sim run failed with env.sh not sourced because ASCEND_HOME_PATH absent
- correct: Must source /usr/local/CANN/cann-9.1.0/bin/setenv.bash before launching sim runs
- action: add to skill-foundry run instructions
- status: promoted


## LRN-20261105-008
- id: LRN-20261105-008
- category: correction
- context: baseline promotion flow
- skill: pto-isa
- wrong: baseline.sh marked first real run as seed generated=false and would refuse non-all-PASS promotion
- correct: A populated baseline with known failures can only be set by direct copy with a force-like step; first real run should be promoted via workflow baseline.sh
- action: document in skill-foundry baseline.sh workflow
- status: promoted


## LRN-20261105-009
- id: LRN-20261105-009
- category: correction
- context: skill-foundry git divergence
- skill: pto-isa
- wrong: ecs repo diverged from origin/main with unpushed baseline and duplicate parse-gtest fix
- correct: Reset to origin/main, cherry-pick the baseline commit, push, then fast-forward local to reconcile cleanly
- action: document git reconciliation workflow for skill-foundry
- status: promoted


## LRN-20261105-010
- id: LRN-20261105-010
- category: correction
- context: full run 20261102-141304-pto-isa
- skill: skill-foundry
- wrong: run.json recorded npu-sim-a5 fail=1 and cpu-st total=2 because parse_gtest overwrote per-binary gtest summaries and ignored binary crashes
- correct: parse_gtest must accumulate passed and failed across all per-binary gtest summaries and match BINARY_CRASH_RE to count SIGABRT/SIGSEGV binaries as FAIL
- action: update skill-foundry parse_gtest tests and docs
- status: promoted


## LRN-20261105-011
- id: LRN-20261105-011
- category: correction
- context: npu-sim-a5 serial rerun
- skill: pto-isa
- wrong: assumed the ScheTop SIGABRTs were caused by parallel load; isolated tload_mix appeared to pass
- correct: serial run reproduced the identical 9 failures; manual timeout 120/180 stopped before case 65 which deterministically aborts
- action: update references/known-failures.md to drop the concurrency hypothesis and require full no-timeout binary runs for repro
- status: promoted


## LRN-20261105-012
- id: LRN-20261105-012
- category: error
- context: npu-sim-a5 ScheTop assertion
- skill: pto-isa
- wrong: 8 layout-conversion kernels SIGABRT with ScheTop.cpp:126 thrId < s_thrCnt
- correct: config is esl_top_thread_cnt 32 in /usr/local/CANN/cann-9.1.0/x86_64-linux/simulator/dav_3510/camodel/camodel_v100.json; file is root-owned read-only and cannot be overridden via CWD or env
- action: document in references/known-failures.md; needed fix is sudo sed 32 to 64 for both sim dir copies
- status: promoted


## LRN-20261105-013
- id: LRN-20261105-013
- category: knowledge_gap
- context: MTE3 UB DMA write bytes
- skill: pto-isa
- wrong: vector instr_log.dump does not log teardown MTE3 transfer bytes; earlier calibration factor assumed 1.8
- correct: measured cast kernels give mte3_busy x 128 overcount factor 5.3-6.4; use mte3_busy x 128 / 5.5 estimate; MTE2 read bytes come exactly from XT descriptor low 16 bits
- action: update ca_instr_analysis.py comments and pto-isa analysis docs
- status: promoted


## LRN-20261105-014
- id: LRN-20261105-014
- category: correction
- context: SIMT type code width
- skill: pto-isa
- wrong: forced SIMT byte count equal to SIMD width causing uncertainty for type:2
- correct: type codes encode bytes per lane: 1=B8, 2=B16, 4=B32, 5=B64; type:2 is 2 B/lane x 32 lanes = 64B/instr
- action: update ca_instr_analysis.py decoder documentation
- status: promoted


## LRN-20261105-015
- id: LRN-20261105-015
- category: knowledge_gap
- context: UB bandwidth GB/s clock
- skill: pto-isa
- wrong: no clock frequency available for converting B/cyc to GB/s
- correct: Ascend950pr_9599_model.toml core_period is 200 ps so camodel clock is 5 GHz
- action: update ca_instr_analysis.py clock constant and report docs
- status: promoted


## LRN-20261105-016
- id: LRN-20261105-016
- category: knowledge_gap
- context: CANN env on ecs
- skill: pto-isa
- wrong: run_st.py failed immediately with env.sh not sourced in non-login SSH
- correct: must source /usr/local/CANN/cann-9.1.0/bin/setenv.bash in the execution environment before sim runs
- action: update skill-foundry run workflow docs or wrapper script
- status: promoted


## LRN-20261105-017
- id: LRN-20261105-017
- category: error
- context: TMOVTest.case_nz2nd_3
- skill: pto-isa
- wrong: same test appears OK 3 times and FAILED 2 times in one run so it is flaky
- correct: treat as pto-isa numeric or nondeterminism issue rather than camodel failure
- action: add to references/known-failures.md triage backlog
- status: promoted


## LRN-20261105-018
- id: LRN-20261105-018
- category: feature
- context: ecs pto-isa readiness
- skill: pto-isa
- wrong: Running `--all-suites` could abort the regression when a suite lacks env
- correct: `--all-suites` skips unavailable suites and runs runnable ones; npu-sim-a6 is skipped due missing CANN headers and dav_9201 simulator
- action: update pto-isa run docs and add npu-sim-a6 skip to known-failures
- status: rejected


## LRN-20261105-019
- id: LRN-20261105-019
- category: error
- context: ecs cmake/gcc temp file creation
- skill: pto-isa
- wrong: gcc/cmake failed to create temp files because /tmp on the root filesystem was full
- correct: Set TMPDIR=~/tmp before the run so temp files use /home which has free space
- action: add TMPDIR workaround to ecs known-failures or setup notes
- status: promoted


## LRN-20261105-020
- id: LRN-20261105-020
- category: correction
- context: ecs /tmp cannot create files
- skill: pto-isa
- wrong: Assumed full disk blocks caused /tmp file creation failure
- correct: Root filesystem inode exhaustion (df -i / showed 6553600/6553600 used) can prevent temp file creation even when blocks are free; check df -i
- action: update ecs triage docs to diagnose inode exhaustion when temp files fail
- status: promoted

