# Changelog

All notable changes to skill-foundry are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows
[SemVer](https://semver.org/); the canonical version lives in `VERSION`
(`pyproject.toml` mirrors it — bump both via `scripts/release.sh`).

## [Unreleased]

### Added
- GitHub Actions CI (`selfcheck` merge gate + `lint` + `package` jobs).
- One-way GitHub → GitCode mirror workflow (`main` + tags).
- GitHub PR support in `--pr` (`gh pr create` → GitHub REST, `GH_TOKEN`/`GITHUB_TOKEN`).
- `config/fleet.json` — single source of truth for fleet hosts + MCP endpoint.
- Multi-tool skill install: Codex, Cursor, Copilot, OpenCode.

### Fixed
- `pip install -e .` (added `setup.py` shim + `wheel` build requirement).

### Changed
- `ruff` scoped to product code (`skill_foundry/`, `mcp/`, `tests/`, `scripts/`) and
  made a blocking merge gate; the bundled `.claude/skills` corpus is excluded.

## [0.6.0] - 2026-11-05

- Skill-ops platform: capture → promote → hub → discover loop with MR-gated,
  LLM-judged promotion.
- Bundled regression workflow (run → extract → report → review) for `pto-isa`,
  `pto-vmi`, and `tilelangGym` targets.
- MCP server exposing the loop as five typed tools.
- Open Agent Skills conformance (`SKILL.md` + `name`/`description` frontmatter,
  machine-checked via `validate_skills`).
