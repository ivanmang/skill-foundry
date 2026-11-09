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


## LRN-20261106-001
- id: LRN-20261106-001
- category: knowledge_gap
- context: pto-isa regression monitoring on ecs
- skill: pto-isa
- wrong: Newest reports/*/run.json was a stale earlier attempt with all suites FAIL and exit 1 while the current run was still RUNNING
- correct: run.json is only written at workflow completion; do not use newest run.json unless pgrep reports DONE and the nohup wrapper has appended EXITCODE, and confirm the report dir is newer than the current run start
- action: pto-isa workflow docs
- status: promoted


## LRN-20261106-002
- id: LRN-20261106-002
- category: knowledge_gap
- context: pto-isa full regression duration
- skill: pto-isa
- wrong: Monitoring was stopped after about 16h42m with the process still RUNNING, exceeding the 2.5h budget
- correct: A full pto-isa regression can exceed 16 hours; plan for a much longer timeout or report progress and re-poll later instead of waiting indefinitely
- action: pto-isa task-planning docs
- status: promoted


## LRN-20261106-003
- id: LRN-20261106-003
- category: feature
- context: pto-isa ecs suite status
- skill: pto-isa
- wrong: The npu-sim-a6 suite was skipped due to missing compile headers and the dav_9201 simulator and could be mistaken for failure
- correct: Treat npu-sim-a6 skip as an expected environment limitation on this machine rather than a regression failure
- action: pto-isa known-failures
- status: promoted


## LRN-20261106-004
- id: LRN-20261106-004
- category: feature
- context: nohup wrapper completion signal
- skill: pto-isa
- wrong: Checking only pgrep was insufficient to know whether the wrapper had finished
- correct: The nohup wrapper appends an EXITCODE line to ~/ecs-regression.log only when the process exits; check for that line together with pgrep DONE before collecting results
- action: pto-isa workflow docs
- status: promoted


## LRN-20261106-005
- id: LRN-20261106-005
- category: feature
- context: workflow.run liveness check
- skill: pto-isa
- wrong: A long-running run appeared possibly hung without recent suite markers
- correct: Compare the line count of ~/ecs-regression.log over about 60 seconds; line growth confirms active progress even when no new suite markers appear
- action: pto-isa monitoring docs
- status: promoted


## LRN-20261106-161702-f2423987
- id: LRN-20261106-161702-f2423987
- category: knowledge_gap
- context: pto-isa ecs run 20261105-172537
- skill: pto-isa
- wrong: npu-sim-a5 suite summary reports 10 failures but run.json case list has only 9 FAIL entries
- correct: extract failing filters from the per-suite log not run.json case list to avoid missing failures
- action: update known-failures
- status: promoted


## LRN-20261106-161702-d20743a1
- id: LRN-20261106-161702-d20743a1
- category: knowledge_gap
- context: cpu-st suite on ecs
- skill: pto-isa
- wrong: gtest binary SIGABRT on /tmp because root fs full makes cpu-st FAIL despite 3/3 passing
- correct: attribute cpu-st failure to environment when root fs is full; not a test regression
- action: update known-failures
- status: promoted


## LRN-20261106-161702-338b6066
- id: LRN-20261106-161702-338b6066
- category: feature
- context: npu-sim-a6 on ecs
- skill: pto-isa
- wrong: suite auto-skipped because CANN lacks compile headers and simulator dav_9201 is missing
- correct: treat npu-sim-a6 skip as expected
- action: update known-failures
- status: rejected


## LRN-20261106-161702-50a5aee5
- id: LRN-20261106-161702-50a5aee5
- category: knowledge_gap
- context: pto-isa review baseline
- skill: pto-isa
- wrong: review diff shows 1844 removed and 41 new indicating reports/baseline/pto-isa.json is stale
- correct: refresh baseline before trusting review diff; single flagged regression trems may be due baseline drift
- action: update known-failures
- status: promoted


## LRN-20261109-115844-e9d2afd4
- id: LRN-20261109-115844-e9d2afd4
- category: correction
- context: new testcase files
- skill: pto-isa
- wrong: cases.h filename mismatch: test had case.h (singular) but main.cpp and kernel included cases.h (plural)
- correct: match the header filename to what sources include (cases.h) and mirror sibling testcases
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115844-629f0bc6
- id: LRN-20261109-115844-629f0bc6
- category: error
- context: adding subdirectory in CMake
- skill: pto-isa
- wrong: CMakeList.txt (singular) silently ignored by add_subdirectory
- correct: must be named CMakeLists.txt (plural) to be discovered
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115844-192947c0
- id: LRN-20261109-115844-192947c0
- category: feature
- context: license headers in new files
- skill: pto-isa
- wrong: OAT hook rejected headers using "You should not use this file" and missing comma in "MERCHANTABILITY OR FITNESS"
- correct: use canonical wording "You may not use this file" and "MERCHANTABILITY, OR FITNESS" on one line
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115844-7dd5f4a7
- id: LRN-20261109-115844-7dd5f4a7
- category: knowledge_gap
- context: pre-commit OAT scan scope
- skill: pto-isa
- wrong: OAT check missed license issues in #-comment files (gen_data.py, CMakeLists.txt) yet still requires them compliant
- correct: run oat-check manually and fix license wording even in files OAT didn't flag in the log
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115844-b983190f
- id: LRN-20261109-115844-b983190f
- category: correction
- context: A6 vec-core kernel DMA
- skill: pto-isa
- wrong: kernel used PTO TLOAD/TSTORE wrappers, which CMakeLists says do not lower correctly for dav-920r1-vec
- correct: use raw pto_copy_gm_to_ubuf_align_v2 / pto_copy_ubuf_to_gm_align_v2 intrinsics directly, length in bytes
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115844-b9fc550b
- id: LRN-20261109-115844-b9fc550b
- category: error
- context: pre-commit end-of-file-fixer
- skill: pto-isa
- wrong: main.cpp missing trailing newline at EOF failed the hook
- correct: ensure every file ends with exactly one newline before pushing
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115844-f895e8a1
- id: LRN-20261109-115844-f895e8a1
- category: feature
- context: PR squashing before merge
- skill: pto-isa
- wrong: reviewer required the whole PR squashed into one single commit on master
- correct: cherry-pick or squash all PR changes into one commit and force-push
- action: update pto-isa known-failures
- status: promoted


## LRN-20261109-115916-4bb42856
- id: LRN-20261109-115916-4bb42856
- category: knowledge_gap
- context: pto-isa full regression 22h run
- skill: pto-isa
- wrong: run.json is written only at completion so the newest run.json can be stale
- correct: trust results only when workflow.run pgrep empty and the nohup wrapper has appended EXITCODE
- action: pto-isa/references/suite-matrix.md Long runs and monitoring section
- status: rejected


## LRN-20261109-115916-053889fe
- id: LRN-20261109-115916-053889fe
- category: knowledge_gap
- context: pto-isa full regression
- skill: pto-isa
- wrong: full --all-suites run can exceed 16h and look stuck
- correct: plan a long window or use --parallel and re-poll
- action: pto-isa/references/suite-matrix.md
- status: rejected


## LRN-20261109-115916-e357cb36
- id: LRN-20261109-115916-e357cb36
- category: knowledge_gap
- context: pto-isa full regression
- skill: pto-isa
- wrong: npu-sim-a6 auto-skip was mistaken for a regression
- correct: npu-sim-a6 skip is an expected environment limitation not a regression
- action: pto-isa/references/suite-matrix.md cross-ref cann-matrix
- status: rejected


## LRN-20261109-115916-dedd6cfa
- id: LRN-20261109-115916-dedd6cfa
- category: knowledge_gap
- context: pto-isa full regression
- skill: pto-isa
- wrong: absence of suite markers makes a long run look stuck
- correct: confirm liveness by log line growth over about 60 seconds
- action: pto-isa/references/suite-matrix.md
- status: rejected


## LRN-20261109-115916-409029e7
- id: LRN-20261109-115916-409029e7
- category: knowledge_gap
- context: pto-isa full regression
- skill: pto-isa
- wrong: nohup wrapper appends EXITCODE only on process exit
- correct: combine EXITCODE presence with empty pgrep as the reliable completion signal
- action: pto-isa/references/suite-matrix.md
- status: rejected


## LRN-20261109-115916-5f603e40
- id: LRN-20261109-115916-5f603e40
- category: correction
- context: ecs a5 full regression TREMSTest
- skill: pto-isa
- wrong: trems case1 was reported as a true PASS to FAIL regression
- correct: 10 isolated passes and 6 seed-sweep passes all succeeded so reclassify as unreproduced suspect run-order or env state plus separate minor defect of unseeded gen_data and ill-conditioned float32 rem
- action: known-failures.md TREMSTest.case1 entry
- status: rejected


## LRN-20261109-115916-b7bb757b
- id: LRN-20261109-115916-b7bb757b
- category: correction
- context: ecs a5 a3 regression tgather
- skill: pto-isa
- wrong: tgather crash was blamed on the int64 guard kernel
- correct: actual crashing cases are float gathers a5 TGATHERTest.case16_float_gt_neg_typedk and a3 TGATHERTest.case_1D_float_32x1024_16x64
- action: known-failures.md tgather entry
- status: rejected


## LRN-20261109-115916-305dfb43
- id: LRN-20261109-115916-305dfb43
- category: correction
- context: CI lint gate
- skill: skill-foundry
- wrong: editing py files without running ruff format left 5 unformatted files and failed CI
- correct: always run ruff format . or make check before pushing because CI enforces both ruff check and ruff format --check
- action: selfcheck.sh and development workflow docs
- status: rejected


## LRN-20261109-115916-da91b998
- id: LRN-20261109-115916-da91b998
- category: feature
- context: multi-user learnings concurrency
- skill: skill-foundry
- wrong: LRN ids from per-file counter could collide for teammates and same-day promote branches could clash
- correct: use LRN-YYYYMMDD-HHMMSS-random-hex ids and unique date-rand branch names plus force-with-lease push
- action: log_correction.py session_digest.py promote.py status.py
- status: rejected


## LRN-20261109-115916-8025e492
- id: LRN-20261109-115916-8025e492
- category: knowledge_gap
- context: background ecs worker auto-capture
- skill: skill-foundry
- wrong: worker re-captured knowledge already promoted creating a duplicate 16-entry batch
- correct: auto-capture should check promoted.md or the target doc before capture because dedupe only happens at promote time
- action: teach auto-capture path
- status: promoted


## LRN-20261109-120216-3890b3f5
- id: LRN-20261109-120216-3890b3f5
- category: error
- context: OAT pre-commit check
- skill: pto-isa
- wrong: new files used "You should not use this file" and "MERCHANTABILITY OR FITNESS" without comma
- correct: use canonical header "You may not use this file except in compliance with the License" and "MERCHANTABILITY, OR FITNESS"
- action: known-failures for OAT compliance
- status: promoted


## LRN-20261109-120216-a7ed0ddf
- id: LRN-20261109-120216-a7ed0ddf
- category: error
- context: pre-commit end-of-file-fixer
- skill: pto-isa
- wrong: main.cpp failed CI for missing trailing newline at EOF
- correct: every source file needs a trailing newline before commit run pre-commit end-of-file-fixer
- action: known-failures
- status: promoted


## LRN-20261109-120216-6ebfcabd
- id: LRN-20261109-120216-6ebfcabd
- category: feature
- context: A6 vec-core kernel on dav-920r1-vec
- skill: pto-isa
- wrong: kernel used TLOAD/TSTORE wrappers for GM-UB transfer
- correct: TLOAD/TSTORE do not lower correctly for A6 use pto_copy_gm_to_ubuf_align_v2 and pto_copy_ubuf_to_gm_align_v2 with lenBurst in bytes per tload_common.hpp
- action: A6 kernel dev guidance or known-failures
- status: promoted


## LRN-20261109-120216-72aafa3f
- id: LRN-20261109-120216-72aafa3f
- category: error
- context: CMake add_subdirectory
- skill: pto-isa
- wrong: testcase dir had CMakeList.txt singular and was silently skipped
- correct: file must be CMakeLists.txt plural for add_subdirectory to resolve
- action: known-failures
- status: promoted


## LRN-20261109-120216-f0beacf4
- id: LRN-20261109-120216-f0beacf4
- category: error
- context: header include mismatch
- skill: pto-isa
- wrong: new file named case.h singular but sources included cases.h plural
- correct: match header filename to include name sibling dirs use cases.h
- action: known-failures
- status: promoted


## LRN-20261109-120216-0714a751
- id: LRN-20261109-120216-0714a751
- category: correction
- context: OAT license header year
- skill: pto-isa
- wrong: new file kept old year 2025 in license
- correct: new files get current year 2026 in header
- action: known-failures
- status: promoted


## LRN-20261109-120216-3c262bd3
- id: LRN-20261109-120216-3c262bd3
- category: knowledge_gap
- context: adding A6 header include
- skill: pto-isa
- wrong: needed A6 TCvt support
- correct: mirror a5/TCvt.hpp as thin wrapper since tcvt_common.hpp is shared update header.hpp include from a5/TCvt.hpp to a6/TCvt.hpp
- action: A6 porting notes
- status: promoted


## LRN-20261109-120238-ac375085
- id: LRN-20261109-120238-ac375085
- category: correction
- context: GitHub CI lint failed ruff format --check
- skill: pto-isa
- wrong: After editing .py files without running ruff format, CI reported 5 files would be reformatted
- correct: Always run make check or ruff format . after any .py edit before pushing; CI enforces ruff check and ruff format --check
- action: Update developer workflow docs; selfcheck.sh must run ruff format --check
- status: rejected


## LRN-20261109-120238-19f896e0
- id: LRN-20261109-120238-19f896e0
- category: feature
- context: concurrent learnings capture in multi-user hub
- skill: pto-isa
- wrong: Per-file LRN-YYYYMMDD-NNN counter caused id collisions; same-day branch names clashed; plain push could clobber
- correct: Use LRN-YYYYMMDD-HHMMSS-8hex ids, unique feat/learnings-date-6hex branches, and git fetch plus push --force-with-lease before promote
- action: Update promote and teach code docs
- status: rejected


## LRN-20261109-120238-1014b7bc
- id: LRN-20261109-120238-1014b7bc
- category: knowledge_gap
- context: long full pto-isa regression run
- skill: pto-isa
- wrong: run.json is written only at completion, so newest run.json misleads until process exits; full all-suites can run over 16h
- correct: Wait for pgrep empty and EXITCODE appended; confirm liveness by log line-growth over 60s; plan long window or parallel
- action: pto-isa/references/suite-matrix.md Long runs and monitoring
- status: rejected


## LRN-20261109-120238-890cb0d7
- id: LRN-20261109-120238-890cb0d7
- category: knowledge_gap
- context: ecs full regression environment
- skill: pto-isa
- wrong: cpu-st FAIL was SIGABRT caused by root fs 100 percent full with deleted open files holding about 30G
- correct: Clean deleted open files and ensure tmp space before regression; treat as environmental not suite failure
- action: pto-isa env doc or known-failures.md
- status: promoted


## LRN-20261109-120238-00f0ec94
- id: LRN-20261109-120238-00f0ec94
- category: correction
- context: trems TREMSTest.case1 regression triage
- skill: pto-isa
- wrong: PASS to FAIL looked like true regression but isolated runs passed 10 of 10; gen_data.py lacks seed and uses near-float32-max operands with 0.001 absolute tolerance
- correct: Reclassify as run-order or environment interaction not code regression; seed gen_data and constrain value range in pto-isa test
- action: known-failures.md trems entry
- status: rejected


## LRN-20261109-120238-983ddc98
- id: LRN-20261109-120238-983ddc98
- category: knowledge_gap
- context: tgather crash triage
- skill: pto-isa
- wrong: tgather crashed SIGABRT on a5 and SIGSEGV on a3 but case names were unknown
- correct: Record confirmed cases TGATHERTest.case16_float_gt_neg_typedk and TGATHERTest.case_1D_float_32x1024_16x64; crash is float gather path not int64 guard
- action: known-failures.md tgather entry
- status: rejected


## LRN-20261109-120238-56c75437
- id: LRN-20261109-120238-56c75437
- category: knowledge_gap
- context: npu-sim-a6 regression run
- skill: pto-isa
- wrong: npu-sim-a6 skipped during full regression
- correct: Expected environment limitation, not regression; see cann-matrix
- action: known-failures.md or env doc
- status: rejected


## LRN-20261109-120238-ac5dec29
- id: LRN-20261109-120238-ac5dec29
- category: knowledge_gap
- context: capture and promote loop
- skill: pto-isa
- wrong: teach appends recent.md but does not commit or promote; background worker captured redundant already-promoted knowledge
- correct: Require explicit promote steps and check promoted.md before capture to avoid duplicate pending entries
- action: harness docs and capture code
- status: promoted

