#!/bin/bash
#
# Run Alembic Migrations on Bastion Host (production ONLY)
#
# This script copies the Alembic migrations to the bastion host and runs them
# against the production PostgreSQL database.
#
# Usage:
#   ./scripts/run_alembic_on_bastion_production.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
BASTION_HOST="bastion.trigpointing.uk"
SSH_KEY_PATH="${SSH_KEY_PATH:-~/.ssh/trigpointing-bastion.pem}"
BASTION_USER="ec2-user"
REMOTE_DIR="/home/ec2-user/alembic-migrations"

# Expand tilde in SSH key path
SSH_KEY_PATH_EXPANDED="${SSH_KEY_PATH/#\~/$HOME}"

print_warning "⚠️  PRODUCTION DATABASE ONLY ⚠️"
print_status "Alembic Migrations - Bastion Execution (Production)"
echo "============================================================"

# Check if SSH key exists
if [[ ! -f "${SSH_KEY_PATH_EXPANDED}" ]]; then
    print_error "SSH key not found at ${SSH_KEY_PATH_EXPANDED}"
    print_error "Please set SSH_KEY_PATH environment variable or ensure ~/.ssh/trigpointing-bastion.pem exists"
    exit 1
fi

# Check if we can connect to bastion
print_status "Testing connection to bastion host..."
if ! ssh -i "${SSH_KEY_PATH_EXPANDED}" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${BASTION_USER}@${BASTION_HOST}" "echo 'Connection successful'" > /dev/null 2>&1; then
    print_error "Cannot connect to bastion host at ${BASTION_HOST}"
    print_error "Please check:"
    print_error "  - Bastion hostname resolves correctly"
    print_error "  - SSH key path is correct: ${SSH_KEY_PATH_EXPANDED}"
    print_error "  - SSH key has access to bastion"
    exit 1
fi
print_success "Connected to bastion"

# Create remote directory
print_status "Creating remote directory..."
ssh -i "${SSH_KEY_PATH_EXPANDED}" "${BASTION_USER}@${BASTION_HOST}" "mkdir -p ${REMOTE_DIR}"

# Copy Alembic files
print_status "Copying Alembic configuration and migrations..."
scp -i "${SSH_KEY_PATH_EXPANDED}" alembic.ini "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/"

# Copy alembic directory
print_status "Copying alembic directory..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
    -e "ssh -i ${SSH_KEY_PATH_EXPANDED}" \
    alembic/ "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/alembic/"

# Copy api directory (needed for models)
print_status "Copying API directory..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' --exclude='test.db' \
    -e "ssh -i ${SSH_KEY_PATH_EXPANDED}" \
    api/ "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/api/"

# Copy minimal requirements for Alembic
print_status "Copying requirements file..."
scp -i "${SSH_KEY_PATH_EXPANDED}" requirements-alembic.txt "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/"

print_success "Files copied to bastion"

# Run Alembic on bastion
print_status "Executing Alembic migrations on bastion..."
echo "============================================================"

ssh -i "${SSH_KEY_PATH_EXPANDED}" "${BASTION_USER}@${BASTION_HOST}" << 'ENDSSH'
set -e
export AWS_DEFAULT_REGION=eu-west-1

cd /home/ec2-user/alembic-migrations

echo "🔧 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "📦 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements-alembic.txt

echo ""
echo "🔐 Loading PRODUCTION PostgreSQL credentials from AWS Secrets Manager..."
PG_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id fastapi-production-postgres-credentials \
    --region eu-west-1 \
    --query SecretString --output text)

PG_HOST=$(echo "$PG_SECRET" | jq -r '.host')
PG_PORT=$(echo "$PG_SECRET" | jq -r '.port')
PG_USER=$(echo "$PG_SECRET" | jq -r '.username')
PG_PASSWORD=$(echo "$PG_SECRET" | jq -r '.password')
PG_DATABASE=$(echo "$PG_SECRET" | jq -r '.dbname')

# Set environment variable for Alembic
export DATABASE_URL="postgresql+psycopg2://${PG_USER}:${PG_PASSWORD}@${PG_HOST}:${PG_PORT}/${PG_DATABASE}"

echo "✅ Connected to PRODUCTION database: ${PG_HOST}/${PG_DATABASE}"
echo ""

# Create .env file with individual DB fields for FastAPI settings
# (DATABASE_URL is a computed property, not a field)
cat > .env << DOTENV
DB_HOST=${PG_HOST}
DB_PORT=${PG_PORT}
DB_USER=${PG_USER}
DB_PASSWORD=${PG_PASSWORD}
DB_NAME=${PG_DATABASE}
DOTENV

echo "🔧 Created .env file with database settings for Alembic"
echo ""

echo "============================================================"
echo "🔍 Checking current migration status..."
echo "============================================================"
alembic current

echo ""
echo "============================================================"
echo "📋 Available migrations:"
echo "============================================================"
alembic history

echo ""
echo "============================================================"
echo "🚀 Running migrations (alembic upgrade head)..."
echo "============================================================"
alembic upgrade head

echo ""
echo "============================================================"
echo "✅ Migration completed!"
echo "============================================================"
alembic current

echo ""
echo "🔍 Verifying user_activity_summary view exists..."
psql "${DATABASE_URL}" -c "\d user_activity_summary" || echo "⚠️  View might not be visible yet"

ENDSSH

print_success "Alembic migrations completed on PRODUCTION!"
echo ""
print_status "Next steps:"
echo "  1. Test the /users/browse endpoint on production"
echo "  2. If successful, run the same migrations on production (when ready)"
echo ""

