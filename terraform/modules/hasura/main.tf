# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "hasura" {
  name              = "/aws/ecs/${var.project_name}-hasura-${var.environment}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-hasura-${var.environment}-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "hasura" {
  family                   = "${var.project_name}-hasura-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-hasura"
      image = "hasura/graphql-engine:v2.44.0-ce"
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "HASURA_GRAPHQL_METADATA_DATABASE_URL", value = var.metadata_database_url },
        { name = "HASURA_GRAPHQL_DATABASE_URL", value = var.database_url },
        { name = "HASURA_GRAPHQL_ADMIN_SECRET", value = var.admin_secret },
        { name = "HASURA_GRAPHQL_JWT_SECRET", value = var.jwt_secret },
        { name = "HASURA_GRAPHQL_UNAUTHORIZED_ROLE", value = "anonymous" },
        { name = "HASURA_GRAPHQL_ENABLE_CONSOLE", value = "true" },
        { name = "HASURA_GRAPHQL_ENABLE_TELEMETRY", value = "false" },
        { name = "HASURA_GRAPHQL_DEV_MODE", value = "false" },
        { name = "HASURA_GRAPHQL_LOG_LEVEL", value = "info" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.hasura.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 60
      }
      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-hasura-${var.environment}-task-definition"
  }
}

# ECS Service
resource "aws_ecs_service" "hasura" {
  name            = "${var.project_name}-hasura-${var.environment}"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.hasura.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "${var.project_name}-hasura"
    container_port   = 8080
  }

  tags = {
    Name = "${var.project_name}-hasura-${var.environment}-service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "hasura" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.hasura.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "hasura_cpu" {
  name               = "${var.project_name}-hasura-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.hasura.resource_id
  scalable_dimension = aws_appautoscaling_target.hasura.scalable_dimension
  service_namespace  = aws_appautoscaling_target.hasura.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
