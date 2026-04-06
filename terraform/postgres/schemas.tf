# PostgreSQL Database Schemas and Users
# Creates production and staging databases for FastAPI backend
# This is analogous to terraform/mysql/rds-schemas.tf but for PostgreSQL

# Generate random passwords for database users
resource "random_password" "production_password" {
  length  = 32
  special = false
}

resource "random_password" "staging_password" {
  length  = 32
  special = false
}

resource "random_password" "backups_password" {
  length  = 32
  special = false
}

# Create PostGIS extension in the default postgres database
# This must be done before creating other databases that will use PostGIS
resource "postgresql_extension" "postgis_default" {
  name     = "postgis"
  database = "postgres"
}

# Create production schema
resource "postgresql_database" "production" {
  name  = "tuk_production"
  owner = "postgres"

  depends_on = [postgresql_extension.postgis_default]
}

# Enable PostGIS extension in production database
resource "postgresql_extension" "postgis_production" {
  name     = "postgis"
  database = postgresql_database.production.name
}

# Enable pgvector extension in production database (for RAG vector search)
resource "postgresql_extension" "pgvector_production" {
  name     = "vector"
  database = postgresql_database.production.name

  depends_on = [postgresql_database.production]
}

# Create staging schema
resource "postgresql_database" "staging" {
  name  = "tuk_staging"
  owner = "postgres"

  depends_on = [postgresql_extension.postgis_default]
}

# Enable PostGIS extension in staging database
resource "postgresql_extension" "postgis_staging" {
  name     = "postgis"
  database = postgresql_database.staging.name
}

# Enable pgvector extension in staging database (for RAG vector search)
resource "postgresql_extension" "pgvector_staging" {
  name     = "vector"
  database = postgresql_database.staging.name

  depends_on = [postgresql_database.staging]
}

# Enable pg_cron extension - IMPORTANT LIMITATION
# ================================================
# In AWS RDS PostgreSQL, pg_cron can ONLY be enabled in ONE database per RDS instance.
# This is because:
# 1. pg_cron is loaded via shared_preload_libraries (instance-wide parameter)
# 2. The cron.database_name parameter specifies which database gets the extension
# 3. Only that ONE database can have the cron schema and functions
#
# Therefore, either production OR staging can have pg_cron, but not both.
# For production cutover, we enable it on tuk_production.
#
# The count conditional checks if var.pgcron_database_name matches the database name.

# Enable pg_cron extension in production database if configured
resource "postgresql_extension" "pgcron_production" {
  count    = var.pgcron_database_name == postgresql_database.production.name ? 1 : 0
  name     = "pg_cron"
  database = postgresql_database.production.name

  depends_on = [
    postgresql_extension.postgis_default,
    postgresql_database.production,
  ]
}

# Enable pg_cron extension in staging database if configured
resource "postgresql_extension" "pgcron_staging" {
  count    = var.pgcron_database_name == postgresql_database.staging.name ? 1 : 0
  name     = "pg_cron"
  database = postgresql_database.staging.name

  depends_on = [
    postgresql_extension.postgis_default,
    postgresql_database.staging,
  ]
}

# Grant permissions on the cron schema for the application user
resource "postgresql_grant" "production_cron_schema_usage" {
  count       = var.pgcron_database_name == postgresql_database.production.name ? 1 : 0
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "cron"
  object_type = "schema"
  privileges  = ["USAGE"]
  depends_on  = [postgresql_extension.pgcron_production]
}

resource "postgresql_grant" "production_cron_job_table" {
  count       = var.pgcron_database_name == postgresql_database.production.name ? 1 : 0
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "cron"
  object_type = "table"
  objects     = ["job", "job_run_details"]
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE"]
  depends_on  = [postgresql_extension.pgcron_production]
}

resource "postgresql_grant" "staging_cron_schema_usage" {
  count       = var.pgcron_database_name == postgresql_database.staging.name ? 1 : 0
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "cron"
  object_type = "schema"
  privileges  = ["USAGE"]
  depends_on  = [postgresql_extension.pgcron_staging]
}

resource "postgresql_grant" "staging_cron_job_table" {
  count       = var.pgcron_database_name == postgresql_database.staging.name ? 1 : 0
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "cron"
  object_type = "table"
  objects     = ["job", "job_run_details"]
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE"]
  depends_on  = [postgresql_extension.pgcron_staging]
}

# Create production user
resource "postgresql_role" "production" {
  name     = "fastapi_production"
  login    = true
  password = random_password.production_password.result
}

# Grant full permissions to production user on production schema
resource "postgresql_grant" "production_database" {
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE", "TEMPORARY"]
}

# Grant schema privileges
resource "postgresql_grant" "production_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["CREATE", "USAGE"]
}

# Grant table privileges (for future tables)
resource "postgresql_default_privileges" "production_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "public"
  owner       = postgresql_role.production.name
  object_type = "table"
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
}

# Grant sequence privileges
resource "postgresql_default_privileges" "production_sequences" {
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "public"
  owner       = postgresql_role.production.name
  object_type = "sequence"
  privileges  = ["SELECT", "UPDATE", "USAGE"]
}

# Create staging user
resource "postgresql_role" "staging" {
  name     = "fastapi_staging"
  login    = true
  password = random_password.staging_password.result
}

# Grant full permissions to staging user on staging schema
resource "postgresql_grant" "staging_database" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE", "TEMPORARY"]
}

resource "postgresql_grant" "staging_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["CREATE", "USAGE"]
}

resource "postgresql_default_privileges" "staging_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "public"
  owner       = postgresql_role.staging.name
  object_type = "table"
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
}

resource "postgresql_default_privileges" "staging_sequences" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "public"
  owner       = postgresql_role.staging.name
  object_type = "sequence"
  privileges  = ["SELECT", "UPDATE", "USAGE"]
}

# =============================================================================
# Analytics Data Mart: dbt and Metabase roles + analytics schema
# =============================================================================

# Passwords for analytics roles
resource "random_password" "dbt_production_password" {
  length  = 32
  special = false
}

resource "random_password" "dbt_staging_password" {
  length  = 32
  special = false
}

resource "random_password" "metabase_production_password" {
  length  = 32
  special = false
}

resource "random_password" "metabase_staging_password" {
  length  = 32
  special = false
}

# dbt roles: read public, write analytics
resource "postgresql_role" "dbt_production" {
  name     = "dbt_production"
  login    = true
  password = random_password.dbt_production_password.result
}

resource "postgresql_role" "dbt_staging" {
  name     = "dbt_staging"
  login    = true
  password = random_password.dbt_staging_password.result
}

# Metabase roles: read analytics only
resource "postgresql_role" "metabase_production" {
  name     = "metabase_production"
  login    = true
  password = random_password.metabase_production_password.result
}

resource "postgresql_role" "metabase_staging" {
  name     = "metabase_staging"
  login    = true
  password = random_password.metabase_staging_password.result
}

# Analytics schema in production (owned by dbt_production)
resource "postgresql_schema" "analytics_production" {
  name     = "analytics"
  database = postgresql_database.production.name
  owner    = postgresql_role.dbt_production.name

  depends_on = [
    postgresql_grant.dbt_production_database,
  ]
}

# Analytics schema in staging (owned by dbt_staging)
resource "postgresql_schema" "analytics_staging" {
  name     = "analytics"
  database = postgresql_database.staging.name
  owner    = postgresql_role.dbt_staging.name

  depends_on = [
    postgresql_grant.dbt_staging_database,
  ]
}

# --- dbt production grants ---

resource "postgresql_grant" "dbt_production_database" {
  database    = postgresql_database.production.name
  role        = postgresql_role.dbt_production.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "dbt_production_public_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.dbt_production.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE"]
}

resource "postgresql_grant" "dbt_production_public_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.dbt_production.name
  schema      = "public"
  object_type = "table"
  objects     = []
  privileges  = ["SELECT"]
}

resource "postgresql_grant" "dbt_production_analytics_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.dbt_production.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["CREATE", "USAGE"]

  depends_on = [postgresql_schema.analytics_production]
}

# Default privileges: tables created by dbt_production in analytics grant SELECT to metabase and backups
resource "postgresql_default_privileges" "dbt_production_analytics_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.dbt_production.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_production.name
  object_type = "table"
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]

  depends_on = [postgresql_schema.analytics_production]
}

resource "postgresql_default_privileges" "metabase_production_analytics_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.metabase_production.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_production.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_production]
}

resource "postgresql_default_privileges" "backups_production_analytics_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.backups.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_production.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_production]
}

# --- FastAPI production grants on analytics schema (read-only) ---

resource "postgresql_grant" "production_analytics_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_production]
}

resource "postgresql_default_privileges" "production_analytics_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.production.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_production.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_production]
}

# --- dbt staging grants ---

resource "postgresql_grant" "dbt_staging_database" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.dbt_staging.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "dbt_staging_public_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.dbt_staging.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE"]
}

resource "postgresql_grant" "dbt_staging_public_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.dbt_staging.name
  schema      = "public"
  object_type = "table"
  objects     = []
  privileges  = ["SELECT"]
}

resource "postgresql_grant" "dbt_staging_analytics_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.dbt_staging.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["CREATE", "USAGE"]

  depends_on = [postgresql_schema.analytics_staging]
}

resource "postgresql_default_privileges" "dbt_staging_analytics_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.dbt_staging.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_staging.name
  object_type = "table"
  privileges  = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]

  depends_on = [postgresql_schema.analytics_staging]
}

resource "postgresql_default_privileges" "metabase_staging_analytics_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.metabase_staging.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_staging.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_staging]
}

resource "postgresql_default_privileges" "backups_staging_analytics_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.backups.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_staging.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_staging]
}

# --- FastAPI staging grants on analytics schema (read-only) ---

resource "postgresql_grant" "staging_analytics_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_staging]
}

resource "postgresql_default_privileges" "staging_analytics_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.staging.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_staging.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_staging]
}

# --- Metabase production grants ---

resource "postgresql_grant" "metabase_production_database" {
  database    = postgresql_database.production.name
  role        = postgresql_role.metabase_production.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "metabase_production_analytics_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.metabase_production.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_production]
}

# --- Metabase staging grants ---

resource "postgresql_grant" "metabase_staging_database" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.metabase_staging.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "metabase_staging_analytics_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.metabase_staging.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_staging]
}

# --- Backups user: analytics schema read access ---

resource "postgresql_grant" "backups_production_analytics_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.backups.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_production]
}

resource "postgresql_grant" "backups_staging_analytics_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.backups.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_staging]
}

# =============================================================================
# Backups user (read-only access to public schema)
# =============================================================================

# Create backups user (read-only access)
resource "postgresql_role" "backups" {
  name     = "backups"
  login    = true
  password = random_password.backups_password.result
}

# Grant SELECT permissions to backups user on production schema
resource "postgresql_grant" "backups_production_database" {
  database    = postgresql_database.production.name
  role        = postgresql_role.backups.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "backups_production_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.backups.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE"]
}

resource "postgresql_default_privileges" "backups_production_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.backups.name
  schema      = "public"
  owner       = postgresql_role.production.name
  object_type = "table"
  privileges  = ["SELECT"]
}

# Grant SELECT permissions to backups user on staging schema
resource "postgresql_grant" "backups_staging_database" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.backups.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "backups_staging_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.backups.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE"]
}

resource "postgresql_default_privileges" "backups_staging_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.backups.name
  schema      = "public"
  owner       = postgresql_role.staging.name
  object_type = "table"
  privileges  = ["SELECT"]
}

# ============================================================================
# Metabase metadata database
# Metabase stores its own internal state (questions, dashboards, settings) in
# a dedicated database. Using PostgreSQL instead of the default H2 prevents
# data loss when the ECS task restarts.
# ============================================================================

resource "postgresql_database" "metabase" {
  name  = "metabase"
  owner = "postgres"
}

# Grant metabase roles full access to the metabase metadata database
resource "postgresql_grant" "metabase_production_metabase_db" {
  database    = postgresql_database.metabase.name
  role        = postgresql_role.metabase_production.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE"]
}

resource "postgresql_grant" "metabase_staging_metabase_db" {
  database    = postgresql_database.metabase.name
  role        = postgresql_role.metabase_staging.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE"]
}

resource "postgresql_grant" "metabase_production_metabase_public_schema" {
  database    = postgresql_database.metabase.name
  role        = postgresql_role.metabase_production.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE", "CREATE"]
}

resource "postgresql_grant" "metabase_staging_metabase_public_schema" {
  database    = postgresql_database.metabase.name
  role        = postgresql_role.metabase_staging.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE", "CREATE"]
}

# =============================================================================
# Hasura GraphQL engine
# Hasura auto-generates a GraphQL API over the analytics schema for third-party
# developers. It stores its own metadata in a dedicated database.
# =============================================================================

resource "random_password" "hasura_production_password" {
  length  = 32
  special = false
}

resource "random_password" "hasura_staging_password" {
  length  = 32
  special = false
}

# Hasura roles: read analytics schema, write own metadata database
resource "postgresql_role" "hasura_production" {
  name     = "hasura_production"
  login    = true
  password = random_password.hasura_production_password.result
}

resource "postgresql_role" "hasura_staging" {
  name     = "hasura_staging"
  login    = true
  password = random_password.hasura_staging_password.result
}

# --- Hasura production grants on analytics schema (read-only) ---

resource "postgresql_grant" "hasura_production_database" {
  database    = postgresql_database.production.name
  role        = postgresql_role.hasura_production.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "hasura_production_analytics_schema" {
  database    = postgresql_database.production.name
  role        = postgresql_role.hasura_production.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_production]
}

resource "postgresql_default_privileges" "hasura_production_analytics_tables" {
  database    = postgresql_database.production.name
  role        = postgresql_role.hasura_production.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_production.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_production]
}

# --- Hasura staging grants on analytics schema (read-only) ---

resource "postgresql_grant" "hasura_staging_database" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.hasura_staging.name
  object_type = "database"
  privileges  = ["CONNECT"]
}

resource "postgresql_grant" "hasura_staging_analytics_schema" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.hasura_staging.name
  schema      = "analytics"
  object_type = "schema"
  privileges  = ["USAGE"]

  depends_on = [postgresql_schema.analytics_staging]
}

resource "postgresql_default_privileges" "hasura_staging_analytics_tables" {
  database    = postgresql_database.staging.name
  role        = postgresql_role.hasura_staging.name
  schema      = "analytics"
  owner       = postgresql_role.dbt_staging.name
  object_type = "table"
  privileges  = ["SELECT"]

  depends_on = [postgresql_schema.analytics_staging]
}

# --- Hasura metadata database ---

resource "postgresql_database" "hasura" {
  name  = "hasura"
  owner = "postgres"
}

resource "postgresql_grant" "hasura_production_hasura_db" {
  database    = postgresql_database.hasura.name
  role        = postgresql_role.hasura_production.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE"]
}

resource "postgresql_grant" "hasura_staging_hasura_db" {
  database    = postgresql_database.hasura.name
  role        = postgresql_role.hasura_staging.name
  object_type = "database"
  privileges  = ["CONNECT", "CREATE"]
}

resource "postgresql_grant" "hasura_production_hasura_public_schema" {
  database    = postgresql_database.hasura.name
  role        = postgresql_role.hasura_production.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE", "CREATE"]
}

resource "postgresql_grant" "hasura_staging_hasura_public_schema" {
  database    = postgresql_database.hasura.name
  role        = postgresql_role.hasura_staging.name
  schema      = "public"
  object_type = "schema"
  privileges  = ["USAGE", "CREATE"]
}

