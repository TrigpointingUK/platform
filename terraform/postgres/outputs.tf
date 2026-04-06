output "production_credentials_arn" {
  description = "ARN of the production PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.production_credentials.arn
  sensitive   = true
}

output "staging_credentials_arn" {
  description = "ARN of the staging PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.staging_credentials.arn
  sensitive   = true
}

output "backups_credentials_arn" {
  description = "ARN of the backups PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.backups_credentials.arn
  sensitive   = true
}

output "production_database_name" {
  description = "Production database name"
  value       = postgresql_database.production.name
}

output "staging_database_name" {
  description = "Staging database name"
  value       = postgresql_database.staging.name
}

output "dbt_production_credentials_arn" {
  description = "ARN of the dbt production PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.dbt_production_credentials.arn
  sensitive   = true
}

output "dbt_staging_credentials_arn" {
  description = "ARN of the dbt staging PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.dbt_staging_credentials.arn
  sensitive   = true
}

output "metabase_production_credentials_arn" {
  description = "ARN of the Metabase production PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.metabase_production_credentials.arn
  sensitive   = true
}

output "metabase_staging_credentials_arn" {
  description = "ARN of the Metabase staging PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.metabase_staging_credentials.arn
  sensitive   = true
}

output "hasura_production_credentials_arn" {
  description = "ARN of the Hasura production PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.hasura_production_credentials.arn
  sensitive   = true
}

output "hasura_staging_credentials_arn" {
  description = "ARN of the Hasura staging PostgreSQL credentials secret"
  value       = aws_secretsmanager_secret.hasura_staging_credentials.arn
  sensitive   = true
}

