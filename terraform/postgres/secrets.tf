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

