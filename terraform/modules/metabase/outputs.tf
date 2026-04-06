output "service_name" {
  description = "Name of the Metabase ECS service"
  value       = aws_ecs_service.metabase.name
}

output "task_definition_arn" {
  description = "ARN of the Metabase task definition"
  value       = aws_ecs_task_definition.metabase.arn
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.metabase.name
}
