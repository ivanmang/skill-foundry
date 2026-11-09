# Publishing — how the agent auto-creates the pull request

`./harness promote --pr` publishes pending learnings as a pull request (PR) on
GitHub. The branch + push are automatic; whether the PR is created automatically
depends on how GitHub is reached (`gh` CLI / `GH_TOKEN`).

## What the agent does, in order

1. `git push -u origin <branch>` with GitLab push options (`-o merge_request.create`)
   — GitHub **ignores** these (the push succeeds, no PR).
2. Falls through to create the PR on GitHub:
   - **`gh` CLI** — `gh pr create --head <branch> --base main --title …`.
     Preferred: reuses the existing `gh auth` (or `GH_TOKEN`/`GITHUB_TOKEN`).
   - **GitHub REST** — `POST https://api.github.com/repos/{owner}/{repo}/pulls`
     with `Authorization: Bearer <token>` (header auth, not query param).
3. If no token and `gh` is not authenticated, prints the manual "create PR" URL
   for a human (`https://github.com/<owner>/<repo>/compare/main...<branch>`).

## Options to auto-create the PR

| Option | Works? | Notes |
|---|---|---|
| `gh` CLI (`gh pr create`) | ✅ | preferred — `gh auth login` or `GH_TOKEN`/`GITHUB_TOKEN` |
| `GH_TOKEN` → GitHub REST | ✅ | `Authorization: Bearer <token>` (header auth) |
| SSH push options (`merge_request.create`) | ❌ | GitHub ignores them; push succeeds, no PR |

## The GitHub REST API (fallback)

```
POST https://api.github.com/repos/{owner}/{repo}/pulls
Authorization: Bearer <TOKEN>
Content-Type: application/json
{ "title": …, "head": "<source branch>", "base": "<target branch>", "body": "<description>" }
```

- Auth is the `Authorization: Bearer` **header** (GitHub uses header auth, not a
  query param).
- Response `html_url` is the PR web URL, e.g.
  `https://github.com/<owner>/<repo>/pull/<n>`.

## Standard PR description

Every PR the agent opens carries a description in this shape:

```markdown
## What
<what changed — prose, can be a few sentences>

## Files changed

| File | Change | What changed | Diff |
|---|---|---|---|
| `path/to/file` | modified | <what changed in it> | +n/−m |

## Why
<the problem / root cause this fixes>

## Impact
<what's affected — commands, targets, users, blast radius>

## Testing
<how verified — commands, results, before/after>

## Rollback
<how to revert / risk if it goes wrong>

## Notes
<optional: follow-ups, related links>
```

`## Files changed` is a table: **File · Change (added/modified/removed) · What
changed · Diff (+n/−m)**. `## Why` / `## Impact` / `## Testing` / `## Rollback` /
`## Notes` are optional; `## What` and `## Files changed` are always present.
`./harness promote --pr` fills the table automatically from the promoted entries
(change type + line stats are computed from the edit).

## Token handling

- Keep `export GH_TOKEN=…` (GitHub) in `env.sh` (gitignored), or run
  `gh auth login`. **Never commit it** — the no-secrets gate rejects it.
- The merge is always human: `--pr` opens the PR but never merges it.

## External gitcode-origin repos (footnote)

This repo is GitHub-canonical; GitCode is a read-only mirror. `promote --pr`
still **auto-detects the remote host** from `origin`, so for an *external*
gitcode-origin checkout it creates the GitCode equivalent of a PR (GitCode calls
it an **MR**) via the gitcode v5 API:

```
POST https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls?access_token=<TOKEN>
Content-Type: application/json
{ "title": …, "head": "<source branch>", "base": "<target branch>", "body": "<description>" }
```

- gitcode v5 auth is the `access_token` **query param** (header auth returns 401;
  verified live). It is Gitee-style — `/api/v4` + `PRIVATE-TOKEN` do **not** work.
- Set `GITCODE_TOKEN` (or `GITLAB_TOKEN`) in `env.sh` for that path.
- Never open an MR on the GitCode **mirror** of this repo.
