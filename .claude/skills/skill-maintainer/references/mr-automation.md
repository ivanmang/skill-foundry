# Publishing — how the agent auto-creates the merge request

`./harness promote --pr` publishes pending learnings as a merge request (gitcode
calls it a **pull request**). The branch + push are automatic; whether the PR is
created automatically depends on how the platform is reached.

## What the agent does, in order

1. `git push -u origin <branch>` with GitLab push options (`-o merge_request.create`)
   — works on real GitLab, **ignored by gitcode**.
2. If no PR was created, falls back to the **gitcode v5 API** using `GITCODE_TOKEN`.
3. If no token, prints the manual "create PR" URL for a human to open.

## Options to auto-create the PR

| Option | Works on gitcode? | Notes |
|---|---|---|
| SSH push options (`merge_request.create`) | ❌ | gitcode accepts the push but ignores the option; prints `merge_requests/new?…` instead |
| `GITCODE_TOKEN` → gitcode v5 API | ✅ | the wired-in path; token kept in gitignored `env.sh` |
| `glab` CLI (`glab mr create`) | ⚠️ untested | `glab` speaks GitLab API (`/api/v4`), which gitcode does not expose — likely fails |

## The gitcode v5 API (what the agent calls)

```
POST https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls?access_token=<TOKEN>
Content-Type: application/json
{ "title": …, "head": <source branch>, "base": <target branch>, "body": <description> }
```

- Auth is the `access_token` **query parameter** (not a header — `Authorization: token`
  and `Bearer` both return 401; verified live).
- `body` is the PR description; the API accepts it on create and on `PATCH`.
- Response `html_url` is the PR web URL, e.g.
  `https://gitcode.com/<owner>/<repo>/merge_requests/<n>`.
- This is Gitee-style, not GitLab-style — `/api/v4` + `PRIVATE-TOKEN` do **not**
  work against gitcode (verified live).

## Standard MR description

Every MR the agent opens carries a description in this shape (built by
`promote.build_mr_body`):

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

- Keep `export GH_TOKEN=…` (GitHub) or `export GITCODE_TOKEN=…` (GitCode) in
  `env.sh` (gitignored). **Never commit it** — the no-secrets gate rejects it,
  and it is a credential.
- The merge is always human: `--pr` opens the PR but never merges it.

## GitHub (post-migration)

When the repo migrates to GitHub, `--pr` auto-creates the PR through two paths
(in priority order, both human-merged):

1. **`gh` CLI** — `gh pr create --head <branch> --base main --title …`.
   Preferred: uses the existing `gh auth` (or `GH_TOKEN`/`GITHUB_TOKEN`).
2. **GitHub REST API** — `POST https://api.github.com/repos/{owner}/{repo}/pulls`
   with `Authorization: Bearer <token>` (header auth, not query param).

Env vars accepted: `GH_TOKEN`, then `GITHUB_TOKEN` (GitHub);
`GITCODE_TOKEN`, then `GITLAB_TOKEN` (GitCode/GitLab). If none are set and `gh`
is not authenticated, `--pr` pushes the branch and prints the manual URL
(`https://github.com/<owner>/<repo>/compare/main...<branch>`).

> GitHub ignores the GitLab push options (`-o merge_request.create`) the agent
> sends first — that push succeeds but creates no PR, and the agent falls
> through to the paths above. No action needed.
