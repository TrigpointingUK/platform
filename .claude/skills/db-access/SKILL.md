---
name: db-access
description: Connect to staging or production PostgreSQL for queries, investigation, migration prep, user-support questions, or cross-environment comparisons. Both environments live on a single shared RDS instance reached via an SSM tunnel through the bastion. Use whenever a task requires reading or comparing data in the live databases.
---

# Database access (staging / production PostgreSQL)

## Connection model

- **One shared RDS instance** hosts both `staging` and `production` databases. They differ only by `DB_NAME` (and credentials).
- Reached via SSM port-forward through the bastion → `localhost:5433`.
- Credentials live in AWS Secrets Manager: `fastapi-staging-postgres-credentials` and `fastapi-production-postgres-credentials`.
- Helper scripts: [scripts/set-db-env-staging.sh](../../../scripts/set-db-env-staging.sh) and [scripts/set-db-env-production.sh](../../../scripts/set-db-env-production.sh) fetch the secret and `export` `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME/ENVIRONMENT` into the current shell. They must be **sourced**, not executed.

## Preflight (run every time)

### 1. Tunnel must be up

The tunnel is a long-running foreground process and **must be started by the user** in a separate terminal — do not try to launch `make postgres-tunnel` from inside a Claude turn (it will hang the turn). Just check it:

```bash
pg_isready -h localhost -p 5433
# expected: "localhost:5433 - accepting connections"
```

If it isn't up, ask the user to run `make postgres-tunnel` in another terminal, then continue.

### 2. Source the right env

```bash
source scripts/set-db-env-staging.sh        # default for exploration
source scripts/set-db-env-production.sh     # warn the user; see safety section
```

Each source overwrites the previous values, so switching environments mid-session is just re-sourcing.

### 3. Connect

```bash
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -c "SELECT count(*) FROM trig"
```

For multi-statement queries use a heredoc:

```bash
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
SELECT trig_type_id, count(*) FROM trig GROUP BY 1 ORDER BY 2 DESC LIMIT 5;
SQL
```

## Cross-environment queries

Because both DBs live on the same RDS instance, the recipe is: dump from one side as TSV, `\copy` into a temp table on the other side, run the diff in SQL.

**Example — count of `trig.id` rows in production not in staging:**

```bash
# Make sure tunnel is up first

source scripts/set-db-env-production.sh
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -c "COPY (SELECT id FROM trig ORDER BY id) TO STDOUT" > /tmp/prod_trig_ids.tsv

source scripts/set-db-env-staging.sh
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<'SQL'
CREATE TEMP TABLE prod_ids (id BIGINT PRIMARY KEY);
\copy prod_ids FROM '/tmp/prod_trig_ids.tsv'
SELECT count(*) AS in_prod_not_in_staging
FROM   prod_ids p
WHERE  NOT EXISTS (SELECT 1 FROM trig t WHERE t.id = p.id);
SQL

rm /tmp/prod_trig_ids.tsv
```

Same skeleton works for any "rows in X not in Y" or "rows differing between X and Y" question — adapt the SELECT and the diff predicate.

## Safety norms

- **Reads** in either environment: fine.
- **Always show the user the SQL** before running it on production. No exceptions.
- **Writes / DDL on production**: NEVER ad-hoc. Schema changes go through Alembic (`make migrate-production`, which prompts for a typed `production` confirmation). Data fixes go through a reviewed migration or a one-off script the user has approved.
- **Writes on staging**: confirm with the user; prefer a migration even when "just experimenting" so the change is reproducible.
- **Mark production output with ⚠️** in your response so the env is unambiguous to the user.
- Never echo `$DB_PASSWORD` or write it to a file. The env scripts already mask it in their own output.
- Clean up `/tmp` files containing data extracts when you're done.

## Useful pointers

- Schema reference: `docs/database/schema_documentation.md` (38 tables — `user`, `trig`, `tlog`, `tphoto`, `attr/attrval`, `place/town/county`, etc.).
- Domain note: `user.public_ind` and `tphoto.public_ind` are **photo licensing** flags, not profile-visibility. `'Y'` = Public Domain; anything else = non-transferable display licence to TUK.
- Migration commands: see the Makefile (`migration-create`, `migrate-staging`, `migrate-production`, `migrate-status`, `downgrade-staging`).
- Any migration with `INSERT/UPDATE/DELETE` must log `result.rowcount` per statement — `make migrate-staging`'s output is the audit trail.
