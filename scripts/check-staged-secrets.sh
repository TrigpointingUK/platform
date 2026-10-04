#!/usr/bin/env bash
# Refuse to commit Terraform plan/state files or private key material.
#
# This repository is public. A saved plan (`terraform plan -out=...`) is a zip
# holding the full state, sensitive variable values and remote-state outputs,
# so one stray file leaks every secret Terraform can see.
#
# Checks the files passed as arguments (pre-commit), or every staged file when
# called with none (Claude Code hook, manual use). Always reads the staged blob.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ "$#" -gt 0 ]; then
    files=("$@")
else
    mapfile -t files < <(git diff --cached --name-only --diff-filter=ACMR)
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

fail=0
reject() {
    echo "BLOCKED: $1 - $2" >&2
    fail=1
}

for f in "${files[@]}"; do
    [ -n "$f" ] || continue
    base=${f##*/}

    case "$base" in
        tfplan | tfplan.* | *.tfplan | *.tfplan.json | *.plan | plan.out)
            reject "$f" "Terraform plan file"
            continue
            ;;
        *.tfstate | *.tfstate.*)
            reject "$f" "Terraform state file"
            continue
            ;;
    esac

    git cat-file -e ":$f" 2>/dev/null || continue
    git show ":$f" > "$tmp"

    # A plan file under any name: a zip archive with tfplan/tfstate members.
    if [ "$(head -c 2 "$tmp")" = "PK" ] &&
        unzip -Z1 "$tmp" 2>/dev/null | grep -qxE 'tfplan|tfstate|tfstate-prev'; then
        reject "$f" "Terraform plan archive (contains state)"
        continue
    fi

    # Real PEM private keys start with base64 DER ("MII..."); placeholders do not.
    if grep -aqE -A1 -e '-----BEGIN ([A-Z]+ )?PRIVATE KEY-----' "$tmp" &&
        grep -aE -A1 -e '-----BEGIN ([A-Z]+ )?PRIVATE KEY-----' "$tmp" | grep -aqE '^[[:space:]]*MI[A-Za-z0-9+/]{20,}'; then
        reject "$f" "private key material"
        continue
    fi

    # Terraform state serialised as JSON under another name.
    if grep -aq '"terraform_version"' "$tmp" && grep -aq '"lineage"' "$tmp"; then
        reject "$f" "Terraform state content"
    fi
done

if [ "$fail" -ne 0 ]; then
    cat >&2 <<'EOF'

Unstage these files (git restore --staged <file>) and keep them out of the repo.
If a secret has already been committed, it must be rotated, not just deleted.
EOF
    exit 1
fi
