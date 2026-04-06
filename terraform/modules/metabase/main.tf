# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "metabase" {
  name              = "/aws/ecs/${var.project_name}-metabase-${var.environment}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-metabase-${var.environment}-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "metabase" {
  family                   = "${var.project_name}-metabase-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-metabase"
      image = "metabase/metabase:latest"
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "MB_DB_TYPE", value = "postgres" },
        { name = "MB_DB_HOST", value = var.mb_db_host },
        { name = "MB_DB_PORT", value = tostring(var.mb_db_port) },
        { name = "MB_DB_DBNAME", value = var.mb_db_dbname },
        { name = "MB_DB_USER", value = var.mb_db_user },
        { name = "MB_DB_PASS", value = var.mb_db_pass },
        { name = "JAVA_TIMEZONE", value = var.java_timezone },
        { name = "MB_EMOJI_IN_LOGS", value = "false" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.metabase.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:3000/api/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 120
      }
      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-metabase-${var.environment}-task-definition"
  }
}

# ECS Service
resource "aws_ecs_service" "metabase" {
  name            = "${var.project_name}-metabase-${var.environment}"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.metabase.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "${var.project_name}-metabase"
    container_port   = 3000
  }

  tags = {
    Name = "${var.project_name}-metabase-${var.environment}-service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "metabase" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.metabase.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "metabase_cpu" {
  name               = "${var.project_name}-metabase-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.metabase.resource_id
  scalable_dimension = aws_appautoscaling_target.metabase.scalable_dimension
  service_namespace  = aws_appautoscaling_target.metabase.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
