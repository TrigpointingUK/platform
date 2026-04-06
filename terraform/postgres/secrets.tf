# AWS Secrets Manager entries for PostgreSQL database credentials
# Stores credentials for FastAPI backend to access PostgreSQL

# Production user credentials
resource "aws_secretsmanager_secret" "production_credentials" {
  name                    = "fastapi-production-postgres-credentials"
  description             = "PostgreSQL production user credentials for FastAPI backend"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-production-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "production_credentials" {
  secret_id = aws_secretsmanager_secret.production_credentials.id
  secret_string = jsonencode({
    username             = "fastapi_production"
    password             = random_password.production_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_production"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# Staging user credentials
resource "aws_secretsmanager_secret" "staging_credentials" {
  name                    = "fastapi-staging-postgres-credentials"
  description             = "PostgreSQL staging user credentials for FastAPI backend"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-staging-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "staging_credentials" {
  secret_id = aws_secretsmanager_secret.staging_credentials.id
  secret_string = jsonencode({
    username             = "fastapi_staging"
    password             = random_password.staging_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_staging"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# dbt production credentials (analytics data mart)
resource "aws_secretsmanager_secret" "dbt_production_credentials" {
  name                    = "dbt-production-postgres-credentials"
  description             = "PostgreSQL dbt production user credentials for analytics data mart"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-dbt-production-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "dbt_production_credentials" {
  secret_id = aws_secretsmanager_secret.dbt_production_credentials.id
  secret_string = jsonencode({
    username             = "dbt_production"
    password             = random_password.dbt_production_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_production"
    schema               = "analytics"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# dbt staging credentials (analytics data mart)
resource "aws_secretsmanager_secret" "dbt_staging_credentials" {
  name                    = "dbt-staging-postgres-credentials"
  description             = "PostgreSQL dbt staging user credentials for analytics data mart"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-dbt-staging-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "dbt_staging_credentials" {
  secret_id = aws_secretsmanager_secret.dbt_staging_credentials.id
  secret_string = jsonencode({
    username             = "dbt_staging"
    password             = random_password.dbt_staging_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_staging"
    schema               = "analytics"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# Backups user credentials
resource "aws_secretsmanager_secret" "backups_credentials" {
  name                    = "trigpointing-postgres-backups-credentials"
  description             = "PostgreSQL backups user credentials (read-only)"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-backups-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "backups_credentials" {
  secret_id = aws_secretsmanager_secret.backups_credentials.id
  secret_string = jsonencode({
    username             = "backups"
    password             = random_password.backups_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_production" # Backups user has access to both schemas
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# Metabase production credentials (analytics read + metadata write)
resource "aws_secretsmanager_secret" "metabase_production_credentials" {
  name                    = "metabase-production-postgres-credentials"
  description             = "PostgreSQL Metabase production user credentials"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-metabase-production-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "metabase_production_credentials" {
  secret_id = aws_secretsmanager_secret.metabase_production_credentials.id
  secret_string = jsonencode({
    username             = "metabase_production"
    password             = random_password.metabase_production_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_production"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# Metabase staging credentials (analytics read + metadata write)
resource "aws_secretsmanager_secret" "metabase_staging_credentials" {
  name                    = "metabase-staging-postgres-credentials"
  description             = "PostgreSQL Metabase staging user credentials"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-metabase-staging-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "metabase_staging_credentials" {
  secret_id = aws_secretsmanager_secret.metabase_staging_credentials.id
  secret_string = jsonencode({
    username             = "metabase_staging"
    password             = random_password.metabase_staging_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_staging"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# Hasura production credentials (analytics read + metadata write)
resource "aws_secretsmanager_secret" "hasura_production_credentials" {
  name                    = "hasura-production-postgres-credentials"
  description             = "PostgreSQL Hasura production user credentials for GraphQL API"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-hasura-production-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "hasura_production_credentials" {
  secret_id = aws_secretsmanager_secret.hasura_production_credentials.id
  secret_string = jsonencode({
    username             = "hasura_production"
    password             = random_password.hasura_production_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_production"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

# Hasura staging credentials (analytics read + metadata write)
resource "aws_secretsmanager_secret" "hasura_staging_credentials" {
  name                    = "hasura-staging-postgres-credentials"
  description             = "PostgreSQL Hasura staging user credentials for GraphQL API"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-postgres-hasura-staging-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "hasura_staging_credentials" {
  secret_id = aws_secretsmanager_secret.hasura_staging_credentials.id
  secret_string = jsonencode({
    username             = "hasura_staging"
    password             = random_password.hasura_staging_password.result
    engine               = "postgres"
    host                 = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
    port                 = data.terraform_remote_state.common.outputs.postgres_rds_port
    dbname               = "tuk_staging"
    dbInstanceIdentifier = data.terraform_remote_state.common.outputs.postgres_rds_identifier
  })
}

