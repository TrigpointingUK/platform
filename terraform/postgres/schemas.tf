# PostgreSQL Database Schemas and Users
# Creates production and staging databases for FastAPI backend
# This is analogous to terraform/mysql/rds-schemas.tf but for PostgreSQL

# Generate random passwords for database users
resource "random_password" "production_password" {
  length  = 32
  special = true
}

resource "random_password" "staging_password" {
  length  = 32
  special = true
}

resource "random_password" "backups_password" {
  length  = 32
  special = true
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

