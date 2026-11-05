# Changelog

All notable changes to skill-foundry are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows
[SemVer](https://semver.org/); the canonical version lives in `VERSION`
(`pyproject.toml` mirrors it — bump both via `scripts/release.sh`).

## [Unreleased]

### Added
- GitHub Actions CI: `selfcheck` (gate + demo + tilelangGym), `lint` (ruff),
  `typecheck` (mypy), `package` (editable-install smoke), `secret-scan` (gitleaks).
- One-way GitHub → GitCode mirror workflow (`main` + tags).
- Release workflow (`release.yml`): build sdist/wheel + GitHub Release on tag.
- GitHub PR support in `--pr` (`gh pr create` → GitHub REST, `GH_TOKEN`/`GITHUB_TOKEN`).
- Product-loop telemetry (`./harness metrics`) — capture/promote/judge counters +
  LLM-judge calibration (`--calibrate`).
- State schema migration (`lib/state.py`) — `run.json` stamped with `schema_version`
  and migrated on load.
- Governance: `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, PR + issue templates,
  `CHANGELOG.md`, `scripts/release.sh`.
- 15 unit tests for the science core (parse_gtest, review.p99, perf_metrics).
- 6 npu-case-writing skills + `pto-isa/references/ca-metrics.md`.
- Multi-tool skill install: Codex, Cursor, Copilot, OpenCode.
- `config/fleet.json` — fleet hosts + MCP endpoint.

### Fixed
- `pip install -e .` (added `setup.py` shim + `wheel` build requirement).
- 36 mypy type errors across 9 files (drive type check to zero).
- parse_gtest multi-binary overwrite + crash counting (now unit-tested).

### Changed
- `ruff` scoped to product code and made a blocking merge gate.
- `mypy` driven to zero and made a blocking merge gate.
- All 23 learnings promoted into skills (`known-failures.md`, `env.md`, `ca-metrics.md`).

## [0.6.0] - 2026-11-05

- Skill-ops platform: capture → promote → hub → discover loop with MR-gated,
  LLM-judged promotion.
- Bundled regression workflow (run → extract → report → review) for `pto-isa`,
  `pto-vmi`, and `tilelangGym` targets.
- MCP server exposing the loop as five typed tools.
- Open Agent Skills conformance (`SKILL.md` + `name`/`description` frontmatter,
  machine-checked via `validate_skills`).
