# Migration Targets Cleanup

**Date:** 30 November 2025

## Summary

Removed confusing and unused migration-related Makefile targets that assumed a local PostgreSQL database setup, which is not part of the actual development workflow.

## Problem Statement

The Makefile had two sets of overlapping migration targets:
1. **Legacy `db-*` targets** - Ambiguous, unclear which database they targeted
2. **Local `migration-*` targets** - Assumed local PostgreSQL database (not used)
3. **Remote `migrate-*` targets** - Used for staging/production deployments (the actual workflow)

This caused confusion about:
- Which target to use when
- Which database the target would affect
- What the actual development workflow was

## Changes Made

### Removed Targets

| Target | What it did | Why removed |
|--------|-------------|-------------|
| `db-migrate` | `alembic upgrade head` | Ambiguous - which database? |
| `db-migration` | `alembic revision --autogenerate -m "$(msg)"` | Confusing lowercase `msg`, use `migration-create` instead |
| `migration-upgrade` | Apply migrations locally | No local PostgreSQL in dev workflow |
| `migration-downgrade` | Rollback local migration | Use CLI directly for troubleshooting |
| `migration-current` | Show local DB revision | Not used, CLI for troubleshooting |
| `migration-check` | Check local DB up-to-date | Not used by tests or CI |

**Total removed:** 6 targets, ~40 lines of Makefile

### Kept Targets (Actually Used)

| Target | Purpose | When to use |
|--------|---------|-------------|
| `migration-create` | Create new migration file | Developing schema changes |
| `migration-history` | Show all migrations | Reference/documentation |
| `migrate-staging` | Deploy to staging | After creating migration |
| `migrate-production` | Deploy to production | After staging validation |
| `migrate-status` | Check remote status | Verify deployments |

## Actual Development Workflow

### Creating a Migration

```bash
# 1. Modify SQLAlchemy models in api/models/
# 2. Create migration file
make migration-create MSG="add user preferences"

# 3. Review generated file in alembic/versions/
# 4. Edit if needed

# 5. Test on staging
make db-tunnel-staging-ssm-start  # Terminal 1
make migrate-staging              # Terminal 2

# 6. Commit
git add alembic/versions/xxx_add_user_preferences.py
git commit -m "Add user preferences migration"
```

### Deploying to Production

```bash
# 1. Ensure tunnel is running
make db-tunnel-staging-ssm-start  # Uses same tunnel, different creds

# 2. Deploy with confirmation
make migrate-production  # Requires typing "production"

# 3. Verify
make migrate-status ENV=production
```

### Troubleshooting (CLI)

For problems, use Alembic CLI directly:

```bash
# View migration history
alembic history

# Check current revision
alembic current

# Rollback one migration
alembic downgrade -1

# View SQL without executing
alembic upgrade head --sql
```

## Key Principles

1. **Makefiles are for happy-days** - When things go wrong, use CLI directly
2. **No local PostgreSQL** - Development uses staging-connected workflow
3. **Tests are independent** - Use Docker Compose test database
4. **Environment awareness** - Targets clearly indicate staging vs production

## Documentation Updates

Updated `api/migrations/ALEMBIC_GUIDE.md`:
- Removed references to deleted targets
- Updated Quick Start section
- Emphasized `migrate-staging` for testing migrations
- Clarified rollback procedures use CLI
- Updated examples and workflows

## Verification

Check available migration targets:
```bash
make help | grep -E "migration|migrate"
```

Should show only:
```
migration-create     Create a new migration
migration-history    Show migration history
migrate-staging      Apply migrations to staging
migrate-production   Apply migrations to production
migrate-status       Check migration status
```

## Rationale

### Why Remove Local Database Targets?

1. **Nobody uses a local PostgreSQL database**
   - Development workflow: `make run-staging` (connects to staging)
   - Tests: Docker Compose test database (managed separately)
   - No `.env` file setup for local database

2. **Targets were ambiguous**
   - `db-migrate` - which database? staging? production? local?
   - `migration-upgrade` - assumes local DB exists
   - Created confusion and potential for mistakes

3. **Redundant with CLI**
   - `migration-current` → `alembic current`
   - `migration-check` → `alembic current` + compare
   - CLI is more flexible for troubleshooting

4. **Not used by tests or CI**
   - Checked: none of these targets called by `make test` or `make ci`
   - Tests handle their own database setup via Docker Compose

### Why Keep These Targets?

- **`migration-create`** - Frequently used, validates MSG parameter
- **`migration-history`** - Convenient reference
- **`migrate-staging`** - Core workflow, handles credentials automatically
- **`migrate-production`** - Core workflow, includes safety confirmation
- **`migrate-status`** - Quick verification of deployments

## Breaking Changes

### ❌ These Commands No Longer Work

```bash
make db-migrate          # Use: make migrate-staging (or alembic upgrade head)
make db-migration        # Use: make migration-create
make migration-upgrade   # Use: make migrate-staging (or alembic upgrade head)
make migration-downgrade # Use: alembic downgrade -1
make migration-current   # Use: alembic current
make migration-check     # Use: alembic current (compare manually)
```

### ✅ Migration Path

For each removed target, either:
1. Use the `migrate-*` target for staging/production
2. Use Alembic CLI directly for troubleshooting

## Benefits

1. **Less Confusion** - Clear distinction between dev (staging-connected) and deployment
2. **Fewer Targets** - Simpler Makefile, easier to learn
3. **Honest Documentation** - Reflects actual workflow
4. **Safety** - Less chance of accidentally running against wrong database
5. **Flexibility** - CLI always available for edge cases

## Related Changes

This cleanup is part of a larger Makefile rationalization effort:

- **Previous:** [MAKEFILE_CLEANUP_SUMMARY.md](MAKEFILE_CLEANUP_SUMMARY.md) - Removed deprecated SSH tunnel scripts
- **Previous:** [TERRAFORM_MAKEFILE_CLEANUP.md](TERRAFORM_MAKEFILE_CLEANUP.md) - Removed unused tf-* targets  
- **Previous:** [MAKEFILE_RUN_TARGET_CLEANUP.md](MAKEFILE_RUN_TARGET_CLEANUP.md) - Removed make run target

## See Also

- [api/migrations/ALEMBIC_GUIDE.md](api/migrations/ALEMBIC_GUIDE.md) - Complete migration guide
- [DATABASE_CLEANUP_SUMMARY.md](DATABASE_CLEANUP_SUMMARY.md) - Database cleanup template
- [docs/README-fastapi.md](docs/README-fastapi.md) - API documentation
