#!/usr/bin/env bash
# Claude Code PreToolUse hook for Bash. Exit 2 blocks the command and feeds
# stderr back to Claude.
#
# Guards against the 2025-11 leak, where a saved Terraform plan was swept into a
# commit on this public repo: no blanket staging, no skipping the git hooks, no
# plan files written into the repo, and nothing secret-bearing in the index at
# commit time.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // empty')
[ -n "$cmd" ] || exit 0

root=${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}

block() {
    echo "$1" >&2
    exit 2
}

sep='(^|[;&|(]|&&)[[:space:]]*'

if grep -qE "${sep}git[[:space:]]+add[[:space:]]+([^;&|]*[[:space:]])?(-A|--all|-u|--update|\.|\*|:/)([[:space:]]|$|[;&|)])" <<<"$cmd"; then
    block "Blanket 'git add' is not allowed in this public repo. Stage each file by explicit path."
fi

if grep -qE "${sep}git[[:space:]]+commit[[:space:]]+([^;&|]*[[:space:]])?(-[a-zA-Z]*a[a-zA-Z]*|--all)([[:space:]]|$)" <<<"$cmd"; then
    block "'git commit -a' is not allowed in this public repo. Stage each file by explicit path, then commit."
fi

if grep -qE "${sep}git[[:space:]]+(commit|push)[[:space:]][^;&|]*(--no-verify|[[:space:]]-n([[:space:]]|$))" <<<"$cmd"; then
    block "Do not bypass the git hooks (--no-verify): they are the secret scan for this public repo."
fi

if grep -qE "terraform[[:space:]]+plan[[:space:]][^;&|]*-out" <<<"$cmd" &&
    ! grep -qE -- "-out[= ]\"?/tmp/" <<<"$cmd"; then
    block "Saved Terraform plans contain secrets. Run 'terraform plan' without -out, or write the plan under /tmp and delete it afterwards."
fi

if grep -qE "${sep}git[[:space:]]+commit([[:space:]]|$)" <<<"$cmd"; then
    if ! out=$("$root/scripts/check-staged-secrets.sh" 2>&1); then
        block "$out"
    fi
fi

exit 0
