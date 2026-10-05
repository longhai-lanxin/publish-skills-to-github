#!/usr/bin/env bash
# Create GitHub repos (gh + PAT) and push them over SSH.
# Usage:
#   bash publish_repos.sh <workspace-dir> <owner> <repo1> [repo2 ...]
#
# Requires:
#   - gh already authed with a PAT that has `repo` scope (gh auth login --with-token)
#   - ~/.ssh/config pointing github.com -> ssh.github.com:443
#   - each repo already git-init'ed and committed

set -u
BASE="${1:?workspace dir}"
OWNER="${2:?github owner}"
shift 2

GH="${GH:-C:/Users/<you>/.workbuddy/bin/gh/bin/gh.exe}"

for d in "$@"; do
  repo_dir="$BASE/$d"
  if [ ! -d "$repo_dir/.git" ]; then
    printf '%-40s %s\n' "$d" "SKIP (no .git)"
    continue
  fi
  # create repo; ignore error when it already exists
  "$GH" repo create "$d" --public >/dev/null 2>&1
  (
    cd "$repo_dir" || exit 1
    git remote remove origin >/dev/null 2>&1
    git remote add origin "git@github.com:${OWNER}/${d}.git"
    out=$(timeout 180 git push -u origin HEAD:main 2>&1 | tail -1)
    git branch -m master main >/dev/null 2>&1
    git branch --set-upstream-to=origin/main main >/dev/null 2>&1
    printf '%-40s %s\n' "$d" "$out"
  )
done
