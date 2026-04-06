output "service_name" {
  description = "Name of the Hasura ECS service"
  value       = aws_ecs_service.hasura.name
}

output "task_definition_arn" {
  description = "ARN of the Hasura task definition"
  value       = aws_ecs_task_definition.hasura.arn
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.hasura.name
}
