output "service_name" {
  description = "Name of the pgAdmin ECS service"
  value       = aws_ecs_service.pgadmin.name
}

output "task_definition_arn" {
  description = "ARN of the pgAdmin task definition"
  value       = aws_ecs_task_definition.pgadmin.arn
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.pgadmin.name
}

