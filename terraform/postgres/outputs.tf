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

