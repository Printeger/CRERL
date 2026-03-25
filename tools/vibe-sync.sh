#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

commit_message="${1:-chore: update traceability}"

non_traceable_staged="$(
  git diff --cached --name-only -- . ":(exclude)Traceability.md"
)"

if [[ -z "$non_traceable_staged" ]]; then
  echo "No staged repo changes found. Stage the files you want first."
  exit 1
fi

python3 tools/update_traceability.py
git add Traceability.md

if git diff --cached --quiet; then
  echo "Nothing left to commit after refreshing Traceability.md."
  exit 1
fi

git commit -m "$commit_message"

current_branch="$(git branch --show-current)"
if [[ -z "$current_branch" ]]; then
  echo "Unable to detect current branch."
  exit 1
fi

git push origin "$current_branch"
