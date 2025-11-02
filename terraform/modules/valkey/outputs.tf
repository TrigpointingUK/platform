output "valkey_endpoint" {
  description = "Valkey endpoint for service discovery"
  value       = "valkey.trigpointing.local"
}

output "valkey_port" {
  description = "Valkey port"
  value       = 6379
}

output "valkey_commander_target_group_arn" {
  description = "Target group ARN for Redis Commander"
  value       = aws_lb_target_group.valkey_commander.arn
}

output "valkey_service_name" {
  description = "ECS service name for Valkey"
  value       = aws_ecs_service.valkey.name
}

output "valkey_task_definition_arn" {
  description = "Task definition ARN for Valkey"
  value       = aws_ecs_task_definition.valkey.arn
}

output "efs_file_system_id" {
  description = "EFS file system ID for Valkey data"
  value       = aws_efs_file_system.valkey.id
}

output "efs_access_point_id" {
  description = "EFS access point ID for Valkey"
  value       = aws_efs_access_point.valkey.id
}
