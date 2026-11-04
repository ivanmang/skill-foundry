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
