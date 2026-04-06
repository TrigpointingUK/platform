#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TARGET="${1:-staging}"

echo "=== dbt analytics build (target: ${TARGET}) ==="
echo ""

# Auto-fetch credentials from Secrets Manager when not already set
if [ -z "${DBT_PASSWORD:-}" ]; then
    command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
    command -v jq >/dev/null 2>&1 || { echo "❌ jq not found."; exit 1; }

    SECRET_ID="dbt-${TARGET}-postgres-credentials"
    AWS_REGION="${AWS_REGION:-eu-west-1}"

    echo "🔑 Fetching credentials from Secrets Manager (${SECRET_ID})..."
    SECRET_JSON=$(aws --region "$AWS_REGION" secretsmanager get-secret-value \
        --secret-id "$SECRET_ID" \
        --query SecretString --output text)

    export DBT_HOST="${DBT_HOST:-localhost}"
    export DBT_PORT="${DBT_PORT:-5433}"
    export DBT_USER=$(echo "$SECRET_JSON" | jq -r '.username')
    export DBT_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password')
    export DBT_DATABASE=$(echo "$SECRET_JSON" | jq -r '.dbname')
    echo "   Host: ${DBT_HOST}:${DBT_PORT}  User: ${DBT_USER}  DB: ${DBT_DATABASE}"
fi

echo ""
echo "--- Installing packages ---"
dbt deps

echo ""
echo "--- Building models and running tests ---"
dbt build --target "$TARGET"

echo ""
echo "--- Syncing medal awards ---"
python "$SCRIPT_DIR/sync_medals.py" "$TARGET"

echo ""
echo "--- Generating docs ---"
dbt docs generate --target "$TARGET"

echo ""
echo "=== Build complete ==="
