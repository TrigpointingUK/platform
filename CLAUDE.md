# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

Monorepo for **Trigpointing.uk**, a long-running trigpoint/surveying community site. Multiple deployable units share infrastructure:

- [api/](api/) — FastAPI (Python 3.11+) REST API. Entry point [api/main.py](api/main.py); endpoints under [api/api/v1/](api/api/v1/); business logic in [api/services/](api/services/); SQLAlchemy models in [api/models/](api/models/); CRUD in [api/crud/](api/crud/); Pydantic schemas in [api/schemas/](api/schemas/); tests in [api/tests/](api/tests/).
- [web/](web/) — React 19 + TypeScript SPA built with Vite 8, TanStack Query, React Router 7, Auth0 PKCE, Tailwind v4. Source under [web/src/](web/src/).
- [forum/](forum/) — phpBB 3.3 with Auth0 SSO (production only, no staging).
- [wiki/](wiki/) — MediaWiki with Auth0 SSO (production only, no staging).
- [terraform/](terraform/) — AWS IaC, split into [common/](terraform/common/), [staging/](terraform/staging/), [production/](terraform/production/), and reusable [modules/](terraform/modules/). ECS Fargate behind ALB, RDS PostgreSQL, Valkey (Redis-compatible) ElastiCache, Cloudflare in front.
- [Ansible/](Ansible/) — bastion host and server config.
- [alembic/](alembic/) — DB migrations (PostgreSQL; mid-2025 migration from MySQL is reflected in `docs/POSTGRES_MIGRATION_COMPLETE.md`).
- [dbt/](dbt/) — analytics models built against the same Postgres.
- [scripts/](scripts/) — one-off maintenance scripts and Auth0 utilities.

Branch flow: **develop → staging (trigpointing.me)**, **main → production (trigpointing.uk)**. CI/CD auto-deploys on push.

## Common commands

All Python commands assume the venv is active: `source venv/bin/activate`.

### CI gate (run before every push to develop or main)

```bash
make ci
```

Runs (in order): terraform fmt + validate, test DB up, black/isort/flake8/mypy/bandit, full pytest, web lint/type-check/test, test DB down. **CI must pass locally before pushing** — see `.cursor/rules/strict-pre-push-validation.md`. The pre-commit hooks ([.pre-commit-config.yaml](.pre-commit-config.yaml)) run a subset on commit.

### Backend (Python / FastAPI)

```bash
make test-db-start          # spin up local Postgres test container (required for tests)
make test                   # pytest -n auto
make test-cov               # tests + HTML coverage in htmlcov/
make test-db-stop

make format                 # black + isort + terraform fmt
make lint                   # flake8 api
make type-check             # mypy api --ignore-missing-imports
make security               # bandit + pip-audit

# Run a single test:
pytest api/tests/path/to/test_x.py::TestClass::test_name -xvs
```

### Run API locally against staging data

Easiest: `make dev-stack` brings up postgres-tunnel, redis-tunnel, FastAPI (`run-staging`), and the Vite dev server in a single tmux session (2x2 grid). `make dev-stack-attach` to view, `make dev-stack-stop` to tear down.

Manually: open separate terminals for `make postgres-tunnel` and `make redis-tunnel` (SSM port-forwarding via the bastion), then `make run-staging` starts uvicorn with `--reload` on `127.0.0.1:8000` using staging credentials pulled from Secrets Manager.

`make bastion-ssm-shell` opens an SSM shell on the bastion. `make ecs-exec-phpbb` / `make ecs-exec-mediawiki` exec into the running ECS tasks.

### Database access from scripts and queries

When writing scripts or running ad-hoc queries against staging or production PostgreSQL, follow the pattern documented in the **`db-access` skill** ([`.claude/skills/db-access/SKILL.md`](.claude/skills/db-access/SKILL.md)): user keeps `make postgres-tunnel` running in a terminal, scripts source `scripts/set-db-env-{staging,production}.sh`, then read `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` from the environment. Both environments share one RDS instance — switching is just re-sourcing the env script. Never hardcode hostnames, never fetch secrets a different way.

### Database migrations

```bash
make migration-create MSG="description"   # alembic revision --autogenerate
make migration-history
make migrate-status ENV=staging           # or ENV=production
make migrate-staging                      # requires postgres-tunnel
make migrate-production                   # requires typing 'production' to confirm
make downgrade-staging                    # rolls back one revision
```

Any migration that runs `INSERT`/`UPDATE`/`DELETE` **must log `result.rowcount`** for each statement — `make migrate-staging` output is the audit trail.

### Web (React / Vite)

```bash
make web-install            # npm ci
make web-dev                # vite dev server on http://localhost:5173
make web-build
make web-test               # vitest run
make web-lint               # eslint
make web-type-check         # tsc --noEmit

# Single web test:
cd web && npx vitest run path/to/test.test.ts -t "test name"
```

Note `web/package.json` requires Node ≥ 24; the README still mentions Node 20 but the engines field is authoritative.

### dbt analytics

`make dbt-staging` / `make dbt-production` (both need `postgres-tunnel`).

## Project conventions

### Always apply changes to both environments

For shared components — **API, Auth0 (infra + Actions), and the SPA** — any change to staging must also be applied to production (and vice versa) unless the user explicitly says otherwise. The forum and wiki run **production only**, so don't fabricate staging counterparts for them.

### British English throughout

Spelling, copy, identifiers in user-facing surfaces — favour, colour, organisation, etc.

### AWS resource lifecycle

- **Reading** AWS state with `aws` CLI is fine (`describe`, `list`, `get`).
- **Creating** AWS resources goes through Terraform (preferred) or Ansible. Don't `aws ... create-*` without explicit user consent.
- **Deleting** is allowed when the user explicitly asks.
- The origin server only accepts HTTPS; HTTP→HTTPS redirects are handled at Cloudflare.

### SQLAlchemy: joins with aggregations

When a query joins multiple tables and selects columns from joined tables (especially with aggregations), establish the left side explicitly with `.select_from(BaseTable)`. Cover the query with an integration test that populates **all** joined tables (e.g. `trig_type`, `trig_category`) — unit tests with mocks have masked broken joins here before.

### Tailwind is v4, not v3

`web/` uses `tailwindcss@^4.2.x` with the Vite plugin. CSS uses `@import "tailwindcss"` (not the v3 `@tailwind base/components/utilities` directives). When debugging styling, first check whether you've drifted into v3-era patterns — that has been the root cause of multiple "broken" styles.

### Domain note: `public_ind` is photo licensing

Both `user.public_ind` (default for new uploads) and `tphoto.public_ind` (per-photo) describe **licensing**, not profile visibility. `'Y'` means Public Domain; anything else means a non-transferable display licence to TUK with all other rights retained by the photographer. Do **not** treat it as a profile-visibility flag in analytics or reporting.

### Auth

Auth0 with PKCE everywhere. SPA holds tokens in memory (no localStorage, no cookies) and sends `Authorization: Bearer …` to the API. CORS allows the SPA origin without credentials.

## Reference docs in this repo

- [docs/README-fastapi.md](docs/README-fastapi.md) — API setup details
- [docs/LOCAL_ENV.md](docs/LOCAL_ENV.md) — local environment setup
- [docs/database/](docs/database/) — schema documentation
- [docs/infrastructure/](docs/infrastructure/) — deployment / Terraform notes
- [web/README.md](web/README.md), [web/TESTING.md](web/TESTING.md), [web/COMPONENT_GUIDE.md](web/COMPONENT_GUIDE.md) — web app specifics
