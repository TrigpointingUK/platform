# Tunnel Target Renaming for Shared Infrastructure

**Date:** 30 November 2025

## Summary

Renamed tunnel-related Makefile targets to accurately reflect that PostgreSQL and Redis/Valkey are shared infrastructure resources used by both staging and production, not environment-specific services.

## Problem Statement

The original target names implied that database and cache were environment-specific:
- `db-tunnel-staging-ssm-start` - Suggested a staging-only database
- `redis-tunnel-staging-ssm-start` - Suggested a staging-only cache
- `redis-cli-staging` - Suggested staging-specific Redis CLI

**Reality:** The platform has:
- **One shared PostgreSQL RDS instance** - Used by both staging and production
- **One shared Valkey (Redis) instance** - Used by both staging and production

The old names were misleading and caused confusion about infrastructure architecture.

## Changes Made

### Target Renames

| Old Name | New Name | Notes |
|----------|----------|-------|
| `db-tunnel-staging-ssm-start` | `postgres-tunnel` | Clarifies it's PostgreSQL, shared resource |
| `redis-tunnel-staging-ssm-start` | `redis-tunnel` | Clarifies shared Valkey/Redis |
| `redis-cli-staging` | `redis-cli` | Connects to shared instance |

### Updated Targets

**Direct references updated:**
- `run-staging` - Updated comment and help text
- `migrate-staging` - Updated comment
- `migrate-production` - Updated comment  
- `.PHONY` list - Updated target names

### Enhanced Help Text

Added clarification in tunnel targets:
```makefile
postgres-tunnel: ## Start SSM tunnel to shared PostgreSQL RDS → localhost:5433
	...
	echo "💡 Note: This connects to the shared PostgreSQL instance (used by both staging and production)"

redis-tunnel: ## Start SSM tunnel to shared Valkey (Redis) → localhost:6379
	...
	echo "💡 Note: This connects to the shared Valkey instance (used by both staging and production)"
```

## Architecture Clarification

### Shared Resources

```
┌─────────────────────┐
│  Staging API (ECS)  │
│  trigpointing.me    │
└──────────┬──────────┘
           │
           ├──────────────────┐
           │                  │
           ▼                  ▼
    ┌──────────────┐   ┌────────────┐
    │ PostgreSQL   │   │   Valkey   │
    │ RDS (shared) │   │  (shared)  │
    └──────┬───────┘   └──────┬─────┘
           │                  │
           ├──────────────────┘
           │
           ▼
┌─────────────────────┐
│ Production API (ECS)│
│  trigpointing.uk    │
└─────────────────────┘
```

### Database Segregation

- **Same PostgreSQL instance**
- **Different databases:**
  - Staging uses: `trigpoin_trigs` with staging credentials
  - Production uses: `trigpoin_trigs` with production credentials
- **Credentials from AWS Secrets Manager:**
  - `fastapi-staging-postgres-credentials`
  - `fastapi-production-postgres-credentials`

### Cache Segregation

- **Same Valkey instance**
- **Different key prefixes:**
  - Staging uses: Keys prefixed with environment identifier
  - Production uses: Keys prefixed with environment identifier
- **Single endpoint:** Fetched from Terraform common infrastructure

## Updated Workflows

### Development (No Change in Behavior)

```bash
# Terminal 1: Database tunnel
make postgres-tunnel

# Terminal 2: Cache tunnel
make redis-tunnel

# Terminal 3: Run API against staging
make run-staging
```

### Migration Deployment (No Change in Behavior)

```bash
# Terminal 1: Start tunnel (connects to shared PostgreSQL)
make postgres-tunnel

# Terminal 2: Deploy to staging
make migrate-staging

# Or deploy to production (same tunnel, different credentials)
make migrate-production
```

## Documentation Updates

Updated all references across 7 files:

1. **Makefile** - Target definitions, comments, help text
2. **README.md** - Main development workflow
3. **docs/README-fastapi.md** - Local development setup, clarified shared infrastructure
4. **api/migrations/ALEMBIC_GUIDE.md** - All migration examples
5. **docs/infrastructure/OPENTELEMETRY_GRAFANA.md** - Local dev examples
6. **MAKEFILE_CLEANUP_SUMMARY.md** - Historical reference
7. **MAKEFILE_RUN_TARGET_CLEANUP.md** - Historical reference
8. **MIGRATION_TARGETS_CLEANUP.md** - Historical reference

## Benefits

1. **Clarity** - Names reflect actual architecture
2. **Shorter** - `postgres-tunnel` vs `db-tunnel-staging-ssm-start`
3. **Accurate** - No false implication of environment-specific resources
4. **Onboarding** - New developers understand infrastructure correctly
5. **Documentation** - Technical debt removed

## Breaking Changes

### ❌ Old Commands No Longer Work

```bash
make db-tunnel-staging-ssm-start  # No longer exists
make redis-tunnel-staging-ssm-start  # No longer exists
make redis-cli-staging  # No longer exists
```

### ✅ New Commands

```bash
make postgres-tunnel  # Start tunnel to shared PostgreSQL
make redis-tunnel     # Start tunnel to shared Valkey/Redis
make redis-cli        # Connect to shared Valkey via tunnel
```

## Migration Guide for Developers

### Update Your Muscle Memory

**Before:**
```bash
make db-tunnel-staging-ssm-start
make redis-tunnel-staging-ssm-start
make run-staging
```

**After:**
```bash
make postgres-tunnel
make redis-tunnel
make run-staging
```

### Update Scripts/Aliases

If you have personal scripts or shell aliases:

```bash
# Update aliases in ~/.bashrc or ~/.zshrc
alias pgtunnel='make postgres-tunnel'  # was: db-tunnel-staging-ssm-start
alias redistunnel='make redis-tunnel'  # was: redis-tunnel-staging-ssm-start
```

### IDE Terminal Sessions

If you have saved terminal commands in your IDE:
- Update bookmarks/saved commands to use new target names
- Update run configurations that reference old names

## Technical Details

### No Functional Changes

- **Same AWS SSM tunnels** - Implementation unchanged
- **Same ports** - localhost:5433 (PostgreSQL), localhost:6379 (Redis)
- **Same credentials** - Fetched from same AWS Secrets Manager secrets
- **Same behavior** - Tunnels work identically

### What Changed

- **Target names only** - More accurate naming
- **Help text** - Added clarification about shared resources
- **Comments** - Updated to reflect architecture

## Verification

Check available targets:
```bash
make help | grep tunnel
```

Should show:
```
postgres-tunnel      Start SSM tunnel to shared PostgreSQL RDS → localhost:5433
redis-tunnel         Start SSM tunnel to shared Valkey (Redis) → localhost:6379
```

Test workflow:
```bash
# Terminal 1
make postgres-tunnel  # Should connect successfully

# Terminal 2
make redis-tunnel     # Should connect successfully

# Terminal 3
make run-staging      # Should start API
curl http://localhost:8000/health  # Should return 200
```

## Related Changes

This renaming is part of ongoing Makefile cleanup:

1. [MAKEFILE_CLEANUP_SUMMARY.md](MAKEFILE_CLEANUP_SUMMARY.md) - Removed deprecated SSH tunnels
2. [TERRAFORM_MAKEFILE_CLEANUP.md](TERRAFORM_MAKEFILE_CLEANUP.md) - Removed unused tf-* targets
3. [MAKEFILE_RUN_TARGET_CLEANUP.md](MAKEFILE_RUN_TARGET_CLEANUP.md) - Removed make run target
4. [MIGRATION_TARGETS_CLEANUP.md](MIGRATION_TARGETS_CLEANUP.md) - Removed local DB migration targets

## Future Considerations

### If Infrastructure Separates

If staging and production get separate databases in the future:
- Could reintroduce environment-specific targets
- Or keep generic names with ENV parameter: `make postgres-tunnel ENV=staging`
- Current naming still works (tunnel connects to shared instance, credentials determine access)

### Naming Philosophy

Going forward, prefer:
- **Resource-based names** (`postgres-tunnel`, `redis-tunnel`) over environment names
- **Shorter names** for frequently-used targets
- **Accurate names** that match architecture
- **Generic names** when resources are shared

## Rollback Plan

If needed, restore old target names:

```makefile
db-tunnel-staging-ssm-start: postgres-tunnel  ## Alias for backward compatibility

redis-tunnel-staging-ssm-start: redis-tunnel  ## Alias for backward compatibility

redis-cli-staging: redis-cli  ## Alias for backward compatibility
```

This creates aliases that forward to new targets for backward compatibility.

## See Also

- [Makefile](Makefile) - All current targets
- [api/migrations/ALEMBIC_GUIDE.md](api/migrations/ALEMBIC_GUIDE.md) - Migration workflow
- [docs/README-fastapi.md](docs/README-fastapi.md) - API documentation
- [terraform/common/](terraform/common/) - Common infrastructure (shared resources)
