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

