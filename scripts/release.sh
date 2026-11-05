#!/usr/bin/env bash
# Release helper: bump the version, update the changelog placeholder, commit, tag.
#
#   scripts/release.sh 0.7.0            # bump VERSION + pyproject.toml, commit + tag
#   scripts/release.sh 0.7.0 --dry-run  # show what would change, change nothing
#
# After tagging, push the tag; the release workflow builds + creates the GitHub
# Release (sdist + wheel). The `[Unreleased]` section of CHANGELOG.md is renamed
# to the new version and a fresh `[Unreleased]` section is added.
set -euo pipefail

NEW="${1:?usage: scripts/release.sh <version> [--dry-run]}"
DRY=0
[ "${2:-}" = "--dry-run" ] && DRY=1

case "$NEW" in
  v*) NEW="${NEW#v}" ;;
esac
case "$NEW" in
  *.*.*) ;;
  *) echo "version must be semver X.Y.Z (got '$NEW')" >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OLD="$(cat VERSION)"
[ -n "$OLD" ] || { echo "VERSION is empty" >&2; exit 1; }

bump() { # bump <path> <old> <new>
  sed -i "s/${1}/${2}/" "$3"
}
pyver() { sed -n 's/^version *= *"\([^"]*\)"/\1/p' pyproject.toml | head -1; }

if [ "$DRY" = "1" ]; then
  echo "dry-run: VERSION $OLD -> $NEW"
  echo "dry-run: pyproject.toml version = \"$(pyver)\" -> \"$NEW\""
  echo "dry-run: CHANGELOG.md [Unreleased] -> [$NEW] $(date +%Y-%m-%d)"
  echo "dry-run: git commit -m 'release: $NEW' && git tag v$NEW"
  exit 0
fi

echo "releasing $OLD -> $NEW"

printf '%s' "$NEW" > VERSION
sed -i "s/^version = \".*\"/version = \"$NEW\"/" pyproject.toml
# Rename the [Unreleased] header to the release, and open a new one on top.
sed -i "0,/^## \[Unreleased\]/s//## [$NEW] - $(date +%Y-%m-%d)/" CHANGELOG.md
sed -i "0,/^# Changelog/s//# Changelog\n\n## [Unreleased]/" CHANGELOG.md

git add VERSION pyproject.toml CHANGELOG.md
git commit -m "release: $NEW"
git tag "v$NEW"
echo "done — push with: git push origin main --follow-tags"