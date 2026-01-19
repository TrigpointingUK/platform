# CloudWatch Log Group for phpBB
resource "aws_cloudwatch_log_group" "phpbb" {
  name              = "/aws/ecs/${var.project_name}-phpbb-${var.environment}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-phpbb-${var.environment}-logs"
  }
}

# ECS Task Definition for phpBB with EFS volumes
resource "aws_ecs_task_definition" "phpbb" {
  family                   = "${var.project_name}-phpbb-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn
  enable_fault_injection   = false
  volume {
    name                = "phpbb-efs"
    configure_at_launch = false
    efs_volume_configuration {
      file_system_id     = var.efs_file_system_id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.efs_access_point_id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-phpbb"
      image = var.image_uri
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "PHPBB_DB_HOST"
          value = var.db_host
        },
        {
          name  = "PHPBB_DB_NAME"
          value = var.db_name
        },
        {
          name  = "PHPBB_DB_USER"
          value = var.db_user
        },
        {
          name  = "PHPBB_TABLE_PREFIX"
          value = var.table_prefix
        }
      ]
      secrets = [
        {
          name      = "PHPBB_DB_PASS"
          valueFrom = "${var.db_credentials_arn}:password::"
        },
        {
          name      = "AUTH0_DOMAIN"
          valueFrom = "${var.phpbb_secrets_arn}:AUTH0_DOMAIN::"
        },
        {
          name      = "AUTH0_CLIENT_ID"
          valueFrom = "${var.phpbb_secrets_arn}:AUTH0_CLIENT_ID::"
        },
        {
          name      = "AUTH0_CLIENT_SECRET"
          valueFrom = "${var.phpbb_secrets_arn}:AUTH0_CLIENT_SECRET::"
        },
        {
          name      = "AUTH0_GROUPS_CLAIM"
          valueFrom = "${var.phpbb_secrets_arn}:AUTH0_GROUPS_CLAIM::"
        },
        {
          name      = "AUTH0_GROUP_MAP_JSON"
          valueFrom = "${var.phpbb_secrets_arn}:AUTH0_GROUP_MAP_JSON::"
        }
      ]
      mountPoints = [
        {
          sourceVolume  = "phpbb-efs"
          containerPath = "/mnt/phpbb"
          readOnly      = false
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.phpbb.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-phpbb-${var.environment}-task-definition"
  }
}

# ECS Service for phpBB
resource "aws_ecs_service" "phpbb" {
  name                   = "${var.project_name}-phpbb-${var.environment}"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.phpbb.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "${var.project_name}-phpbb"
    container_port   = 80
  }

  tags = {
    Name = "${var.project_name}-phpbb-${var.environment}-service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "phpbb" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.phpbb.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "phpbb_cpu" {
  name               = "${var.project_name}-phpbb-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.phpbb.resource_id
  scalable_dimension = aws_appautoscaling_target.phpbb.scalable_dimension
  service_namespace  = aws_appautoscaling_target.phpbb.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto Scaling Policy - Memory (commented out to reduce CloudWatch costs)
# resource "aws_appautoscaling_policy" "phpbb_memory" {
#   name               = "${var.project_name}-phpbb-${var.environment}-memory-scaling"
#   policy_type        = "TargetTrackingScaling"
#   resource_id        = aws_appautoscaling_target.phpbb.resource_id
#   scalable_dimension = aws_appautoscaling_target.phpbb.scalable_dimension
#   service_namespace  = aws_appautoscaling_target.phpbb.service_namespace
#
#   target_tracking_scaling_policy_configuration {
#     predefined_metric_specification {
#       predefined_metric_type = "ECSServiceAverageMemoryUtilization"
#     }
#     target_value       = var.memory_target_value
#     scale_in_cooldown  = 300
#     scale_out_cooldown = 60
#   }
# }
