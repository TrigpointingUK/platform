#!/bin/bash
# Set database environment variables for production from AWS Secrets Manager.
#
# Usage: source scripts/set-db-env-production.sh
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - jq installed
#   - SSM tunnel running on localhost:5433 (make postgres-tunnel)
#
# This script should be SOURCED, not executed, to set variables in your shell:
#   source scripts/set-db-env-production.sh
#   # or
#   . scripts/set-db-env-production.sh
#
# ⚠️  WARNING: This connects to PRODUCTION. Be careful!

# Note: Don't use 'set -e' in sourced scripts - it persists in the calling shell

SECRET_NAME="fastapi-production-postgres-credentials"
REGION="eu-west-1"

echo "⚠️  WARNING: Fetching PRODUCTION database credentials!"
echo ""
echo "Fetching production database credentials from AWS Secrets Manager..."

# Fetch secret
SECRET_JSON=$(aws secretsmanager get-secret-value \
    --region "$REGION" \
    --secret-id "$SECRET_NAME" \
    --query SecretString \
    --output text)

if [ -z "$SECRET_JSON" ]; then
    echo "Error: Failed to fetch secret $SECRET_NAME"
    return 1 2>/dev/null || exit 1
fi

# Parse credentials
DB_USER_VALUE=$(echo "$SECRET_JSON" | jq -r '.username')
DB_PASSWORD_VALUE=$(echo "$SECRET_JSON" | jq -r '.password')
DB_NAME_VALUE=$(echo "$SECRET_JSON" | jq -r '.dbname')

if [ -z "$DB_USER_VALUE" ] || [ "$DB_USER_VALUE" = "null" ]; then
    echo "Error: Failed to parse username from secret"
    return 1 2>/dev/null || exit 1
fi

# Export environment variables
# Use localhost:5433 for SSM tunnel (ignore host/port from secret)
export DB_HOST="localhost"
export DB_PORT="5433"
export DB_USER="$DB_USER_VALUE"
export DB_PASSWORD="$DB_PASSWORD_VALUE"
export DB_NAME="$DB_NAME_VALUE"
export ENVIRONMENT="production"

echo "✓ Production database environment configured:"
echo "  DB_HOST=$DB_HOST"
echo "  DB_PORT=$DB_PORT"
echo "  DB_USER=$DB_USER"
echo "  DB_NAME=$DB_NAME"
echo "  DB_PASSWORD=****"
echo "  ENVIRONMENT=$ENVIRONMENT"
echo ""
echo "⚠️  You are now connected to PRODUCTION!"
echo "Make sure the SSM tunnel is running: make postgres-tunnel"

