# Makefile `run` Target Removal and Documentation Update

**Date:** 30 November 2025

## Summary

Removed the `make run` target and updated all documentation to accurately reflect the **staging-connected development workflow** used in practice.

## Changes Made

### 1. Removed Makefile Targets

**Removed:**
- `make run` - Generic uvicorn start without database configuration

**Why:**
- Suggested a local database workflow that isn't used
- Would fail or connect to non-existent database
- Created confusion about proper development setup
- All actual development uses `make run-staging` (staging-connected)

### 2. Documentation Updates

#### README.md (Main Repository README)
**Before:** Showed `make run` as the way to start API development
**After:** Shows actual multi-terminal workflow:
```bash
make postgres-tunnel      # Terminal 1: Database
make redis-tunnel         # Terminal 2: Cache
make run-staging          # Terminal 3: API
```

#### docs/README-fastapi.md (API Documentation)
**Major Changes:**
- Completely rewrote "Local Development Setup" section
- Added clear explanation: "This project uses a staging-connected development workflow"
- Removed references to `.env` files and local database setup
- Added step-by-step guide with 3 terminals for tunnels + API
- Updated "Database Setup" section - clarified no local database needed
- Updated "Docker" section - clarified Docker only used for production and tests

**Removed misleading content:**
- "Set up environment variables" step (not used)
- "Start with Docker Compose (Recommended)" (not how we develop)
- "Or run manually: make run" (didn't work)
- Local database configuration instructions

#### docs/infrastructure/OPENTELEMETRY_GRAFANA.md
**Changed:** Local development section
- Replaced `.env` file approach with `export` statements
- Changed `make run` to `make run-staging`
- Added reminder to start db-tunnel in another terminal

### 3. What Wasn't Changed

**Still referenced in archived documentation:**
- `scripts/archive/` may contain old references (intentionally kept)

**Tests:**
- No test changes needed (tests don't use `make run`)

## Actual Development Workflow (Now Documented)

### Standard Development Session

```bash
# Terminal 1: Database tunnel
make postgres-tunnel

# Terminal 2: Redis tunnel  
make redis-tunnel

# Terminal 3: Run API
make run-staging  # Fetches staging credentials, runs against staging
```

### What `run-staging` Does
1. Fetches staging PostgreSQL credentials from AWS Secrets Manager
2. Fetches staging Auth0 configuration from AWS Secrets Manager
3. Sets environment variables for local ports (5433 for DB, 6380 for Redis)
4. Runs `uvicorn api.main:app --reload` with staging connection

### Benefits of This Approach
- **No local database setup** - Use real staging data
- **Matches production infrastructure** - Same PostgreSQL, Valkey, Auth0
- **Realistic testing** - Real data, real auth, real performance
- **Simplified onboarding** - No complex local setup

## Related Makefile Targets

### Still Available (and used)
- `make run-staging` - Run against staging (primary development)
- `make postgres-tunnel` - Start database tunnel
- `make redis-tunnel` - Start Redis tunnel
- `make test` - Run tests (uses Docker test database)
- `make test-db-start` - Start test database
- `make docker-build` - Build production Docker image

### Also Removed (Previously)
- `make db-tunnel-staging-start/stop` - Old SSH tunnels
- `make db-tunnel-production-start/stop` - Old SSH tunnels
- `make docker-dev`, `make docker-down` - Unused Docker dev
- `make tf-init`, `make tf-plan`, etc. - Unused Terraform
- `make bastion-revoke-my-ip` - Unused security group helper

## Impact Assessment

### ✅ No Breaking Changes
- Nobody used `make run` (would have failed without DB)
- All developers already use `make run-staging`
- Tests unaffected (use `make test` with Docker)

### ✅ Benefits
- **Honest documentation** - Reflects actual practices
- **Clearer onboarding** - New developers see real workflow
- **Less confusion** - No misleading "quick start" that doesn't work
- **Simpler Makefile** - Removed unused target

### 📚 Documentation Now Accurate
- README shows multi-terminal setup
- API docs explain staging-connected workflow
- No references to unsupported local database setup

## Verification

To verify documentation is correct:
```bash
# This should work (actual workflow):
make postgres-tunnel  # Terminal 1
make redis-tunnel     # Terminal 2  
make run-staging      # Terminal 3
curl http://localhost:8000/health  # Should return 200

# This no longer exists:
make run  # Should error: "No rule to make target 'run'"
```

## Rollback Plan

If needed, restore the `run` target:
```makefile
run: ## Run the application locally
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

But this would still require manual environment variable setup and wouldn't match the documented workflow.

## See Also

- [MAKEFILE_CLEANUP_SUMMARY.md](MAKEFILE_CLEANUP_SUMMARY.md) - Previous Makefile cleanup
- [TERRAFORM_MAKEFILE_CLEANUP.md](TERRAFORM_MAKEFILE_CLEANUP.md) - Terraform targets cleanup
- [api/migrations/ALEMBIC_GUIDE.md](api/migrations/ALEMBIC_GUIDE.md) - Database migration workflow
