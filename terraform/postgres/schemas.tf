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

