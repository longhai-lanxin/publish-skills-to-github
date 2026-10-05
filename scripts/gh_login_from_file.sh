#!/usr/bin/env bash
# Re-authenticate gh from the locally stored PAT file.
# Usage: bash gh_login_from_file.sh [path-to-token-file]
#
# Default token file: ~/.workbuddy/secrets/github_pat
# Never echo the token; it is piped straight into gh.

set -u
TOKEN_FILE="${1:-$HOME/.workbuddy/secrets/github_pat}"
GH="${GH:-C:/Users/<you>/.workbuddy/bin/gh/bin/gh.exe}"

if [ ! -r "$TOKEN_FILE" ]; then
  echo "token file not readable: $TOKEN_FILE" >&2
  exit 1
fi

cat "$TOKEN_FILE" | "$GH" auth login --with-token >/dev/null 2>&1
"$GH" auth status 2>&1 | sed -n '1,3p'
