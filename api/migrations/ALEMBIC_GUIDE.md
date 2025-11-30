gs# Alembic Database Migration Guide

This guide covers everything you need to know about managing database migrations with Alembic for the Trigpointing Platform.

## Table of Contents

- [Quick Start](#quick-start)
- [Local Development Workflow](#local-development-workflow)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Common Tasks](#common-tasks)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Python virtual environment activated: `source venv/bin/activate`
- Alembic is already installed (see `requirements.txt`)
- AWS CLI configured with appropriate credentials
- For remote migrations: SSM tunnel to database running

### Basic Commands

```bash
# See all available migration commands
make help | grep migration

# Create a new migration (auto-detects model changes)
make migration-create MSG="add user preferences table"

# View migration history
make migration-history

# Check current database version
make migration-current

# Apply migrations locally (for testing)
make migration-upgrade

# Rollback one migration locally
make migration-downgrade

# Apply migrations to staging (requires SSM tunnel running)
make migrate-staging

# Apply migrations to production (requires SSM tunnel + confirmation)
make migrate-production

# Check migration status on remote environment
make migrate-status ENV=staging
make migrate-status ENV=production
```

## Local Development Workflow

### 1. Making Model Changes

When you modify SQLAlchemy models in `api/models/`, Alembic can automatically detect the changes:

```python
# Example: Add a new column to User model
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    email = Column(String(255), nullable=False)
    # New field
    last_login = Column(DateTime, nullable=True)  # <-- New
```

### 2. Generate Migration

```bash
make migration-create MSG="add last_login to user table"
```

This will:
- Create a new file in `alembic/versions/` with a unique revision ID
- Auto-detect changes between your models and the database
- Format the file with black
- Show you the path to review

### 3. Review the Generated Migration

**CRITICAL**: Always review auto-generated migrations before applying them!

```bash
# The file will be at: alembic/versions/<revision>_add_last_login_to_user_table.py
```

Check for:
- Correct column types
- Proper NULL/NOT NULL constraints
- Index creation/deletion
- Foreign key changes
- Any unexpected changes

Edit the migration file if needed. Common adjustments:
- Add data migration logic
- Set default values for existing rows
- Add custom SQL operations

### 4. Apply Migration Locally

```bash
# Apply all pending migrations
make migration-upgrade

# Or use alembic directly
alembic upgrade head
```

### 5. Test Your Changes

Run your application and tests to ensure everything works:

```bash
make test
```

### 6. Rollback if Needed

```bash
# Rollback one migration
make migration-downgrade

# Or rollback to a specific revision
alembic downgrade <revision_id>
```

## Staging Deployment

**Recommended Approach: Make Targets with SSM Tunnel**

This is the simplest and most reliable method for applying migrations to staging.

### 1. Start the SSM Tunnel

In a separate terminal window:

```bash
make db-tunnel-staging-ssm-start
```

Keep this terminal open - it maintains the tunnel connection.

### 2. Apply Migrations

In your main terminal:

```bash
# Apply all pending migrations to staging
make migrate-staging
```

This will:
- Automatically fetch staging credentials from AWS Secrets Manager
- Show "🔍 Alembic running against: STAGING" to confirm the environment
- Apply all pending migrations
- Display the current migration status

### 3. Verify

```bash
# Check current migration status
make migrate-status ENV=staging
```

### Alternative: Manual Alembic with Environment Variables

If you prefer more control, you can set environment variables manually:

```bash
# Start tunnel (in separate terminal)
make db-tunnel-staging-ssm-start

# Fetch credentials and run alembic
SECRET_JSON=$(aws --region eu-west-1 secretsmanager get-secret-value \
  --secret-id fastapi-staging-postgres-credentials \
  --query SecretString --output text)

DB_HOST=localhost \
DB_PORT=5433 \
DB_USER=$(echo "$SECRET_JSON" | jq -r '.username') \
DB_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password') \
DB_NAME=$(echo "$SECRET_JSON" | jq -r '.dbname') \
ENV_NAME=STAGING \
alembic upgrade head
```

## Production Deployment

**CRITICAL**: Always test migrations on staging first!

### Pre-Deployment Checklist

- [ ] Migrations tested and verified on staging
- [ ] Database backup created (if applicable)
- [ ] Rollback plan documented
- [ ] Downtime window communicated (if needed)
- [ ] Team notified

### Deployment Steps

**Recommended Approach: Make Targets with SSM Tunnel**

1. **Start the SSM Tunnel**

In a separate terminal window:

```bash
make db-tunnel-staging-ssm-start  # Uses same tunnel, different credentials
```

2. **Apply migrations with confirmation:**

```bash
make migrate-production
```

You will be prompted to type `production` to confirm. This provides a safety check.

The command will:
- Automatically fetch production credentials from AWS Secrets Manager
- Show "🔍 Alembic running against: PRODUCTION" to confirm the environment
- Apply all pending migrations
- Display the current migration status

3. **Verify:**

```bash
# Check migration status
make migrate-status ENV=production

# Test the application
curl https://api.trigpointing.uk/health
```

### Alternative: Manual Approach

If you prefer direct control:

```bash
# Start tunnel (in separate terminal)
make db-tunnel-staging-ssm-start

# Fetch production credentials and apply
SECRET_JSON=$(aws --region eu-west-1 secretsmanager get-secret-value \
  --secret-id fastapi-production-postgres-credentials \
  --query SecretString --output text)

DB_HOST=localhost \
DB_PORT=5433 \
DB_USER=$(echo "$SECRET_JSON" | jq -r '.username') \
DB_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password') \
DB_NAME=$(echo "$SECRET_JSON" | jq -r '.dbname') \
ENV_NAME=PRODUCTION \
alembic upgrade head
```

### Rollback in Production

If something goes wrong:

```bash
# Rollback one migration (with tunnel still running)
DB_HOST=localhost DB_PORT=5433 \
DB_USER=<user> DB_PASSWORD=<pass> DB_NAME=<db> \
ENV_NAME=PRODUCTION \
alembic downgrade -1

# Or use local migration commands if you have credentials set
alembic downgrade -1
```

## Common Tasks

### Create a Manual Migration

Sometimes you need to write custom SQL that can't be auto-generated:

```bash
# Create empty migration
alembic revision -m "add custom indexes for performance"
```

Then edit the generated file:

```python
def upgrade() -> None:
    """Add performance indexes."""
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_tlog_created_at 
        ON tlog (created_at DESC);
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_user_email_lower 
        ON user (LOWER(email));
    """)


def downgrade() -> None:
    """Remove performance indexes."""
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_tlog_created_at;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_email_lower;")
```

### Check Pending Migrations

```bash
make migration-check
# Exits 0 if up-to-date, 1 if pending migrations exist
```

### View SQL Without Executing

```bash
# See what SQL will be run
alembic upgrade head --sql

# Or for a specific revision
alembic upgrade <revision> --sql
```

### Merge Migration Branches

If multiple developers created migrations in parallel:

```bash
# List all heads
alembic heads

# Create a merge migration
alembic merge -m "merge parallel migrations" <rev1> <rev2>
```

## Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic's autogenerate is smart but not perfect. It might:
- Miss some types of changes (like CHECK constraints)
- Generate unnecessary operations
- Not handle data migrations

**Always** review the generated migration file before applying it.

### 2. Test Migrations on Staging First

Never apply untested migrations directly to production.

### 3. Make Small, Focused Migrations

Instead of:
```bash
make migration-create MSG="big refactor"
```

Do:
```bash
make migration-create MSG="add user preferences table"
make migration-create MSG="add indexes to user table"
make migration-create MSG="migrate old user data to preferences"
```

### 4. Include Both Upgrade and Downgrade

Always implement both `upgrade()` and `downgrade()` functions, even if you don't plan to rollback. This makes the migration history clear.

### 5. Handle Data Migrations Carefully

When renaming or restructuring data:

```python
def upgrade() -> None:
    """Migrate user location data to new format."""
    # 1. Add new columns
    op.add_column('user', sa.Column('country_code', sa.String(2), nullable=True))
    
    # 2. Migrate existing data
    op.execute("""
        UPDATE user 
        SET country_code = 'GB' 
        WHERE country = 'United Kingdom'
    """)
    
    # 3. Make NOT NULL after data is migrated
    op.alter_column('user', 'country_code', nullable=False)
    
    # 4. Remove old column
    op.drop_column('user', 'country')
```

### 6. Use CONCURRENTLY for Indexes (PostgreSQL)

```python
def upgrade() -> None:
    """Add index without locking the table."""
    # Use raw SQL with CONCURRENTLY
    op.execute("CREATE INDEX CONCURRENTLY idx_user_email ON user(email);")
    
    # Instead of:
    # op.create_index('idx_user_email', 'user', ['email'])
```

### 7. Document Complex Migrations

Add detailed docstrings explaining:
- Why the migration is needed
- What data is affected
- Any manual steps required
- Expected downtime (if any)

### 8. Commit Migrations with Code Changes

Include the migration file in the same commit as the model changes:

```bash
git add api/models/user.py
git add alembic/versions/*_add_user_preferences.py
git commit -m "Add user preferences feature"
```

## Troubleshooting

### "Multiple head revisions are present"

You have parallel migration branches. Merge them:

```bash
alembic heads
alembic merge -m "merge branches" <rev1> <rev2>
```

### "Can't locate revision identified by 'xyz'"

Your local alembic history doesn't match the database:

```bash
# Check what revision is in the database
alembic current

# Check your local migration history
alembic history

# You may need to pull latest migrations from git
git pull origin develop
```

### "Target database is not up to date"

Your database is ahead of your code:

```bash
alembic current  # Shows database revision
alembic heads    # Shows latest revision in code

# Pull latest migrations or checkout correct branch
git pull origin develop
```

### Auto-generate Creates Unwanted Changes

Alembic detected differences between models and database:

```bash
# Review what it detected
alembic upgrade head --sql

# Common causes:
# 1. Model changes not reflected in previous migrations
# 2. Manual database changes not captured in migrations
# 3. Alembic can't detect certain changes (e.g., CHECK constraints)
```

### Migration Fails Halfway

```bash
# Check current state
alembic current

# Alembic should be at the previous revision
# You may need to manually fix database state

# Check migration history
alembic history --verbose

# Try to finish the migration manually or rollback
alembic downgrade -1
```

### "relation already exists"

The migration is trying to create something that already exists:

```bash
# Check database state manually
psql $DATABASE_URL -c "\d tablename"

# Fix the migration to check if exists:
# In Python migration:
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add IF NOT EXISTS checks
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'tablename' not in inspector.get_table_names():
        op.create_table(...)
```

## Additional Resources

- [Alembic Official Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Project README: `/docs/README-fastapi.md`
- Database Schema Documentation: `/docs/database/schema_documentation.md`

## Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review Alembic's verbose output: `alembic upgrade head --verbose`
3. Check the database state: `alembic current`
4. Review migration history: `alembic history`
5. Ask the team in Slack/Discord

## Migration History

### 726a21695c73 - remove_audit_tables_and_gc_columns (2025-11-30)

Remove legacy audit tables and Geocaching.com integration columns that are no longer used in the modern Auth0-based authentication system.

**Tables removed**:
- `audit` - Legacy audit logging (1 row of data)
- `audit_simple` - Simplified audit logging (0 rows)

**Columns removed from user table**:
- `gc_licence_ind`, `gc_licence_timestamp`
- `gc_auth_ind`, `gc_auth_challenge`, `gc_auth_timestamp`
- `gc_premium_ind`, `gc_premium_timestamp`

**Impact**: Removes unused legacy features. No functional impact on current system. Note: Admin tracking fields (admin_user_id, admin_timestamp, admin_ip_addr) remain on the trig table and are unaffected.

**Code changes**: Removed `has_gc_auth()` and `has_gc_premium()` functions from `api/crud/user.py`.

### 0e59c3885358 - make_tlog_location_nullable (2025-11-04)

Make location fields (osgb_eastings, osgb_northings, osgb_gridref) nullable in tlog table to allow logs without specific location data.

**Impact**: Allows creation of logs without mandatory location data.

**Converted from**: `api/migrations/001_make_tlog_location_nullable.sql`

