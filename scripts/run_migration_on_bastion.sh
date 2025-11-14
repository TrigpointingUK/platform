#!/bin/bash
#
# Run PostgreSQL Migration on Bastion Host
#
# This script copies migration scripts to the bastion host and executes them there,
# where they have direct access to both MySQL and PostgreSQL RDS instances.
#
# Usage:
#   ./scripts/run_migration_on_bastion.sh [--export-only|--import-only]
#
# Options:
#   --export-only   Only run the export and transform steps
#   --import-only   Only run the import and validation steps (requires prior export)
#   (no option)     Run complete migration pipeline
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
REMOTE_DIR="/home/ec2-user/postgres-migration"

# Parse options
EXPORT_ONLY=false
IMPORT_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --export-only)
            EXPORT_ONLY=true
            shift
            ;;
        --import-only)
            IMPORT_ONLY=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Usage: $0 [--export-only|--import-only]"
            exit 1
            ;;
    esac
done

# Expand tilde in SSH key path
SSH_KEY_PATH_EXPANDED="${SSH_KEY_PATH/#\~/$HOME}"

print_status "PostgreSQL Migration - Bastion Execution"
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
ssh -i "${SSH_KEY_PATH_EXPANDED}" "${BASTION_USER}@${BASTION_HOST}" "mkdir -p ${REMOTE_DIR}/scripts"

# Copy migration scripts
print_status "Copying migration scripts to bastion..."
scp -i "${SSH_KEY_PATH_EXPANDED}" \
    scripts/export_mysql_to_postgres.py \
    scripts/transform_coordinates_to_postgis.py \
    scripts/import_postgres.py \
    scripts/validate_migration.py \
    "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/scripts/"

# Copy requirements
print_status "Copying requirements file..."
scp -i "${SSH_KEY_PATH_EXPANDED}" \
    requirements-migration.txt \
    "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/"

# Copy api directory (needed for models and config)
print_status "Copying API directory..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    -e "ssh -i ${SSH_KEY_PATH_EXPANDED}" \
    api/ "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/api/"

# Copy .env file (with database credentials)
print_status "Copying .env file..."
if [[ -f .env ]]; then
    scp -i "${SSH_KEY_PATH_EXPANDED}" .env "${BASTION_USER}@${BASTION_HOST}:${REMOTE_DIR}/.env.local"
    print_status "Creating bastion-specific .env with RDS endpoints..."
    ssh -i "${SSH_KEY_PATH_EXPANDED}" "${BASTION_USER}@${BASTION_HOST}" << 'EOF'
set -e
export AWS_DEFAULT_REGION=eu-west-1

cd /home/ec2-user/postgres-migration

# Get MySQL RDS endpoint from AWS Secrets Manager
MYSQL_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id fastapi-staging-credentials \
    --region eu-west-1 \
    --query SecretString --output text)

MYSQL_HOST=$(echo "$MYSQL_SECRET" | jq -r '.host')
MYSQL_PORT=$(echo "$MYSQL_SECRET" | jq -r '.port')
MYSQL_USER=$(echo "$MYSQL_SECRET" | jq -r '.username')
MYSQL_PASSWORD=$(echo "$MYSQL_SECRET" | jq -r '.password')
MYSQL_DATABASE=$(echo "$MYSQL_SECRET" | jq -r '.dbname')

# Get PostgreSQL RDS endpoint from AWS Secrets Manager
PG_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id trigpointing-postgres-fastapi-staging \
    --region eu-west-1 \
    --query SecretString --output text)

PG_HOST=$(echo "$PG_SECRET" | jq -r '.host')
PG_PORT=$(echo "$PG_SECRET" | jq -r '.port')
PG_USER=$(echo "$PG_SECRET" | jq -r '.username')
PG_PASSWORD=$(echo "$PG_SECRET" | jq -r '.password')
PG_DATABASE=$(echo "$PG_SECRET" | jq -r '.dbname')

# Create .env file with RDS endpoints
cat > .env << ENVEOF
# MySQL RDS (source database for export)
MYSQL_HOST=${MYSQL_HOST}
MYSQL_PORT=${MYSQL_PORT}
MYSQL_USER=${MYSQL_USER}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_NAME=${MYSQL_DATABASE}

# PostgreSQL RDS (target database for import)
DB_HOST=${PG_HOST}
DB_PORT=${PG_PORT}
DB_USER=${PG_USER}
DB_PASSWORD=${PG_PASSWORD}
DB_NAME=${PG_DATABASE}

# For validation script (it needs both)
DATABASE_URL=postgresql+psycopg2://${PG_USER}:${PG_PASSWORD}@${PG_HOST}:${PG_PORT}/${PG_DATABASE}
ENVEOF

echo "✓ Created .env with RDS credentials"
EOF
else
    print_warning "No .env file found locally - will create one on bastion from AWS Secrets Manager"
    ssh -i "${SSH_KEY_PATH_EXPANDED}" "${BASTION_USER}@${BASTION_HOST}" << 'EOF'
set -e
export AWS_DEFAULT_REGION=eu-west-1

cd /home/ec2-user/postgres-migration

# Get MySQL RDS endpoint from AWS Secrets Manager
MYSQL_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id fastapi-staging-credentials \
    --region eu-west-1 \
    --query SecretString --output text)

MYSQL_HOST=$(echo "$MYSQL_SECRET" | jq -r '.host')
MYSQL_PORT=$(echo "$MYSQL_SECRET" | jq -r '.port')
MYSQL_USER=$(echo "$MYSQL_SECRET" | jq -r '.username')
MYSQL_PASSWORD=$(echo "$MYSQL_SECRET" | jq -r '.password')
MYSQL_DATABASE=$(echo "$MYSQL_SECRET" | jq -r '.dbname')

# Get PostgreSQL RDS endpoint from AWS Secrets Manager
PG_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id trigpointing-postgres-fastapi-staging \
    --region eu-west-1 \
    --query SecretString --output text)

PG_HOST=$(echo "$PG_SECRET" | jq -r '.host')
PG_PORT=$(echo "$PG_SECRET" | jq -r '.port')
PG_USER=$(echo "$PG_SECRET" | jq -r '.username')
PG_PASSWORD=$(echo "$PG_SECRET" | jq -r '.password')
PG_DATABASE=$(echo "$PG_SECRET" | jq -r '.dbname')

# Create .env file with RDS endpoints
cat > .env << ENVEOF
# MySQL RDS (source database for export)
MYSQL_HOST=${MYSQL_HOST}
MYSQL_PORT=${MYSQL_PORT}
MYSQL_USER=${MYSQL_USER}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_NAME=${MYSQL_DATABASE}

# PostgreSQL RDS (target database for import)
DB_HOST=${PG_HOST}
DB_PORT=${PG_PORT}
DB_USER=${PG_USER}
DB_PASSWORD=${PG_PASSWORD}
DB_NAME=${PG_DATABASE}

# For validation script (it needs both)
DATABASE_URL=postgresql+psycopg2://${PG_USER}:${PG_PASSWORD}@${PG_HOST}:${PG_PORT}/${PG_DATABASE}
ENVEOF

echo "✓ Created .env with RDS credentials from AWS Secrets Manager"
EOF
fi

print_success "Files copied to bastion"

# Run migration on bastion
print_status "Executing migration on bastion..."
echo "============================================================"

ssh -i "${SSH_KEY_PATH_EXPANDED}" "${BASTION_USER}@${BASTION_HOST}" << 'ENDSSH'
set -e

cd /home/ec2-user/postgres-migration

echo "🔧 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "📦 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements-migration.txt

echo ""
echo "============================================================"
echo "🚀 Starting Migration Process"
echo "============================================================"
echo ""

# Determine which steps to run
EXPORT_ONLY=${EXPORT_ONLY:-false}
IMPORT_ONLY=${IMPORT_ONLY:-false}

if [ "$IMPORT_ONLY" = "false" ]; then
    echo "📤 Step 1: Exporting MySQL data..."
    python3 scripts/export_mysql_to_postgres.py --output-dir mysql_export
    echo ""
    
    echo "🔄 Step 2: Transforming coordinates to PostGIS format..."
    python3 scripts/transform_coordinates_to_postgis.py --input-dir mysql_export
    echo ""
fi

if [ "$EXPORT_ONLY" = "false" ]; then
    echo "📥 Step 3: Importing data to PostgreSQL..."
    python3 scripts/import_postgres.py --input-dir mysql_export
    echo ""
    
    echo "✅ Step 4: Validating migration..."
    python3 scripts/validate_migration.py
    echo ""
fi

echo "============================================================"
echo "✅ Migration completed successfully!"
echo "============================================================"
echo ""
echo "Data export location: /home/ec2-user/postgres-migration/mysql_export"
echo ""
echo "To download the export for backup:"
echo "  scp -r -i ~/.ssh/trigpointing-bastion.pem ec2-user@bastion.trigpointing.uk:/home/ec2-user/postgres-migration/mysql_export ."
echo ""

ENDSSH

print_success "Migration completed on bastion!"
echo ""
print_status "Next steps:"
echo "  1. Review the validation output above"
echo "  2. Test the application against PostgreSQL"
echo "  3. If satisfied, update environment variables to use PostgreSQL"
echo "  4. Deploy updated code"
echo ""

